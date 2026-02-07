# 🚀 Guide de Démarrage Rapide - Trading Economics

## ⚡ Configuration en 5 minutes

### 1️⃣ Créer un Webhook Discord (2 minutes)

1. Ouvrez Discord et allez sur votre serveur
2. Cliquez sur la roue dentée ⚙️ à côté du nom du canal
3. Allez dans **Intégrations** → **Webhooks**
4. Cliquez sur **Créer un Webhook**
5. Nommez-le "DrevmBot" et copiez l'URL du webhook

### 2️⃣ Configurer le fichier .env (1 minute)

Créez un fichier `.env` dans le dossier `backend/` :

```bash
# Windows
copy backend\env.template backend\.env
notepad backend\.env

# Linux/Mac
cp backend/env.template backend/.env
nano backend/.env
```

Ajoutez votre webhook Discord :

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/VOTRE_WEBHOOK_ICI
```

### 3️⃣ Installer les dépendances (1 minute)

```bash
# Activer l'environnement virtuel
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install requests beautifulsoup4 lxml schedule python-dotenv
```

### 4️⃣ Tester le système (1 minute)

#### Windows
```bash
test_trading_economics.bat
```

#### Linux/Mac
```bash
python test_trading_economics.py
```

Vous devriez voir :
- ✅ Récupération des événements
- ✅ Test de connexion Discord réussi
- ✅ Message de test dans Discord
- ✅ Calendrier du jour envoyé

### 5️⃣ Démarrer le worker automatique

#### Windows
```bash
start_daily_worker.bat
```

#### Linux/Mac
```bash
python start_daily_worker.py
```

Le worker va maintenant :
- 📅 Envoyer le calendrier tous les jours à **7h00**
- ⏰ Vérifier les événements à venir toutes les **15 minutes**
- 🚨 Envoyer des alertes **30 minutes avant** les événements importants

## 🎯 C'est tout !

Votre bot est maintenant configuré et fonctionnel. Vous recevrez automatiquement :

- **Chaque matin à 7h00** : Le calendrier économique complet du jour
- **30 minutes avant** : Des rappels pour les événements importants
- **En temps réel** : Des alertes pour les événements à fort impact

## 📊 Exemple de notification

Voici ce que vous recevrez dans Discord :

```
📊 Calendrier Économique - 07/02/2024
45 événements prévus aujourd'hui

📈 Résumé
🔴 8 Fort impact
🟡 15 Impact moyen
🟢 22 Faible impact

🔴 Événements à Fort Impact
14:30 | USD | Non-Farm Payrolls
Prévision: 180K | Précédent: 216K
...
```

## 🔧 Dépannage Rapide

### Le webhook ne fonctionne pas
```bash
# Vérifiez que le fichier .env existe
dir backend\.env  # Windows
ls backend/.env   # Linux/Mac

# Vérifiez le contenu
type backend\.env  # Windows
cat backend/.env   # Linux/Mac
```

### Aucun événement trouvé
- Vérifiez votre connexion internet
- Le site Trading Economics peut être temporairement indisponible
- Réessayez dans quelques minutes

### Le worker ne démarre pas
```bash
# Vérifiez que toutes les dépendances sont installées
pip list | findstr "requests beautifulsoup4 schedule"  # Windows
pip list | grep -E "requests|beautifulsoup4|schedule"  # Linux/Mac
```

## 📚 Documentation Complète

Pour plus de détails, consultez [TRADING_ECONOMICS_SETUP.md](TRADING_ECONOMICS_SETUP.md)

## 💡 Astuces

### Changer l'heure d'envoi

Éditez `backend/app/workers/daily_calendar_worker.py` ligne 121 :

```python
# Pour 8h30 au lieu de 7h00
schedule.every().day.at("08:30").do(self.run_daily_job)
```

### Filtrer par devise

Éditez `backend/app/services/economic_calendar/tradingeconomics_scraper.py` pour ne garder que certaines devises :

```python
# Filtrer uniquement EUR et USD
if currency not in ['EUR', 'USD']:
    return None
```

### Désactiver les alertes 30 minutes avant

Commentez la ligne 125 dans `backend/app/workers/daily_calendar_worker.py` :

```python
# schedule.every(15).minutes.do(self.run_upcoming_alerts)
```

## 🎉 Profitez de votre bot !

Votre bot Trading Economics est maintenant opérationnel. Il travaillera pour vous 24/7 pour vous tenir informé des événements économiques importants.

**Bon trading ! 📈💰**
