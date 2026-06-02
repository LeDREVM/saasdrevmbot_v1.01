"""
==============================================================================
 NY SESSION BOT — Moteur pilotable (US30 + USDJPY, session New York)
==============================================================================

 Version refactorée du bot full-auto pour être PILOTÉE par une interface :
 la boucle de trading tourne dans un thread, l'état est exposé via snapshot()
 et les commandes (start/stop, DRY_RUN, profil, kill switch, fermeture) sont
 thread-safe.

 La logique de scoring vient de `trading_ny_session.classify_setup`
 (ta Trading Bible). Les détecteurs techniques restent des heuristiques de
 départ, à caler sur ta définition exacte.

 ⚠️  TRADING RÉEL = ARGENT RÉEL. DRY_RUN=True par défaut (aucun ordre envoyé).
     Sans MetaTrader5 installé, le moteur bascule en mode SIMULATION (faux
     marché) pour pouvoir tester l'interface.
==============================================================================
"""

from __future__ import annotations

import os
import threading
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

# --- Backend de marché : MT5 réel, sinon simulateur (mode démo) --------------
try:
    import MetaTrader5 as mt5  # type: ignore
    SIMULATE = False
except ImportError:
    import sim_mt5 as mt5       # façade compatible mt5
    SIMULATE = True

# --- Trading Bible (source de vérité du scoring) -----------------------------
try:
    from app.services.trading_ny_session import (  # type: ignore
        MarketContext, HTFPhase, FibZone, classify_setup, build_journal_entry,
    )
except ImportError:
    from trading_ny_session import (  # placeholder local
        MarketContext, HTFPhase, FibZone, classify_setup, build_journal_entry,
    )


# ============================================================================
# CONFIGURATION
# ============================================================================

MT5_LOGIN: int | None = None
MT5_PASSWORD: str | None = None
MT5_SERVER: str | None = None

KILL_SWITCH_FILE = "STOP.flag"
MAGIC = 770077

TZ_NY = ZoneInfo("America/New_York")
NY_SESSION_START = (9, 30)
NY_SESSION_END = (16, 0)

PROFILES = {
    "SCALPING": dict(risk_pct=0.5, min_grade="A",  rr_target=2.0,
                     max_trades_per_symbol=3, max_daily_dd_pct=3.0, move_sl_to_be_at_r=1.0),
    "BALANCED": dict(risk_pct=1.0, min_grade="A",  rr_target=2.5,
                     max_trades_per_symbol=2, max_daily_dd_pct=4.0, move_sl_to_be_at_r=1.0),
    "CONSERVATIVE": dict(risk_pct=0.5, min_grade="A+", rr_target=3.0,
                         max_trades_per_symbol=1, max_daily_dd_pct=2.0, move_sl_to_be_at_r=1.0),
    "AGGRESSIVE": dict(risk_pct=1.5, min_grade="B",  rr_target=2.0,
                       max_trades_per_symbol=4, max_daily_dd_pct=5.0, move_sl_to_be_at_r=1.0),
}
DEFAULT_PROFILE = "SCALPING"

SYMBOLS = {
    "US30":   dict(mt5_symbol="US30",   max_spread_points=50, sl_atr_mult=1.5),
    "USDJPY": dict(mt5_symbol="USDJPY", max_spread_points=20, sl_atr_mult=1.5),
}

POLL_SECONDS = 15
ONE_POSITION_PER_SYMBOL = True
CLOSE_AT_SESSION_END = True
NEWS_BLACKOUTS: list[tuple[datetime, datetime]] = []

_GRADE_RANK = {"C": 0, "B": 1, "A": 2, "A+": 3}


# ============================================================================
# LOGGING + buffer mémoire (consommé par l'interface)
# ============================================================================

class RingLogHandler(logging.Handler):
    """Conserve les derniers logs en mémoire, indexés, pour l'API."""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self._buf: deque = deque(maxlen=capacity)
        self._idx = 0
        self._lock = threading.Lock()

    def emit(self, record):
        with self._lock:
            self._buf.append({
                "i": self._idx,
                "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
                "level": record.levelname,
                "msg": self.format(record),
            })
            self._idx += 1

    def since(self, after_index: int = -1):
        with self._lock:
            return [r for r in self._buf if r["i"] > after_index]


log = logging.getLogger("ny_bot")
log.setLevel(logging.INFO)
_ring = RingLogHandler()
_ring.setFormatter(logging.Formatter("%(message)s"))
if not any(isinstance(h, RingLogHandler) for h in log.handlers):
    _stream = logging.StreamHandler()
    _stream.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
    log.addHandler(_stream)
    log.addHandler(_ring)
    try:
        _fh = logging.FileHandler("ny_session_bot.log", encoding="utf-8")
        _fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
        log.addHandler(_fh)
    except OSError:
        pass


# ============================================================================
# DÉTECTEURS TECHNIQUES (heuristiques — à caler sur la Bible)
# ============================================================================

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> float:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def swing_levels(df: pd.DataFrame, left: int = 2, right: int = 2):
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(left, len(df) - right):
        if h[i] == max(h[i - left:i + right + 1]):
            highs.append(h[i])
        if l[i] == min(l[i - left:i + right + 1]):
            lows.append(l[i])
    return highs, lows


def detect_h4(df_h4: pd.DataFrame):
    close = df_h4["close"]
    ema21, ema50 = ema(close, 21), ema(close, 50)
    price = float(close.iloc[-1])
    slope = float(ema50.iloc[-1] - ema50.iloc[-5])
    rng_hi = float(df_h4["high"].iloc[-30:].max())
    rng_lo = float(df_h4["low"].iloc[-30:].min())
    width = (rng_hi - rng_lo) or 1e-9
    pos = (price - rng_lo) / width
    if ema21.iloc[-1] > ema50.iloc[-1] and slope > 0 and price > ema50.iloc[-1]:
        return HTFPhase.MARKUP, "up"
    if ema21.iloc[-1] < ema50.iloc[-1] and slope < 0 and price < ema50.iloc[-1]:
        return HTFPhase.MARKDOWN, "down"
    return (HTFPhase.ACCUMULATION, "range") if pos < 0.5 else (HTFPhase.DISTRIBUTION, "range")


def detect_m15_fib(df_m15: pd.DataFrame, trend: str):
    hi = float(df_m15["high"].iloc[-40:].max())
    lo = float(df_m15["low"].iloc[-40:].min())
    price = float(df_m15["close"].iloc[-1])
    rng = (hi - lo) or 1e-9
    retr = (hi - price) / rng if trend != "down" else (price - lo) / rng
    if retr < 0.45:
        return FibZone.SHALLOW
    if retr < 0.66:
        return FibZone.EQUILIBRIUM
    if retr < 0.76:
        return FibZone.SNIPER
    return FibZone.DEEP


def detect_m15_logical_zone(df_m15: pd.DataFrame) -> bool:
    close = df_m15["close"]
    price = float(close.iloc[-1])
    kijun = (df_m15["high"].rolling(26).max() + df_m15["low"].rolling(26).min()) / 2
    ema50 = ema(close, 50)
    a = atr(df_m15)
    near_kijun = abs(price - float(kijun.iloc[-1])) <= a
    near_ema = abs(price - float(ema50.iloc[-1])) <= a
    return bool(near_kijun or near_ema)


def detect_m5_sweep_and_bos(df_m5: pd.DataFrame):
    highs, lows = swing_levels(df_m5, 2, 2)
    if len(highs) < 2 or len(lows) < 2:
        return None, None
    prior_high, prior_low = highs[-2], lows[-2]
    recent = df_m5.iloc[-5:]
    last_close = float(df_m5["close"].iloc[-1])
    swept = None
    if (recent["high"] > prior_high).any() and last_close < prior_high:
        swept = "high"
    elif (recent["low"] < prior_low).any() and last_close > prior_low:
        swept = "low"
    bos = None
    if last_close > highs[-1]:
        bos = "up"
    elif last_close < lows[-1]:
        bos = "down"
    return swept, bos


def get_rates(symbol: str, timeframe: int, n: int) -> pd.DataFrame | None:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None or len(rates) == 0:
        log.warning("Pas de données pour %s tf=%s", symbol, timeframe)
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def build_context(symbol_cfg: dict):
    s = symbol_cfg["mt5_symbol"]
    df_h4 = get_rates(s, mt5.TIMEFRAME_H4, 120)
    df_m15 = get_rates(s, mt5.TIMEFRAME_M15, 120)
    df_m5 = get_rates(s, mt5.TIMEFRAME_M5, 120)
    if df_h4 is None or df_m15 is None or df_m5 is None:
        return None, None, None
    phase, trend = detect_h4(df_h4)
    fib = detect_m15_fib(df_m15, trend)
    logical = detect_m15_logical_zone(df_m15)
    swept, bos = detect_m5_sweep_and_bos(df_m5)
    ctx = MarketContext(
        h4_phase=phase, h4_trend=trend, m15_fib_zone=fib,
        m15_is_logical_zone=logical, swept_liquidity_side_m5=swept, m5_bos_direction=bos,
    )
    return ctx, df_m5, atr(df_m5)


# ============================================================================
# ÉTAT JOURNALIER
# ============================================================================

@dataclass
class DailyState:
    day: str = ""
    start_equity: float = 0.0
    halted: bool = False
    trades: dict = field(default_factory=dict)

    def reset(self, equity: float, day: str):
        self.day, self.start_equity, self.halted = day, equity, False
        self.trades = {s: 0 for s in SYMBOLS}


# ============================================================================
# MOTEUR PILOTABLE
# ============================================================================

class BotEngine:
    def __init__(self):
        self.profile_name = DEFAULT_PROFILE
        self.dry_run = True
        self.kill_switch = os.path.exists(KILL_SWITCH_FILE)
        self.simulate = SIMULATE

        self.state = DailyState()
        self.signals: deque = deque(maxlen=100)

        self.running = False
        self.connected = False
        self.session_open = False
        self.last_error: str | None = None
        self.last_update: str | None = None

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._mt5_lock = threading.RLock()   # sérialise tous les accès marché
        self._state_lock = threading.RLock()

    # ── helpers ───────────────────────────────────────────────────────────
    @property
    def profile(self) -> dict:
        return PROFILES[self.profile_name]

    def _my_positions(self, symbol: str | None = None):
        with self._mt5_lock:
            allp = mt5.positions_get() or []
        out = [p for p in allp if getattr(p, "magic", MAGIC) == MAGIC]
        if symbol:
            out = [p for p in out if p.symbol == symbol]
        return out

    # ── connexion ─────────────────────────────────────────────────────────
    def _connect(self) -> bool:
        with self._mt5_lock:
            ok = (mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
                  if MT5_LOGIN else mt5.initialize())
            if not ok:
                self.last_error = f"Échec init MT5 : {mt5.last_error()}"
                log.error(self.last_error)
                return False
            acc = mt5.account_info()
            for cfg in SYMBOLS.values():
                mt5.symbol_select(cfg["mt5_symbol"], True)
        self.connected = True
        log.info("MT5 connecté%s | compte=%s | solde=%.2f %s | levier=1:%s",
                 " (SIMULATION)" if self.simulate else "", acc.login, acc.balance,
                 acc.currency, acc.leverage)
        return True

    # ── exécution ─────────────────────────────────────────────────────────
    def _calc_lot(self, symbol: str, sl_distance_price: float, risk_pct: float) -> float:
        info = mt5.symbol_info(symbol)
        acc = mt5.account_info()
        risk_money = acc.balance * risk_pct / 100.0
        ticks = sl_distance_price / info.trade_tick_size
        loss_per_lot = ticks * info.trade_tick_value
        if loss_per_lot <= 0:
            return 0.0
        lots = risk_money / loss_per_lot
        step = info.volume_step
        lots = max(info.volume_min, min(info.volume_max, round(lots / step) * step))
        return round(lots, 2)

    def _open_trade(self, symbol: str, direction: str, atr_val: float, cfg: dict):
        with self._mt5_lock:
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            profile = self.profile
            sl_dist = atr_val * cfg["sl_atr_mult"]
            if direction == "up":
                entry, sl = tick.ask, tick.ask - sl_dist
                tp = entry + sl_dist * profile["rr_target"]
                order_type = mt5.ORDER_TYPE_BUY
            else:
                entry, sl = tick.bid, tick.bid + sl_dist
                tp = entry - sl_dist * profile["rr_target"]
                order_type = mt5.ORDER_TYPE_SELL

            lots = self._calc_lot(symbol, sl_dist, profile["risk_pct"])
            if lots <= 0:
                log.warning("[%s] Lot calculé = 0, ordre annulé.", symbol)
                return None

            log.info("[%s] SIGNAL %s | entry=%.5f SL=%.5f TP=%.5f lots=%.2f R:R=%.1f",
                     symbol, direction.upper(), entry, sl, tp, lots, profile["rr_target"])
            order = dict(symbol=symbol, direction=direction, entry=round(entry, info.digits),
                         sl=round(sl, info.digits), tp=round(tp, info.digits), lots=lots,
                         rr=profile["rr_target"])

            if self.dry_run:
                log.info("[%s] DRY_RUN → aucun ordre réel envoyé.", symbol)
                return {**order, "dry_run": True}

            request = {
                "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lots,
                "type": order_type, "price": entry, "sl": round(sl, info.digits),
                "tp": round(tp, info.digits), "deviation": 20, "magic": MAGIC,
                "comment": "NY_SESSION_BOT", "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                log.error("[%s] Ordre REFUSÉ : retcode=%s comment=%s",
                          symbol, result.retcode, result.comment)
                return None
            log.info("[%s] ✅ Ordre exécuté | ticket=%s prix=%.5f",
                     symbol, result.order, result.price)
            return {**order, "ticket": result.order, "dry_run": False}

    def _manage_open_positions(self):
        if self.dry_run:
            return
        r_at_be = self.profile["move_sl_to_be_at_r"]
        for pos in self._my_positions():
            with self._mt5_lock:
                tick = mt5.symbol_info_tick(pos.symbol)
                r_dist = abs(pos.price_open - pos.sl)
                if r_dist <= 0:
                    continue
                if pos.type == mt5.POSITION_TYPE_BUY:
                    in_profit_r = (tick.bid - pos.price_open) / r_dist
                    if in_profit_r >= r_at_be and pos.sl < pos.price_open:
                        self._modify_sl(pos, pos.price_open)
                else:
                    in_profit_r = (pos.price_open - tick.ask) / r_dist
                    if in_profit_r >= r_at_be and pos.sl > pos.price_open:
                        self._modify_sl(pos, pos.price_open)

    def _modify_sl(self, pos, new_sl: float):
        info = mt5.symbol_info(pos.symbol)
        mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket,
                        "sl": round(new_sl, info.digits), "tp": pos.tp})
        log.info("[%s] SL → break-even (ticket %s)", pos.symbol, pos.ticket)

    def close_all_positions(self, reason: str = "manuel") -> int:
        """Ferme toutes les positions du bot. Renvoie le nombre fermé."""
        closed = 0
        for pos in self._my_positions():
            with self._mt5_lock:
                if self.dry_run:
                    closed += 1
                    log.info("[%s] DRY_RUN → fermeture simulée (%s)", pos.symbol, reason)
                    continue
                tick = mt5.symbol_info_tick(pos.symbol)
                otype = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                res = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": pos.volume,
                    "type": otype, "position": pos.ticket, "price": price, "deviation": 20,
                    "magic": MAGIC, "comment": f"close:{reason}",
                    "type_filling": mt5.ORDER_FILLING_IOC,
                })
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    closed += 1
                    log.info("[%s] Position fermée (%s)", pos.symbol, reason)
        return closed

    def close_position(self, ticket: int) -> bool:
        for pos in self._my_positions():
            if pos.ticket != ticket:
                continue
            with self._mt5_lock:
                if self.dry_run:
                    log.info("[%s] DRY_RUN → fermeture simulée ticket %s", pos.symbol, ticket)
                    return True
                tick = mt5.symbol_info_tick(pos.symbol)
                otype = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                res = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": pos.volume,
                    "type": otype, "position": ticket, "price": price, "deviation": 20,
                    "magic": MAGIC, "comment": "close:ui", "type_filling": mt5.ORDER_FILLING_IOC,
                })
                ok = bool(res and res.retcode == mt5.TRADE_RETCODE_DONE)
                if ok:
                    log.info("[%s] Position %s fermée (UI)", pos.symbol, ticket)
                return ok
        return False

    # ── garde-fous ────────────────────────────────────────────────────────
    @staticmethod
    def _in_ny_session(now_ny: datetime) -> bool:
        if now_ny.weekday() >= 5:
            return False
        start = now_ny.replace(hour=NY_SESSION_START[0], minute=NY_SESSION_START[1], second=0, microsecond=0)
        end = now_ny.replace(hour=NY_SESSION_END[0], minute=NY_SESSION_END[1], second=0, microsecond=0)
        return start <= now_ny <= end

    def _daily_dd_breached(self) -> bool:
        with self._mt5_lock:
            equity = mt5.account_info().equity
        max_dd = self.profile["max_daily_dd_pct"]
        dd_pct = ((self.state.start_equity - equity) / self.state.start_equity * 100
                  if self.state.start_equity else 0)
        if dd_pct >= max_dd:
            if not self.state.halted:
                log.warning("🛑 Daily DD atteint (%.2f%% ≥ %.2f%%) — arrêt des entrées du jour.",
                            dd_pct, max_dd)
            return True
        return False

    def _spread_ok(self, symbol: str, max_points: int) -> bool:
        with self._mt5_lock:
            info = mt5.symbol_info(symbol)
        return info is not None and info.spread <= max_points

    # ── boucle ────────────────────────────────────────────────────────────
    def _interruptible_sleep(self, seconds: float):
        end = time.time() + seconds
        while time.time() < end and not self._stop.is_set():
            time.sleep(min(0.5, end - time.time()))

    def _loop(self):
        if not self._connect():
            self.running = False
            return
        with self._mt5_lock:
            eq = mt5.account_info().equity
        self.state.reset(eq, datetime.now(TZ_NY).strftime("%Y-%m-%d"))
        log.info("🌅 Session prête | equity départ=%.2f | profil=%s", eq, self.profile_name)
        session_was_open = False

        try:
            while not self._stop.is_set():
                now_ny = datetime.now(TZ_NY)
                now_utc = datetime.now(ZoneInfo("UTC"))
                today = now_ny.strftime("%Y-%m-%d")
                self.last_update = now_utc.isoformat(timespec="seconds")

                if today != self.state.day:
                    with self._mt5_lock:
                        eq = mt5.account_info().equity
                    self.state.reset(eq, today)
                    log.info("🌅 Nouveau jour NY %s | equity départ=%.2f", today, eq)

                self.session_open = self._in_ny_session(now_ny)
                self.kill_switch = self.kill_switch or os.path.exists(KILL_SWITCH_FILE)

                if session_was_open and not self.session_open and CLOSE_AT_SESSION_END:
                    self.close_all_positions("fin_session_NY")
                session_was_open = self.session_open

                if self.kill_switch:
                    self._interruptible_sleep(POLL_SECONDS); continue
                if not self.session_open:
                    self._interruptible_sleep(POLL_SECONDS); continue
                if any(a <= now_utc <= b for a, b in NEWS_BLACKOUTS):
                    log.info("📰 Blackout news — pas d'entrée.")
                    self._interruptible_sleep(POLL_SECONDS); continue

                self._manage_open_positions()

                if self._daily_dd_breached():
                    self.state.halted = True
                    self._interruptible_sleep(POLL_SECONDS); continue

                self._scan_symbols()
                self._interruptible_sleep(POLL_SECONDS)

        except Exception as e:  # noqa: BLE001
            self.last_error = str(e)
            log.exception("Erreur fatale de boucle : %s", e)
        finally:
            with self._mt5_lock:
                mt5.shutdown()
            self.connected = False
            self.running = False
            log.info("MT5 déconnecté. Moteur arrêté.")

    def _scan_symbols(self):
        profile = self.profile
        min_rank = _GRADE_RANK[profile["min_grade"]]
        for name, cfg in SYMBOLS.items():
            sym = cfg["mt5_symbol"]
            try:
                if ONE_POSITION_PER_SYMBOL and self._my_positions(sym):
                    continue
                if self.state.trades.get(name, 0) >= profile["max_trades_per_symbol"]:
                    continue
                if not self._spread_ok(sym, cfg["max_spread_points"]):
                    continue

                with self._mt5_lock:
                    ctx, _df, atr_val = build_context(cfg)
                if ctx is None:
                    continue

                setup = classify_setup(ctx, rr_ratio=profile["rr_target"])
                if not setup.is_valid:
                    continue
                if _GRADE_RANK[setup.grade.value] < min_rank:
                    log.info("[%s] Setup %s grade %s < %s requis — skip.",
                             name, setup.setup_type.value, setup.grade.value, profile["min_grade"])
                    continue

                direction = ctx.m5_bos_direction
                res = self._open_trade(sym, direction, atr_val, cfg)
                if res:
                    self.state.trades[name] = self.state.trades.get(name, 0) + 1
                    journal = build_journal_entry(
                        symbol=name, context=ctx, setup=setup,
                        risk_r_percent=profile["risk_pct"], result_r=None, discipline_score=None)
                    signal = {
                        "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                        "symbol": name, "direction": direction, "grade": setup.grade.value,
                        "setup_type": setup.setup_type.value, "dry_run": res.get("dry_run", True),
                        "entry": res.get("entry"), "sl": res.get("sl"), "tp": res.get("tp"),
                        "lots": res.get("lots"), "journal": journal,
                    }
                    self.signals.appendleft(signal)
                    log.info("📓 Journal: %s", journal)
            except Exception as e:  # noqa: BLE001
                log.exception("[%s] Erreur scan : %s", name, e)

    # ── contrôle (appelé par l'API) ───────────────────────────────────────
    def start(self) -> bool:
        with self._state_lock:
            if self.running:
                return False
            self._stop.clear()
            self.running = True
            self.last_error = None
            self._thread = threading.Thread(target=self._loop, name="ny-bot-loop", daemon=True)
            self._thread.start()
            log.info("▶️  Moteur démarré (profil=%s, DRY_RUN=%s)", self.profile_name, self.dry_run)
            return True

    def stop(self) -> bool:
        with self._state_lock:
            if not self.running:
                return False
            log.info("⏹️  Arrêt demandé…")
            self._stop.set()
        if self._thread:
            self._thread.join(timeout=POLL_SECONDS + 5)
        self.running = False
        return True

    def set_profile(self, name: str) -> bool:
        if name not in PROFILES:
            return False
        self.profile_name = name
        log.info("⚙️  Profil → %s", name)
        return True

    def set_dry_run(self, enabled: bool):
        self.dry_run = bool(enabled)
        log.info("⚙️  DRY_RUN → %s", self.dry_run)

    def set_kill_switch(self, active: bool):
        self.kill_switch = bool(active)
        if active:
            try:
                open(KILL_SWITCH_FILE, "w").close()
            except OSError:
                pass
            log.warning("⛔ KILL SWITCH ACTIVÉ — plus aucune entrée.")
        else:
            if os.path.exists(KILL_SWITCH_FILE):
                try:
                    os.remove(KILL_SWITCH_FILE)
                except OSError:
                    pass
            log.info("✅ Kill switch désactivé.")

    # ── lecture d'état (API) ──────────────────────────────────────────────
    def snapshot(self) -> dict:
        acc = None
        if self.connected:
            try:
                with self._mt5_lock:
                    a = mt5.account_info()
                if a:
                    dd = ((self.state.start_equity - a.equity) / self.state.start_equity * 100
                          if self.state.start_equity else 0)
                    acc = {"login": a.login, "balance": round(a.balance, 2),
                           "equity": round(a.equity, 2), "currency": a.currency,
                           "leverage": a.leverage, "start_equity": round(self.state.start_equity, 2),
                           "dd_pct": round(dd, 2)}
            except Exception:  # noqa: BLE001
                acc = None
        return {
            "running": self.running, "connected": self.connected, "simulate": self.simulate,
            "dry_run": self.dry_run, "kill_switch": self.kill_switch,
            "session_open": self.session_open, "profile": self.profile_name,
            "profiles": list(PROFILES.keys()), "profile_config": self.profile,
            "max_daily_dd_pct": self.profile["max_daily_dd_pct"],
            "daily_trades": dict(self.state.trades), "halted": self.state.halted,
            "account": acc, "symbols": list(SYMBOLS.keys()),
            "last_update": self.last_update, "last_error": self.last_error,
            "session_window": {"start": NY_SESSION_START, "end": NY_SESSION_END},
        }

    def positions(self) -> list[dict]:
        out = []
        try:
            for p in self._my_positions():
                with self._mt5_lock:
                    tick = mt5.symbol_info_tick(p.symbol)
                    info = mt5.symbol_info(p.symbol)
                px = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask
                diff = (px - p.price_open) if p.type == mt5.POSITION_TYPE_BUY else (p.price_open - px)
                pnl = diff / info.trade_tick_size * info.trade_tick_value
                out.append({
                    "ticket": p.ticket, "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": p.volume, "price_open": round(p.price_open, info.digits),
                    "price_now": round(px, info.digits), "sl": round(p.sl, info.digits),
                    "tp": round(p.tp, info.digits), "pnl": round(pnl, 2),
                })
        except Exception:  # noqa: BLE001
            pass
        return out

    def recent_logs(self, after_index: int = -1):
        return _ring.since(after_index)

    def recent_signals(self):
        return list(self.signals)


# Singleton partagé par l'API
engine = BotEngine()


if __name__ == "__main__":
    # Lancement direct (sans interface) : démarre le moteur et boucle.
    engine.start()
    try:
        while engine.running:
            time.sleep(1)
    except KeyboardInterrupt:
        engine.stop()
