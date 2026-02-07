from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.services.economic_calendar.base_scraper import EconomicEvent
from app.services.stats.price_fetcher import PriceFetcher
from app.services.stats.impact_calculator import ImpactCalculator

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Analyse la corrélation entre événements économiques et mouvements de prix"""
    
    def __init__(self):
        self.price_fetcher = PriceFetcher()
        self.impact_calculator = ImpactCalculator()
    
    def analyze_event(
        self,
        event: EconomicEvent,
        symbol: str
    ) -> Optional[Dict]:
        """
        Analyse l'impact d'un événement spécifique
        
        Returns:
        {
            'event': {...},
            'symbol': str,
            'impact': {...},
            'analyzed_at': str
        }
        """
        
        try:
            # Récupérer les prix autour de l'événement
            price_df = self.price_fetcher.get_price_around_event(
                symbol=symbol,
                event_datetime=event.datetime_obj,
                minutes_before=30,
                minutes_after=240
            )
            
            if price_df is None:
                logger.warning(f"Pas de données prix pour {symbol} à {event.datetime_obj}")
                return None
            
            # Calculer l'impact
            impact = self.impact_calculator.calculate_event_impact(
                price_df=price_df,
                event_datetime=event.datetime_obj
            )
            
            if impact is None:
                return None
            
            return {
                'event': {
                    'date': event.date,
                    'time': event.time,
                    'currency': event.currency,
                    'event_name': event.event,
                    'impact_level': event.impact.value,
                    'actual': event.actual,
                    'forecast': event.forecast,
                    'previous': event.previous
                },
                'symbol': symbol,
                'impact': impact,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse événement: {e}")
            return None
    
    def analyze_historical_events(
        self,
        events: List[EconomicEvent],
        symbol: str,
        min_impact: str = "Medium"
    ) -> List[Dict]:
        """
        Analyse en batch plusieurs événements historiques
        
        Filtrage automatique par impact et pertinence
        """
        
        results = []
        
        # Filtrer événements pertinents pour le symbole
        relevant_events = self._filter_relevant_events(events, symbol)
        
        logger.info(f"Analyse de {len(relevant_events)} événements pour {symbol}...")
        
        for event in relevant_events:
            # Skip low impact si demandé
            if min_impact == "High" and event.impact.value != "High":
                continue
            if min_impact == "Medium" and event.impact.value == "Low":
                continue
            
            analysis = self.analyze_event(event, symbol)
            
            if analysis:
                results.append(analysis)
        
        logger.info(f"✅ {len(results)} événements analysés avec succès")
        
        return results
    
    def _filter_relevant_events(
        self,
        events: List[EconomicEvent],
        symbol: str
    ) -> List[EconomicEvent]:
        """Filtre les événements pertinents pour un symbole donné"""
        
        # Mapping symbole → devises pertinentes
        symbol_currencies = {
            'EURUSD': ['EUR', 'USD'],
            'GBPUSD': ['GBP', 'USD'],
            'USDJPY': ['USD', 'JPY'],
            'AUDUSD': ['AUD', 'USD'],
            'USDCAD': ['USD', 'CAD'],
            'XAUUSD': ['USD'],  # Gold sensible à USD
            'SPX': ['USD'],     # S&P500
            'NDX': ['USD'],     # Nasdaq
        }
        
        relevant_currencies = symbol_currencies.get(symbol, ['USD'])
        
        return [
            e for e in events
            if e.currency in relevant_currencies
        ]
    
    def generate_stats_summary(
        self,
        analyses: List[Dict]
    ) -> Dict:
        """
        Génère des stats agrégées à partir d'analyses individuelles
        
        Returns:
        {
            'total_events': int,
            'avg_volatility_increase': float,
            'impact_rate': float,  # % événements avec impact significatif
            'avg_movement_pips': float,
            'direction_stats': {'up': int, 'down': int, 'neutral': int},
            'by_event_type': {...}
        }
        """
        
        if not analyses:
            return {}
        
        total = len(analyses)
        had_impact_count = sum(1 for a in analyses if a['impact']['had_impact'])
        
        # Moyennes
        avg_pre_vol = sum(a['impact']['pre_volatility'] for a in analyses) / total
        avg_post_vol = sum(a['impact']['post_volatility_1h'] for a in analyses) / total
        avg_movement = sum(a['impact']['movement_pips'] for a in analyses) / total
        
        # Direction stats
        direction_counts = {
            'up': sum(1 for a in analyses if a['impact']['direction'] == 'up'),
            'down': sum(1 for a in analyses if a['impact']['direction'] == 'down'),
            'neutral': sum(1 for a in analyses if a['impact']['direction'] == 'neutral')
        }
        
        # Par type d'événement
        by_event = {}
        for analysis in analyses:
            event_name = analysis['event']['event_name']
            if event_name not in by_event:
                by_event[event_name] = {
                    'count': 0,
                    'avg_impact': 0,
                    'avg_pips': 0
                }
            by_event[event_name]['count'] += 1
            by_event[event_name]['avg_impact'] += analysis['impact']['post_volatility_1h']
            by_event[event_name]['avg_pips'] += analysis['impact']['movement_pips']
        
        # Moyennes finales
        for event_name in by_event:
            count = by_event[event_name]['count']
            by_event[event_name]['avg_impact'] = round(by_event[event_name]['avg_impact'] / count, 4)
            by_event[event_name]['avg_pips'] = round(by_event[event_name]['avg_pips'] / count, 1)
        
        return {
            'total_events': total,
            'had_impact_count': had_impact_count,
            'impact_rate': round((had_impact_count / total) * 100, 1),
            'avg_pre_volatility': round(avg_pre_vol, 4),
            'avg_post_volatility': round(avg_post_vol, 4),
            'volatility_increase': round(((avg_post_vol - avg_pre_vol) / avg_pre_vol * 100) if avg_pre_vol > 0 else 0, 1),
            'avg_movement_pips': round(avg_movement, 1),
            'direction_stats': direction_counts,
            'by_event_type': dict(sorted(by_event.items(), key=lambda x: x[1]['avg_pips'], reverse=True)[:10])
        }