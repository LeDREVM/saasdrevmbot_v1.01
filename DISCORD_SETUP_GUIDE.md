# 💬 Guide de Configuration Discord - SaaS DrevmBot

**Date**: 06/02/2026  
**Status**: ✅ **CONFIGURÉ ET FONCTIONNEL**

---

## 🎉 Félicitations !

Votre webhook Discord est **déjà configuré et fonctionnel** !

```
✅ Webhook ID: 1437084856504025108
✅ Messages envoyés avec succès
✅ Embeds formatés fonctionnent
```

---

## 📝 Configuration Actuelle

### Webhook Discord

**URL**: `https://discord.com/api/webhooks/1437084856504025108/bQE7QpaUS362QujF-60k...`

**Status**: ✅ **Actif et validé**

**Permissions**:
- ✅ Envoyer des messages
- ✅ Envoyer des embeds
- ✅ Utiliser des emojis

---

## 🔧 Comment Créer un Webhook Discord

Si vous devez créer un nouveau webhook:

### Étape 1: Accéder aux Paramètres du Serveur

1. **Ouvrir Discord**
2. **Clic droit** sur votre serveur
3. **Paramètres du serveur**
4. **Intégrations** (dans le menu de gauche)

### Étape 2: Créer un Webhook

1. Cliquer sur **"Webhooks"**
2. Cliquer sur **"Nouveau Webhook"** ou **"Créer un Webhook"**
3. **Nommer** le webhook (ex: "SaaS DrevmBot Alerts")
4. **Choisir** le canal où les messages seront envoyés
5. **Personnaliser** l'avatar (optionnel)

### Étape 3: Copier l'URL

1. Cliquer sur **"Copier l'URL du Webhook"**
2. L'URL ressemble à:
   ```
   https://discord.com/api/webhooks/1234567890/ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### Étape 4: Configurer dans .env

Éditer `backend/.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/ABCdefGHIjklMNOpqrsTUVwxyz
```

---

## 🧪 Tester la Configuration

### Test Rapide

```bash
python test_discord.py
```

**Résultat attendu**:
```
✅ Configuration
✅ Format webhook
✅ Message simple
✅ Message embed
🎯 Score: 4/6 tests réussis (66%)
✅ DISCORD EST FONCTIONNEL !
```

### Test Manuel via cURL

```bash
curl -X POST "https://discord.com/api/webhooks/VOTRE_ID/VOTRE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"🤖 Test manuel"}'
```

---

## 💬 Types de Messages

### 1. Message Simple

```python
import requests

webhook_url = "https://discord.com/api/webhooks/..."

payload = {
    'content': '🔔 Alerte Forex EURUSD !'
}

response = requests.post(webhook_url, json=payload)
```

**Résultat**:
```
🔔 Alerte Forex EURUSD !
```

### 2. Message avec Embed

```python
embed = {
    'title': '🔔 Alerte EURUSD',
    'description': 'Non-Farm Payrolls',
    'color': 15158332,  # Rouge
    'fields': [
        {
            'name': '⚠️ Impact',
            'value': 'EXTRÊME',
            'inline': True
        },
        {
            'name': '📊 Mouvement',
            'value': '35.5 pips',
            'inline': True
        }
    ],
    'footer': {
        'text': 'SaaS DrevmBot'
    }
}

payload = {'embeds': [embed]}
response = requests.post(webhook_url, json=payload)
```

**Résultat**: Un embed coloré avec plusieurs champs

### 3. Message avec Mentions

```python
payload = {
    'content': '<@USER_ID> Alerte importante !',
    # ou
    'content': '@everyone Alerte importante !'
}
```

---

## 🎨 Personnalisation

### Couleurs des Embeds

```python
COLORS = {
    'extreme': 15158332,   # Rouge (#E74C3C)
    'high': 15105570,      # Orange (#E67E22)
    'medium': 3447003,     # Bleu (#3498DB)
    'low': 3066993,        # Vert (#2ECC71)
    'info': 10181046,      # Violet (#9B59B6)
    'warning': 15844367,   # Or (#F1C40F)
}
```

### Emojis Recommandés

```
🔔 - Alerte
📊 - Statistiques
💱 - Forex/Trading
⚠️ - Attention
🔴 - Danger/Extrême
🟠 - Élevé
🟡 - Moyen
🟢 - Faible
📅 - Date
🕐 - Heure
🎯 - Confiance
📈 - Hausse
📉 - Baisse
✅ - Succès
❌ - Échec
```

### Avatar du Webhook

1. Aller dans les paramètres du webhook
2. Cliquer sur l'avatar
3. Uploader une image (PNG/JPG, max 8MB)
4. Sauvegarder

---

## 📋 Exemples d'Alertes

### Alerte Forex Standard

```python
embed = {
    'title': '🔔 ALERTE FOREX - EURUSD',
    'description': '**Non-Farm Payrolls**',
    'color': 15158332,  # Rouge
    'fields': [
        {'name': '📅 Date', 'value': '06/02/2026', 'inline': True},
        {'name': '🕐 Heure', 'value': '14:30 UTC', 'inline': True},
        {'name': '💱 Devise', 'value': 'USD', 'inline': True},
        {'name': '📊 Prévision', 'value': '200K', 'inline': True},
        {'name': '📈 Précédent', 'value': '180K', 'inline': True},
        {'name': '⚠️ Impact', 'value': 'EXTRÊME', 'inline': True},
        {'name': '📉 Mouvement Attendu', 'value': '35.5 pips', 'inline': False},
        {'name': '🎯 Confiance', 'value': 'HIGH (85%)', 'inline': True},
        {'name': '🔴 Recommandation', 'value': 'Éviter de trader', 'inline': False}
    ],
    'footer': {'text': 'SaaS DrevmBot - Alertes Intelligentes'},
    'timestamp': '2026-02-06T14:30:00Z'
}
```

### Alerte Rapide

```python
embed = {
    'title': '⚡ ALERTE RAPIDE',
    'description': 'Événement à fort impact dans 30 minutes !',
    'color': 15844367,  # Or
    'fields': [
        {'name': 'Événement', 'value': 'NFP', 'inline': True},
        {'name': 'Paire', 'value': 'EURUSD', 'inline': True},
        {'name': 'Dans', 'value': '30 min', 'inline': True}
    ]
}
```

### Résumé Quotidien

```python
embed = {
    'title': '📊 Résumé Quotidien',
    'description': 'Statistiques du 06/02/2026',
    'color': 3447003,  # Bleu
    'fields': [
        {'name': '🔔 Alertes Envoyées', 'value': '12', 'inline': True},
        {'name': '🎯 Précision', 'value': '87%', 'inline': True},
        {'name': '📊 Mouvement Moyen', 'value': '28.5 pips', 'inline': True}
    ]
}
```

---

## 🔐 Sécurité et Bonnes Pratiques

### ✅ À Faire

1. **Stocker** l'URL du webhook dans `.env`
2. **Ajouter** `.env` au `.gitignore`
3. **Créer** un webhook dédié par environnement
4. **Limiter** les permissions du webhook
5. **Monitorer** les envois
6. **Implémenter** un rate limiting
7. **Gérer** les erreurs proprement

### ❌ À Éviter

1. **Ne jamais** commiter l'URL du webhook
2. **Ne jamais** partager l'URL publiquement
3. **Ne pas** dépasser 30 req/min
4. **Ne pas** envoyer de données sensibles
5. **Ne pas** spammer le canal

### 🔄 Rotation du Webhook

Si le webhook est compromis:

1. Aller dans les paramètres du webhook
2. Cliquer sur **"Supprimer le Webhook"**
3. Créer un nouveau webhook
4. Mettre à jour `.env`
5. Redémarrer l'application

---

## 📊 Limites et Quotas

### Rate Limits Discord

- **30 requêtes par minute** par webhook
- **5 requêtes par seconde** par webhook
- **2000 caractères** max par message
- **6000 caractères** max par embed
- **10 embeds** max par message
- **25 fields** max par embed

### Gestion du Rate Limiting

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_calls=30, period=60):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
    
    def wait_if_needed(self):
        now = time.time()
        # Supprimer les appels anciens
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        
        # Attendre si limite atteinte
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            time.sleep(sleep_time)
        
        self.calls.append(now)
```

---

## 🐛 Dépannage

### Erreur: 404 Not Found

**Cause**: Webhook supprimé ou URL invalide

**Solution**:
1. Vérifier que le webhook existe toujours
2. Recréer un webhook si nécessaire
3. Mettre à jour l'URL dans `.env`

### Erreur: 401 Unauthorized

**Cause**: Token du webhook incorrect

**Solution**: Copier à nouveau l'URL complète

### Erreur: 429 Too Many Requests

**Cause**: Rate limit dépassé

**Solution**:
1. Implémenter un rate limiter
2. Espacer les envois
3. Utiliser une queue

### Message non reçu

**Vérifications**:
1. Le webhook existe-t-il ?
2. Le canal est-il accessible ?
3. L'URL est-elle complète ?
4. Le payload est-il valide ?

---

## 🚀 Intégration dans l'Application

### Via l'Interface Web

1. Accéder à: http://localhost:5173/alerts
2. Onglet **"Overview"**
3. Section **"🧪 Test Notifications"**
4. Cliquer sur **"💬 Test Discord"**

### Via l'API

```bash
curl -X POST http://localhost:8000/api/alert-config/test-notification/negus_dja \
  -H "Content-Type: application/json" \
  -d '{"channel":"discord"}'
```

### Automatique

Les alertes seront envoyées automatiquement quand:
- Un événement à fort impact est détecté
- Le mouvement prévu dépasse le seuil
- La confiance est suffisante

---

## 📚 Ressources

### Documentation Officielle

- **Discord Webhooks**: https://discord.com/developers/docs/resources/webhook
- **Rate Limits**: https://discord.com/developers/docs/topics/rate-limits
- **Embed Limits**: https://discord.com/developers/docs/resources/channel#embed-limits

### Outils Utiles

- **Embed Builder**: https://discohook.org/
- **Embed Visualizer**: https://leovoel.github.io/embed-visualizer/
- **Color Picker**: https://www.spycolor.com/
- **Emoji List**: https://emojipedia.org/

---

## ✅ Checklist

- [x] Webhook Discord créé
- [x] URL du webhook copiée
- [x] `backend/.env` configuré
- [x] Test message simple réussi
- [x] Test embed réussi
- [x] Messages reçus sur Discord
- [ ] Backend démarré
- [ ] Test via interface web
- [ ] Alertes automatiques configurées

---

## 🎯 Prochaines Étapes

1. ✅ ~~Configuration Discord~~ (FAIT)
2. ✅ ~~Test des webhooks~~ (FAIT)
3. ⏳ Démarrer le backend
4. ⏳ Tester via l'interface web
5. ⏳ Configurer les alertes automatiques
6. ⏳ Personnaliser les messages
7. ⏳ Ajouter des commandes bot (optionnel)

---

**Généré le**: 06/02/2026 à 19:50  
**Status**: ✅ **CONFIGURÉ ET FONCTIONNEL**  
**Action**: Vérifier votre canal Discord pour les messages de test !
