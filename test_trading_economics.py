"""
Script de test pour le système de calendrier économique Trading Economics
"""

import sys
import os
import logging
from datetime import datetime

# Ajouter le chemin backend au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
from app.services.economic_calendar.tradingeconomics_scraper import TradingEconomicsScraper
from app.services.notifications.discord_notifier import DiscordNotifier

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scraper():
    """Test du scraper Trading Economics"""
    logger.info("=" * 60)
    logger.info("TEST DU SCRAPER TRADING ECONOMICS")
    logger.info("=" * 60)
    
    scraper = TradingEconomicsScraper()
    
    # Test 1: Récupérer les événements d'aujourd'hui
    logger.info("\n📊 Test 1: Récupération des événements d'aujourd'hui")
    events = scraper.get_today_events()
    
    if events:
        logger.info(f"✅ {len(events)} événements récupérés")
        
        # Afficher quelques événements
        logger.info("\n📋 Premiers événements:")
        for i, event in enumerate(events[:5], 1):
            logger.info(f"\n{i}. {event.get('event', 'Unknown')}")
            logger.info(f"   ⏰ Heure: {event.get('time', 'N/A')}")
            logger.info(f"   💱 Devise: {event.get('currency', 'N/A')}")
            logger.info(f"   🌍 Pays: {event.get('country', 'N/A')}")
            logger.info(f"   📊 Impact: {event.get('impact', 'N/A')}")
            logger.info(f"   📈 Prévision: {event.get('forecast', 'N/A')}")
            logger.info(f"   📉 Précédent: {event.get('previous', 'N/A')}")
        
        # Statistiques par impact
        high_impact = len([e for e in events if e.get('impact') == 'high'])
        medium_impact = len([e for e in events if e.get('impact') == 'medium'])
        low_impact = len([e for e in events if e.get('impact') == 'low'])
        
        logger.info(f"\n📊 Statistiques par impact:")
        logger.info(f"   🔴 Fort impact: {high_impact}")
        logger.info(f"   🟡 Impact moyen: {medium_impact}")
        logger.info(f"   🟢 Faible impact: {low_impact}")
        
        return events
    else:
        logger.warning("⚠️ Aucun événement trouvé")
        return []


def test_discord_notifier(events):
    """Test du notifier Discord"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST DU NOTIFIER DISCORD")
    logger.info("=" * 60)
    
    # Charger les variables d'environnement
    load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))
    
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL non configuré")
        logger.error("💡 Créez un fichier backend/.env avec:")
        logger.error("   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        return False
    
    notifier = DiscordNotifier(webhook_url=webhook_url)
    
    # Test 1: Test de connexion
    logger.info("\n🔍 Test 1: Test de connexion")
    if notifier.test_connection():
        logger.info("✅ Connexion Discord réussie")
    else:
        logger.error("❌ Échec de la connexion Discord")
        return False
    
    # Test 2: Envoyer le calendrier quotidien
    if events:
        logger.info("\n📤 Test 2: Envoi du calendrier quotidien")
        success = notifier.send_daily_calendar(events)
        
        if success:
            logger.info("✅ Calendrier envoyé avec succès")
        else:
            logger.error("❌ Échec de l'envoi du calendrier")
            return False
        
        # Test 3: Envoyer une alerte pour un événement à fort impact
        high_impact_events = [e for e in events if e.get('impact') == 'high']
        if high_impact_events:
            logger.info("\n🚨 Test 3: Envoi d'une alerte à fort impact")
            success = notifier.send_high_impact_alert(high_impact_events[0])
            
            if success:
                logger.info("✅ Alerte envoyée avec succès")
            else:
                logger.error("❌ Échec de l'envoi de l'alerte")
    
    return True


def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage des tests")
    logger.info(f"📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    try:
        # Test du scraper
        events = test_scraper()
        
        # Test du notifier Discord
        if events:
            test_discord_notifier(events)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ TESTS TERMINÉS")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ Erreur lors des tests: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
