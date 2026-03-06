#!/usr/bin/env python3
"""
Test rapide Telegram - Configuration manuelle
Utilisez ce script pour tester votre configuration Telegram
"""

import requests

print("=" * 60)
print("🧪 TEST RAPIDE TELEGRAM")
print("=" * 60)

# ⚠️ REMPLACER CES VALEURS PAR VOS VRAIES VALEURS
BOT_TOKEN = "VOTRE_TOKEN_ICI"  # Format: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHAT_ID = "VOTRE_CHAT_ID_ICI"  # Format: 123456789 (nombre)

print("\n📝 Configuration:")
print(f"  Token: {BOT_TOKEN[:20]}..." if len(BOT_TOKEN) > 20 else f"  Token: {BOT_TOKEN}")
print(f"  Chat ID: {CHAT_ID}")

if BOT_TOKEN == "VOTRE_TOKEN_ICI" or CHAT_ID == "VOTRE_CHAT_ID_ICI":
    print("\n❌ ERREUR: Vous devez remplacer les valeurs par défaut !")
    print("\n📝 Instructions:")
    print("  1. Éditer ce fichier (test_telegram_quick.py)")
    print("  2. Remplacer BOT_TOKEN par votre token")
    print("  3. Remplacer CHAT_ID par votre chat ID")
    print("  4. Relancer le script")
    print("\n💡 Voir TELEGRAM_SETUP_GUIDE.md pour plus d'infos")
    exit(1)

# Test 1: Vérifier le bot
print("\n🔍 Test 1: Vérification du bot...")
try:
    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            bot_info = data['result']
            print(f"✅ Bot connecté: @{bot_info['username']}")
            print(f"   Nom: {bot_info['first_name']}")
            print(f"   ID: {bot_info['id']}")
        else:
            print(f"❌ Erreur API: {data.get('description')}")
            exit(1)
    else:
        print(f"❌ Status code: {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    exit(1)

# Test 2: Envoyer un message
print("\n📤 Test 2: Envoi d'un message...")
try:
    from datetime import datetime
    
    message = f"""🤖 **Test SaaS DrevmBot**

📅 {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

✅ Si vous recevez ce message, votre configuration Telegram fonctionne !

🔧 Configuration validée:
• Bot Token: ✅
• Chat ID: {CHAT_ID}

---
Test généré par: test_telegram_quick.py
"""
    
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print(f"✅ Message envoyé avec succès !")
            print(f"   Message ID: {data['result']['message_id']}")
        else:
            print(f"❌ Erreur API: {data.get('description')}")
            exit(1)
    else:
        print(f"❌ Status code: {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    exit(1)

# Succès
print("\n" + "=" * 60)
print("✅ TOUS LES TESTS SONT PASSÉS !")
print("=" * 60)
print("\n🎉 Votre configuration Telegram est correcte !")
print(f"📱 Vérifiez votre Telegram (Chat ID: {CHAT_ID})")
print("\n📝 Prochaines étapes:")
print("  1. Copier ces valeurs dans backend/.env")
print("  2. Relancer: python test_telegram.py")
print("  3. Tester via l'interface web")
