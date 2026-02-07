import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import logging
from .base_scraper import BaseEconomicScraper, EconomicEvent, ImpactLevel

logger = logging.getLogger(__name__)

class ForexFactoryScraper(BaseEconomicScraper):
    """Scraper ForexFactory avec gestion d'erreurs robuste"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.forexfactory.com/calendar"
    
    def scrape_day(self, date: datetime) -> List[EconomicEvent]:
        """Récupère événements d'un jour spécifique"""
        
        date_str = date.strftime("%b%d.%Y").lower()
        url = f"{self.base_url}?day={date_str}"
        
        try:
            logger.info(f"[FF] Scraping {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            calendar_rows = soup.find_all('tr', class_='calendar__row')
            
            for row in calendar_rows:
                try:
                    event = self._parse_row(row, date)
                    if event and event.currency and event.event:
                        events.append(event)
                except Exception as e:
                    logger.debug(f"[FF] Skip row: {e}")
                    continue
            
            logger.info(f"[FF] {len(events)} événements récupérés pour {date_str}")
            return events
            
        except requests.RequestException as e:
            logger.error(f"[FF] Erreur réseau: {e}")
            return []
        except Exception as e:
            logger.error(f"[FF] Erreur parsing: {e}")
            return []
    
    def _parse_row(self, row, date: datetime) -> EconomicEvent:
        """Parse une ligne du calendrier"""
        
        time_elem = row.find('td', class_='calendar__time')
        currency_elem = row.find('td', class_='calendar__currency')
        impact_elem = row.find('td', class_='calendar__impact')
        event_elem = row.find('td', class_='calendar__event')
        actual_elem = row.find('td', class_='calendar__actual')
        forecast_elem = row.find('td', class_='calendar__forecast')
        previous_elem = row.find('td', class_='calendar__previous')
        
        # Déterminer l'impact
        impact = ImpactLevel.LOW
        if impact_elem:
            impact_spans = impact_elem.find_all('span', class_='calendar__impact-icon')
            span_count = len(impact_spans)
            if span_count >= 3:
                impact = ImpactLevel.HIGH
            elif span_count >= 2:
                impact = ImpactLevel.MEDIUM
        
        return EconomicEvent(
            source="forexfactory",
            date=date.strftime("%Y-%m-%d"),
            time=time_elem.text.strip() if time_elem else "00:00",
            currency=currency_elem.text.strip() if currency_elem else "",
            event=event_elem.text.strip() if event_elem else "",
            impact=impact,
            actual=actual_elem.text.strip() if actual_elem else None,
            forecast=forecast_elem.text.strip() if forecast_elem else None,
            previous=previous_elem.text.strip() if previous_elem else None
        )
    
    def scrape_week(self) -> List[EconomicEvent]:
        """Récupère 7 jours d'événements"""
        all_events = []
        current_date = datetime.now()
        
        for i in range(7):
            date = current_date + timedelta(days=i)
            events = self.scrape_day(date)
            all_events.extend(events)
        
        return all_events