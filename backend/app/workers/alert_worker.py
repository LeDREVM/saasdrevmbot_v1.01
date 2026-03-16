from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.alerts.alert_predictor import AlertPredictor
from app.services.alerts.notification_manager import NotificationManager
from app.services.alerts.markdown_exporter import MarkdownExporter
from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
from app.services.watchlist.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)

# Celery app
celery_app = Celery(
    'alert_worker',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Guadeloupe',
    enable_utc=True,
)

# Instances
predictor = AlertPredictor()
notifier = NotificationManager(
    discord_webhook=settings.DISCORD_WEBHOOK,
    telegram_token=settings.TELEGRAM_TOKEN,
    telegram_chat_id=settings.TELEGRAM_CHAT_ID
)
exporter = MarkdownExporter(output_dir="/mnt/user-data/outputs/reports")
calendar_aggregator = CalendarAggregator()
watchlist_service = WatchlistService()

# === TÂCHES PLANIFIÉES ===

@celery_app.task(name="check_upcoming_alerts")
def check_upcoming_alerts():
    """
    Vérifie les événements à venir (2h ahead) et envoie alertes
    Exécuté toutes les 30 minutes
    """
    
    logger.info("🔍 Vérification événements à venir...")
    
    db = SessionLocal()
    
    try:
        # Récupérer événements des 2 prochaines heures
        upcoming = calendar_aggregator.get_upcoming_high_impact(hours_ahead=2)
        
        if not upcoming:
            logger.info("Aucun événement imminent")
            return
        
        logger.info(f"📊 {len(upcoming)} événements high impact détectés")
        
        # Symboles à analyser
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'SPX']
        
        for event in upcoming:
            for symbol in symbols:
                # Prédire impact
                prediction = predictor.predict_upcoming_impact(event, symbol, db)
                
                if prediction and prediction['prediction']['risk_level'] in ['extreme', 'high']:
                    # Envoyer alerte
                    notifier.send_predictive_alert(
                        prediction,
                        channels=['discord', 'telegram']
                    )
                    
                    logger.info(f"✅ Alerte envoyée: {event.event} ({symbol})")
        
    except Exception as e:
        logger.error(f"Erreur check_upcoming_alerts: {e}")
    finally:
        db.close()

@celery_app.task(name="send_daily_summary")
def send_daily_summary():
    """
    Envoie résumé quotidien à 6h du matin
    """
    
    logger.info("📅 Génération résumé quotidien...")
    
    db = SessionLocal()
    
    try:
        # Récupérer événements du jour
        today_events = calendar_aggregator.get_today_events()
        
        # Filtrer high impact uniquement
        high_impact = [e for e in today_events if e.is_high_impact]
        
        if not high_impact:
            logger.info("Aucun événement high impact aujourd'hui")
            return
        
        # Prédictions pour tous les événements
        symbols = ['EURUSD', 'XAUUSD']
        all_predictions = []
        
        for event in high_impact:
            for symbol in symbols:
                prediction = predictor.predict_upcoming_impact(event, symbol, db)
                if prediction:
                    all_predictions.append(prediction)
        
        # Envoyer résumé Discord
        notifier.send_daily_summary(all_predictions, channels=['discord'])
        
        # Export Markdown
        for symbol in symbols:
            symbol_preds = [p for p in all_predictions if p['symbol'] == symbol]
            if symbol_preds:
                filepath = exporter.export_daily_predictions(symbol_preds, symbol)
                logger.info(f"📝 Rapport quotidien généré: {filepath}")
        
        logger.info("✅ Résumé quotidien envoyé")
        
    except Exception as e:
        logger.error(f"Erreur send_daily_summary: {e}")
    finally:
        db.close()

@celery_app.task(name="generate_weekly_report")
def generate_weekly_report():
    """
    Génère rapport hebdomadaire (dimanche soir)
    """
    
    logger.info("📊 Génération rapport hebdomadaire...")
    
    db = SessionLocal()
    
    try:
        # Récupérer événements de la semaine à venir
        week_events = calendar_aggregator.get_week_events()
        high_impact = [e for e in week_events if e.is_high_impact]
        
        symbols = ['EURUSD', 'XAUUSD', 'SPX']
        
        for symbol in symbols:
            predictions = []
            
            for event in high_impact:
                prediction = predictor.predict_upcoming_impact(event, symbol, db)
                if prediction:
                    predictions.append(prediction)
            
            # Export Markdown
            if predictions:
                filepath = exporter.export_weekly_summary(predictions, symbol)
                logger.info(f"📝 Rapport hebdomadaire généré: {filepath}")
                
                # TODO: Upload vers Nextcloud
        
        logger.info("✅ Rapports hebdomadaires générés")
        
    except Exception as e:
        logger.error(f"Erreur generate_weekly_report: {e}")
    finally:
        db.close()

@celery_app.task(name="export_monthly_stats")
def export_monthly_stats():
    """
    Export stats mensuelles (1er du mois)
    """
    
    logger.info("📈 Export stats mensuelles...")
    
    from app.services.stats.stats_aggregator import StatsAggregator
    
    db = SessionLocal()
    aggregator = StatsAggregator(settings.REDIS_URL)
    
    try:
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'SPX', 'NDX']
        
        for symbol in symbols:
            # Récupérer stats 30 jours
            stats = aggregator.get_dashboard_stats(symbol, days_back=30, db=db)
            
            # Export Markdown
            filepath = exporter.export_stats_report(stats, symbol, period_days=30)
            logger.info(f"📊 Stats {symbol} exportées: {filepath}")
        
        logger.info("✅ Stats mensuelles exportées")
        
    except Exception as e:
        logger.error(f"Erreur export_monthly_stats: {e}")
    finally:
        db.close()


@celery_app.task(name="watchlist_daily_snapshot")
def watchlist_daily_snapshot():
    """
    Snapshot quotidien de la watchlist à 6h (heure Guadeloupe):
    - lit le CSV de portefeuille
    - récupère les quotes "temps réel"
    - génère un rapport Markdown (Nextcloud)
    - envoie un résumé rapide sur Discord
    """

    logger.info("📋 Génération snapshot quotidien watchlist...")

    try:
        snapshots = watchlist_service.fetch_realtime_snapshot()
        if not snapshots:
            logger.info("Aucune donnée de watchlist à envoyer")
            return

        # Générer rapport Markdown (+ upload Nextcloud)
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = exporter.export_watchlist_snapshot(snapshots, today)
        logger.info(f"📝 Snapshot watchlist généré: {filepath}")

        # Résumé Discord simple (top 5 par % variation)
        try:
            sorted_snaps = sorted(
                snapshots,
                key=lambda s: abs(s.get("change_percent", 0)),
                reverse=True,
            )
            top = sorted_snaps[:5]

            lines = []
            for s in top:
                name = s.get("name", "")
                backend = s.get("backend_symbol", "")
                last = s.get("last", 0)
                chg = s.get("change", 0)
                chg_pct = s.get("change_percent", 0)
                sign = "+" if chg >= 0 else ""
                emoji = "📈" if chg > 0 else "📉" if chg < 0 else "➖"
                lines.append(
                    f"{emoji} **{name}** (`{backend}`) → {last} ({sign}{chg} | {sign}{chg_pct}%)"
                )

            summary = "\n".join(lines)

            payload = {
                "username": "📋 Watchlist Snapshot",
                "content": (
                    f"🕕 Snapshot quotidien de la watchlist (6h Guadeloupe)\n\n{summary}\n\n"
                    f"_Rapport détaillé synchronisé dans Nextcloud._"
                ),
            }

            import requests

            if settings.DISCORD_WEBHOOK_URL:
                resp = requests.post(settings.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
                if resp.status_code == 204:
                    logger.info("✅ Résumé watchlist envoyé sur Discord")
                else:
                    logger.error(
                        f"Erreur Discord watchlist: {resp.status_code} - {resp.text}"
                    )
            else:
                logger.warning("DISCORD_WEBHOOK_URL non configuré pour watchlist_daily_snapshot")
        except Exception as e:
            logger.error(f"Erreur envoi Discord watchlist: {e}")

    except Exception as e:
        logger.error(f"Erreur watchlist_daily_snapshot: {e}")

# === CONFIGURATION DES HORAIRES ===

celery_app.conf.beat_schedule = {
    'check-upcoming-alerts-every-30min': {
        'task': 'check_upcoming_alerts',
        'schedule': crontab(minute='*/30'),  # Toutes les 30 min
    },
    'send-daily-summary-6am': {
        'task': 'send_daily_summary',
        'schedule': crontab(hour=6, minute=0),  # 6h du matin
    },
    'generate-weekly-report-sunday': {
        'task': 'generate_weekly_report',
        'schedule': crontab(day_of_week=0, hour=20, minute=0),  # Dimanche 20h
    },
    'export-monthly-stats-first-day': {
        'task': 'export_monthly_stats',
        'schedule': crontab(day_of_month=1, hour=8, minute=0),  # 1er du mois 8h
    },
    'watchlist-daily-snapshot-6am': {
        'task': 'watchlist_daily_snapshot',
        'schedule': crontab(hour=6, minute=0),  # 6h du matin (America/Guadeloupe)
    },
}

from app.services.nextcloud.sync_manager import NextcloudSyncManager

# Initialiser sync manager
nc_sync = NextcloudSyncManager(
    nextcloud_url=settings.NEXTCLOUD_URL,
    username=settings.NEXTCLOUD_USER,
    password=settings.NEXTCLOUD_PASSWORD
)

@celery_app.task(name="auto_sync_to_nextcloud")
def auto_sync_to_nextcloud():
    """
    Synchronise automatiquement vers Nextcloud après génération de rapports
    Exécuté après chaque tâche de génération
    """
    
    logger.info("☁️ Auto-sync Nextcloud...")
    
    db = SessionLocal()
    
    try:
        symbols = ['EURUSD', 'XAUUSD', 'GBPUSD', 'SPX']
        
        # Sync alertes quotidiennes
        for symbol in symbols:
            # Récupérer événements
            events = calendar_aggregator.get_today_events()
            high_impact = [e for e in events if e.is_high_impact]
            
            predictions = []
            for event in high_impact:
                pred = predictor.predict_upcoming_impact(event, symbol, db)
                if pred:
                    predictions.append(pred)
            
            if predictions:
                result = nc_sync.sync_daily_alert_report(predictions, symbol)
                if result['uploaded']:
                    logger.info(f"✅ Sync quotidien {symbol}: {result['remote_path']}")
        
        # Sync calendrier
        all_events = calendar_aggregator.get_today_events()
        cal_result = nc_sync.sync_calendar_data(all_events)
        if cal_result['uploaded']:
            logger.info(f"✅ Sync calendrier: {cal_result['events_count']} événements")
        
        logger.info("✅ Auto-sync Nextcloud terminé")
        
    except Exception as e:
        logger.error(f"Erreur auto_sync_to_nextcloud: {e}")
    finally:
        db.close()

# Ajouter au beat_schedule
celery_app.conf.beat_schedule.update({
    'auto-sync-nextcloud-daily': {
        'task': 'auto_sync_to_nextcloud',
        'schedule': crontab(hour=7, minute=0),  # 7h du matin après le résumé
    },
})