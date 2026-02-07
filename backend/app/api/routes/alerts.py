from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.services.alerts.alert_predictor import AlertPredictor
from app.services.alerts.notification_manager import NotificationManager
from app.services.alerts.markdown_exporter import MarkdownExporter
from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts & Predictions"])

predictor = AlertPredictor()
notifier = NotificationManager(
    discord_webhook=settings.DISCORD_WEBHOOK_URL,
    telegram_token=settings.TELEGRAM_BOT_TOKEN,
    telegram_chat_id=settings.TELEGRAM_CHAT_ID
)
exporter = MarkdownExporter()
calendar = CalendarAggregator()

@router.get("/upcoming")
async def get_upcoming_alerts(
    symbol: str = Query("EURUSD", description="Symbole à analyser"),
    hours_ahead: int = Query(2, ge=1, le=24, description="Heures à l'avance"),
    db: Session = Depends(get_db)
):
    """
    🔔 Événements à venir avec prédictions d'impact
    
    **Returns:** Liste des événements high impact avec prédictions
    """
    
    upcoming = calendar.get_upcoming_high_impact(hours_ahead=hours_ahead)
    
    predictions = []
    for event in upcoming:
        prediction = predictor.predict_upcoming_impact(event, symbol, db)
        if prediction:
            predictions.append(prediction)
    
    return JSONResponse(content={
        "symbol": symbol,
        "hours_ahead": hours_ahead,
        "count": len(predictions),
        "predictions": predictions
    })

@router.post("/test-notification")
async def test_notification(
    channels: str = Query("discord", description="discord,telegram"),
    db: Session = Depends(get_db)
):
    """
    🧪 Test d'envoi de notification (dev only)
    """
    
    # Créer une prédiction fictive
    from app.services.economic_calendar.base_scraper import EconomicEvent, ImpactLevel
    
    test_event = EconomicEvent(
        source="test",
        date=datetime.now().strftime("%Y-%m-%d"),
        time="14:30",
        currency="USD",
        event="Non-Farm Payrolls (TEST)",
        impact=ImpactLevel.HIGH,
        forecast="200K",
        previous="185K"
    )
    
    prediction = predictor.predict_upcoming_impact(test_event, "EURUSD", db)
    
    if not prediction:
        return JSONResponse(
            status_code=404,
            content={"error": "Impossible de générer prédiction test"}
        )
    
    # Envoyer
    notifier.send_predictive_alert(prediction, channels=channels.split(','))
    
    return JSONResponse(content={
        "status": "sent",
        "channels": channels.split(','),
        "prediction": prediction
    })

@router.get("/export/daily/{symbol}")
async def export_daily_markdown(
    symbol: str,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    📝 Export rapport quotidien en Markdown
    
    **Returns:** Fichier .md téléchargeable
    """
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Récupérer événements du jour
    events = calendar.get_today_events()
    high_impact = [e for e in events if e.is_high_impact]
    
    # Générer prédictions
    predictions = []
    for event in high_impact:
        prediction = predictor.predict_upcoming_impact(event, symbol, db)
        if prediction:
            predictions.append(prediction)
    
    if not predictions:
        return JSONResponse(
            status_code=404,
            content={"error": "Aucune prédiction disponible pour ce jour"}
        )
    
    # Export Markdown
    filepath = exporter.export_daily_predictions(predictions, symbol, date)
    
    return FileResponse(
        filepath,
        media_type='text/markdown',
        filename=f"predictions_{symbol}_{date}.md"
    )

@router.get("/export/stats/{symbol}")
async def export_stats_markdown(
    symbol: str,
    period_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    📊 Export rapport stats en Markdown
    """
    
    from app.services.stats.stats_aggregator import StatsAggregator
    
    aggregator = StatsAggregator(settings.REDIS_URL)
    stats = aggregator.get_dashboard_stats(symbol, period_days, db)
    
    filepath = exporter.export_stats_report(stats, symbol, period_days)
    
    return FileResponse(
        filepath,
        media_type='text/markdown',
        filename=f"stats_{symbol}_{datetime.now().strftime('%Y-%m-%d')}.md"
    )

@router.get("/export/weekly/{symbol}")
async def export_weekly_markdown(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    📅 Export résumé hebdomadaire en Markdown
    """
    
    # Événements de la semaine
    week_events = calendar.get_week_events()
    high_impact = [e for e in week_events if e.is_high_impact]
    
    predictions = []
    for event in high_impact:
        prediction = predictor.predict_upcoming_impact(event, symbol, db)
        if prediction:
            predictions.append(prediction)
    
    if not predictions:
        return JSONResponse(
            status_code=404,
            content={"error": "Aucune prédiction pour la semaine"}
        )
    
    filepath = exporter.export_weekly_summary(predictions, symbol)
    
    return FileResponse(
        filepath,
        media_type='text/markdown',
        filename=f"weekly_{symbol}_{datetime.now().strftime('%Y-W%W')}.md"
    )

@router.post("/manual-alert")
async def send_manual_alert(
    event_name: str = Query(..., description="Nom de l'événement"),
    symbol: str = Query("EURUSD"),
    channels: str = Query("discord", description="discord,telegram"),
    db: Session = Depends(get_db)
):
    """
    📣 Envoi manuel d'une alerte pour un événement spécifique
    """
    
    # Chercher événement dans le calendrier du jour
    today_events = calendar.get_today_events()
    
    matching = [e for e in today_events if event_name.lower() in e.event.lower()]
    
    if not matching:
        return JSONResponse(
            status_code=404,
            content={"error": f"Événement '{event_name}' non trouvé"}
        )
    
    event = matching[0]
    
    # Générer prédiction
    prediction = predictor.predict_upcoming_impact(event, symbol, db)
    
    if not prediction:
        return JSONResponse(
            status_code=500,
            content={"error": "Impossible de générer prédiction"}
        )
    
    # Envoyer alerte
    notifier.send_predictive_alert(prediction, channels=channels.split(','))
    
    return JSONResponse(content={
        "status": "sent",
        "event": event_name,
        "symbol": symbol,
        "channels": channels.split(','),
        "prediction": prediction
    })

@router.get("/config")
async def get_alert_config():
    """
    ⚙️ Configuration actuelle du système d'alertes
    """
    
    return JSONResponse(content={
        "discord_webhook": bool(settings.DISCORD_WEBHOOK),
        "telegram_enabled": bool(settings.TELEGRAM_TOKEN and settings.TELEGRAM_CHAT_ID),
        "schedules": {
            "check_upcoming": "Toutes les 30 minutes",
            "daily_summary": "06:00 (Guadeloupe)",
            "weekly_report": "Dimanche 20:00",
            "monthly_stats": "1er du mois 08:00"
        },
        "prediction_thresholds": {
            "high_impact": "20 pips",
            "medium_impact": "10 pips",
            "min_samples": 3
        },
        "export_directory": "/mnt/user-data/outputs/reports"
    })