from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import List, Optional


class ImpactLevel(Enum):
    """Niveau d'impact d'un événement économique"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class EconomicEvent:
    """Représente un événement économique"""
    source: str  # 'forexfactory', 'investing'
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    currency: str  # USD, EUR, GBP, etc.
    event: str  # Nom de l'événement
    impact: ImpactLevel
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    
    @property
    def datetime_obj(self) -> datetime:
        """Convertit date + time en objet datetime"""
        try:
            return datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback si le format est différent
            return datetime.strptime(self.date, "%Y-%m-%d")
    
    @property
    def is_high_impact(self) -> bool:
        """Vérifie si l'événement est à fort impact"""
        return self.impact == ImpactLevel.HIGH
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour JSON"""
        return {
            'source': self.source,
            'date': self.date,
            'time': self.time,
            'currency': self.currency,
            'event': self.event,
            'impact': self.impact.value,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous
        }


class BaseEconomicScraper(ABC):
    """Classe de base pour les scrapers de calendrier économique"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    @abstractmethod
    def scrape_day(self, date: datetime) -> List[EconomicEvent]:
        """Récupère les événements d'un jour spécifique"""
        pass
    
    @abstractmethod
    def scrape_week(self) -> List[EconomicEvent]:
        """Récupère les événements de la semaine"""
        pass


class BaseScraper:
    """
    Base minimale pour les scrapers qui renvoient des structures dict
    (ex. TradingEconomicsScraper), distincte de BaseEconomicScraper / EconomicEvent.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
