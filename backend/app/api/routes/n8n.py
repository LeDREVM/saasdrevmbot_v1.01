"""
Router n8n — endpoints dédiés à l'automatisation n8n.

Surfaces :
  GET  /api/n8n/calendar/today          → événements du jour (format n8n-ready)
  GET  /api/n8n/upcoming                → annonces dans N min (défaut 30)
  POST /api/n8n/scoring                 → déclenche l'agent IA de scoring
  POST /api/n8n/notify/discord          → envoi Discord depuis n8n
  POST /api/n8n/notify/telegram         → envoi Telegram depuis n8n
  GET  /api/n8n/health                  → healthcheck rapide pour n8n

Sécurité : header X-N8N-Secret optionnel (variable N8N_WEBHOOK_SECRET).
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.services.economic_calendar.cache_manager import CacheManager
from app.services.notifications.discord_notifier import DiscordNotifier
from app.services.notifications.telegram_notifier import TelegramNotifier
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n Automation"])

_aggregator = CalendarAggregator()
_cache = CacheManager(settings.REDIS_URL)
_discord = DiscordNotifier()
_telegram = TelegramNotifier()


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _check_secret(x_n8n_secret: Optional[str] = Header(default=None)):
    secret = os.getenv("N8N_WEBHOOK_SECRET")
    if secret and x_n8n_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid N8N secret")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ScoringRequest(BaseModel):
    symbol: str
    setup_grade: str          # A+/A/B/C
    htf_phase: str            # markup/markdown/accumulation/distribution
    direction: str            # BUY/SELL
    session_active: bool = True
    spread_ok: bool = True
    event_context: Optional[dict] = None


class NotifyRequest(BaseModel):
    events: List[dict]
    message_type: str = "daily_calendar"   # daily_calendar | pre_event | custom
    custom_text: Optional[str] = None
    minutes_until: Optional[int] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/health")
async def n8n_health():
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "service": "saasDrevmBot"}


@router.get("/calendar/today")
async def get_today_for_n8n(
    currencies: Optional[str] = Query(None, description="USD,EUR,GBP"),
    impact: Optional[str] = Query(None, description="High,Medium,Low"),
    _: None = Depends(_check_secret),
    db: Session = Depends(get_db),
):
    """
    Retourne le calendrier du jour dans un format optimisé pour n8n.
    Chaque événement a un champ `impact_level` (1-3) pour faciliter le filtrage.
    """
    cache_key = f"n8n:calendar:today:{currencies}:{impact}"
    cached = _cache.get_cached_events(cache_key)
    if cached:
        return JSONResponse({"source": "cache", "date": datetime.now().strftime("%Y-%m-%d"),
                             "count": len(cached), "events": cached})

    cur_list = [c.strip().upper() for c in currencies.split(",")] if currencies else []
    events = _aggregator.get_today_events(currencies=cur_list or None)

    # Filtrer par impact
    if impact:
        wanted = {i.strip().lower() for i in impact.split(",")}
        events = [e for e in events if e.impact.value.lower() in wanted]

    events_dict = [_enrich_event(e.to_dict()) for e in events]

    _cache.set_cached_events(cache_key, events)

    return JSONResponse({
        "source": "live",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": len(events_dict),
        "high_impact_count": sum(1 for e in events_dict if e["impact_level"] == 3),
        "events": events_dict,
    })


@router.get("/upcoming")
async def get_upcoming_for_n8n(
    minutes: int = Query(30, description="Fenêtre en minutes"),
    impact: str = Query("High", description="High,Medium,Low"),
    _: None = Depends(_check_secret),
):
    """Retourne les annonces imminentes dans la fenêtre de temps."""
    now = datetime.now()
    cutoff_low = now + timedelta(minutes=max(0, minutes - 10))
    cutoff_high = now + timedelta(minutes=minutes + 5)

    events = _aggregator.get_today_events()
    wanted_impact = {i.strip().lower() for i in impact.split(",")}

    upcoming = []
    for e in events:
        if e.impact.value.lower() not in wanted_impact:
            continue
        try:
            evt_dt = e.datetime_obj
            if cutoff_low <= evt_dt <= cutoff_high:
                d = _enrich_event(e.to_dict())
                d["minutes_until"] = int((evt_dt - now).total_seconds() / 60)
                upcoming.append(d)
        except Exception:
            continue

    return JSONResponse({
        "window_minutes": minutes,
        "count": len(upcoming),
        "has_events": len(upcoming) > 0,
        "events": upcoming,
    })


@router.post("/scoring")
async def trigger_scoring(
    req: ScoringRequest,
    _: None = Depends(_check_secret),
):
    """Lance l'agent IA de scoring et retourne le résultat."""
    try:
        from app.services.ai.scoring_agent import ScoringAgent
        from app.services.ai import scoring_store
        agent = ScoringAgent()
        result = agent.score_setup(req.dict())
        scoring_store.save_score(result)

        # Notification automatique Discord + Telegram
        _discord.send_high_impact_alert({
            "event": f"Score IA {req.symbol}: {result['score']}/100 → {result['recommendation']}",
            "currency": req.symbol,
            "impact": "high" if result["score"] >= 75 else "medium",
            "time": datetime.now().strftime("%H:%M"),
            "forecast": result.get("reasoning", "")[:100],
            "previous": f"Grade: {req.setup_grade}",
        })
        _telegram.send_scoring_result(result)

        return JSONResponse(result)

    except Exception as exc:
        logger.error(f"Scoring error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/notify/discord")
async def notify_discord(
    req: NotifyRequest,
    _: None = Depends(_check_secret),
):
    """Envoie une notification Discord depuis un workflow n8n."""
    ok = False
    if req.message_type == "daily_calendar":
        ok = _discord.send_daily_calendar(req.events)
    elif req.message_type == "pre_event" and req.minutes_until:
        ok = _discord.send_upcoming_events(req.events, req.minutes_until)
    elif req.message_type == "custom" and req.custom_text:
        # Envoi texte libre via embed minimal
        ok = _discord._send_embed(
            {"title": "📢 saasDrevmBot", "description": req.custom_text, "color": 0x5865F2,
             "timestamp": datetime.utcnow().isoformat()}
        )
    return JSONResponse({"sent": ok})


@router.post("/notify/telegram")
async def notify_telegram(
    req: NotifyRequest,
    _: None = Depends(_check_secret),
):
    """Envoie une notification Telegram depuis un workflow n8n."""
    ok = False
    if req.message_type == "daily_calendar":
        ok = _telegram.send_daily_calendar(req.events)
    elif req.message_type == "pre_event" and req.minutes_until:
        ok = _telegram.send_pre_event_alert(req.events, req.minutes_until)
    elif req.message_type == "custom" and req.custom_text:
        ok = _telegram._send_message(req.custom_text)
    return JSONResponse({"sent": ok})


# ─── helper ───────────────────────────────────────────────────────────────────

def _enrich_event(e: dict) -> dict:
    """Ajoute impact_level (1/2/3) et has_forecast pour faciliter le filtrage n8n."""
    level_map = {"High": 3, "Medium": 2, "Low": 1}
    e["impact_level"] = level_map.get(e.get("impact", "Low"), 1)
    e["has_forecast"] = bool(e.get("forecast"))
    return e
