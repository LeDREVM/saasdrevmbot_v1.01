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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import alphavantage
import news
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
# Source(s) de prix du validator : "mt5" (défaut) ou une CASCADE ordonnée,
# séparée par des virgules, ex. "twelvedata,alphavantage,mt5". Chaque source est
# essayée dans l'ordre jusqu'à obtenir des bougies valides ; MT5/sim sert de
# filet final même s'il n'est pas listé.
PRICE_SOURCE = os.environ.get("PRICE_SOURCE", "mt5").lower()


def _mt5_label() -> str:
    return "sim" if engine.simulate else "mt5"


def _provider_candles(src: str, name: str, cfg: dict):
    """Bougies d'une source donnée, ou None si indisponible."""
    if src == "twelvedata" and twelvedata.enabled():
        return twelvedata.get_candles(name, interval="5min", outputsize=SIGNAL_BARS)
    if src == "alphavantage" and alphavantage.enabled():
        return alphavantage.get_candles(name, interval="5min", outputsize=SIGNAL_BARS)
    if src in ("mt5", "sim"):
        with engine._mt5_lock:
            return get_rates(cfg["mt5_symbol"], mt5.TIMEFRAME_M5, SIGNAL_BARS)
    return None


def _load_ohlc(name: str, cfg: dict):
    """Charge les bougies M5 en cascade selon PRICE_SOURCE. Renvoie (df, source)."""
    order = [s.strip() for s in PRICE_SOURCE.split(",") if s.strip()] or ["mt5"]
    for src in order:
        df = _provider_candles(src, name, cfg)
        if df is not None and len(df) >= 60:
            return df, (_mt5_label() if src in ("mt5", "sim") else src)
    # Filet final MT5/sim si non déjà tenté dans la cascade.
    if not ({"mt5", "sim"} & set(order)):
        df = _provider_candles("mt5", name, cfg)
        if df is not None and len(df) >= 60:
            return df, _mt5_label()
    return None, _mt5_label()

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="NY Session Bot — Console", version="1.0")


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
    return engine.snapshot()


@app.get("/api/positions")
def get_positions():
    return {"positions": engine.positions()}


@app.get("/api/signals")
def get_signals():
    return {"signals": engine.recent_signals()}


@app.get("/api/scan")
def get_scan():
    """Confluence courante par symbole (Wyckoff + FVG + Ichimoku), lecture seule."""
    return {"scan": engine.scan_setups()}


# ── Réception des données MT5 poussées par le pont (mt5_data_sender.py) ───────
# Store en mémoire des dernières bougies par symbole (source alternative quand
# le terminal MT5 tourne sur un VPS séparé qui POST vers MARKET_DATA_API_URL).
_market_data: dict[str, dict] = {}


class MarketDataBody(BaseModel):
    symbol: str
    candles: list[dict]


@app.post("/api/market-data")
def post_market_data(body: MarketDataBody):
    """Reçoit {symbol, candles:[{time,open,high,low,close,volume}]} du pont MT5."""
    _market_data[body.symbol] = {
        "candles": body.candles,
        "count": len(body.candles),
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return {"ok": True, "symbol": body.symbol, "count": len(body.candles)}


@app.get("/api/market-data")
def get_market_data(symbol: str | None = None):
    """État des données MT5 reçues (monitoring). ?symbol=XAUUSD pour les bougies."""
    if symbol:
        return _market_data.get(symbol, {"count": 0, "candles": []})
    return {"symbols": {s: {"count": d["count"], "received_at": d["received_at"]}
                        for s, d in _market_data.items()}}


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

    direction = body.direction or sig["direction"]
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
