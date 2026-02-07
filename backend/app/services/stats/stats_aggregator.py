import json
import redis
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.services.stats.correlation_analyzer import CorrelationAnalyzer
from app.models.database import EconomicEventDB

logger = logging.getLogger(__name__)

class StatsAggregator:
    """Agrège et cache les statistiques pour le dashboard"""
    
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.analyzer = CorrelationAnalyzer()
        self.cache_ttl = 3600  # 1 heure
    
    def get_dashboard_stats(
        self,
        symbol: str,
        days_back: int = 30,
        db: Session = None
    ) -> Dict:
        """
        Récupère les stats complètes pour le dashboard
        
        Returns:
        {
            'summary': {...},
            'top_impact_events': [...],
            'heatmap_data': {...},
            'timeline': [...]
        }
        """
        
        cache_key = f"dashboard_stats:{symbol}:{days_back}"
        
        # Check cache
        cached = self.redis_client.get(cache_key)
        if cached:
            logger.info(f"✅ Stats dashboard en cache: {symbol}")
            return json.loads(cached)
        
        logger.info(f"🔄 Génération stats dashboard pour {symbol}...")
        
        # Récupérer événements historiques depuis DB
        if db:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            historical_events = db.query(EconomicEventDB).filter(
                EconomicEventDB.date >= cutoff_date.strftime("%Y-%m-%d")
            ).all()
            
            # Convertir en EconomicEvent objects
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
                for e in historical_events
            ]
        else:
            events = []
        
        if not events:
            return {
                'summary': {},
                'top_impact_events': [],
                'heatmap_data': {},
                'timeline': []
            }
        
        # Analyser les événements
        analyses = self.analyzer.analyze_historical_events(
            events=events,
            symbol=symbol,
            min_impact="Medium"
        )
        
        # Générer summary
        summary = self.analyzer.generate_stats_summary(analyses)
        
        # Top 10 événements à fort impact
        top_events = sorted(
            analyses,
            key=lambda x: x['impact']['movement_pips'],
            reverse=True
        )[:10]
        
        # Heatmap data (jour de la semaine × heure)
        heatmap_data = self._generate_heatmap_data(analyses)
        
        # Timeline (pour graphique)
        timeline = self._generate_timeline_data(analyses)
        
        result = {
            'symbol': symbol,
            'period_days': days_back,
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'top_impact_events': top_events,
            'heatmap_data': heatmap_data,
            'timeline': timeline
        }
        
        # Cache
        self.redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(result)
        )
        
        logger.info(f"✅ Stats générées et cachées: {symbol}")
        
        return result
    
    def _generate_heatmap_data(self, analyses: List[Dict]) -> Dict:
        """
        Génère données pour heatmap jour × heure
        
        Returns:
        {
            'Monday': {0: 2.5, 1: 0, ..., 23: 5.2},
            'Tuesday': {...},
            ...
        }
        """
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap = {day: {hour: [] for hour in range(24)} for day in days}
        
        for analysis in analyses:
            event_dt = datetime.fromisoformat(analysis['event']['date'] + 'T' + analysis['event']['time'])
            day_name = event_dt.strftime('%A')
            hour = event_dt.hour
            
            movement = analysis['impact']['movement_pips']
            
            if day_name in heatmap:
                heatmap[day_name][hour].append(movement)
        
        # Moyennes
        heatmap_avg = {}
        for day in days:
            heatmap_avg[day] = {}
            for hour in range(24):
                movements = heatmap[day][hour]
                heatmap_avg[day][hour] = round(sum(movements) / len(movements), 1) if movements else 0
        
        return heatmap_avg
    
    def _generate_timeline_data(self, analyses: List[Dict]) -> List[Dict]:
        """
        Génère données pour timeline graphique
        
        Returns: Liste triée chronologiquement
        """
        
        timeline = []
        
        for analysis in analyses:
            timeline.append({
                'timestamp': analysis['event']['date'] + 'T' + analysis['event']['time'],
                'event_name': analysis['event']['event_name'],
                'currency': analysis['event']['currency'],
                'impact_level': analysis['event']['impact_level'],
                'movement_pips': analysis['impact']['movement_pips'],
                'direction': analysis['impact']['direction'],
                'had_impact': analysis['impact']['had_impact']
            })
        
        # Trier par timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        return timeline