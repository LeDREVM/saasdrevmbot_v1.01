from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.services.economic_calendar.base_scraper import EconomicEvent, ImpactLevel
from app.services.stats.correlation_analyzer import CorrelationAnalyzer
from app.models.database import EconomicEventDB

logger = logging.getLogger(__name__)

class AlertPredictor:
    """
    Prédit l'impact potentiel d'un événement à venir basé sur l'historique
    """
    
    def __init__(self):
        self.analyzer = CorrelationAnalyzer()
        
        # Seuils configurables
        self.HIGH_IMPACT_THRESHOLD = 20  # pips
        self.MEDIUM_IMPACT_THRESHOLD = 10
        self.CONFIDENCE_THRESHOLD = 3  # min 3 événements historiques
    
    def predict_upcoming_impact(
        self,
        upcoming_event: EconomicEvent,
        symbol: str,
        db: Session
    ) -> Optional[Dict]:
        """
        Prédit l'impact d'un événement à venir
        
        Returns:
        {
            'event': {...},
            'symbol': str,
            'prediction': {
                'expected_movement_pips': float,
                'confidence': str,  # 'high', 'medium', 'low'
                'historical_samples': int,
                'direction_probability': {'up': float, 'down': float, 'neutral': float},
                'volatility_increase_expected': float,
                'risk_level': str  # 'extreme', 'high', 'medium', 'low'
            },
            'recommendation': str,
            'time_until_event': str
        }
        """
        
        try:
            # 1. Chercher événements similaires dans l'historique
            similar_events = self._find_similar_historical_events(
                upcoming_event,
                db,
                lookback_days=180  # 6 mois d'historique
            )
            
            if len(similar_events) < self.CONFIDENCE_THRESHOLD:
                logger.warning(f"Pas assez d'historique pour {upcoming_event.event} ({len(similar_events)} samples)")
                return None
            
            # 2. Analyser les événements historiques
            historical_analyses = self.analyzer.analyze_historical_events(
                similar_events,
                symbol,
                min_impact="Medium"
            )
            
            if not historical_analyses:
                return None
            
            # 3. Calculer les statistiques prédictives
            prediction = self._calculate_prediction_stats(historical_analyses)
            
            # 4. Générer la recommandation
            recommendation = self._generate_recommendation(prediction, upcoming_event)
            
            # 5. Calculer temps restant
            time_until = self._format_time_until(upcoming_event.datetime_obj)
            
            return {
                'event': {
                    'date': upcoming_event.date,
                    'time': upcoming_event.time,
                    'currency': upcoming_event.currency,
                    'event_name': upcoming_event.event,
                    'impact_level': upcoming_event.impact.value,
                    'actual': upcoming_event.actual,
                    'forecast': upcoming_event.forecast,
                    'previous': upcoming_event.previous
                },
                'symbol': symbol,
                'prediction': prediction,
                'recommendation': recommendation,
                'time_until_event': time_until,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return None
    
    def _find_similar_historical_events(
        self,
        upcoming_event: EconomicEvent,
        db: Session,
        lookback_days: int = 180
    ) -> List[EconomicEvent]:
        """
        Trouve des événements similaires dans l'historique
        Matching sur: nom d'événement similaire + même devise
        """
        
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Recherche par nom d'événement (LIKE) et devise
        similar = db.query(EconomicEventDB).filter(
            EconomicEventDB.event.ilike(f"%{upcoming_event.event[:20]}%"),
            EconomicEventDB.currency == upcoming_event.currency,
            EconomicEventDB.date >= cutoff_date.strftime("%Y-%m-%d"),
            EconomicEventDB.date < datetime.now().strftime("%Y-%m-%d")  # Seulement passé
        ).all()
        
        # Convertir en EconomicEvent
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
            for e in similar
        ]
        
        logger.info(f"Trouvé {len(events)} événements similaires pour '{upcoming_event.event}'")
        
        return events
    
    def _calculate_prediction_stats(self, analyses: List[Dict]) -> Dict:
        """Calcule les statistiques prédictives"""
        
        total = len(analyses)
        
        # Mouvement moyen
        avg_movement = sum(a['impact']['movement_pips'] for a in analyses) / total
        
        # Direction probabilities
        up_count = sum(1 for a in analyses if a['impact']['direction'] == 'up')
        down_count = sum(1 for a in analyses if a['impact']['direction'] == 'down')
        neutral_count = sum(1 for a in analyses if a['impact']['direction'] == 'neutral')
        
        direction_probs = {
            'up': round((up_count / total) * 100, 1),
            'down': round((down_count / total) * 100, 1),
            'neutral': round((neutral_count / total) * 100, 1)
        }
        
        # Volatilité moyenne post-event
        avg_pre_vol = sum(a['impact']['pre_volatility'] for a in analyses) / total
        avg_post_vol = sum(a['impact']['post_volatility_1h'] for a in analyses) / total
        vol_increase = ((avg_post_vol - avg_pre_vol) / avg_pre_vol * 100) if avg_pre_vol > 0 else 0
        
        # Confiance basée sur nombre de samples
        if total >= 10:
            confidence = 'high'
        elif total >= 5:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Niveau de risque
        if avg_movement > self.HIGH_IMPACT_THRESHOLD:
            risk_level = 'extreme'
        elif avg_movement > self.MEDIUM_IMPACT_THRESHOLD:
            risk_level = 'high'
        elif avg_movement > 5:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'expected_movement_pips': round(avg_movement, 1),
            'confidence': confidence,
            'historical_samples': total,
            'direction_probability': direction_probs,
            'volatility_increase_expected': round(vol_increase, 1),
            'risk_level': risk_level,
            'avg_pre_volatility': round(avg_pre_vol, 4),
            'avg_post_volatility': round(avg_post_vol, 4)
        }
    
    def _generate_recommendation(self, prediction: Dict, event: EconomicEvent) -> str:
        """Génère une recommandation actionnable"""
        
        risk = prediction['risk_level']
        movement = prediction['expected_movement_pips']
        confidence = prediction['confidence']
        
        # Direction dominante
        probs = prediction['direction_probability']
        dominant_dir = max(probs, key=probs.get)
        dominant_prob = probs[dominant_dir]
        
        recommendations = {
            'extreme': f"🔴 ALERTE EXTRÊME - Mouvement attendu: {movement} pips. "
                      f"Probabilité {dominant_dir}: {dominant_prob}%. "
                      f"ÉVITER de trader 30min avant et 1h après. "
                      f"Ou attendre fin de volatilité pour entrer sur retracement.",
            
            'high': f"🟡 RISQUE ÉLEVÉ - Mouvement attendu: {movement} pips. "
                   f"Si tu trades: reduce position size 50%, stops larges (+{int(movement * 1.5)} pips). "
                   f"Attendre confirmation post-event recommandé.",
            
            'medium': f"🟢 RISQUE MODÉRÉ - Mouvement attendu: {movement} pips. "
                     f"Trading possible avec prudence. Surveiller réaction initiale. "
                     f"Stop loss +{int(movement * 1.2)} pips.",
            
            'low': f"⚪ RISQUE FAIBLE - Impact historique limité ({movement} pips). "
                  f"Trading normal possible. Surveiller quand même."
        }
        
        base_rec = recommendations.get(risk, "")
        
        # Ajouter note sur confiance
        if confidence == 'low':
            base_rec += f" ⚠️ Confiance faible ({prediction['historical_samples']} échantillons seulement)."
        
        return base_rec
    
    def _format_time_until(self, event_time: datetime) -> str:
        """Formate le temps restant de manière lisible"""
        
        now = datetime.now()
        delta = event_time - now
        
        if delta.total_seconds() < 0:
            return "MAINTENANT"
        
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        
        if hours > 24:
            days = hours // 24
            return f"Dans {days}j {hours % 24}h"
        elif hours > 0:
            return f"Dans {hours}h {minutes}min"
        else:
            return f"Dans {minutes}min"