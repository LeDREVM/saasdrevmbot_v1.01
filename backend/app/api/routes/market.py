"""
Router market data — proxy Hyperliquid (public, lecture seule).

  GET /api/market/status          → état du feed + coins suivis
  GET /api/market/candles/{coin}  → historique bufferisé (Lightweight Charts ready)
  WS  /api/market/ws              → flux temps réel des bougies

Aucune route d'exécution d'ordre ici : ce module ne fait que lire.
"""

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.services.market_data import hyperliquid_feed
from app.services.market_data.hyperliquid_feed import COINS, INTERVAL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/status")
async def status():
    """État de la connexion amont et périmètre suivi."""
    return JSONResponse(
        {
            "connected": hyperliquid_feed.connected,
            "source": "hyperliquid",
            "coins": COINS,
            "interval": INTERVAL,
            "buffered": {coin: len(hyperliquid_feed.get_candles(coin)) for coin in COINS},
        }
    )


@router.get("/candles/{coin}")
async def candles(coin: str):
    """Historique bufferisé d'un coin, du plus ancien au plus récent."""
    coin = coin.upper()
    if coin not in COINS:
        raise HTTPException(status_code=404, detail=f"Coin non suivi: {coin}. Suivis: {COINS}")
    data = hyperliquid_feed.get_candles(coin)
    return JSONResponse({"coin": coin, "interval": INTERVAL, "count": len(data), "candles": data})


@router.websocket("/ws")
async def stream(websocket: WebSocket):
    """
    Flux temps réel de toutes les bougies suivies.

    Le client filtre par `coin` côté frontend — une seule socket suffit pour
    les 3 actifs.
    """
    await websocket.accept()
    queue = hyperliquid_feed.subscribe()
    try:
        while True:
            candle = await queue.get()
            await websocket.send_json(candle)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Client websocket fermé: %s", exc)
    finally:
        hyperliquid_feed.unsubscribe(queue)
