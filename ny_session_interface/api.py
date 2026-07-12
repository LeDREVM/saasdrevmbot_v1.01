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
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ny_session_bot import engine

API_TOKEN = os.environ.get("API_TOKEN")  # facultatif : protège les commandes
HOST = os.environ.get("NY_BOT_HOST", "127.0.0.1")
PORT = int(os.environ.get("NY_BOT_PORT", "8800"))
# Backend FastAPI principal (agent de scoring IA). Surchargeable par env.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

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
