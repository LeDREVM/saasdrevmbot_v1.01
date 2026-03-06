import redis
import json
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from .base_scraper import EconomicEvent
from app.models.database import EconomicEventDB

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestion du cache Redis + persistance PostgreSQL"""
    
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.cache_ttl = 1800  # 30 minutes
    
    def get_cached_events(self, cache_key: str) -> Optional[List[dict]]:
        """Récupère événements depuis Redis"""
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ Cache HIT: {cache_key}")
                return json.loads(cached)
            logger.info(f"❌ Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Erreur cache: {e}")
            return None
    
    def set_cached_events(self, cache_key: str, events: List[EconomicEvent]):
        """Stocke événements dans Redis"""
        
        try:
            events_dict = [e.to_dict() for e in events]
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(events_dict)
            )
            logger.info(f"💾 Cached {len(events)} events: {cache_key}")
        except Exception as e:
            logger.error(f"Erreur cache write: {e}")
    
    def save_to_db(self, events: List[EconomicEvent], db: Session):
        """Persiste événements en base de données"""
        
        for event in events:
            # Check if exists
            existing = db.query(EconomicEventDB).filter_by(
                date=event.date,
                time=event.time,
                currency=event.currency,
                event=event.event
            ).first()
            
            if not existing:
                db_event = EconomicEventDB(**event.to_dict())
                db.add(db_event)
        
        try:
            db.commit()
            logger.info(f"💾 {len(events)} événements sauvegardés en DB")
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur DB: {e}")
    
    def invalidate_cache(self, pattern: str = "calendar:*"):
        """Invalide le cache (force refresh)"""
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            logger.info(f"🗑️ Cache invalidé: {len(keys)} clés")
        except Exception as e:
            logger.error(f"Erreur invalidation: {e}")