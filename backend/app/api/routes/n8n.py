import logging
from fastapi import APIRouter, Depends, Query, Header, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests

from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.services.economic_calendar.cache_manager import CacheManager
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n"])

aggregator = CalendarAggregator()
cache_manager = CacheManager(settings.REDIS_URL)


def verify_n8n_secret(x_n8n_secret: Optional[str] = Header(None)):
    """
    Vérifie le secret partagé envoyé par n8n via l'en-tête `X-N8N-Secret`.

    - Si `N8N_WEBHOOK_SECRET` n'est pas configuré côté serveur, la vérification
      est ignorée (utile en dev / rétro-compatibilité).
    - Sinon, l'en-tête doit correspondre, sous peine de 401.
    """
    expected = settings.N8N_WEBHOOK_SECRET
    if not expected:
        return
    if x_n8n_secret != expected:
        raise HTTPException(status_code=401, detail="Secret n8n invalide ou manquant")


def _impact_emoji(impact: Optional[str]) -> str:
    return {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(impact or "", "⚪")


def _format_telegram_message(date: str, events: List[Dict[str, Any]]) -> str:
    """Construit un message HTML pour Telegram à partir des événements."""
    lines = [f"📅 <b>Calendrier économique — {date}</b>", ""]

    if not events:
        lines.append("✅ Aucun événement à fort impact aujourd'hui.")
        return "\n".join(lines)

    events = sorted(events, key=lambda e: str(e.get("time") or ""))
    for e in events:
        emoji = _impact_emoji(e.get("impact"))
        line = f"{emoji} <b>{e.get('time') or '--:--'}</b>  {e.get('currency') or ''} — {e.get('event') or ''}"
        details = []
        if e.get("forecast"):
            details.append(f"prév: {e['forecast']}")
        if e.get("previous"):
            details.append(f"préc: {e['previous']}")
        if e.get("actual"):
            details.append(f"réel: {e['actual']}")
        if details:
            line += "\n   <i>" + "  |  ".join(details) + "</i>"
        lines.append(line)

    lines += ["", f"<b>Total:</b> {len(events)} événement(s)"]
    return "\n".join(lines)


@router.get("/calendar/today", dependencies=[Depends(verify_n8n_secret)])
async def n8n_today_calendar(
    currencies: Optional[str] = Query(None, description="USD,EUR,JPY"),
    impact: Optional[str] = Query(None, description="High,Medium,Low"),
    db: Session = Depends(get_db)
):
    """
    📅 Calendrier économique du jour — endpoint dédié n8n.

    Renvoie la même forme que `/calendar/today`
    (`{ source, date, events, count }`) afin d'être consommé directement
    par un workflow n8n (HTTP Request → formatage → Telegram / Discord).

    **Exemple:** `/n8n/calendar/today?impact=High,Medium`
    """

    # Check cache (clé distincte pour ne pas interférer avec /calendar/today)
    cache_key = f"calendar:n8n:today:{currencies}:{impact}"
    cached = cache_manager.get_cached_events(cache_key)

    if cached:
        return JSONResponse(content={
            "source": "cache",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "events": cached,
            "count": len(cached)
        })

    # Scrape
    currency_list = currencies.split(",") if currencies else None
    events = aggregator.get_today_events(currency_list)

    # Filter by impact
    if impact:
        impact_levels = impact.split(",")
        events = [e for e in events if e.impact.value in impact_levels]

    # Cache + Save DB
    cache_manager.set_cached_events(cache_key, events)
    cache_manager.save_to_db(events, db)

    return JSONResponse(content={
        "source": "fresh",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "events": [e.to_dict() for e in events],
        "count": len(events)
    })


@router.post("/notify/telegram", dependencies=[Depends(verify_n8n_secret)])
async def n8n_notify_telegram(payload: Dict[str, Any] = Body(...)):
    """
    📱 Notifie Telegram avec le calendrier du jour — appelé par n8n.

    Corps accepté (souple) :
    - `{ "date", "events": [...], "count" }` → message formaté côté serveur.
    - `{ "text": "..." }` → message HTML déjà prêt à envoyer.
    - `chat_id` (optionnel) pour surcharger `TELEGRAM_CHAT_ID`.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN non configuré")

    chat_id = payload.get("chat_id") or settings.TELEGRAM_CHAT_ID
    if not chat_id:
        raise HTTPException(status_code=500, detail="TELEGRAM_CHAT_ID non configuré")

    text = payload.get("text")
    if not text:
        date = payload.get("date") or datetime.now().strftime("%Y-%m-%d")
        events = payload.get("events") or []
        text = _format_telegram_message(date, events)

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"❌ Erreur envoi Telegram (n8n): {e}")
        raise HTTPException(status_code=502, detail=f"Echec envoi Telegram: {e}")

    logger.info("✅ Notification Telegram envoyée via n8n")
    return {"status": "sent", "chat_id": str(chat_id)}
