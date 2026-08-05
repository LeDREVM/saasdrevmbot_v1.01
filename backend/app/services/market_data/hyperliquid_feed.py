"""
Hyperliquid market data feed.

Keeps ONE upstream websocket to Hyperliquid open for the whole backend, buffers
the last N candles per coin in memory, and fans out live updates to every
connected dashboard client.

Why a single upstream connection: N browser tabs must not open N sockets to
Hyperliquid. The backend is the only subscriber; clients read from a local
broadcast queue.

Public data only — no API key, no auth, no order placement here.
"""

import asyncio
import json
import logging
import time
from collections import deque
from typing import Optional

import httpx
import websockets

logger = logging.getLogger(__name__)

WS_URL = "wss://api.hyperliquid.xyz/ws"
INFO_URL = "https://api.hyperliquid.xyz/info"

# Hyperliquid uses bare asset names ("BTC"), not pairs ("BTCUSD").
COINS = ["BTC", "ETH", "SOL"]
INTERVAL = "5m"

# Ring buffer depth per coin. 500 x 5m ~= 41h of history, enough for HTF context.
MAX_CANDLES = 500

# Hyperliquid closes idle connections; keep it warm well under that.
PING_INTERVAL = 30.0

# Reconnect backoff bounds (seconds).
BACKOFF_START = 1.0
BACKOFF_MAX = 60.0

# Per-client queue depth. A client that cannot keep up drops updates rather
# than growing the buffer without bound.
CLIENT_QUEUE_SIZE = 100


def _normalize(raw: dict) -> dict:
    """
    Convert a Hyperliquid candle into the shape Lightweight Charts expects.

    Hyperliquid sends OHLCV as strings and timestamps in milliseconds;
    Lightweight Charts wants numbers and seconds.
    """
    return {
        "coin": raw["s"],
        "interval": raw["i"],
        "time": int(raw["t"]) // 1000,
        "open": float(raw["o"]),
        "high": float(raw["h"]),
        "low": float(raw["l"]),
        "close": float(raw["c"]),
        "volume": float(raw["v"]),
        # Hyperliquid stamps every tick of the forming candle with the same "t"
        # and only advances "T" (close time). A candle is final once now >= T.
        "closed": int(time.time() * 1000) >= int(raw["T"]),
    }


class HyperliquidFeed:
    """Single upstream websocket + in-memory candle buffers + client fan-out."""

    def __init__(self) -> None:
        self._candles: dict[str, deque] = {coin: deque(maxlen=MAX_CANDLES) for coin in COINS}
        self._clients: set[asyncio.Queue] = set()
        self._task: Optional[asyncio.Task] = None
        self._connected = False

    # ---------------------------------------------------------------- lifecycle

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._load_history()
        self._task = asyncio.create_task(self._run(), name="hyperliquid-feed")
        logger.info("📡 Hyperliquid feed started (%s @ %s)", ", ".join(COINS), INTERVAL)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self._connected = False
        logger.info("📡 Hyperliquid feed stopped")

    # ------------------------------------------------------------------ readers

    @property
    def connected(self) -> bool:
        return self._connected

    def get_candles(self, coin: str) -> list[dict]:
        """Buffered history for a coin, oldest first. Empty list if unknown coin."""
        return list(self._candles.get(coin, ()))

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._clients.discard(queue)

    # ------------------------------------------------------------------ internals

    async def _load_history(self) -> None:
        """Seed the buffers over REST so a chart opens populated, not empty."""
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - MAX_CANDLES * 5 * 60 * 1000

        async with httpx.AsyncClient(timeout=15.0) as client:
            for coin in COINS:
                try:
                    resp = await client.post(
                        INFO_URL,
                        json={
                            "type": "candleSnapshot",
                            "req": {
                                "coin": coin,
                                "interval": INTERVAL,
                                "startTime": start_ms,
                                "endTime": end_ms,
                            },
                        },
                    )
                    resp.raise_for_status()
                    for raw in resp.json():
                        self._candles[coin].append(_normalize(raw))
                    logger.info("📥 %s: %d historical candles", coin, len(self._candles[coin]))
                except Exception as exc:
                    # A failed snapshot is not fatal: the websocket will refill
                    # the buffer as candles close.
                    logger.warning("⚠️  History fetch failed for %s: %s", coin, exc)

    async def _run(self) -> None:
        """Connect, subscribe, consume. Reconnect forever with backoff."""
        backoff = BACKOFF_START
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=None) as ws:
                    await self._subscribe_all(ws)
                    self._connected = True
                    backoff = BACKOFF_START
                    logger.info("✅ Hyperliquid websocket connected")

                    pinger = asyncio.create_task(self._ping_loop(ws))
                    try:
                        async for message in ws:
                            self._handle(message)
                    finally:
                        pinger.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("🔌 Hyperliquid websocket lost (%s), retry in %.0fs", exc, backoff)
            finally:
                self._connected = False

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    async def _subscribe_all(self, ws) -> None:
        for coin in COINS:
            await ws.send(
                json.dumps(
                    {
                        "method": "subscribe",
                        "subscription": {"type": "candle", "coin": coin, "interval": INTERVAL},
                    }
                )
            )

    async def _ping_loop(self, ws) -> None:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await ws.send(json.dumps({"method": "ping"}))

    def _handle(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return

        if payload.get("channel") != "candle":
            return

        data = payload.get("data")
        # The docs describe Candle[]; the live feed sends a single object.
        # Accept both so a server-side format change does not blind the feed.
        for raw in data if isinstance(data, list) else [data]:
            try:
                candle = _normalize(raw)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("⚠️  Malformed candle dropped: %s", exc)
                continue
            self._store(candle)
            self._broadcast(candle)

    def _store(self, candle: dict) -> None:
        buffer = self._candles.get(candle["coin"])
        if buffer is None:
            return
        # Same timestamp = the candle is still forming, replace it in place.
        # New timestamp = a candle closed, append.
        if buffer and buffer[-1]["time"] == candle["time"]:
            buffer[-1] = candle
        else:
            buffer.append(candle)

    def _broadcast(self, candle: dict) -> None:
        for queue in list(self._clients):
            try:
                queue.put_nowait(candle)
            except asyncio.QueueFull:
                # Slow client: drop this tick rather than stall the whole feed.
                pass


hyperliquid_feed = HyperliquidFeed()
