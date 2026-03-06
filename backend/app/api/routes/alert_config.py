import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.alert_settings import UserAlertSettings, AlertLog

router = APIRouter(prefix="/alert-config", tags=["Alert Configuration"])

# === SCHEMAS PYDANTIC ===

class AlertSettingsSchema(BaseModel):
    user_id: str
    watched_symbols: List[str]
    alert_extreme: bool
    alert_high: bool
    alert_medium: bool
    discord_enabled: bool
    telegram_enabled: bool
    custom_discord_webhook: Optional[str] = None
    custom_telegram_token: Optional[str] = None
    custom_telegram_chat_id: Optional[str] = None
    quiet_hours_start: int
    quiet_hours_end: int
    quiet_hours_enabled: bool
    advance_notice_hours: int
    min_expected_pips: float
    require_high_confidence: bool

class AlertSettingsUpdate(BaseModel):
    watched_symbols: Optional[List[str]] = None
    alert_extreme: Optional[bool] = None
    alert_high: Optional[bool] = None
    alert_medium: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    custom_discord_webhook: Optional[str] = None
    custom_telegram_token: Optional[str] = None
    custom_telegram_chat_id: Optional[str] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    quiet_hours_enabled: Optional[bool] = None
    advance_notice_hours: Optional[int] = None
    min_expected_pips: Optional[float] = None
    require_high_confidence: Optional[bool] = None

# === ENDPOINTS ===

@router.get("/settings/{user_id}")
async def get_user_settings(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    ⚙️ Récupère les préférences d'alerte de l'utilisateur
    """
    
    settings = db.query(UserAlertSettings).filter(
        UserAlertSettings.user_id == user_id
    ).first()
    
    if not settings:
        # Créer settings par défaut
        settings = UserAlertSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return JSONResponse(content={
        "user_id": settings.user_id,
        "watched_symbols": settings.watched_symbols,
        "alert_levels": {
            "extreme": settings.alert_extreme,
            "high": settings.alert_high,
            "medium": settings.alert_medium
        },
        "channels": {
            "discord": settings.discord_enabled,
            "telegram": settings.telegram_enabled
        },
        "custom_webhooks": {
            "discord": settings.custom_discord_webhook,
            "telegram_token": settings.custom_telegram_token,
            "telegram_chat_id": settings.custom_telegram_chat_id
        },
        "quiet_hours": {
            "enabled": settings.quiet_hours_enabled,
            "start": settings.quiet_hours_start,
            "end": settings.quiet_hours_end
        },
        "advanced": {
            "advance_notice_hours": settings.advance_notice_hours,
            "min_expected_pips": settings.min_expected_pips,
            "require_high_confidence": settings.require_high_confidence
        },
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    })

@router.patch("/settings/{user_id}")
async def update_user_settings(
    user_id: str,
    updates: AlertSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    🔧 Met à jour les préférences d'alerte
    """
    
    settings = db.query(UserAlertSettings).filter(
        UserAlertSettings.user_id == user_id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    
    # Appliquer les mises à jour
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    return JSONResponse(content={
        "status": "updated",
        "user_id": user_id,
        "updated_fields": list(update_data.keys())
    })

@router.get("/history/{user_id}")
async def get_alert_history(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    📜 Historique des alertes envoyées
    """
    
    logs = db.query(AlertLog).filter(
        AlertLog.user_id == user_id
    ).order_by(AlertLog.sent_at.desc()).limit(limit).all()
    
    return JSONResponse(content={
        "user_id": user_id,
        "total": len(logs),
        "alerts": [
            {
                "id": log.id,
                "event": {
                    "name": log.event_name,
                    "date": log.event_date,
                    "time": log.event_time,
                    "currency": log.currency,
                    "symbol": log.symbol
                },
                "prediction": {
                    "pips": log.predicted_pips,
                    "direction": log.predicted_direction,
                    "risk_level": log.risk_level,
                    "confidence": log.confidence
                },
                "actual": {
                    "pips": log.actual_pips,
                    "direction": log.actual_direction,
                    "accurate": log.prediction_accurate
                } if log.actual_pips else None,
                "sent_at": log.sent_at.isoformat(),
                "channels": log.channels_sent,
                "status": log.delivery_status
            }
            for log in logs
        ]
    })

@router.get("/stats/{user_id}")
async def get_alert_stats(
    user_id: str,
    days_back: int = 30,
    db: Session = Depends(get_db)
):
    """
    📊 Statistiques d'efficacité des alertes
    """
    
    from datetime import timedelta
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    logs = db.query(AlertLog).filter(
        AlertLog.user_id == user_id,
        AlertLog.sent_at >= cutoff_date
    ).all()
    
    # Calculer stats
    total_alerts = len(logs)
    
    # Seulement les alertes avec résultat réel
    verified_logs = [log for log in logs if log.actual_pips is not None]
    
    if verified_logs:
        accurate_predictions = sum(1 for log in verified_logs if log.prediction_accurate)
        accuracy_rate = (accurate_predictions / len(verified_logs)) * 100
        
        avg_predicted_pips = sum(log.predicted_pips for log in verified_logs) / len(verified_logs)
        avg_actual_pips = sum(log.actual_pips for log in verified_logs) / len(verified_logs)
        prediction_error = abs(avg_predicted_pips - avg_actual_pips)
    else:
        accuracy_rate = 0
        avg_predicted_pips = 0
        avg_actual_pips = 0
        prediction_error = 0
    
    # Par niveau de risque
    by_risk = {}
    for risk in ['extreme', 'high', 'medium']:
        risk_logs = [log for log in verified_logs if log.risk_level == risk]
        if risk_logs:
            risk_accurate = sum(1 for log in risk_logs if log.prediction_accurate)
            by_risk[risk] = {
                "total": len(risk_logs),
                "accurate": risk_accurate,
                "accuracy_rate": (risk_accurate / len(risk_logs)) * 100
            }
        else:
            by_risk[risk] = {"total": 0, "accurate": 0, "accuracy_rate": 0}
    
    return JSONResponse(content={
        "user_id": user_id,
        "period_days": days_back,
        "summary": {
            "total_alerts_sent": total_alerts,
            "verified_predictions": len(verified_logs),
            "accuracy_rate": round(accuracy_rate, 1),
            "avg_predicted_pips": round(avg_predicted_pips, 1),
            "avg_actual_pips": round(avg_actual_pips, 1),
            "prediction_error": round(prediction_error, 1)
        },
        "by_risk_level": by_risk,
        "by_channel": {
            "discord": sum(1 for log in logs if "discord" in log.channels_sent),
            "telegram": sum(1 for log in logs if "telegram" in log.channels_sent)
        }
    })

@router.post("/test-alert/{user_id}")
async def send_test_alert(
    user_id: str,
    channel: str = "discord",
    db: Session = Depends(get_db)
):
    """
    🧪 Envoie une alerte de test
    """
    
    settings = db.query(UserAlertSettings).filter(
        UserAlertSettings.user_id == user_id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    
    # Vérifier que le canal est activé
    if channel == "discord" and not settings.discord_enabled:
        raise HTTPException(status_code=400, detail="Discord notifications disabled")
    if channel == "telegram" and not settings.telegram_enabled:
        raise HTTPException(status_code=400, detail="Telegram notifications disabled")
    
    # Créer une prédiction de test
    from app.services.alerts.notification_manager import NotificationManager
    
    webhook = settings.custom_discord_webhook or os.getenv('DISCORD_WEBHOOK')
    tg_token = settings.custom_telegram_token or os.getenv('TELEGRAM_TOKEN')
    tg_chat = settings.custom_telegram_chat_id or os.getenv('TELEGRAM_CHAT_ID')
    
    notifier = NotificationManager(webhook, tg_token, tg_chat)
    
    test_prediction = {
        'event': {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': "14:30",
            'currency': "USD",
            'event_name': "Non-Farm Payrolls (TEST)",
            'impact_level': "High",
            'forecast': "200K",
            'previous': "185K"
        },
        'symbol': "EURUSD",
        'prediction': {
            'expected_movement_pips': 25.5,
            'confidence': 'high',
            'historical_samples': 12,
            'direction_probability': {'up': 58, 'down': 25, 'neutral': 17},
            'volatility_increase_expected': 78,
            'risk_level': 'extreme'
        },
        'recommendation': "🔴 ALERTE TEST - Ceci est un test de notification. Si tu reçois ce message, ton système fonctionne correctement !",
        'time_until_event': "MAINTENANT (TEST)"
    }
    
    try:
        notifier.send_predictive_alert(test_prediction, channels=[channel])
        
        return JSONResponse(content={
            "status": "sent",
            "user_id": user_id,
            "channel": channel,
            "message": "Test alert sent successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test: {str(e)}")

@router.get("/active-alerts/{user_id}")
async def get_active_alerts(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    🔔 Alertes actives (événements à venir dans les N prochaines heures)
    """
    
    settings = db.query(UserAlertSettings).filter(
        UserAlertSettings.user_id == user_id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    
    # Utiliser le service de prédiction
    from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
    from app.services.alerts.alert_predictor import AlertPredictor
    
    calendar = CalendarAggregator()
    predictor = AlertPredictor()
    
    # Événements à venir
    hours_ahead = settings.advance_notice_hours
    upcoming = calendar.get_upcoming_high_impact(hours_ahead=hours_ahead)
    
    active_alerts = []
    
    for event in upcoming:
        for symbol in settings.watched_symbols:
            prediction = predictor.predict_upcoming_impact(event, symbol, db)
            
            if not prediction:
                continue
            
            # Filtrer par niveau de risque
            risk = prediction['prediction']['risk_level']
            if risk == 'extreme' and not settings.alert_extreme:
                continue
            if risk == 'high' and not settings.alert_high:
                continue
            if risk == 'medium' and not settings.alert_medium:
                continue
            
            # Filtrer par mouvement minimum
            if prediction['prediction']['expected_movement_pips'] < settings.min_expected_pips:
                continue
            
            # Filtrer par confiance
            if settings.require_high_confidence and prediction['prediction']['confidence'] != 'high':
                continue
            
            active_alerts.append(prediction)
    
    return JSONResponse(content={
        "user_id": user_id,
        "count": len(active_alerts),
        "alerts": active_alerts
    })