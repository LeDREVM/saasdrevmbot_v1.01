#!/usr/bin/env python3
"""
Script de test pour les notifications Telegram
Teste l'envoi de messages via le bot Telegram
"""

import sys
sys.path.insert(0, 'backend')

import os
from datetime import datetime

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv('backend/.env')

from app.core.config import settings


def print_header(title):
    """Affiche un header formaté"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step, message):
    """Affiche une étape"""
    print(f"\n{step}. {message}")


def print_result(success, message):
    """Affiche un résultat"""
    icon = "✅" if success else "❌"
    print(f"   {icon} {message}")


def test_configuration():
    """Test 1: Vérifier la configuration Telegram"""
    print_header("TEST 1: Configuration Telegram")
    
    print_step("1.1", "Vérification des variables d'environnement")
    
    config_ok = True
    
    if settings.TELEGRAM_BOT_TOKEN:
        print_result(True, f"TELEGRAM_BOT_TOKEN: {settings.TELEGRAM_BOT_TOKEN[:20]}...")
    else:
        print_result(False, "TELEGRAM_BOT_TOKEN non configuré")
        config_ok = False
    
    if settings.TELEGRAM_CHAT_ID:
        print_result(True, f"TELEGRAM_CHAT_ID: {settings.TELEGRAM_CHAT_ID}")
    else:
        print_result(False, "TELEGRAM_CHAT_ID non configuré")
        config_ok = False
    
    return config_ok


def test_telegram_api():
    """Test 2: Test de l'API Telegram"""
    print_header("TEST 2: API Telegram")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print_result(False, "Token non configuré")
        return False
    
    try:
        import requests
        
        print_step("2.1", "Test getMe (vérification du bot)")
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print_result(True, f"Bot connecté: @{bot_info.get('username')}")
                print(f"   Nom: {bot_info.get('first_name')}")
                print(f"   ID: {bot_info.get('id')}")
                return True
            else:
                print_result(False, f"Erreur API: {data.get('description')}")
                return False
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def test_send_message():
    """Test 3: Envoi d'un message de test"""
    print_header("TEST 3: Envoi de Message")
    
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print_result(False, "Configuration incomplète")
        return False
    
    try:
        import requests
        
        print_step("3.1", "Envoi d'un message de test")
        
        message = f"""🤖 **Test SaaS DrevmBot**

📅 Date: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

✅ Si vous recevez ce message, la connexion Telegram fonctionne parfaitement !

🔧 Configuration:
• Bot Token: Configuré ✅
• Chat ID: {settings.TELEGRAM_CHAT_ID}

---
Généré par: test_telegram.py
"""
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print_result(True, "Message envoyé avec succès !")
                print(f"   Message ID: {data.get('result', {}).get('message_id')}")
                return True
            else:
                print_result(False, f"Erreur API: {data.get('description')}")
                return False
        else:
            print_result(False, f"Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notification_manager():
    """Test 4: Test via NotificationManager"""
    print_header("TEST 4: NotificationManager")
    
    try:
        print_step("4.1", "Import de NotificationManager")
        from app.services.alerts.notification_manager import NotificationManager
        print_result(True, "Import réussi")
        
        print_step("4.2", "Création de l'instance")
        notifier = NotificationManager(
            telegram_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID
        )
        print_result(True, "Instance créée")
        
        print_step("4.3", "Envoi d'une notification de test")
        
        # Créer un événement de test
        test_event = {
            'event_name': 'Non-Farm Payrolls (TEST)',
            'currency': 'USD',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': '14:30',
            'impact_level': 'High',
            'forecast': '200K',
            'previous': '180K'
        }
        
        test_prediction = {
            'symbol': 'EURUSD',
            'expected_movement_pips': 35.5,
            'confidence': 'high',
            'risk_level': 'extreme',
            'direction_probability': {
                'up': 45.0,
                'down': 40.0,
                'neutral': 15.0
            }
        }
        
        success = notifier.send_telegram_alert(test_event, test_prediction)
        
        if success:
            print_result(True, "Notification envoyée via NotificationManager")
            return True
        else:
            print_result(False, "Échec de l'envoi")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """Test 5: Test de l'endpoint API"""
    print_header("TEST 5: Endpoint API")
    
    try:
        import requests
        
        print_step("5.1", "Test POST /api/alert-config/test-notification")
        
        url = "http://localhost:8000/api/alert-config/test-notification/negus_dja"
        payload = {
            'channel': 'telegram'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Endpoint accessible")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_result(False, "API non démarrée (normal si backend pas lancé)")
        return False
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🧪 TEST TELEGRAM - SaaS DrevmBot")
    print("=" * 60)
    print(f"\nDate: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    
    results = []
    
    # Test 1: Configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))
    
    if not config_ok:
        print("\n" + "=" * 60)
        print("❌ ERREUR: Configuration incomplète")
        print("=" * 60)
        print("\n📝 Actions requises:")
        print("  1. Créer un bot Telegram via @BotFather")
        print("  2. Obtenir le token du bot")
        print("  3. Obtenir votre Chat ID (via @userinfobot)")
        print("  4. Configurer dans backend/.env:")
        print("     TELEGRAM_BOT_TOKEN=votre_token")
        print("     TELEGRAM_CHAT_ID=votre_chat_id")
        print("\n  5. Relancer ce test")
        return 1
    
    # Test 2: API Telegram
    api_ok = test_telegram_api()
    results.append(("API Telegram", api_ok))
    
    if not api_ok:
        print("\n❌ Impossible de continuer sans connexion API")
        return 1
    
    # Test 3: Envoi message
    message_ok = test_send_message()
    results.append(("Envoi message", message_ok))
    
    # Test 4: NotificationManager
    manager_ok = test_notification_manager()
    results.append(("NotificationManager", manager_ok))
    
    # Test 5: API Endpoint
    endpoint_ok = test_api_endpoint()
    results.append(("API Endpoint", endpoint_ok))
    
    # Résultats finaux
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS FINAUX")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    
    for test_name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis ({passed*100//total}%)")
    
    if passed >= 3:  # Au moins les 3 premiers tests
        print("\n✅ TELEGRAM EST FONCTIONNEL !")
        print("🎉 Vous pouvez recevoir des notifications !")
        print(f"\n📱 Vérifiez votre Telegram (Chat ID: {settings.TELEGRAM_CHAT_ID})")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        print("Vérifier la configuration et les logs ci-dessus")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
