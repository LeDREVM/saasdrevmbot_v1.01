from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.services.economic_calendar.cache_manager import CacheManager
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/calendar", tags=["Economic Calendar"])

aggregator = CalendarAggregator()
cache_manager = CacheManager(settings.REDIS_URL)

@router.get("/today")
async def get_today_calendar(
    currencies: Optional[str] = Query(None, description="USD,EUR,JPY"),
    impact: Optional[str] = Query(None, description="High,Medium,Low"),
    db: Session = Depends(get_db)
):
    """
    📅 Calendrier économique du jour
    
    **Exemple:** `/calendar/today?currencies=USD,EUR&impact=High`
    """
    
    # Check cache
    cache_key = f"calendar:today:{currencies}:{impact}"
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

@router.get("/week")
async def get_week_calendar(
    currencies: Optional[str] = Query(None),
    impact: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    📆 Calendrier économique de la semaine (7 jours)
    """
    
    cache_key = f"calendar:week:{currencies}:{impact}"
    cached = cache_manager.get_cached_events(cache_key)
    
    if cached:
        return {"source": "cache", "events": cached, "count": len(cached)}
    
    currency_list = currencies.split(",") if currencies else None
    events = aggregator.get_week_events(currency_list)
    
    if impact:
        impact_levels = impact.split(",")
        events = [e for e in events if e.impact.value in impact_levels]
    
    cache_manager.set_cached_events(cache_key, events)
    cache_manager.save_to_db(events, db)
    
    return {
        "source": "fresh",
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }

@router.get("/upcoming")
async def get_upcoming_high_impact(
    hours: int = Query(2, description="Heures à l'avance")
):
    """
    ⚠️ Événements HIGH IMPACT dans les N prochaines heures
    
    **Utilisé pour alertes Discord/Telegram**
    """
    
    events = aggregator.get_upcoming_high_impact(hours_ahead=hours)
    
    return {
        "hours_ahead": hours,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }

@router.post("/sync")
async def force_sync(background_tasks: BackgroundTasks):
    """
    🔄 Force le refresh du calendrier (invalide cache)
    """
    
    cache_manager.invalidate_cache()
    
    # Rescrape en background
    background_tasks.add_task(aggregator.get_today_events)
    
    return {"status": "syncing", "message": "Cache invalidé, rescraping en cours"}

@router.get("/history")
async def get_history(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    📜 Historique des événements d'un jour passé (depuis DB)
    """
    
    from app.models.database import EconomicEventDB
    
    events = db.query(EconomicEventDB).filter_by(date=date).all()
    
    return {
        "date": date,
        "events": [
            {
                "time": e.time,
                "currency": e.currency,
                "event": e.event,
                "impact": e.impact,
                "actual": e.actual,
                "forecast": e.forecast,
                "previous": e.previous
            }
            for e in events
        ],
        "count": len(events)
    }