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

import json
import math
import os
import random
import threading
import time
import logging
import urllib.parse
import urllib.request
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
    SIMULATE = False

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

# Identifiants du compte MT5 (production, VPS Windows). Fournis via l'ENVIRONNEMENT
# (.env non committé, ou secrets NSSM) — JAMAIS en clair dans le code. Laisser vide
# pour se brancher sur le terminal MT5 déjà ouvert et loggé manuellement
# (mt5.initialize() sans identifiants).
def _env_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw.isdigit() else None


MT5_LOGIN: int | None = _env_int("MT5_LOGIN")
MT5_PASSWORD: str | None = os.environ.get("MT5_PASSWORD") or None
MT5_SERVER: str | None = os.environ.get("MT5_SERVER") or None

# Kill-switch : chemin ABSOLU (ancré sur ce dossier, indépendant du cwd du
# service NSSM/systemd) — surchargeable via l'env. Créer ce fichier stoppe
# toute nouvelle entrée, boucle auto ET chemin API.
KILL_SWITCH_FILE = os.environ.get("KILL_SWITCH_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "STOP.flag")
# Persistance de l'état journalier (baseline drawdown, halt, compteurs) —
# survit aux restarts pour que le halt DD du jour ne soit pas réinitialisable.
STATE_FILE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "daily_state.json")
MAGIC = 770077

# Alertes Telegram (section 8) — facultatif : définir les variables d'env
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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
DEFAULT_PROFILE = os.environ.get("BOT_PROFILE", "SCALPING").upper()
if DEFAULT_PROFILE not in PROFILES:
    DEFAULT_PROFILE = "SCALPING"

SYMBOLS = {
    "US30":   dict(mt5_symbol="US30",   max_spread_points=50, sl_atr_mult=1.5),
    "USDJPY": dict(mt5_symbol="USDJPY", max_spread_points=20, sl_atr_mult=1.5),
}

POLL_SECONDS = 15
ONE_POSITION_PER_SYMBOL = True
CLOSE_AT_SESSION_END = True
# Démo : injecte parfois un setup en SIMULATION pour exercer l'UI (jamais en MT5 réel)
DEMO_SIGNALS = os.environ.get("DEMO_SIGNALS", "1") != "0"
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


# ============================================================================
# ALERTES TELEGRAM (section 8)
# ============================================================================

def _telegram_send(text: str):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML",
        }).encode()
        urllib.request.urlopen(url, data=data, timeout=8)  # noqa: S310
    except Exception as e:  # noqa: BLE001
        log.warning("Telegram échec: %s", e)


def notify_telegram(text: str):
    """Envoi non bloquant (thread détaché) pour ne pas ralentir la boucle."""
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return
    threading.Thread(target=_telegram_send, args=(text,), daemon=True).start()


def _demo_context():
    """Contexte de démonstration (SIMULATION) : smart signal valide, confluence
    variable pour produire différents grades. Jamais utilisé en MT5 réel."""
    up = random.random() < 0.5
    bias_ok = random.random() < 0.7
    return MarketContext(
        h4_bias=("BULLISH" if up else "BEARISH") if bias_ok else ("BEARISH" if up else "BULLISH"),
        m15_zone_touched=random.random() < 0.7,
        m5_trigger=(("BUY_TRIGGER" if up else "SELL_TRIGGER") if random.random() < 0.7 else None),
        rsi_divergence=("BULLISH" if up else "BEARISH"),
        wyckoff=("SPRING" if up else "UTAD"),
        price_above_kijun=up,
    )


# ── Moteurs Smart Money (RSI / Ichimoku / Wyckoff / biais / zone / trigger) ──

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI de Wilder (sans dépendance externe)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - 100 / (1 + rs)


def get_bias_h4(df_h4: pd.DataFrame) -> str:
    """Biais H4 (section 2) : close actuel vs close il y a 20 bougies."""
    return "BULLISH" if df_h4["close"].iloc[-1] > df_h4["close"].iloc[-20] else "BEARISH"


def zone_touched_m15(df_m15: pd.DataFrame) -> bool:
    """Zone de liquidité M15 (section 2) : prix sur l'extrême du range 30 bougies."""
    high = float(df_m15["high"].rolling(30).max().iloc[-1])
    low = float(df_m15["low"].rolling(30).min().iloc[-1])
    price = float(df_m15["close"].iloc[-1])
    a = atr(df_m15)
    return bool(abs(price - high) <= a or abs(price - low) <= a)


def entry_trigger_m5(df_m5: pd.DataFrame):
    """Déclencheur M5 (section 2) : bougie haussière/baissière."""
    last = float(df_m5["close"].iloc[-1])
    prev = float(df_m5["close"].iloc[-2])
    if last > prev:
        return "BUY_TRIGGER"
    if last < prev:
        return "SELL_TRIGGER"
    return None


def detect_wyckoff(df: pd.DataFrame):
    """
    Wyckoff Spring / UTAD (section 3) — version corrigée du snippet PDF :
    Spring = mèche sous le plus-bas swing(20) mais clôture au-dessus (faux cassure).
    UTAD   = mèche au-dessus du plus-haut swing(20) mais clôture en dessous.
    """
    prior_high = float(df["high"].rolling(20).max().iloc[-2])
    prior_low = float(df["low"].rolling(20).min().iloc[-2])
    last = df.iloc[-1]
    if float(last["low"]) < prior_low and float(last["close"]) > prior_low:
        return "SPRING"
    if float(last["high"]) > prior_high and float(last["close"]) < prior_high:
        return "UTAD"
    return None


def detect_divergence(df: pd.DataFrame):
    """RSI divergence (section 4) : compare prix et RSI sur ~10 bougies."""
    r = rsi(df["close"])
    p1, p2 = float(df["close"].iloc[-10]), float(df["close"].iloc[-1])
    r1, r2 = float(r.iloc[-10]), float(r.iloc[-1])
    if p2 < p1 and r2 > r1:
        return "BULLISH"
    if p2 > p1 and r2 < r1:
        return "BEARISH"
    return None


def price_above_kijun(df: pd.DataFrame, period: int = 26) -> bool:
    """Filtre Ichimoku (section 5) : prix au-dessus de la Kijun."""
    kijun = (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2
    return float(df["close"].iloc[-1]) > float(kijun.iloc[-1])


def detect_fvg(df: pd.DataFrame, scan: int = 20) -> dict:
    """
    Fair Value Gap (imbalance 3 bougies) façon `ICT_RSI_Wyckoff.pine` :
      • FVG haussier : low[i]  > high[i-2]  (vide au-dessus de la bougie i-2)
      • FVG baissier : high[i] < low[i-2]   (vide en dessous de la bougie i-2)

    Renvoie le FVG le plus récent encore « frais » (non comblé par une clôture
    ultérieure). `price_in_gap` = le prix est revenu tester le gap (mitigation).
    """
    if df is None or len(df) < 3:
        return {"direction": None, "top": None, "bottom": None,
                "bars_ago": None, "price_in_gap": False, "fresh": False}
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    n = len(df)
    last_close = float(closes[-1])
    stop = max(2, n - scan)
    for i in range(n - 1, stop - 1, -1):
        if lows[i] > highs[i - 2]:                       # haussier
            top, bottom = float(lows[i]), float(highs[i - 2])
            fresh = not any(closes[j] < bottom for j in range(i + 1, n))
            if fresh:
                return {"direction": "BULLISH", "top": round(top, 5),
                        "bottom": round(bottom, 5), "bars_ago": (n - 1) - i,
                        "price_in_gap": bottom <= last_close <= top, "fresh": True}
        if highs[i] < lows[i - 2]:                        # baissier
            top, bottom = float(lows[i - 2]), float(highs[i])
            fresh = not any(closes[j] > top for j in range(i + 1, n))
            if fresh:
                return {"direction": "BEARISH", "top": round(top, 5),
                        "bottom": round(bottom, 5), "bars_ago": (n - 1) - i,
                        "price_in_gap": bottom <= last_close <= top, "fresh": True}
    return {"direction": None, "top": None, "bottom": None,
            "bars_ago": None, "price_in_gap": False, "fresh": False}


# Barème de confluence du scan (les 3 piliers Wyckoff/FVG/Ichimoku pèsent le plus).
CONFLUENCE_WEIGHTS = {
    "wyckoff": 3, "fvg": 3, "ichimoku": 2,
    "fvg_mitigation": 1, "divergence": 1, "bias": 1,
}
CONFLUENCE_MAX = sum(CONFLUENCE_WEIGHTS.values())   # 11


def score_confluence(ctx, fvg: dict, direction: str | None) -> dict:
    """
    Note la confluence Wyckoff + FVG + Ichimoku (+ divergence, biais, mitigation)
    dans le sens `direction` ("up"/"down"). Lecture seule : sert au panneau de
    scan, sans toucher à la décision de trade (`classify_setup`).
    """
    # Direction candidate si le smart signal n'a rien tranché.
    if direction not in ("up", "down"):
        if ctx.wyckoff == "SPRING" or fvg.get("direction") == "BULLISH":
            direction = "up"
        elif ctx.wyckoff == "UTAD" or fvg.get("direction") == "BEARISH":
            direction = "down"
    want_bull = direction == "up"

    items = {
        "wyckoff": (ctx.wyckoff == "SPRING") if want_bull else (ctx.wyckoff == "UTAD"),
        "fvg": (fvg.get("direction") == "BULLISH") if want_bull else (fvg.get("direction") == "BEARISH"),
        "ichimoku": ctx.price_above_kijun if want_bull else (not ctx.price_above_kijun),
        "fvg_mitigation": bool(fvg.get("price_in_gap")) and (
            (fvg.get("direction") == "BULLISH") if want_bull else (fvg.get("direction") == "BEARISH")),
        "divergence": (ctx.rsi_divergence == "BULLISH") if want_bull else (ctx.rsi_divergence == "BEARISH"),
        "bias": (ctx.h4_bias == "BULLISH") if want_bull else (ctx.h4_bias == "BEARISH"),
    }
    points = sum(CONFLUENCE_WEIGHTS[k] for k, ok in items.items() if ok)
    return {
        "direction": direction, "points": points, "max": CONFLUENCE_MAX,
        "items": items, "weights": CONFLUENCE_WEIGHTS,
        "pillars_aligned": items["wyckoff"] and items["fvg"] and items["ichimoku"],
    }


# Fournisseur de prix optionnel (cascade multi-source, cf. api.py). Signature :
#   provider(symbol, timeframe, n) -> DataFrame | None
# S'il renvoie des bougies, elles priment sur MT5 ; sinon on retombe sur MT5/sim.
last_price_source: dict = {}
_price_provider = None


def set_price_provider(fn):
    global _price_provider
    _price_provider = fn


def get_rates(symbol: str, timeframe: int, n: int) -> pd.DataFrame | None:
    """Bougies CLÔTURÉES uniquement (invariant no-repaint) : la dernière bougie
    des deux sources (position 0 MT5 / dernière ligne provider) est celle EN
    FORMATION — on demande n+1 bougies et on l'exclut systématiquement."""
    if _price_provider is not None:
        try:
            pdf = _price_provider(symbol, timeframe, n + 1)
        except Exception:  # noqa: BLE001
            log.exception("price provider error (%s tf=%s)", symbol, timeframe)
            pdf = None
        if pdf is not None and len(pdf) > 1:
            return pdf.iloc[:-1].reset_index(drop=True)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n + 1)
    if rates is None or len(rates) < 2:
        log.warning("Pas de données pour %s tf=%s", symbol, timeframe)
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.iloc[:-1].reset_index(drop=True)  # exclut la bougie en formation
    if timeframe == mt5.TIMEFRAME_M5:
        last_price_source[symbol] = "sim" if SIMULATE else "mt5"
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
        h4_phase=phase, h4_trend=trend, h4_bias=get_bias_h4(df_h4),
        m15_fib_zone=fib, m15_is_logical_zone=logical,
        m15_zone_touched=zone_touched_m15(df_m15),
        m5_trigger=entry_trigger_m5(df_m5), m5_bos_direction=bos,
        swept_liquidity_side_m5=swept,
        rsi_divergence=detect_divergence(df_m5),
        wyckoff=detect_wyckoff(df_m5),
        price_above_kijun=price_above_kijun(df_m5),
    )
    return ctx, df_m5, atr(df_m5)


# ============================================================================
# ÉTAT JOURNALIER
# ============================================================================

@dataclass
class DailyState:
    day: str = ""
    start_equity: float = 0.0
    start_balance: float = 0.0
    halted: bool = False
    trades: dict = field(default_factory=dict)

    def reset(self, equity: float, day: str, balance: float | None = None):
        self.day, self.start_equity, self.halted = day, equity, False
        self.start_balance = balance if balance is not None else equity
        self.trades = {s: 0 for s in SYMBOLS}


# ============================================================================
# MOTEUR PILOTABLE
# ============================================================================

class BotEngine:
    def __init__(self):
        self.profile_name = DEFAULT_PROFILE
        # DRY_RUN par défaut = True (aucun ordre réel envoyé). Mettre DRY_RUN=0
        # dans l'environnement (VPS/NSSM) pour armer l'exécution LIVE full-auto.
        self.dry_run = os.environ.get("DRY_RUN", "1") != "0"
        self.kill_switch = os.path.exists(KILL_SWITCH_FILE)
        self.simulate = SIMULATE
        self.telegram = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

        self.state = DailyState()
        self._last_scan_bar: dict = {}  # gating new-bar : dernière M5 clôturée évaluée
        self._load_state()              # restaure baseline DD/halt/compteurs du jour
        self.signals: deque = deque(maxlen=100)
        self.closed_trades: deque = deque(maxlen=200)
        self.equity_history: deque = deque(maxlen=720)  # ~ courbe d'équité
        self._last_eq_sample = 0.0

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
        if info is None or acc is None or info.trade_tick_size <= 0:
            log.warning("[%s] symbol/account_info indisponible — lot=0.", symbol)
            return 0.0
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
        # Garde ATR : un NaN passe `not atr_val` (not nan == False) et produirait
        # entry/SL/TP/lots NaN envoyés au broker (audit P1-3).
        if atr_val is None or not math.isfinite(atr_val) or atr_val <= 0:
            log.warning("[%s] ATR invalide (%s) — ordre annulé.", symbol, atr_val)
            return None
        with self._mt5_lock:
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                log.warning("[%s] symbol_info/tick indisponible — ordre annulé.", symbol)
                return None
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
            if result is None:
                log.error("[%s] order_send → None (connexion perdue ?)", symbol)
                return None
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
                if tick is None:
                    continue
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
        if info is None:
            return
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
                if tick is None:
                    log.warning("[%s] tick indisponible — fermeture reportée.", pos.symbol)
                    continue
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
                    self._record_closed(pos, price, reason)
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
                if tick is None:
                    return False
                otype = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                res = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": pos.volume,
                    "type": otype, "position": ticket, "price": price, "deviation": 20,
                    "magic": MAGIC, "comment": "close:ui", "type_filling": mt5.ORDER_FILLING_IOC,
                })
                ok = bool(res and res.retcode == mt5.TRADE_RETCODE_DONE)
                if ok:
                    self._record_closed(pos, price, "ui")
                    log.info("[%s] Position %s fermée (UI)", pos.symbol, ticket)
                return ok
        return False

    def execute_signal(self, name: str, direction: str, source: str = "api") -> dict:
        """
        Exécute un signal externe (ex : orchestrateur n8n) sur un symbole.
        LECTURE DES GARDE-FOUS : kill switch, halt (DD), une position/symbole,
        max trades/jour, DRY_RUN (respecté par `_open_trade`). Renvoie un dict
        {ok, reason?, order?}. N'envoie un ordre RÉEL que si DRY_RUN est OFF.
        """
        cfg = SYMBOLS.get(name)
        if cfg is None:
            return {"ok": False, "reason": f"symbole inconnu : {name}"}
        if direction not in ("up", "down"):
            return {"ok": False, "reason": "direction invalide (up/down)"}
        # Kill-switch : relire le DISQUE à chaque appel — la boucle peut être
        # arrêtée, l'attribut mémoire seul ne suffit pas (audit P0-2).
        if self.kill_switch or os.path.exists(KILL_SWITCH_FILE):
            self.kill_switch = True
            return {"ok": False, "reason": "kill switch actif (STOP.flag)"}
        # Halt drawdown : baseline garantie pour aujourd'hui + check réel,
        # même boucle arrêtée / après restart (audit P0-3).
        reason = self._ensure_daily_state()
        if reason:
            return {"ok": False, "reason": reason}
        if self.state.halted or self._daily_dd_breached():
            if not self.state.halted:
                self.state.halted = True
                self._save_state()
            return {"ok": False, "reason": "entrées stoppées (drawdown journalier)"}

        sym = cfg["mt5_symbol"]
        profile = self.profile
        with self._mt5_lock:
            if ONE_POSITION_PER_SYMBOL and self._my_positions(sym):
                return {"ok": False, "reason": "position déjà ouverte sur ce symbole"}
            if self.state.trades.get(name, 0) >= profile["max_trades_per_symbol"]:
                return {"ok": False, "reason": "max trades/jour atteint pour ce symbole"}
            if not self._spread_ok(sym, cfg["max_spread_points"]):
                return {"ok": False, "reason": "spread trop large"}
            ctx, _df, atr_val = build_context(cfg)

        if atr_val is None or not math.isfinite(atr_val) or atr_val <= 0:
            return {"ok": False, "reason": "pas de données de marché / ATR indisponible"}

        res = self._open_trade(sym, direction, atr_val, cfg)
        if not res:
            return {"ok": False, "reason": "ordre refusé (lot=0 ou rejet broker)"}

        self.state.trades[name] = self.state.trades.get(name, 0) + 1
        self._save_state()
        signal = {
            "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
            "symbol": name, "direction": direction, "grade": "—",
            "setup_type": f"exec:{source}", "dry_run": res.get("dry_run", True),
            "entry": res.get("entry"), "sl": res.get("sl"), "tp": res.get("tp"),
            "lots": res.get("lots"), "demo": False, "journal": {"source": source},
        }
        self.signals.appendleft(signal)
        log.info("🎯 EXÉCUTION %s %s (%s) | %s", name, direction.upper(), source,
                 "DRY RUN" if res.get("dry_run") else "LIVE")
        notify_telegram(
            f"🎯 <b>EXÉCUTION {name}</b> ({source})\n"
            f"{'🟢 BUY' if direction == 'up' else '🔴 SELL'} · "
            f"{'DRY RUN' if res.get('dry_run') else 'LIVE'}\n"
            f"entrée {res.get('entry')} | SL {res.get('sl')} | TP {res.get('tp')} | "
            f"lots {res.get('lots')}"
        )
        return {"ok": True, "order": res, "dry_run": res.get("dry_run", True)}

    def _record_closed(self, pos, exit_px: float, reason: str):
        """Enregistre un trade fermé avec son PnL réalisé (pour les stats)."""
        try:
            info = mt5.symbol_info(pos.symbol)
            if info is None:
                return
            diff = (exit_px - pos.price_open) if pos.type == mt5.POSITION_TYPE_BUY else (pos.price_open - exit_px)
            pnl = diff / info.trade_tick_size * info.trade_tick_value * pos.volume
            self.closed_trades.appendleft({
                "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": pos.volume, "entry": round(pos.price_open, info.digits),
                "exit": round(exit_px, info.digits), "pnl": round(pnl, 2), "reason": reason,
            })
        except Exception:  # noqa: BLE001
            pass

    # ── garde-fous ────────────────────────────────────────────────────────
    @staticmethod
    def _in_ny_session(now_ny: datetime) -> bool:
        if now_ny.weekday() >= 5:
            return False
        start = now_ny.replace(hour=NY_SESSION_START[0], minute=NY_SESSION_START[1], second=0, microsecond=0)
        end = now_ny.replace(hour=NY_SESSION_END[0], minute=NY_SESSION_END[1], second=0, microsecond=0)
        return start <= now_ny <= end

    # ── état journalier persistant (baseline DD, halt, compteurs) ─────────
    def _save_state(self):
        try:
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"day": self.state.day, "start_equity": self.state.start_equity,
                           "start_balance": self.state.start_balance,
                           "halted": self.state.halted, "trades": self.state.trades}, fh)
            os.replace(tmp, STATE_FILE)
        except OSError:
            log.exception("écriture de %s impossible", STATE_FILE)

    def _load_state(self):
        """Restaure l'état du jour après un restart — un redémarrage ne doit
        JAMAIS remettre à zéro la baseline drawdown ni lever un halt."""
        try:
            with open(STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return
        if data.get("day") != datetime.now(TZ_NY).strftime("%Y-%m-%d"):
            return  # état d'un autre jour : ignoré, la baseline sera recréée
        self.state.day = data["day"]
        self.state.start_equity = float(data.get("start_equity") or 0)
        self.state.start_balance = float(data.get("start_balance") or 0)
        self.state.halted = bool(data.get("halted"))
        self.state.trades = {k: int(v) for k, v in (data.get("trades") or {}).items()}
        log.info("État journalier restauré (%s) : start_equity=%.2f halted=%s trades=%s",
                 self.state.day, self.state.start_equity, self.state.halted,
                 self.state.trades)

    def _ensure_daily_state(self) -> str | None:
        """Garantit une baseline DD valide pour AUJOURD'HUI, même boucle arrêtée
        (chemin API). Renvoie un motif de refus, ou None si l'état est prêt."""
        today = datetime.now(TZ_NY).strftime("%Y-%m-%d")
        if self.state.day == today and self.state.start_equity > 0:
            return None
        with self._mt5_lock:
            acc = mt5.account_info()
            if acc is None:
                if not mt5.initialize():
                    return "état journalier indisponible (MT5 non connecté)"
                acc = mt5.account_info()
                if acc is None:
                    return "état journalier indisponible (MT5 non connecté)"
        if self.state.day != today:
            self.state.reset(acc.equity, today, acc.balance)
            log.info("🌅 Baseline journalière initialisée (hors boucle) : equity=%.2f",
                     acc.equity)
        else:  # jour déjà bon mais baseline absente
            self.state.start_equity = acc.equity
            self.state.start_balance = acc.balance
        self._save_state()
        return None

    def _daily_dd_breached(self) -> bool:
        with self._mt5_lock:
            acc = mt5.account_info()
        if acc is None:  # déconnexion : ne pas crasher la boucle (cf. audit P1)
            log.warning("account_info() indisponible — check DD impossible ce cycle.")
            return False
        equity = acc.equity
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

    def _reconnect(self) -> bool:
        """Rétablit la connexion MT5 (terminal redémarré, coupure réseau) —
        la boucle ne doit plus mourir sur une déconnexion (audit P1-4)."""
        with self._mt5_lock:
            try:
                mt5.shutdown()
            except Exception:  # noqa: BLE001
                pass
            ok = (mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
                  if MT5_LOGIN else mt5.initialize())
        self.connected = bool(ok)
        if ok:
            log.info("🔌 MT5 reconnecté.")
        else:
            log.warning("Reconnexion MT5 échouée : %s", mt5.last_error())
        return bool(ok)

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
            acc = mt5.account_info()
        today = datetime.now(TZ_NY).strftime("%Y-%m-%d")
        # Ne PAS écraser un état déjà établi aujourd'hui (restauré du disque) :
        # un restart ne doit jamais remettre la baseline DD à zéro ni lever
        # un halt (audit P0-3).
        if self.state.day != today or self.state.start_equity <= 0:
            self.state.reset(acc.equity, today, acc.balance)
            self._save_state()
        else:
            log.info("État journalier conservé (restart) : start_equity=%.2f halted=%s",
                     self.state.start_equity, self.state.halted)
        self.sample_equity(force=True)
        log.info("🌅 Session prête | equity départ=%.2f | profil=%s",
                 self.state.start_equity, self.profile_name)
        session_was_open = False

        try:
            while not self._stop.is_set():
                # Résilience (audit P1-4) : une exception dans UNE itération ne
                # tue plus la boucle — log, tentative de reconnexion, on continue.
                try:
                    now_ny = datetime.now(TZ_NY)
                    now_utc = datetime.now(ZoneInfo("UTC"))
                    today = now_ny.strftime("%Y-%m-%d")
                    self.last_update = now_utc.isoformat(timespec="seconds")

                    # Santé connexion : MT5 peut tomber (terminal fermé, réseau).
                    with self._mt5_lock:
                        alive = mt5.account_info() is not None
                    if not alive:
                        log.warning("MT5 déconnecté — tentative de reconnexion…")
                        if not self._reconnect():
                            self._interruptible_sleep(POLL_SECONDS); continue

                    if today != self.state.day:
                        with self._mt5_lock:
                            acc = mt5.account_info()
                        if acc is not None:
                            self.state.reset(acc.equity, today, acc.balance)
                            self._save_state()
                            log.info("🌅 Nouveau jour NY %s | equity départ=%.2f", today, acc.equity)

                    self.sample_equity()

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
                        if not self.state.halted:
                            self.state.halted = True
                            self._save_state()  # le halt survit à un restart
                        self._interruptible_sleep(POLL_SECONDS); continue
                    if self.state.halted:  # halt restauré du disque après restart
                        self._interruptible_sleep(POLL_SECONDS); continue

                    self._scan_symbols()
                    self._interruptible_sleep(POLL_SECONDS)

                except Exception as e:  # noqa: BLE001
                    self.last_error = str(e)
                    log.exception("Erreur boucle (itération survolée) : %s", e)
                    with self._mt5_lock:
                        dead = mt5.account_info() is None
                    if dead:
                        self._reconnect()
                    self._interruptible_sleep(POLL_SECONDS)
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

                # Gating new-bar (no-repaint) : n'évaluer qu'UNE fois par
                # bougie M5 clôturée — la boucle repolle toutes les 15 s.
                bar_ts = str(_df["time"].iloc[-1]) if _df is not None and len(_df) else None
                if bar_ts is not None:
                    if self._last_scan_bar.get(name) == bar_ts:
                        continue
                    self._last_scan_bar[name] = bar_ts

                setup = classify_setup(ctx, rr_ratio=profile["rr_target"])

                # Mode démo (SIMULATION seulement) : si aucun signal réel, injecter
                # occasionnellement un setup type pour exercer toute la chaîne.
                # Jamais actif en mode MT5 réel → aucun risque sur compte live.
                demo = False
                if self.simulate and DEMO_SIGNALS and not setup.is_valid and random.random() < 0.15:
                    ctx = _demo_context()
                    setup = classify_setup(ctx, rr_ratio=profile["rr_target"])
                    demo = setup.is_valid

                if not setup.is_valid:
                    continue
                if _GRADE_RANK[setup.grade.value] < min_rank:
                    log.info("[%s] Setup %s grade %s < %s requis — skip.",
                             name, setup.setup_type.value, setup.grade.value, profile["min_grade"])
                    continue

                direction = setup.direction or ctx.m5_bos_direction
                if direction not in ("up", "down"):
                    continue
                res = self._open_trade(sym, direction, atr_val, cfg)
                if res:
                    self.state.trades[name] = self.state.trades.get(name, 0) + 1
                    self._save_state()
                    journal = build_journal_entry(
                        symbol=name, context=ctx, setup=setup,
                        risk_r_percent=profile["risk_pct"], result_r=None, discipline_score=None)
                    signal = {
                        "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                        "symbol": name, "direction": direction, "grade": setup.grade.value,
                        "setup_type": setup.setup_type.value, "dry_run": res.get("dry_run", True),
                        "entry": res.get("entry"), "sl": res.get("sl"), "tp": res.get("tp"),
                        "lots": res.get("lots"), "demo": demo, "journal": journal,
                    }
                    self.signals.appendleft(signal)
                    log.info("📓 Journal: %s", journal)
                    notify_telegram(
                        f"🦅 <b>NY SESSION BOT — {name}</b>\n"
                        f"{'🟢 BUY' if direction == 'up' else '🔴 SELL'} "
                        f"<b>{setup.grade.value}</b> ({setup.setup_type.value})\n"
                        f"entrée {res.get('entry')} | SL {res.get('sl')} | TP {res.get('tp')}\n"
                        f"lots {res.get('lots')} · {'DRY RUN' if res.get('dry_run') else 'LIVE'}\n"
                        f"divergence {ctx.rsi_divergence} · wyckoff {ctx.wyckoff}"
                    )
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

    # ── équité & stats ────────────────────────────────────────────────────
    def sample_equity(self, force: bool = False):
        """Ajoute un point (equity, balance) à l'historique (throttle 5s)."""
        if not self.connected:
            return
        now = time.time()
        if not force and now - self._last_eq_sample < 5:
            return
        try:
            with self._mt5_lock:
                a = mt5.account_info()
            if a:
                self.equity_history.append({
                    "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                    "equity": round(a.equity, 2), "balance": round(a.balance, 2),
                })
                self._last_eq_sample = now
        except Exception:  # noqa: BLE001
            pass

    def equity_series(self) -> list[dict]:
        return list(self.equity_history)

    def stats(self) -> dict:
        acc = None
        if self.connected:
            try:
                with self._mt5_lock:
                    acc = mt5.account_info()
            except Exception:  # noqa: BLE001
                acc = None

        realized = floating = total = ret_pct = 0.0
        if acc and self.state.start_equity:
            realized = acc.balance - self.state.start_balance
            floating = acc.equity - acc.balance
            total = acc.equity - self.state.start_equity
            ret_pct = total / self.state.start_equity * 100

        closed = list(self.closed_trades)
        wins = [t for t in closed if t["pnl"] > 0]
        losses = [t for t in closed if t["pnl"] <= 0]
        winrate = (len(wins) / len(closed) * 100) if closed else 0.0
        gross = sum(t["pnl"] for t in closed)
        opened_today = sum(self.state.trades.values()) if self.state.trades else 0

        return {
            "realized_pnl": round(realized, 2), "floating_pnl": round(floating, 2),
            "total_pnl": round(total, 2), "return_pct": round(ret_pct, 2),
            "opened_today": opened_today, "closed_count": len(closed),
            "wins": len(wins), "losses": len(losses), "winrate": round(winrate, 1),
            "gross_closed_pnl": round(gross, 2),
            "currency": acc.currency if acc else "",
            "recent_closed": closed[:20],
        }

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
            "telegram": self.telegram,
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
                if tick is None or info is None:
                    continue
                px = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask
                diff = (px - p.price_open) if p.type == mt5.POSITION_TYPE_BUY else (p.price_open - px)
                pnl = diff / info.trade_tick_size * info.trade_tick_value * p.volume
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

    def scan_setups(self) -> list[dict]:
        """
        Photographie LECTURE SEULE de la confluence courante par symbole :
        Wyckoff + FVG + Ichimoku (+ divergence, biais) et grade `classify_setup`.
        N'ouvre aucun trade — sert au panneau « Scan des setups » de l'UI.
        """
        profile = self.profile
        min_rank = _GRADE_RANK[profile["min_grade"]]
        out: list[dict] = []
        for name, cfg in SYMBOLS.items():
            try:
                with self._mt5_lock:
                    ctx, df_m5, _atr = build_context(cfg)
                if ctx is None:
                    out.append({"symbol": name, "available": False})
                    continue
                setup = classify_setup(ctx, rr_ratio=profile["rr_target"])
                fvg = detect_fvg(df_m5)
                conf = score_confluence(ctx, fvg, setup.direction)
                grade = setup.grade.value
                out.append({
                    "symbol": name,
                    "available": True,
                    "price_source": last_price_source.get(cfg["mt5_symbol"], "sim" if SIMULATE else "mt5"),
                    "last_price": round(float(df_m5["close"].iloc[-1]), 5) if df_m5 is not None else None,
                    "direction": conf["direction"],
                    "grade": grade,
                    "is_valid": bool(setup.is_valid),
                    "passes_profile": bool(setup.is_valid and _GRADE_RANK[grade] >= min_rank),
                    "setup_type": setup.setup_type.value,
                    "pillars_aligned": conf["pillars_aligned"],
                    "confluence_points": conf["points"],
                    "confluence_max": conf["max"],
                    "confluence": conf["items"],
                    "weights": conf["weights"],
                    "context": {
                        "wyckoff": ctx.wyckoff,
                        "rsi_divergence": ctx.rsi_divergence,
                        "price_above_kijun": bool(ctx.price_above_kijun),
                        "h4_bias": ctx.h4_bias,
                        "h4_phase": ctx.h4_phase.value,
                        "m15_zone_touched": bool(ctx.m15_zone_touched),
                        "m5_trigger": ctx.m5_trigger,
                    },
                    "fvg": fvg,
                })
            except Exception as e:  # noqa: BLE001
                log.exception("[%s] Erreur scan_setups : %s", name, e)
                out.append({"symbol": name, "available": False})
        return out


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
