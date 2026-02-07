from typing import List
from datetime import datetime, timedelta
import logging
from .forexfactory_scraper import ForexFactoryScraper
from .investing_scraper import InvestingScraper
from .base_scraper import EconomicEvent

logger = logging.getLogger(__name__)

class CalendarAggregator:
    """Agrège et déduplique les événements de toutes les sources"""
    
    def __init__(self):
        self.ff_scraper = ForexFactoryScraper()
        self.inv_scraper = InvestingScraper()
    
    def get_today_events(self, currencies: List[str] = None) -> List[EconomicEvent]:
        """Récupère tous les événements du jour"""
        
        logger.info("🔄 Agrégation calendrier du jour...")
        today = datetime.now()
        
        # Scrape les 2 sources en parallèle (optionnel: utiliser asyncio)
        ff_events = self.ff_scraper.scrape_day(today)
        inv_events = self.inv_scraper.scrape_day(today)
        
        # Fusion et déduplication
        all_events = self._merge_events(ff_events, inv_events)
        
        # Filtrer par devises si spécifié
        if currencies:
            all_events = [e for e in all_events if e.currency in currencies]
        
        # Trier par heure
        all_events.sort(key=lambda x: x.datetime_obj)
        
        logger.info(f"✅ {len(all_events)} événements agrégés")
        return all_events
    
    def get_week_events(self, currencies: List[str] = None) -> List[EconomicEvent]:
        """Récupère 7 jours d'événements"""
        
        logger.info("🔄 Agrégation calendrier hebdomadaire...")
        
        ff_events = self.ff_scraper.scrape_week()
        inv_events = self.inv_scraper.scrape_week()
        
        all_events = self._merge_events(ff_events, inv_events)
        
        if currencies:
            all_events = [e for e in all_events if e.currency in currencies]
        
        all_events.sort(key=lambda x: x.datetime_obj)
        
        logger.info(f"✅ {len(all_events)} événements sur 7 jours")
        return all_events
    
    def get_upcoming_high_impact(self, hours_ahead: int = 2) -> List[EconomicEvent]:
        """Événements high impact dans les N prochaines heures"""
        
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)
        
        events = self.get_today_events()
        
        upcoming = [
            e for e in events
            if e.is_high_impact and now <= e.datetime_obj <= cutoff
        ]
        
        return upcoming
    
    def _merge_events(self, ff_events: List[EconomicEvent], 
                     inv_events: List[EconomicEvent]) -> List[EconomicEvent]:
        """
        Fusionne et déduplique les événements
        Priorité: ForexFactory (plus fiable pour forex)
        """
        
        # Index FF events par (date, time, currency, event name similarity)
        ff_index = {
            (e.date, e.time, e.currency, e.event.lower()[:30]): e 
            for e in ff_events
        }
        
        merged = list(ff_events)
        
        # Ajouter Investing events non-dupliqués
        for inv_event in inv_events:
            key = (inv_event.date, inv_event.time, inv_event.currency, 
                   inv_event.event.lower()[:30])
            
            if key not in ff_index:
                # Pas de doublon trouvé, ajouter
                merged.append(inv_event)
            else:
                # Event existe dans FF, enrichir avec données Investing si meilleures
                ff_event = ff_index[key]
                if not ff_event.actual and inv_event.actual:
                    ff_event.actual = inv_event.actual
                if not ff_event.forecast and inv_event.forecast:
                    ff_event.forecast = inv_event.forecast
        
        return merged