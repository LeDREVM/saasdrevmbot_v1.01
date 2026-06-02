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

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ny_session_bot import engine

API_TOKEN = os.environ.get("API_TOKEN")  # facultatif : protège les commandes
HOST = os.environ.get("NY_BOT_HOST", "127.0.0.1")
PORT = int(os.environ.get("NY_BOT_PORT", "8800"))

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


@app.get("/api/logs")
def get_logs(after: int = -1):
    return {"logs": engine.recent_logs(after)}


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
