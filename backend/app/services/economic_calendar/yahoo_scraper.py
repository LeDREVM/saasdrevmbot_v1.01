import logging
from datetime import datetime, timedelta
from typing import List

import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseEconomicScraper, EconomicEvent, ImpactLevel

logger = logging.getLogger(__name__)


class YahooCalendarScraper(BaseEconomicScraper):
    """
    Scraper pour le calendrier économique Yahoo Finance (version FR).
    Utilise les tableaux HTML publics comme sur:
    https://fr.finance.yahoo.com/calendrier/economic
    """

    def __init__(self):
        super().__init__()
        self.base_url = "https://fr.finance.yahoo.com/calendrier/economic"
        self.headers.update(
            {
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "Referer": "https://fr.finance.yahoo.com/",
            }
        )

    def scrape_day(self, date: datetime) -> List[EconomicEvent]:
        """
        Récupère les événements pour un jour spécifique.
        """
        params = {
            "from": date.strftime("%Y-%m-%d"),
            "to": date.strftime("%Y-%m-%d"),
            "day": date.strftime("%Y-%m-%d"),
        }

        try:
            logger.info(f"[YAHOO] Fetching {date.strftime('%Y-%m-%d')}")
            resp = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=20,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.find("table")
            if not table:
                logger.warning("[YAHOO] Aucun tableau trouvé pour ce jour")
                return []

            events: List[EconomicEvent] = []
            tbody = table.find("tbody")
            if not tbody:
                return []

            rows = tbody.find_all("tr")
            for row in rows:
                try:
                    event = self._parse_row(row, date)
                    if event and event.event:
                        events.append(event)
                except Exception as e:
                    logger.debug(f"[YAHOO] Ligne ignorée: {e}")
                    continue

            logger.info(f"[YAHOO] {len(events)} événements récupérés")
            return events
        except requests.RequestException as e:
            logger.error(f"[YAHOO] Erreur réseau: {e}")
            return []
        except Exception as e:
            logger.error(f"[YAHOO] Erreur parsing: {e}")
            return []

    def _parse_row(self, row, date: datetime) -> EconomicEvent:
        """
        Parse une ligne du tableau Yahoo.
        Colonnes (d’après l’exemple partagé):
        - Événement
        - Pays
        - Heure de l’événement
        - Pendant
        - Réels
        - Attentes du marché
        - Avant
        """
        cols = row.find_all("td")
        if len(cols) < 7:
            raise ValueError("ligne incomplète")

        event_name = cols[0].get_text(strip=True)
        country = cols[1].get_text(strip=True)
        time_str = cols[2].get_text(strip=True)  # ex: "12:30 UTC"
        actual = cols[4].get_text(strip=True) or None
        forecast = cols[5].get_text(strip=True) or None
        previous = cols[6].get_text(strip=True) or None

        # Extraire "HH:MM" depuis "12:30 UTC"
        time_hhmm = "00:00"
        try:
            parts = time_str.split()
            if parts:
                time_hhmm = parts[0]
        except Exception:
            pass

        currency = self._map_country_to_currency(country)
        impact = self._infer_impact(event_name)

        return EconomicEvent(
            source="yahoo",
            date=date.strftime("%Y-%m-%d"),
            time=time_hhmm,
            currency=currency,
            event=event_name,
            impact=impact,
            actual=actual,
            forecast=forecast,
            previous=previous,
        )

    def _map_country_to_currency(self, country: str) -> str:
        mapping = {
            "US": "USD",
            "États-Unis": "USD",
            "FR": "EUR",
            "DE": "EUR",
            "ES": "EUR",
            "IT": "EUR",
            "NL": "EUR",
            "FI": "EUR",
            "NO": "NOK",
            "SE": "SEK",
            "CH": "CHF",
            "GB": "GBP",
            "UK": "GBP",
            "CA": "CAD",
            "AU": "AUD",
            "NZ": "NZD",
            "JP": "JPY",
            "CN": "CNY",
            "IN": "INR",
            "BR": "BRL",
            "TR": "TRY",
            "NG": "NGN",
            "PL": "PLN",
            "CZ": "CZK",
        }
        # Pays affiché sous forme code (NL, FI, ...) d’après l’exemple
        return mapping.get(country, "USD")

    def _infer_impact(self, event_name: str) -> ImpactLevel:
        """
        Approxime l’impact à partir du nom de l’événement.
        """
        high_kw = [
            "CPI",
            "Inflation",
            "Interest Rate",
            "Fed",
            "ECB",
            "GDP",
            "Unemployment",
            "Nonfarm",
            "NFP",
        ]
        med_kw = ["PPI", "PMI", "Retail Sales", "Trade Balance", "Industrial Production"]

        lower = event_name.lower()
        for k in high_kw:
            if k.lower() in lower:
                return ImpactLevel.HIGH
        for k in med_kw:
            if k.lower() in lower:
                return ImpactLevel.MEDIUM
        return ImpactLevel.LOW

    def scrape_week(self) -> List[EconomicEvent]:
        """
        Récupère 7 jours d’événements à partir d’aujourd’hui.
        """
        events: List[EconomicEvent] = []
        today = datetime.now()
        for i in range(7):
            d = today + timedelta(days=i)
            events.extend(self.scrape_day(d))
        return events

