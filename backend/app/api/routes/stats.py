from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.services.stats.stats_aggregator import StatsAggregator
from app.services.stats.correlation_analyzer import CorrelationAnalyzer
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/stats", tags=["Statistics"])

stats_aggregator = StatsAggregator(settings.REDIS_URL)
correlation_analyzer = CorrelationAnalyzer()

@router.get("/dashboard/{symbol}")
async def get_dashboard_stats(
    symbol: str,
    days_back: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    📊 Stats complètes pour le dashboard
    
    **Params:**
    - symbol: EURUSD, GBPUSD, XAUUSD, SPX, etc.
    - days_back: Période d'analyse (7-90 jours)
    
    **Returns:**
```json
 {
        "summary": {
            "total_events": 45,
            "impact_rate": 68.5,
            "avg_movement_pips": 15.3,
            "direction_stats": {...}
        },
        "top_impact_events": [...],
        "heatmap_data": {...},
        "timeline": [...]
    }
```
    """
    
    stats = stats_aggregator.get_dashboard_stats(
        symbol=symbol,
        days_back=days_back,
        db=db
    )
    
    return JSONResponse(content=stats)

@router.get("/event-impact/{symbol}")
async def analyze_single_event(
    symbol: str,
    event_date: str = Query(..., description="YYYY-MM-DD"),
    event_time: str = Query(..., description="HH:MM"),
    event_name: str = Query(..., description="Nom de l'événement")
):
    """
    🎯 Analyse détaillée d'un événement spécifique
    
    **Exemple:** Quel impact a eu le NFP du 2024-01-05 sur EUR/USD ?
    """
    
    from datetime import datetime
    from app.services.economic_calendar.base_scraper import EconomicEvent, ImpactLevel
    
    # Recréer l'événement
    event = EconomicEvent(
        source="manual",
        date=event_date,
        time=event_time,
        currency=symbol[:3],
        event=event_name,
        impact=ImpactLevel.HIGH
    )
    
    analysis = correlation_analyzer.analyze_event(event, symbol)
    
    if not analysis:
        return JSONResponse(
            status_code=404,
            content={"error": "Pas de données disponibles pour cet événement"}
        )
    
    return JSONResponse(content=analysis)

@router.get("/top-movers/{symbol}")
async def get_top_movers(
    symbol: str,
    days_back: int = Query(30, ge=7, le=90),
    limit: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db)
):
    """
    🚀 Top événements qui ont le plus bougé le marché
    
    **Returns:** Liste triée par mouvement en pips
    """
    
    stats = stats_aggregator.get_dashboard_stats(symbol, days_back, db)
    
    top_events = stats.get('top_impact_events', [])[:limit]
    
    return JSONResponse(content={
        "symbol": symbol,
        "period_days": days_back,
        "top_movers": top_events
    })

@router.get("/heatmap/{symbol}")
async def get_volatility_heatmap(
    symbol: str,
    days_back: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    🌡️ Heatmap volatilité par jour/heure
    
    **Returns:** Matrice 7 jours × 24 heures avec volatilité moyenne
    """
    
    stats = stats_aggregator.get_dashboard_stats(symbol, days_back, db)
    
    return JSONResponse(content={
        "symbol": symbol,
        "heatmap": stats.get('heatmap_data', {})
    })

@router.get("/correlation-score")
async def get_correlation_score(
    event_type: str = Query(..., description="NFP, FOMC, CPI, etc."),
    symbol: str = Query(..., description="EURUSD, etc."),
    db: Session = Depends(get_db)
):
    """
    🎲 Score de corrélation: "Quand il y a un NFP, EUR/USD bouge de X pips en moyenne"
    """
    
    from app.models.database import EconomicEventDB
    
    # Récupérer tous les événements de ce type
    events_db = db.query(EconomicEventDB).filter(
        EconomicEventDB.event.ilike(f"%{event_type}%")
    ).all()
    
    if not events_db:
        return JSONResponse(
            status_code=404,
            content={"error": f"Aucun événement trouvé pour '{event_type}'"}
        )
    
    # Convertir et analyser
    from app.services.economic_calendar.base_scraper import EconomicEvent, ImpactLevel
    
    events = [
        EconomicEvent(
            source=e.source,
            date=e.date,
            time=e.time,
            currency=e.currency,
            event=e.event,
            impact=ImpactLevel(e.impact),
            actual=e.actual,
            forecast=e.forecast,
            previous=e.previous
        )
        for e in events_db
    ]
    
    analyses = correlation_analyzer.analyze_historical_events(events, symbol)
    
    if not analyses:
        return JSONResponse(content={
            "event_type": event_type,
            "symbol": symbol,
            "correlation_score": 0,
            "message": "Pas assez de données"
        })
    
    # Calcul score
    avg_movement = sum(a['impact']['movement_pips'] for a in analyses) / len(analyses)
    impact_rate = sum(1 for a in analyses if a['impact']['had_impact']) / len(analyses) * 100
    
    return JSONResponse(content={
        "event_type": event_type,
        "symbol": symbol,
        "sample_size": len(analyses),
        "avg_movement_pips": round(avg_movement, 1),
        "impact_rate": round(impact_rate, 1),
        "correlation_score": round((avg_movement / 50) * (impact_rate / 100) * 10, 1),  # Score 0-10
        "interpretation": _interpret_score(avg_movement, impact_rate)
    })

def _interpret_score(avg_pips: float, impact_rate: float) -> str:
    """Interprétation humaine du score"""
    
    if avg_pips > 30 and impact_rate > 70:
        return "🔥 FORT - Cet événement bouge systématiquement le marché"
    elif avg_pips > 15 and impact_rate > 50:
        return "⚡ MOYEN - Impact régulier mais modéré"
    elif avg_pips > 10 and impact_rate > 30:
        return "📊 FAIBLE - Impact occasionnel"
    else:
        return "💤 NÉGLIGEABLE - Peu d'impact observable"

@router.post("/refresh/{symbol}")
async def refresh_stats(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    🔄 Force le recalcul des stats (invalide cache)
    """
    
    # Invalider cache Redis
    cache_key = f"dashboard_stats:{symbol}:*"
    keys = stats_aggregator.redis_client.keys(cache_key)
    
    if keys:
        stats_aggregator.redis_client.delete(*keys)
    
    # Recalculer
    stats = stats_aggregator.get_dashboard_stats(symbol, 30, db)
    
    return JSONResponse(content={
        "status": "refreshed",
        "symbol": symbol,
        "new_stats": stats['summary']
    })