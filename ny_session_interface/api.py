"""
api.py — Interface web autonome de pilotage du NY Session Bot.

Expose une API REST (état + commandes) et sert la page de contrôle.

Lancement :
    pip install -r requirements.txt
    python api.py                 # http://127.0.0.1:8800

⚠️ SÉCURITÉ : ce serveur peut envoyer des ordres RÉELS (quand DRY_RUN est OFF).
   - Il écoute par défaut sur 127.0.0.1 (localhost) UNIQUEMENT.
   - Pour y accéder à distance, passe par un tunnel SSH plutôt que d'exposer
     le port. Si tu dois l'exposer, définis API_TOKEN et garde un reverse-proxy
     HTTPS devant.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import time

import pandas as pd

import alphavantage
import news
import ny_session_bot as nsb
import setup_validator as validator
import trade_journal
import twelvedata
from ny_session_bot import engine, SYMBOLS, get_rates, mt5

API_TOKEN = os.environ.get("API_TOKEN")  # facultatif : protège les commandes
HOST = os.environ.get("NY_BOT_HOST", "127.0.0.1")
PORT = int(os.environ.get("NY_BOT_PORT", "8800"))
# Backend FastAPI principal (agent de scoring IA). Surchargeable par env.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
# Exécution d'ordres via /api/execute : DÉSACTIVÉE par défaut (garde-fou).
ALLOW_EXECUTION = os.environ.get("ALLOW_EXECUTION", "0") == "1"
SIGNAL_BARS = 250
# Source(s) de prix : "mt5" (défaut) ou une CASCADE ordonnée séparée par des
# virgules, ex. "twelvedata,alphavantage,mt5". Les sources externes sont
# fournies au moteur via un price provider (get_rates), donc le SCAN et le
# SIGNAL cascadent tous deux ; MT5/sim reste le filet final. Cache TTL pour
# borner les appels API (rate-limits).
PRICE_SOURCE = os.environ.get("PRICE_SOURCE", "mt5").lower()
_PRICE_CACHE_TTL = int(os.environ.get("PRICE_CACHE_TTL", "60"))
_TF_INTERVAL = {mt5.TIMEFRAME_M5: "5min", mt5.TIMEFRAME_M15: "15min", mt5.TIMEFRAME_H4: "4h"}
_candle_cache: dict = {}   # (src, symbol, interval) -> (ts, df|None)
# Sources externes reconnues dans PRICE_SOURCE (cascade ordonnée).
_KNOWN_SOURCES = ("mt5bridge", "twelvedata", "alphavantage")

# Store en mémoire des bougies poussées par le pont MT5 (mt5_data_sender.py sur
# le VPS Windows). Structure : {symbol: {timeframe_const: {candles, count, ...}}}.
# Permet à un dashboard hébergé sur Linux/cloud d'utiliser les VRAIES bougies MT5
# comme source de prix (le paquet MetaTrader5 étant Windows-only).
_market_data: dict[str, dict] = {}

# État COMPTE + POSITIONS poussé par le même pont (mt5_data_sender.py). Permet au
# dashboard cloud d'afficher l'équité/le solde/les positions RÉELS du terminal
# Windows au lieu des valeurs de SIMULATION. Considéré périmé au-delà de
# _MT5_STATE_TTL (le feeder pousse toutes les 5 min → on tolère quelques cycles).
_mt5_state: dict = {}   # {account, positions, start_equity, day, received_at, received_ts}
_MT5_STATE_TTL = int(os.environ.get("MT5_STATE_TTL", "900"))  # 15 min


def _fresh_mt5_state():
    """État MT5 poussé s'il est encore frais, sinon None (→ fallback SIMULATION)."""
    if not _mt5_state:
        return None
    if time.time() - _mt5_state.get("received_ts", 0) > _MT5_STATE_TTL:
        return None
    return _mt5_state


def _mt5_label() -> str:
    return "sim" if engine.simulate else "mt5"


def _external_sources() -> list[str]:
    return [s.strip() for s in PRICE_SOURCE.split(",") if s.strip() in _KNOWN_SOURCES]


def _cached_candles(src: str, symbol: str, interval: str, n: int):
    key = (src, symbol, interval)
    now = time.time()
    hit = _candle_cache.get(key)
    if hit and now - hit[0] < _PRICE_CACHE_TTL:
        return hit[1]
    df = None
    if src == "twelvedata" and twelvedata.enabled():
        df = twelvedata.get_candles(symbol, interval, max(n, 250))
    elif src == "alphavantage" and alphavantage.enabled():
        df = alphavantage.get_candles(symbol, interval, max(n, 250))
    _candle_cache[key] = (now, df)
    return df


def _bridge_candles(symbol: str, timeframe: int, n: int):
    """Bougies poussées par le pont MT5 pour ce (symbole, timeframe). Convertit
    le payload JSON du feeder en DataFrame compatible get_rates. None si absent."""
    entry = _market_data.get(symbol, {}).get(timeframe)
    if not entry or not entry.get("candles"):
        return None
    df = pd.DataFrame(entry["candles"])
    if not {"open", "high", "low", "close"}.issubset(df.columns) or len(df) < 40:
        return None
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    if "volume" not in df.columns and "tick_volume" in df.columns:
        df["volume"] = df["tick_volume"]
    return df


def _cascade_provider(symbol: str, timeframe: int, n: int):
    """Price provider (branché sur get_rates) : bougies natives par timeframe,
    en cascade selon l'ordre de PRICE_SOURCE (pont MT5, Twelve Data, Alpha
    Vantage). None → get_rates retombe sur MT5/sim (filet final)."""
    for src in _external_sources():
        if src == "mt5bridge":
            df = _bridge_candles(symbol, timeframe, n)
        else:
            interval = _TF_INTERVAL.get(timeframe)
            df = _cached_candles(src, symbol, interval, n) if interval else None
        if df is not None and len(df) >= 40:
            if timeframe == mt5.TIMEFRAME_M5:
                nsb.last_price_source[symbol] = src
            return df.tail(n).reset_index(drop=True)
    return None


# Enregistre le provider si une source externe est configurée (scan + signal).
if _external_sources():
    nsb.set_price_provider(_cascade_provider)


def _load_ohlc(name: str, cfg: dict):
    """Bougies M5 via get_rates (donc cascade si provider actif). Renvoie (df, source)."""
    with engine._mt5_lock:
        df = get_rates(cfg["mt5_symbol"], mt5.TIMEFRAME_M5, SIGNAL_BARS)
    src = nsb.last_price_source.get(cfg["mt5_symbol"], _mt5_label())
    if df is None or len(df) < 60:
        return None, src
    return df, src

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="NY Session Bot — Console", version="1.0")

# REQUIRE_TOKEN=1 → TOUTES les routes /api/* exigent X-Api-Token (pas seulement
# les POST). OBLIGATOIRE avant toute exposition publique (proxy Netlify, tunnel) :
# sinon équité, positions et logs seraient lisibles par n'importe qui.
REQUIRE_TOKEN = os.environ.get("REQUIRE_TOKEN", "0") == "1"


@app.middleware("http")
async def _token_guard(request, call_next):
    if REQUIRE_TOKEN and request.url.path.startswith("/api/"):
        if not API_TOKEN:
            return JSONResponse(status_code=503, content={
                "detail": "REQUIRE_TOKEN=1 mais API_TOKEN non défini — accès bloqué."})
        if request.headers.get("x-api-token") != API_TOKEN:
            return JSONResponse(status_code=401, content={
                "detail": "Token requis (X-Api-Token) — saisis-le dans le champ « API token » de la console."})
    return await call_next(request)


def _check_token(token: str | None):
    if API_TOKEN and token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalide")


# ── Modèles de requête ───────────────────────────────────────────────────────
class ProfileBody(BaseModel):
    profile: str


class ToggleBody(BaseModel):
    enabled: bool


# ── Lecture d'état ─────────────────────────────────────────────────────────--
@app.get("/api/state")
def get_state():
    snap = engine.snapshot()
    bridge = _fresh_mt5_state()
    if bridge and bridge.get("account"):
        # Compte RÉEL poussé par le pont MT5 → prime sur la SIMULATION cloud.
        snap["account"] = bridge["account"]
        snap["account_source"] = "mt5bridge"
        snap["account_received_at"] = bridge["received_at"]
    else:
        snap["account_source"] = _mt5_label()
    return snap


@app.get("/api/positions")
def get_positions():
    bridge = _fresh_mt5_state()
    if bridge is not None and bridge.get("positions") is not None:
        # Positions RÉELLES poussées par le pont MT5 (terminal Windows).
        return {"positions": bridge["positions"], "source": "mt5bridge",
                "received_at": bridge["received_at"]}
    return {"positions": engine.positions(), "source": _mt5_label()}


@app.get("/api/signals")
def get_signals():
    return {"signals": engine.recent_signals()}


@app.get("/api/scan")
def get_scan():
    """Confluence courante par symbole (Wyckoff + FVG + Ichimoku), lecture seule."""
    return {"scan": engine.scan_setups()}


# ── Réception des données MT5 poussées par le pont (mt5_data_sender.py) ───────
# Le feeder (VPS Windows) POST une fois par timeframe ; branché comme source de
# prix "mt5bridge" (cf. _bridge_candles). `_market_data` est défini plus haut.
_TF_NAME = {"H4": mt5.TIMEFRAME_H4, "M15": mt5.TIMEFRAME_M15, "M5": mt5.TIMEFRAME_M5}


class MarketDataBody(BaseModel):
    symbol: str
    candles: list[dict]
    timeframe: str = "M5"   # "H4" | "M15" | "M5"


@app.post("/api/market-data")
def post_market_data(body: MarketDataBody):
    """Reçoit {symbol, timeframe, candles:[{time,open,high,low,close,volume}]}."""
    tfn = body.timeframe.upper()
    tf = _TF_NAME.get(tfn, mt5.TIMEFRAME_M5)
    _market_data.setdefault(body.symbol, {})[tf] = {
        "candles": body.candles,
        "count": len(body.candles),
        "timeframe": tfn,
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return {"ok": True, "symbol": body.symbol, "timeframe": tfn, "count": len(body.candles)}


@app.get("/api/market-data")
def get_market_data(symbol: str | None = None):
    """État des données MT5 reçues du pont (monitoring)."""
    if symbol:
        tfs = _market_data.get(symbol, {})
        return {"symbol": symbol, "timeframes": {
            d["timeframe"]: {"count": d["count"], "received_at": d["received_at"]}
            for d in tfs.values()}}
    return {"symbols": {s: {
        "timeframes": sorted(d["timeframe"] for d in tfs.values()),
        "last_received": max((d["received_at"] for d in tfs.values()), default=None),
    } for s, tfs in _market_data.items()}}


# ── Réception COMPTE + POSITIONS poussés par le pont (mt5_data_sender.py) ──────
# Même feeder que /api/market-data ; alimente /api/state (account) et
# /api/positions avec les vraies valeurs du terminal MT5 Windows.
class Mt5StateBody(BaseModel):
    account: dict | None = None
    positions: list[dict] | None = None


@app.post("/api/mt5-state")
def post_mt5_state(body: Mt5StateBody):
    """Reçoit {account:{login,balance,equity,currency,leverage,...}, positions:[...]}.

    `start_equity` (donc le drawdown journalier RÉEL) est dérivé côté console :
    première équité reçue de la journée UTC — le feeder n'a pas à la suivre.
    """
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    start_eq = _mt5_state.get("start_equity") if _mt5_state.get("day") == today else None
    acc = dict(body.account) if body.account else None
    if acc is not None:
        eq = acc.get("equity")
        if not start_eq:
            start_eq = eq
        if start_eq:
            acc["start_equity"] = round(start_eq, 2)
            acc["dd_pct"] = round(max(0.0, (start_eq - (eq if eq is not None else start_eq)) / start_eq * 100), 2)
        else:
            acc["dd_pct"] = 0.0
    _mt5_state.clear()
    _mt5_state.update({
        "account": acc,
        "positions": body.positions or [],
        "start_equity": start_eq,
        "day": today,
        "received_at": now.isoformat(timespec="seconds"),
        "received_ts": time.time(),
    })
    return {"ok": True, "positions": len(body.positions or [])}


@app.get("/api/mt5-state")
def get_mt5_state():
    """État compte/positions reçu du pont (monitoring : fraîcheur + source)."""
    bridge = _fresh_mt5_state()
    return {
        "present": _mt5_state.get("received_ts") is not None,
        "fresh": bridge is not None,
        "received_at": _mt5_state.get("received_at"),
        "ttl_seconds": _MT5_STATE_TTL,
        "positions": len(_mt5_state.get("positions") or []),
        "has_account": bool(_mt5_state.get("account")),
    }


# ── Navigation multi-dashboards ──────────────────────────────────────────────
def _dashboards() -> list[dict]:
    """Liste des dashboards du projet (URLs surchargeables par env)."""
    return [
        {"key": "console", "label": "Bot NY Session", "icon": "🦅",
         "url": os.environ.get("DASH_CONSOLE_URL", f"http://localhost:{PORT}"),
         "current": True},
        {"key": "analytics", "label": "Analytics", "icon": "📊",
         "url": os.environ.get("DASH_ANALYTICS_URL", "http://localhost:5173"),
         "current": False},
        {"key": "saas", "label": "SaaS", "icon": "🗂️",
         "url": os.environ.get("DASH_SAAS_URL", "http://localhost:3000"),
         "current": False},
    ]


@app.get("/api/dashboards")
def get_dashboards():
    """Dashboards du projet + celui courant, pour la barre de navigation."""
    return {"dashboards": _dashboards()}


class AiScanBody(BaseModel):
    symbol: str


@app.post("/api/scan/ai")
def scan_ai(body: AiScanBody, x_api_token: str | None = Header(default=None)):
    """
    Branche l'agent de scoring IA (backend `/api/scoring/analyze`) sur un setup
    du scan. Récupère le contexte courant du symbole (grade, phase HTF, sens),
    proxifie vers le backend et retourne son score /100 + recommandation.
    """
    _check_token(x_api_token)

    entry = next((s for s in engine.scan_setups() if s.get("symbol") == body.symbol), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Symbole inconnu : {body.symbol}")
    if not entry.get("available"):
        raise HTTPException(status_code=409, detail="Pas de données de marché pour ce symbole")
    direction = entry.get("direction")
    if direction not in ("up", "down"):
        raise HTTPException(status_code=422, detail="Pas de setup directionnel à analyser")

    ctx = entry.get("context") or {}
    payload = {
        "symbol": body.symbol,
        "setup_grade": entry.get("grade", "C"),
        "htf_phase": ctx.get("h4_phase", "accumulation"),
        "direction": "BUY" if direction == "up" else "SELL",
        "session_active": bool(engine.session_open),
        "spread_ok": True,
        "event_context": None,
        # Confluence réelle Wyckoff+FVG+Ichimoku pour un scoring IA mieux fondé.
        "confluence": {
            "points": entry.get("confluence_points"),
            "max": entry.get("confluence_max"),
            "pillars": entry.get("confluence"),
            "wyckoff": ctx.get("wyckoff"),
            "rsi_divergence": ctx.get("rsi_divergence"),
            "price_above_kijun": ctx.get("price_above_kijun"),
            "m15_zone_touched": ctx.get("m15_zone_touched"),
            "m5_trigger": ctx.get("m5_trigger"),
            "fvg": entry.get("fvg"),
        },
        "notify": False,
    }

    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/scoring/analyze",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise HTTPException(status_code=502, detail=f"Backend scoring {exc.code} : {detail}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=503,
                            detail=f"Backend IA injoignable ({BACKEND_URL}) : {exc.reason}")

    return {"ok": True, "ai": result, "setup": {
        "grade": entry.get("grade"), "direction": direction,
        "confluence_points": entry.get("confluence_points"),
        "confluence_max": entry.get("confluence_max"),
    }}


# ── Pipeline : signal (validateur + filtres) + exécution gardée ──────────────
def _signal_for(name: str) -> dict | None:
    """AI Setup Validator + filtres (session, news, risk/halt) pour un symbole."""
    cfg = SYMBOLS.get(name)
    if cfg is None:
        return None
    df, source = _load_ohlc(name, cfg)
    if df is None or len(df) < 60:
        return {"symbol": name, "available": False, "source": source}

    nc = news.news_context(name)   # news_score + event_context (calendrier backend)
    v = validator.validate(df, symbol=name, session_active=bool(engine.session_open),
                           news_score=nc["news_score"])
    risk_ok = not engine.state.halted and not engine.kill_switch
    filters = {
        "session_ny": bool(engine.session_open),
        "news_ok": float(v.features.get("news_score", 100)) >= 60,
        "risk_ok": bool(risk_ok),
        "confidence_ok": v.confidence >= 80,
    }
    return {
        "symbol": name, "available": True,
        "decision": v.decision, "direction": v.direction, "confidence": v.confidence,
        "scores": v.scores, "filters": filters,
        "news": {"score": nc["news_score"], "event": nc["event_context"], "source": nc["source"]},
        "price_source": source,
        "executable": bool(v.decision == "EXECUTE" and risk_ok),
    }


@app.get("/api/signal")
def get_signal():
    """Signal par symbole (AI Setup Validator + filtres). Consommé par n8n."""
    signals = [s for s in (_signal_for(n) for n in SYMBOLS) if s]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_ny": bool(engine.session_open),
        "signals": signals,
    }


class ExecuteBody(BaseModel):
    symbol: str
    direction: str | None = None   # "up"/"down" ; sinon déduit du signal
    confirm: bool = False


@app.post("/api/execute")
def execute(body: ExecuteBody, x_api_token: str | None = Header(default=None)):
    """
    Exécution gardée d'un signal (déclenchée par n8n). Garde-fous cumulés :
    ALLOW_EXECUTION=1 + token + confirm=true + signal courant == EXECUTE +
    garde-fous moteur (kill/halt/position/DRY_RUN).
    """
    _check_token(x_api_token)
    if not ALLOW_EXECUTION:
        raise HTTPException(status_code=403,
                            detail="Exécution désactivée (variable d'env ALLOW_EXECUTION=1 requise)")
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true requis pour exécuter")

    sig = _signal_for(body.symbol)
    if sig is None:
        raise HTTPException(status_code=404, detail=f"Symbole inconnu : {body.symbol}")
    if not sig.get("available"):
        raise HTTPException(status_code=409, detail="Pas de données de marché")
    if not sig.get("executable"):
        raise HTTPException(status_code=409,
                            detail=f"Signal non exécutable (décision={sig['decision']}, "
                                   f"confiance={sig['confidence']}%, filtres={sig['filters']})")

    # La direction exécutée DOIT être celle que le validator a validée : un
    # body.direction opposé ouvrirait un BUY cautionné par un score SELL.
    if body.direction and body.direction != sig["direction"]:
        raise HTTPException(status_code=409,
                            detail=f"direction demandée ({body.direction}) ≠ direction "
                                   f"du signal validé ({sig['direction']})")
    direction = sig["direction"]
    res = engine.execute_signal(body.symbol, direction, source="n8n")
    if not res.get("ok"):
        raise HTTPException(status_code=409, detail=res.get("reason", "exécution refusée"))

    # Auto-journalisation Supabase (best-effort, n'échoue jamais l'exécution).
    order = res.get("order", {})
    journal = trade_journal.record_trade(
        body.symbol, direction, entry=order.get("entry"), sl=order.get("sl"),
        tp=order.get("tp"), notes=f"auto/n8n · confiance {sig.get('confidence')}%")

    return {"ok": True, "executed": res, "signal": sig, "journal": journal}


@app.get("/api/logs")
def get_logs(after: int = -1):
    return {"logs": engine.recent_logs(after)}


@app.get("/api/equity")
def get_equity():
    return {"points": engine.equity_series()}


@app.get("/api/stats")
def get_stats():
    return engine.stats()


# ── Commandes ─────────────────────────────────────────────────────────────---
@app.post("/api/control/start")
def control_start(x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    return {"ok": engine.start(), "state": engine.snapshot()}


@app.post("/api/control/stop")
def control_stop(x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    return {"ok": engine.stop(), "state": engine.snapshot()}


@app.post("/api/control/dry-run")
def control_dry_run(body: ToggleBody, x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    engine.set_dry_run(body.enabled)
    return {"ok": True, "dry_run": engine.dry_run}


@app.post("/api/control/kill-switch")
def control_kill_switch(body: ToggleBody, x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    engine.set_kill_switch(body.enabled)
    return {"ok": True, "kill_switch": engine.kill_switch}


@app.post("/api/control/profile")
def control_profile(body: ProfileBody, x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    ok = engine.set_profile(body.profile)
    if not ok:
        raise HTTPException(status_code=400, detail="Profil inconnu")
    return {"ok": True, "profile": engine.profile_name}


@app.post("/api/control/close-all")
def control_close_all(x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    n = engine.close_all_positions("ui")
    return {"ok": True, "closed": n}


@app.post("/api/control/close/{ticket}")
def control_close(ticket: int, x_api_token: str | None = Header(default=None)):
    _check_token(x_api_token)
    return {"ok": engine.close_position(ticket)}


# ── UI statique ──────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"\n  NY Session Bot — console sur http://{HOST}:{PORT}\n")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
