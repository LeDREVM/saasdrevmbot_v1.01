from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class EconomicEventDB(Base):
    """Modèle de base de données pour les événements économiques"""
    __tablename__ = "economic_events"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)  # forexfactory, investing
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD
    time = Column(String, nullable=False)  # HH:MM
    currency = Column(String, nullable=False, index=True)
    event = Column(String, nullable=False, index=True)
    impact = Column(String, nullable=False)  # Low, Medium, High
    actual = Column(String, nullable=True)
    forecast = Column(String, nullable=True)
    previous = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EconomicEvent {self.date} {self.time} - {self.event}>"


class PriceData(Base):
    """Modèle pour stocker les données de prix (optionnel, pour cache)"""
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceData {self.symbol} @ {self.timestamp}>"


class AlertLog(Base):
    """Log des alertes envoyées"""
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=True)
    symbol = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)  # predictive, summary
    channel = Column(String, nullable=False)  # discord, telegram
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<AlertLog {self.alert_type} @ {self.sent_at}>"
