#!/usr/bin/env python3
"""
Script de test pour les notifications Discord
Teste l'envoi de messages via webhook Discord
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
    """Test 1: Vérifier la configuration Discord"""
    print_header("TEST 1: Configuration Discord")
    
    print_step("1.1", "Vérification des variables d'environnement")
    
    config_ok = True
    
    if settings.DISCORD_WEBHOOK_URL:
        # Masquer une partie de l'URL pour la sécurité
        url_parts = settings.DISCORD_WEBHOOK_URL.split('/')
        if len(url_parts) >= 3:
            masked_url = f"{url_parts[0]}//{url_parts[2]}/.../{url_parts[-1][:10]}..."
        else:
            masked_url = settings.DISCORD_WEBHOOK_URL[:30] + "..."
        print_result(True, f"DISCORD_WEBHOOK_URL: {masked_url}")
    else:
        print_result(False, "DISCORD_WEBHOOK_URL non configuré")
        config_ok = False
    
    return config_ok


def test_webhook_format():
    """Test 2: Vérifier le format du webhook"""
    print_header("TEST 2: Format du Webhook")
    
    if not settings.DISCORD_WEBHOOK_URL:
        print_result(False, "Webhook non configuré")
        return False
    
    print_step("2.1", "Validation du format")
    
    url = settings.DISCORD_WEBHOOK_URL
    
    # Vérifier que c'est une URL Discord
    if not url.startswith('https://discord.com/api/webhooks/') and \
       not url.startswith('https://discordapp.com/api/webhooks/'):
        print_result(False, "L'URL ne commence pas par https://discord.com/api/webhooks/")
        return False
    
    print_result(True, "Format de base valide")
    
    # Vérifier la structure
    parts = url.split('/')
    if len(parts) < 7:
        print_result(False, "Structure d'URL incomplète")
        return False
    
    webhook_id = parts[-2]
    webhook_token = parts[-1]
    
    if not webhook_id.isdigit():
        print_result(False, "Webhook ID invalide (doit être numérique)")
        return False
    
    print_result(True, f"Webhook ID: {webhook_id}")
    
    if len(webhook_token) < 50:
        print_result(False, "Token trop court (probablement invalide)")
        return False
    
    print_result(True, f"Token: {webhook_token[:20]}... (longueur: {len(webhook_token)})")
    
    return True


def test_send_message():
    """Test 3: Envoi d'un message de test"""
    print_header("TEST 3: Envoi de Message")
    
    if not settings.DISCORD_WEBHOOK_URL:
        print_result(False, "Webhook non configuré")
        return False
    
    try:
        import requests
        
        print_step("3.1", "Envoi d'un message simple")
        
        payload = {
            'content': f'🤖 **Test SaaS DrevmBot**\n\n📅 {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}\n\n✅ Si vous recevez ce message, la connexion Discord fonctionne !'
        }
        
        response = requests.post(
            settings.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 204:
            print_result(True, "Message envoyé avec succès ! (Status 204)")
            return True
        elif response.status_code == 200:
            print_result(True, "Message envoyé avec succès ! (Status 200)")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_send_embed():
    """Test 4: Envoi d'un message avec embed"""
    print_header("TEST 4: Message avec Embed")
    
    if not settings.DISCORD_WEBHOOK_URL:
        print_result(False, "Webhook non configuré")
        return False
    
    try:
        import requests
        
        print_step("4.1", "Envoi d'un embed formaté")
        
        embed = {
            'title': '🔔 Test Alerte Forex',
            'description': 'Test de notification avec embed Discord',
            'color': 3447003,  # Bleu
            'fields': [
                {
                    'name': '📅 Date',
                    'value': datetime.now().strftime('%d/%m/%Y à %H:%M:%S'),
                    'inline': True
                },
                {
                    'name': '💱 Paire',
                    'value': 'EURUSD (TEST)',
                    'inline': True
                },
                {
                    'name': '⚠️ Impact',
                    'value': 'EXTRÊME',
                    'inline': True
                },
                {
                    'name': '📊 Mouvement Prévu',
                    'value': '35.5 pips',
                    'inline': True
                },
                {
                    'name': '🎯 Confiance',
                    'value': 'HIGH',
                    'inline': True
                },
                {
                    'name': '🔴 Recommandation',
                    'value': 'Éviter de trader',
                    'inline': False
                }
            ],
            'footer': {
                'text': 'SaaS DrevmBot - Alertes Intelligentes'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        payload = {
            'embeds': [embed]
        }
        
        response = requests.post(
            settings.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            print_result(True, "Embed envoyé avec succès !")
            return True
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
    """Test 5: Test via NotificationManager"""
    print_header("TEST 5: NotificationManager")
    
    try:
        print_step("5.1", "Import de NotificationManager")
        from app.services.alerts.notification_manager import NotificationManager
        print_result(True, "Import réussi")
        
        print_step("5.2", "Création de l'instance")
        notifier = NotificationManager(
            discord_webhook=settings.DISCORD_WEBHOOK_URL
        )
        print_result(True, "Instance créée")
        
        print_step("5.3", "Envoi d'une notification de test")
        
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
        
        success = notifier.send_discord_alert(test_event, test_prediction)
        
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
    """Test 6: Test de l'endpoint API"""
    print_header("TEST 6: Endpoint API")
    
    try:
        import requests
        
        print_step("6.1", "Test POST /api/alert-config/test-notification")
        
        url = "http://localhost:8000/api/alert-config/test-notification/negus_dja"
        payload = {
            'channel': 'discord'
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
    print("🧪 TEST DISCORD - SaaS DrevmBot")
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
        print("  1. Créer un webhook Discord:")
        print("     - Ouvrir Discord")
        print("     - Paramètres du serveur → Intégrations → Webhooks")
        print("     - Créer un webhook")
        print("     - Copier l'URL du webhook")
        print("  2. Configurer dans backend/.env:")
        print("     DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        print("\n  3. Relancer ce test")
        return 1
    
    # Test 2: Format du webhook
    format_ok = test_webhook_format()
    results.append(("Format webhook", format_ok))
    
    if not format_ok:
        print("\n❌ Format du webhook invalide")
        return 1
    
    # Test 3: Envoi message simple
    message_ok = test_send_message()
    results.append(("Message simple", message_ok))
    
    # Test 4: Envoi embed
    embed_ok = test_send_embed()
    results.append(("Message embed", embed_ok))
    
    # Test 5: NotificationManager
    manager_ok = test_notification_manager()
    results.append(("NotificationManager", manager_ok))
    
    # Test 6: API Endpoint
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
    
    if passed >= 4:  # Au moins les 4 premiers tests
        print("\n✅ DISCORD EST FONCTIONNEL !")
        print("🎉 Vous pouvez recevoir des notifications !")
        print("\n💬 Vérifiez votre canal Discord !")
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
