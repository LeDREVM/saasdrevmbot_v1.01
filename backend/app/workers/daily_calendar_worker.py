"""
Worker pour récupérer et envoyer le calendrier économique quotidien
Exécution: Tous les jours à 7h00 du matin
"""

import logging
import schedule
import time
from datetime import datetime
from typing import Optional

from app.services.economic_calendar.tradingeconomics_scraper import TradingEconomicsScraper
from app.services.notifications.discord_notifier import DiscordNotifier

logger = logging.getLogger(__name__)


class DailyCalendarWorker:
    """Worker pour le calendrier économique quotidien"""
    
    def __init__(self, discord_webhook: Optional[str] = None):
        """
        Initialise le worker
        
        Args:
            discord_webhook: URL du webhook Discord
        """
        self.scraper = TradingEconomicsScraper()
        self.notifier = DiscordNotifier(webhook_url=discord_webhook)
        self.is_running = False
    
    def run_daily_job(self):
        """Exécute le job quotidien"""
        try:
            logger.info("🚀 Démarrage du job quotidien")
            logger.info(f"📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            # 1. Récupérer les événements du jour
            logger.info("📊 Récupération des événements...")
            events = self.scraper.get_today_events()
            
            if not events:
                logger.warning("⚠️ Aucun événement trouvé pour aujourd'hui")
                return
            
            logger.info(f"✅ {len(events)} événements récupérés")
            
            # 2. Envoyer la notification Discord
            logger.info("📤 Envoi de la notification Discord...")
            success = self.notifier.send_daily_calendar(events)
            
            if success:
                logger.info("✅ Notification envoyée avec succès")
            else:
                logger.error("❌ Échec de l'envoi de la notification")
            
            # 3. Envoyer des alertes pour les événements à fort impact
            high_impact_events = [e for e in events if e.get('impact') == 'high']
            if high_impact_events:
                logger.info(f"🔴 {len(high_impact_events)} événements à fort impact détectés")
                for event in high_impact_events[:3]:  # Limiter à 3 alertes
                    self.notifier.send_high_impact_alert(event)
                    time.sleep(1)  # Pause entre les alertes
            
            logger.info("✅ Job quotidien terminé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'exécution du job quotidien: {e}", exc_info=True)
    
    def run_upcoming_alerts(self):
        """Envoie des alertes pour les événements à venir (30 minutes avant)"""
        try:
            logger.info("⏰ Vérification des événements à venir...")
            
            # Récupérer les événements du jour
            events = self.scraper.get_today_events()
            
            if not events:
                return
            
            # Filtrer les événements dans les 30 prochaines minutes
            now = datetime.now()
            upcoming_events = []
            
            for event in events:
                try:
                    event_time = datetime.fromisoformat(event['date'])
                    time_diff = (event_time - now).total_seconds() / 60  # En minutes
                    
                    # Événements entre 25 et 35 minutes (fenêtre de 10 min pour éviter les doublons)
                    if 25 <= time_diff <= 35:
                        upcoming_events.append(event)
                except:
                    continue
            
            if upcoming_events:
                logger.info(f"⏰ {len(upcoming_events)} événements à venir dans 30 minutes")
                self.notifier.send_upcoming_events(upcoming_events, minutes=30)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des événements à venir: {e}")
    
    def start(self):
        """Démarre le worker avec le scheduler"""
        
        logger.info("🤖 Démarrage du Daily Calendar Worker")
        
        # Tester la connexion Discord
        logger.info("🔍 Test de la connexion Discord...")
        if self.notifier.test_connection():
            logger.info("✅ Connexion Discord OK")
        else:
            logger.warning("⚠️ Problème de connexion Discord")
        
        # Programmer les jobs
        # Job quotidien à 7h00 du matin
        schedule.every().day.at("07:00").do(self.run_daily_job)
        logger.info("📅 Job quotidien programmé: tous les jours à 7h00")
        
        # Vérification des événements à venir toutes les 15 minutes
        schedule.every(15).minutes.do(self.run_upcoming_alerts)
        logger.info("⏰ Alertes programmées: toutes les 15 minutes")
        
        # Exécuter immédiatement le job au démarrage (optionnel)
        logger.info("🚀 Exécution immédiate du job de démarrage...")
        self.run_daily_job()
        
        # Boucle principale
        self.is_running = True
        logger.info("✅ Worker démarré - En attente des jobs programmés...")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Vérifier toutes les minutes
                
        except KeyboardInterrupt:
            logger.info("⏹️ Arrêt du worker demandé")
            self.stop()
    
    def stop(self):
        """Arrête le worker"""
        logger.info("🛑 Arrêt du Daily Calendar Worker")
        self.is_running = False
        schedule.clear()


def main():
    """Point d'entrée principal"""
    import os
    from dotenv import load_dotenv
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Configurer le logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('daily_calendar_worker.log'),
            logging.StreamHandler()
        ]
    )
    
    # Récupérer le webhook Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not discord_webhook:
        logger.error("❌ DISCORD_WEBHOOK_URL non configuré dans les variables d'environnement")
        logger.error("💡 Ajoutez DISCORD_WEBHOOK_URL=your_webhook_url dans le fichier .env")
        return
    
    # Créer et démarrer le worker
    worker = DailyCalendarWorker(discord_webhook=discord_webhook)
    worker.start()


if __name__ == "__main__":
    main()
