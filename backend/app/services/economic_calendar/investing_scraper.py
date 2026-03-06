import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import logging
from .base_scraper import BaseEconomicScraper, EconomicEvent, ImpactLevel

logger = logging.getLogger(__name__)

class InvestingScraper(BaseEconomicScraper):
    """Scraper pour Investing.com economic calendar"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.investing.com/economic-calendar"
        self.headers.update({
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://www.investing.com/'
        })
    
    def scrape_day(self, date: datetime) -> List[EconomicEvent]:
        """Récupère événements via l'API Investing.com"""
        
        # Investing.com utilise une API JSON
        api_url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
        
        # Timestamps pour le jour
        date_from = int(date.replace(hour=0, minute=0, second=0).timestamp())
        date_to = int(date.replace(hour=23, minute=59, second=59).timestamp())
        
        payload = {
            'dateFrom': date_from,
            'dateTo': date_to,
            'timeZone': '56',  # GMT-4 (Guadeloupe)
            'timeFilter': 'timeRemain',
            'currentTab': 'today',
            'limit_from': 0
        }
        
        try:
            logger.info(f"[INV] Fetching {date.strftime('%Y-%m-%d')}")
            response = requests.post(
                api_url,
                headers=self.headers,
                data=payload,
                timeout=15
            )
            response.raise_for_status()
            
            # Parse HTML retourné
            soup = BeautifulSoup(response.text, 'html.parser')
            events = []
            
            rows = soup.find_all('tr', class_='js-event-item')
            
            for row in rows:
                try:
                    event = self._parse_json_row(row, date)
                    if event and event.currency and event.event:
                        events.append(event)
                except Exception as e:
                    logger.debug(f"[INV] Skip row: {e}")
                    continue
            
            logger.info(f"[INV] {len(events)} événements récupérés")
            return events
            
        except requests.RequestException as e:
            logger.error(f"[INV] Erreur réseau: {e}")
            return []
        except Exception as e:
            logger.error(f"[INV] Erreur parsing: {e}")
            return []
    
    def _parse_json_row(self, row, date: datetime) -> EconomicEvent:
        """Parse une ligne de l'API Investing"""
        
        # Extraire les attributs data-*
        event_id = row.get('data-event-id', '')
        
        # Time
        time_elem = row.find('td', class_='time')
        time_str = time_elem.text.strip() if time_elem else "00:00"
        
        # Currency (flag)
        flag_elem = row.find('td', class_='flagCur')
        currency = flag_elem.text.strip() if flag_elem else ""
        
        # Impact (1=Low, 2=Medium, 3=High)
        impact_elem = row.find('td', class_='sentiment')
        impact = ImpactLevel.LOW
        if impact_elem:
            bull_icons = impact_elem.find_all('i', class_='grayFullBullishIcon')
            if len(bull_icons) >= 3:
                impact = ImpactLevel.HIGH
            elif len(bull_icons) >= 2:
                impact = ImpactLevel.MEDIUM
        
        # Event name
        event_elem = row.find('td', class_='event')
        event_name = event_elem.find('a').text.strip() if event_elem and event_elem.find('a') else ""
        
        # Actual, Forecast, Previous
        actual_elem = row.find('td', {'id': f'eventActual_{event_id}'})
        forecast_elem = row.find('td', {'id': f'eventForecast_{event_id}'})
        previous_elem = row.find('td', {'id': f'eventPrevious_{event_id}'})
        
        return EconomicEvent(
            source="investing",
            date=date.strftime("%Y-%m-%d"),
            time=time_str,
            currency=currency,
            event=event_name,
            impact=impact,
            actual=actual_elem.text.strip() if actual_elem else None,
            forecast=forecast_elem.text.strip() if forecast_elem else None,
            previous=previous_elem.text.strip() if previous_elem else None
        )
    
    def scrape_week(self) -> List[EconomicEvent]:
        """Récupère 7 jours"""
        all_events = []
        current_date = datetime.now()
        
        for i in range(7):
            date = current_date + timedelta(days=i)
            events = self.scrape_day(date)
            all_events.extend(events)
        
        return all_events