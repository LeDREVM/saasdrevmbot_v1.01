from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.services.economic_calendar.cache_manager import CacheManager
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/n8n", tags=["n8n"])

aggregator = CalendarAggregator()
cache_manager = CacheManager(settings.REDIS_URL)


@router.get("/calendar/today")
async def n8n_today_calendar(
    currencies: Optional[str] = Query(None, description="USD,EUR,JPY"),
    impact: Optional[str] = Query(None, description="High,Medium,Low"),
    db: Session = Depends(get_db)
):
    """
    📅 Calendrier économique du jour — endpoint dédié n8n.

    Renvoie la même forme que `/calendar/today`
    (`{ source, date, events, count }`) afin d'être consommé directement
    par un workflow n8n (HTTP Request → formatage → Telegram).

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
