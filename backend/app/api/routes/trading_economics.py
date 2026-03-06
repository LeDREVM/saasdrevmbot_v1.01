"""
Routes API pour Trading Economics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.services.economic_calendar.tradingeconomics_scraper import TradingEconomicsScraper

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache simple en mémoire
_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 300  # 5 minutes
}


def get_cached_events():
    """Récupère les événements depuis le cache ou le scraper"""
    now = datetime.now()
    
    # Vérifier si le cache est valide
    if (_cache['data'] is not None and 
        _cache['timestamp'] is not None and 
        (now - _cache['timestamp']).total_seconds() < _cache['ttl']):
        logger.info("📦 Utilisation du cache")
        return _cache['data']
    
    # Sinon, récupérer les nouvelles données
    logger.info("🔄 Récupération de nouvelles données")
    scraper = TradingEconomicsScraper()
    events = scraper.get_today_events()
    
    # Mettre à jour le cache
    _cache['data'] = events
    _cache['timestamp'] = now
    
    return events


@router.get("/today")
async def get_today_events(
    currency: Optional[str] = Query(None, description="Filtrer par devise (ex: USD, EUR)"),
    impact: Optional[str] = Query(None, description="Filtrer par impact (low, medium, high)")
):
    """
    Récupère les événements économiques d'aujourd'hui depuis Trading Economics
    
    - **currency**: Filtrer par devise (optionnel)
    - **impact**: Filtrer par impact (optionnel)
    """
    try:
        events = get_cached_events()
        
        # Appliquer les filtres
        if currency:
            events = [e for e in events if e.get('currency', '').upper() == currency.upper()]
        
        if impact:
            events = [e for e in events if e.get('impact', '').lower() == impact.lower()]
        
        # Trier par heure
        events.sort(key=lambda x: x.get('time', '00:00'))
        
        return {
            "success": True,
            "count": len(events),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "events": events,
            "cache_info": {
                "cached": _cache['timestamp'] is not None,
                "cache_age_seconds": (datetime.now() - _cache['timestamp']).total_seconds() if _cache['timestamp'] else None
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des événements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données: {str(e)}")


@router.get("/week")
async def get_week_events(
    currency: Optional[str] = Query(None, description="Filtrer par devise"),
    impact: Optional[str] = Query(None, description="Filtrer par impact")
):
    """
    Récupère les événements économiques de la semaine depuis Trading Economics
    
    - **currency**: Filtrer par devise (optionnel)
    - **impact**: Filtrer par impact (optionnel)
    """
    try:
        scraper = TradingEconomicsScraper()
        events = scraper.get_week_events()
        
        # Appliquer les filtres
        if currency:
            events = [e for e in events if e.get('currency', '').upper() == currency.upper()]
        
        if impact:
            events = [e for e in events if e.get('impact', '').lower() == impact.lower()]
        
        # Trier par date et heure
        events.sort(key=lambda x: (x.get('date', ''), x.get('time', '00:00')))
        
        # Grouper par date
        events_by_date = {}
        for event in events:
            date = event.get('date', '')[:10]  # YYYY-MM-DD
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        return {
            "success": True,
            "count": len(events),
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "events": events,
            "events_by_date": events_by_date
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des événements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données: {str(e)}")


@router.get("/stats")
async def get_stats():
    """
    Récupère les statistiques des événements d'aujourd'hui
    """
    try:
        events = get_cached_events()
        
        # Calculer les statistiques
        total = len(events)
        high_impact = len([e for e in events if e.get('impact') == 'high'])
        medium_impact = len([e for e in events if e.get('impact') == 'medium'])
        low_impact = len([e for e in events if e.get('impact') == 'low'])
        
        # Compter par devise
        currencies = {}
        for event in events:
            currency = event.get('currency', 'Unknown')
            currencies[currency] = currencies.get(currency, 0) + 1
        
        # Compter par pays
        countries = {}
        for event in events:
            country = event.get('country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        return {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_events": total,
            "by_impact": {
                "high": high_impact,
                "medium": medium_impact,
                "low": low_impact
            },
            "by_currency": currencies,
            "by_country": countries,
            "top_currencies": sorted(currencies.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_countries": sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du calcul des statistiques: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des statistiques: {str(e)}")


@router.post("/refresh")
async def refresh_cache():
    """
    Force le rafraîchissement du cache
    """
    try:
        _cache['data'] = None
        _cache['timestamp'] = None
        
        events = get_cached_events()
        
        return {
            "success": True,
            "message": "Cache rafraîchi avec succès",
            "count": len(events),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du rafraîchissement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du rafraîchissement: {str(e)}")


@router.get("/upcoming")
async def get_upcoming_events(
    minutes: int = Query(60, description="Événements dans les X prochaines minutes")
):
    """
    Récupère les événements à venir dans les X prochaines minutes
    
    - **minutes**: Nombre de minutes (par défaut: 60)
    """
    try:
        events = get_cached_events()
        now = datetime.now()
        
        upcoming = []
        for event in events:
            try:
                event_time = datetime.fromisoformat(event['date'])
                time_diff = (event_time - now).total_seconds() / 60  # En minutes
                
                if 0 <= time_diff <= minutes:
                    event['minutes_until'] = int(time_diff)
                    upcoming.append(event)
            except:
                continue
        
        # Trier par temps restant
        upcoming.sort(key=lambda x: x.get('minutes_until', 999))
        
        return {
            "success": True,
            "count": len(upcoming),
            "minutes": minutes,
            "events": upcoming
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des événements à venir: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
