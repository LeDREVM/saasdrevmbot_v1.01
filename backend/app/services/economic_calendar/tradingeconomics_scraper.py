"""
Scraper pour Trading Economics Calendar
Récupère les événements économiques depuis https://tradingeconomics.com/calendar
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import time

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TradingEconomicsScraper(BaseScraper):
    """Scraper pour le calendrier économique de Trading Economics"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://tradingeconomics.com/calendar"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    def scrape(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Récupère les événements économiques
        
        Args:
            start_date: Date de début (par défaut: aujourd'hui)
            end_date: Date de fin (par défaut: dans 7 jours)
            
        Returns:
            Liste des événements économiques
        """
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        logger.info(f"🔍 Scraping Trading Economics du {start_date.date()} au {end_date.date()}")
        
        events = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                date_events = self._scrape_date(current_date)
                events.extend(date_events)
                logger.info(f"✅ {len(date_events)} événements trouvés pour {current_date.date()}")
                
                # Pause pour éviter de surcharger le serveur
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du scraping pour {current_date.date()}: {e}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"✅ Total: {len(events)} événements récupérés")
        return events
    
    def _scrape_date(self, date: datetime) -> List[Dict]:
        """Récupère les événements pour une date spécifique"""
        
        # Format de l'URL: /calendar?d=2024-02-07
        url = f"{self.base_url}?d={date.strftime('%Y-%m-%d')}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Trouver le tableau des événements
            table = soup.find('table', {'id': 'calendar'})
            if not table:
                logger.warning(f"Tableau du calendrier non trouvé pour {date.date()}")
                return events
            
            # Parser les lignes du tableau
            rows = table.find('tbody').find_all('tr', {'data-url': True})
            
            for row in rows:
                try:
                    event = self._parse_event_row(row, date)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Erreur lors du parsing d'une ligne: {e}")
                    continue
            
            return events
            
        except requests.RequestException as e:
            logger.error(f"Erreur de requête pour {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            return []
    
    def _parse_event_row(self, row, date: datetime) -> Optional[Dict]:
        """Parse une ligne du tableau d'événements"""
        
        try:
            # Extraire les données
            time_cell = row.find('td', {'class': 'calendar-time'})
            country_cell = row.find('td', {'class': 'calendar-country'})
            event_cell = row.find('td', {'class': 'calendar-event'})
            actual_cell = row.find('td', {'class': 'calendar-actual'})
            forecast_cell = row.find('td', {'class': 'calendar-forecast'})
            previous_cell = row.find('td', {'class': 'calendar-previous'})
            
            # Temps
            time_str = time_cell.text.strip() if time_cell else "00:00"
            
            # Pays et devise
            country = ""
            currency = ""
            if country_cell:
                country_title = country_cell.get('title', '')
                country = country_title.split('-')[0].strip() if '-' in country_title else country_title
                
                # Mapper les pays vers les devises
                currency_map = {
                    'United States': 'USD',
                    'Euro Area': 'EUR',
                    'Germany': 'EUR',
                    'France': 'EUR',
                    'Italy': 'EUR',
                    'Spain': 'EUR',
                    'United Kingdom': 'GBP',
                    'Japan': 'JPY',
                    'Switzerland': 'CHF',
                    'Canada': 'CAD',
                    'Australia': 'AUD',
                    'New Zealand': 'NZD',
                    'China': 'CNY'
                }
                currency = currency_map.get(country, 'USD')
            
            # Nom de l'événement
            event_name = event_cell.text.strip() if event_cell else "Unknown Event"
            
            # Valeurs
            actual = actual_cell.text.strip() if actual_cell else ""
            forecast = forecast_cell.text.strip() if forecast_cell else ""
            previous = previous_cell.text.strip() if previous_cell else ""
            
            # Déterminer l'impact (basé sur l'importance de l'événement)
            impact = self._determine_impact(event_name, actual, forecast)
            
            # Construire le datetime
            event_datetime = self._parse_datetime(date, time_str)
            
            event = {
                'date': event_datetime.isoformat(),
                'time': time_str,
                'currency': currency,
                'country': country,
                'event': event_name,
                'impact': impact,
                'actual': actual,
                'forecast': forecast,
                'previous': previous,
                'source': 'tradingeconomics'
            }
            
            return event
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un événement: {e}")
            return None
    
    def _parse_datetime(self, date: datetime, time_str: str) -> datetime:
        """Parse la date et l'heure de l'événement"""
        try:
            if time_str and time_str != "Tentative":
                hour, minute = map(int, time_str.split(':'))
                return date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                return date.replace(hour=0, minute=0, second=0, microsecond=0)
        except:
            return date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _determine_impact(self, event_name: str, actual: str, forecast: str) -> str:
        """Détermine l'impact de l'événement"""
        
        # Événements à fort impact
        high_impact_keywords = [
            'NFP', 'Non-Farm', 'Employment', 'GDP', 'Interest Rate',
            'CPI', 'Inflation', 'Fed', 'ECB', 'Central Bank',
            'Unemployment', 'Retail Sales', 'PMI Manufacturing'
        ]
        
        # Événements à impact moyen
        medium_impact_keywords = [
            'PMI', 'Consumer Confidence', 'Industrial Production',
            'Trade Balance', 'Housing', 'PPI', 'Durable Goods'
        ]
        
        event_lower = event_name.lower()
        
        for keyword in high_impact_keywords:
            if keyword.lower() in event_lower:
                return 'high'
        
        for keyword in medium_impact_keywords:
            if keyword.lower() in event_lower:
                return 'medium'
        
        # Impact élevé si grosse différence entre actual et forecast
        if actual and forecast:
            try:
                actual_val = float(actual.replace('%', '').replace('K', '000').replace('M', '000000'))
                forecast_val = float(forecast.replace('%', '').replace('K', '000').replace('M', '000000'))
                
                if abs(actual_val - forecast_val) / max(abs(forecast_val), 1) > 0.5:
                    return 'high'
            except:
                pass
        
        return 'low'
    
    def get_today_events(self) -> List[Dict]:
        """Récupère les événements d'aujourd'hui"""
        today = datetime.now()
        return self.scrape(start_date=today, end_date=today)
    
    def get_week_events(self) -> List[Dict]:
        """Récupère les événements de la semaine"""
        today = datetime.now()
        end_date = today + timedelta(days=7)
        return self.scrape(start_date=today, end_date=end_date)
