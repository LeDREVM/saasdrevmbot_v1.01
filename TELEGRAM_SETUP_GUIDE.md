# 📱 Guide de Configuration Telegram - SaaS DrevmBot

**Date**: 06/02/2026  
**Status**: ⚠️ **CONFIGURATION REQUISE**

---

## 🔴 Problème Détecté

Le test Telegram a échoué avec l'erreur suivante:

```
❌ Status code: 404
TELEGRAM_BOT_TOKEN: @GoldyRogers_bot...
TELEGRAM_CHAT_ID: Goldrogers
```

**Problème**: Le format du token est incorrect. Un token Telegram ne commence jamais par `@`.

---

## 📝 Configuration Correcte

### Étape 1: Créer un Bot Telegram

1. **Ouvrir Telegram** et rechercher `@BotFather`
2. **Envoyer** `/newbot`
3. **Choisir un nom** pour votre bot (ex: "GoldyRogers Alert Bot")
4. **Choisir un username** (doit finir par "bot", ex: "GoldyRogers_bot")
5. **Copier le token** que BotFather vous donne

**Format du token**: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Étape 2: Obtenir votre Chat ID

#### Méthode 1: Via @userinfobot

1. Rechercher `@userinfobot` sur Telegram
2. Envoyer `/start`
3. Le bot vous donnera votre **User ID** (ex: `123456789`)

#### Méthode 2: Via @getmyid_bot

1. Rechercher `@getmyid_bot` sur Telegram
2. Envoyer `/start`
3. Copier votre **Chat ID**

#### Méthode 3: Pour un groupe

1. Ajouter votre bot au groupe
2. Envoyer un message dans le groupe
3. Visiter: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Chercher `"chat":{"id":-123456789}` dans la réponse

**Format du Chat ID**:
- **Utilisateur**: Nombre positif (ex: `123456789`)
- **Groupe**: Nombre négatif (ex: `-987654321`)

### Étape 3: Configurer le fichier .env

Éditer `backend/.env` et configurer:

```env
# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

**⚠️ IMPORTANT**:
- Le token doit être au format `nombre:chaîne_alphanumérique`
- Le Chat ID doit être un nombre (positif ou négatif)
- **PAS de `@`** dans le token
- **PAS de guillemets** autour des valeurs

---

## ✅ Exemple de Configuration Valide

```env
# ✅ CORRECT
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-AbCdEf
TELEGRAM_CHAT_ID=123456789

# ❌ INCORRECT
TELEGRAM_BOT_TOKEN=@GoldyRogers_bot
TELEGRAM_CHAT_ID=Goldrogers

# ❌ INCORRECT
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="123456789"
```

---

## 🧪 Tester la Configuration

### Script de Test Rapide

Créer un fichier `test_telegram_quick.py`:

```python
import requests

BOT_TOKEN = "VOTRE_TOKEN_ICI"
CHAT_ID = "VOTRE_CHAT_ID_ICI"

# Test 1: Vérifier le bot
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
print("Test Bot:", response.json())

# Test 2: Envoyer un message
response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={'chat_id': CHAT_ID, 'text': '✅ Test réussi !'}
)
print("Test Message:", response.json())
```

Exécuter:
```bash
python test_telegram_quick.py
```

### Via le Script Complet

```bash
python test_telegram.py
```

**Résultat attendu**:
```
✅ Bot connecté: @GoldyRogers_bot
✅ Message envoyé avec succès !
🎯 Score: 5/5 tests réussis (100%)
```

---

## 🔧 Dépannage

### Erreur: 404 Not Found

**Cause**: Token invalide

**Solution**:
1. Vérifier que le token est au bon format
2. Régénérer un nouveau token via @BotFather:
   - `/token`
   - Sélectionner votre bot
   - Copier le nouveau token

### Erreur: 400 Bad Request - Chat not found

**Cause**: Chat ID invalide ou bot non démarré

**Solution**:
1. Vérifier le Chat ID
2. **Démarrer le bot** en envoyant `/start` dans la conversation privée
3. Pour un groupe, s'assurer que le bot est membre

### Erreur: 401 Unauthorized

**Cause**: Token incorrect ou révoqué

**Solution**:
1. Vérifier le token dans `.env`
2. Régénérer un nouveau token via @BotFather

### Le bot ne répond pas

**Vérifications**:
1. ✅ Le bot est-il démarré ? (envoyer `/start`)
2. ✅ Le token est-il correct ?
3. ✅ Le Chat ID est-il correct ?
4. ✅ Le backend est-il lancé ?

---

## 📋 Checklist de Configuration

- [ ] Bot créé via @BotFather
- [ ] Token copié (format: `nombre:chaîne`)
- [ ] Chat ID obtenu (format: nombre)
- [ ] `/start` envoyé au bot
- [ ] `backend/.env` configuré
- [ ] Token sans `@` ni guillemets
- [ ] Chat ID sans guillemets
- [ ] Test exécuté: `python test_telegram.py`
- [ ] Message reçu sur Telegram

---

## 🎯 Commandes Utiles

### BotFather

```
/newbot      - Créer un nouveau bot
/token       - Obtenir le token d'un bot existant
/setname     - Changer le nom du bot
/setdescription - Changer la description
/setuserpic  - Changer l'avatar
/deletebot   - Supprimer un bot
```

### Test Manuel via cURL

```bash
# Test getMe
curl https://api.telegram.org/bot<TOKEN>/getMe

# Envoyer un message
curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"<CHAT_ID>","text":"Test"}'

# Obtenir les updates
curl https://api.telegram.org/bot<TOKEN>/getUpdates
```

---

## 📚 Documentation Officielle

- **Telegram Bot API**: https://core.telegram.org/bots/api
- **BotFather**: https://core.telegram.org/bots#6-botfather
- **Getting Updates**: https://core.telegram.org/bots/api#getupdates

---

## 🎨 Exemple de Message d'Alerte

Voici à quoi ressemblera une alerte:

```
🔔 ALERTE FOREX - EURUSD

📅 Non-Farm Payrolls
🕐 14:30 UTC
💱 USD

📊 Prévision: 200K
📈 Précédent: 180K

⚠️ IMPACT: EXTRÊME
📉 Mouvement attendu: 35.5 pips
🎯 Confiance: HIGH

🔴 RECOMMANDATION: Éviter de trader

---
SaaS DrevmBot - Alertes Intelligentes
```

---

## ✅ Configuration Réussie

Une fois configuré correctement, vous devriez voir:

```
============================================================
📊 RÉSULTATS FINAUX
============================================================
  ✅ Configuration
  ✅ API Telegram
  ✅ Envoi message
  ✅ NotificationManager
  ✅ API Endpoint

🎯 Score: 5/5 tests réussis (100%)

✅ TELEGRAM EST FONCTIONNEL !
🎉 Vous pouvez recevoir des notifications !

📱 Vérifiez votre Telegram (Chat ID: 123456789)
```

---

## 🔐 Sécurité

**⚠️ IMPORTANT**:

1. **Ne jamais partager** votre token Telegram
2. **Ne jamais commiter** le fichier `.env`
3. **Révoquer** le token si compromis (via @BotFather)
4. **Utiliser** des variables d'environnement en production
5. **Limiter** les permissions du bot au strict nécessaire

---

## 🚀 Prochaines Étapes

Après configuration réussie:

1. ✅ Tester l'envoi de notifications
2. ✅ Configurer les alertes automatiques
3. ✅ Personnaliser les messages
4. ✅ Ajouter des commandes au bot
5. ✅ Configurer Discord (optionnel)

---

**Généré le**: 06/02/2026 à 19:45  
**Script de test**: `test_telegram.py`  
**Status**: ⚠️ **Configuration requise**
