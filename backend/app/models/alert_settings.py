from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Float
from sqlalchemy.sql import func
from app.core.database import Base

class UserAlertSettings(Base):
    """Préférences utilisateur pour les alertes"""
    
    __tablename__ = "user_alert_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # Email ou ID user
    
    # Symboles surveillés
    watched_symbols = Column(JSON, default=["EURUSD", "XAUUSD"])  # Liste symboles
    
    # Niveaux d'alerte
    alert_extreme = Column(Boolean, default=True)   # Alertes risque extrême
    alert_high = Column(Boolean, default=True)      # Alertes risque élevé
    alert_medium = Column(Boolean, default=False)   # Alertes risque moyen
    
    # Canaux de notification
    discord_enabled = Column(Boolean, default=True)
    telegram_enabled = Column(Boolean, default=False)
    
    # Webhooks personnalisés
    custom_discord_webhook = Column(String, nullable=True)
    custom_telegram_token = Column(String, nullable=True)
    custom_telegram_chat_id = Column(String, nullable=True)
    
    # Horaires silence (heures locales)
    quiet_hours_start = Column(Integer, default=22)  # 22h
    quiet_hours_end = Column(Integer, default=6)     # 6h
    quiet_hours_enabled = Column(Boolean, default=False)
    
    # Préférences avancées
    advance_notice_hours = Column(Integer, default=2)  # Nb heures avant événement
    min_expected_pips = Column(Float, default=10.0)    # Mouvement minimum pour alerte
    require_high_confidence = Column(Boolean, default=False)  # Seulement confiance HIGH
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AlertLog(Base):
    """Historique des alertes envoyées"""
    
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Info événement
    event_name = Column(String)
    event_date = Column(String)  # YYYY-MM-DD
    event_time = Column(String)  # HH:MM
    currency = Column(String)
    symbol = Column(String)
    
    # Prédiction
    predicted_pips = Column(Float)
    predicted_direction = Column(String)  # up/down/neutral
    risk_level = Column(String)  # extreme/high/medium
    confidence = Column(String)  # high/medium/low
    
    # Résultat réel (rempli après événement)
    actual_pips = Column(Float, nullable=True)
    actual_direction = Column(String, nullable=True)
    prediction_accurate = Column(Boolean, nullable=True)
    
    # Envoi
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    channels_sent = Column(JSON)  # ["discord", "telegram"]
    delivery_status = Column(String, default="sent")  # sent/failed
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())