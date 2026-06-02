"""
sim_mt5.py — Simulateur minimal de l'API MetaTrader5 (mode DÉMO).

Permet de faire tourner le moteur + l'interface SANS terminal MT5 :
prix en marche aléatoire, positions virtuelles, équité flottante. Couvre
uniquement la surface d'API utilisée par ny_session_bot.py.

⚠️ Ne JAMAIS utiliser en production : c'est du faux marché destiné aux tests
   d'interface et aux démonstrations.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from itertools import count


# ── Constantes (mêmes noms que MetaTrader5) ──────────────────────────────────
TIMEFRAME_H4 = 16385
TIMEFRAME_M15 = 15
TIMEFRAME_M5 = 5

ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1

TRADE_ACTION_DEAL = 1
TRADE_ACTION_SLTP = 2
ORDER_TIME_GTC = 0
ORDER_FILLING_IOC = 1
TRADE_RETCODE_DONE = 10009

_TF_SECONDS = {TIMEFRAME_H4: 4 * 3600, TIMEFRAME_M15: 15 * 60, TIMEFRAME_M5: 5 * 60}


@dataclass
class _AccountInfo:
    login: int
    balance: float
    equity: float
    currency: str
    leverage: int


@dataclass
class _SymbolInfo:
    trade_tick_size: float
    trade_tick_value: float
    volume_step: float
    volume_min: float
    volume_max: float
    point: float
    digits: int
    spread: int


@dataclass
class _Tick:
    bid: float
    ask: float


@dataclass
class _Position:
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    sl: float
    tp: float
    magic: int = 0


@dataclass
class _OrderResult:
    retcode: int
    order: int
    price: float
    comment: str = "sim"


# Spécifications par symbole (approximatives, suffisantes pour la démo).
_SPECS = {
    "US30":   dict(price=39000.0, vol=18.0, tick_size=0.1, tick_value=0.1,
                   point=0.1, digits=1, spread=20),
    "USDJPY": dict(price=156.50, vol=0.05, tick_size=0.001, tick_value=0.9,
                   point=0.001, digits=3, spread=8),
}


class SimMT5:
    def __init__(self):
        self._prices = {s: spec["price"] for s, spec in _SPECS.items()}
        self._positions: dict[int, _Position] = {}
        self._ticket = count(770078)
        self._balance = 10_000.0
        self._connected = False

    # — connexion —
    def initialize(self, **kwargs) -> bool:
        self._connected = True
        return True

    def last_error(self):
        return (0, "sim ok")

    def shutdown(self):
        self._connected = False

    def symbol_select(self, symbol, enable=True) -> bool:
        return symbol in _SPECS

    # — prix —
    def _step_price(self, symbol):
        spec = _SPECS[symbol]
        p = self._prices[symbol]
        p += random.gauss(0, spec["vol"])
        self._prices[symbol] = max(p, spec["price"] * 0.5)
        return self._prices[symbol]

    def symbol_info(self, symbol):
        spec = _SPECS.get(symbol)
        if not spec:
            return None
        return _SymbolInfo(spec["tick_size"], spec["tick_value"], 0.01, 0.01,
                           100.0, spec["point"], spec["digits"], spec["spread"])

    def symbol_info_tick(self, symbol):
        p = self._prices[symbol]
        half = _SPECS[symbol]["point"] * _SPECS[symbol]["spread"] / 2
        return _Tick(bid=round(p - half, 5), ask=round(p + half, 5))

    def copy_rates_from_pos(self, symbol, timeframe, start, n):
        """Renvoie n bougies (liste de dicts) générées en marche aléatoire."""
        spec = _SPECS[symbol]
        sec = _TF_SECONDS.get(timeframe, 300)
        now = int(time.time())
        price = self._prices[symbol]
        rows = []
        p = price
        for i in range(n):
            o = p
            c = o + random.gauss(0, spec["vol"])
            hi = max(o, c) + abs(random.gauss(0, spec["vol"] / 2))
            lo = min(o, c) - abs(random.gauss(0, spec["vol"] / 2))
            rows.append(dict(time=now - (n - i) * sec, open=round(o, 5),
                             high=round(hi, 5), low=round(lo, 5),
                             close=round(c, 5), tick_volume=random.randint(50, 500)))
            p = c
        return rows

    # — compte —
    def _floating_pnl(self):
        pnl = 0.0
        for pos in self._positions.values():
            tick = self.symbol_info_tick(pos.symbol)
            info = self.symbol_info(pos.symbol)
            px = tick.bid if pos.type == POSITION_TYPE_BUY else tick.ask
            diff = (px - pos.price_open) if pos.type == POSITION_TYPE_BUY else (pos.price_open - px)
            ticks = diff / info.trade_tick_size
            pnl += ticks * info.trade_tick_value * (pos.volume / 0.01) * 0.01
        return pnl

    def account_info(self):
        for s in self._prices:
            self._step_price(s)
        equity = self._balance + self._floating_pnl()
        return _AccountInfo(login=999999, balance=round(self._balance, 2),
                            equity=round(equity, 2), currency="USD", leverage=500)

    # — positions —
    def positions_get(self, magic=None, symbol=None):
        out = list(self._positions.values())
        if symbol:
            out = [p for p in out if p.symbol == symbol]
        if magic is not None:
            out = [p for p in out if p.magic == magic]
        return out

    # — ordres —
    def order_send(self, request):
        action = request.get("action")
        if action == TRADE_ACTION_SLTP:
            pos = self._positions.get(request.get("position"))
            if pos:
                pos.sl = request.get("sl", pos.sl)
                pos.tp = request.get("tp", pos.tp)
            return _OrderResult(TRADE_RETCODE_DONE, request.get("position", 0),
                                self._prices.get(pos.symbol, 0) if pos else 0)

        # DEAL : fermeture si 'position' présent, sinon ouverture
        if "position" in request:
            pos = self._positions.pop(request["position"], None)
            if pos:
                tick = self.symbol_info_tick(pos.symbol)
                info = self.symbol_info(pos.symbol)
                px = tick.bid if pos.type == POSITION_TYPE_BUY else tick.ask
                diff = (px - pos.price_open) if pos.type == POSITION_TYPE_BUY else (pos.price_open - px)
                self._balance += diff / info.trade_tick_size * info.trade_tick_value
            return _OrderResult(TRADE_RETCODE_DONE, request.get("position", 0),
                                request.get("price", 0))

        ticket = next(self._ticket)
        self._positions[ticket] = _Position(
            ticket=ticket, symbol=request["symbol"],
            type=POSITION_TYPE_BUY if request["type"] == ORDER_TYPE_BUY else POSITION_TYPE_SELL,
            volume=request["volume"], price_open=request["price"],
            sl=request.get("sl", 0.0), tp=request.get("tp", 0.0),
            magic=request.get("magic", 0),
        )
        return _OrderResult(TRADE_RETCODE_DONE, ticket, request["price"])


# ── Façade « module mt5 » : un singleton + fonctions délégantes ──────────────
# Permet d'écrire `import sim_mt5 as mt5` et d'utiliser mt5.account_info(), etc.
_default = SimMT5()

initialize = _default.initialize
last_error = _default.last_error
shutdown = _default.shutdown
symbol_select = _default.symbol_select
symbol_info = _default.symbol_info
symbol_info_tick = _default.symbol_info_tick
copy_rates_from_pos = _default.copy_rates_from_pos
account_info = _default.account_info
positions_get = _default.positions_get
order_send = _default.order_send
