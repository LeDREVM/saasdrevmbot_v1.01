# 📊 Configuration du Calendrier Économique Trading Economics

Ce guide explique comment configurer le système de récupération automatique des données de Trading Economics et l'envoi de notifications Discord.

## 🎯 Fonctionnalités

- ✅ Récupération automatique des événements économiques depuis Trading Economics
- ✅ Envoi quotidien du calendrier à 7h00 du matin
- ✅ Alertes pour les événements à fort impact
- ✅ Rappels 30 minutes avant les événements importants
- ✅ Notifications Discord formatées avec embeds

## 📋 Prérequis

1. **Python 3.10+**
2. **Webhook Discord** - [Comment créer un webhook](https://support.discord.com/hc/fr/articles/228383668)
3. **Dépendances Python** installées

## 🚀 Installation

### 1. Installer les dépendances

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

Créez un fichier `.env` dans le dossier `backend/` :

```bash
cp backend/env.template backend/.env
```

Éditez le fichier `backend/.env` et ajoutez votre webhook Discord :

```env
# Discord Webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Database (optionnel pour ce module)
DATABASE_URL=postgresql://user:password@localhost:5432/drevmbot

# Redis (optionnel pour ce module)
REDIS_URL=redis://localhost:6379/0
```

### 3. Obtenir un Webhook Discord

1. Ouvrez Discord et allez sur votre serveur
2. Cliquez sur les paramètres du canal (⚙️)
3. Allez dans **Intégrations** → **Webhooks**
4. Cliquez sur **Nouveau Webhook**
5. Donnez-lui un nom (ex: "DrevmBot Calendar")
6. Copiez l'URL du webhook
7. Collez-la dans votre fichier `.env`

## 🧪 Test du Système

### Test complet (scraper + Discord)

```bash
python test_trading_economics.py
```

Ce script va :
- ✅ Récupérer les événements d'aujourd'hui depuis Trading Economics
- ✅ Afficher les statistiques
- ✅ Tester la connexion Discord
- ✅ Envoyer un message de test
- ✅ Envoyer le calendrier du jour
- ✅ Envoyer une alerte pour un événement à fort impact

### Test uniquement du scraper

```python
python -c "
from backend.app.services.economic_calendar.tradingeconomics_scraper import TradingEconomicsScraper
scraper = TradingEconomicsScraper()
events = scraper.get_today_events()
print(f'{len(events)} événements trouvés')
"
```

### Test uniquement Discord

```python
python -c "
import os
from dotenv import load_dotenv
load_dotenv('backend/.env')
from backend.app.services.notifications.discord_notifier import DiscordNotifier
notifier = DiscordNotifier()
notifier.test_connection()
"
```

## 🤖 Démarrer le Worker

### Exécution en mode développement

```bash
python start_daily_worker.py
```

Le worker va :
- 🕐 Envoyer le calendrier tous les jours à **7h00**
- ⏰ Vérifier les événements à venir toutes les **15 minutes**
- 🚨 Envoyer des alertes **30 minutes avant** les événements importants

### Exécution en arrière-plan (Linux/Mac)

```bash
nohup python start_daily_worker.py > worker.log 2>&1 &
```

### Exécution en arrière-plan (Windows)

```powershell
Start-Process python -ArgumentList "start_daily_worker.py" -WindowStyle Hidden
```

## 📅 Configuration du Planning

Le planning est défini dans `backend/app/workers/daily_calendar_worker.py` :

```python
# Job quotidien à 7h00
schedule.every().day.at("07:00").do(self.run_daily_job)

# Alertes toutes les 15 minutes
schedule.every(15).minutes.do(self.run_upcoming_alerts)
```

### Modifier l'heure d'envoi quotidien

Éditez le fichier `backend/app/workers/daily_calendar_worker.py` :

```python
# Pour 8h30 du matin
schedule.every().day.at("08:30").do(self.run_daily_job)

# Pour 6h00 du matin
schedule.every().day.at("06:00").do(self.run_daily_job)
```

## 📊 Format des Notifications Discord

### Calendrier Quotidien

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

15:30 | USD | Unemployment Rate
Prévision: 3.7% | Précédent: 3.7%
...
```

### Alerte Événement Important

```
🚨 ALERTE ÉVÉNEMENT À FORT IMPACT 🚨

🚨 Non-Farm Employment Change
USD - United States

⏰ Heure: 14:30
💱 Devise: USD
📊 Impact: 🔴 ÉLEVÉ
📈 Prévision: 180K
📉 Précédent: 216K
```

## 🔧 Dépannage

### Erreur "DISCORD_WEBHOOK_URL non configuré"

```bash
# Vérifiez que le fichier .env existe
ls backend/.env

# Vérifiez le contenu
cat backend/.env | grep DISCORD_WEBHOOK_URL
```

### Erreur de connexion au site

- Trading Economics peut bloquer les requêtes trop fréquentes
- Le scraper inclut des pauses de 2 secondes entre les requêtes
- Vérifiez votre connexion internet

### Aucun événement trouvé

- Vérifiez que la date est correcte
- Le site peut avoir changé sa structure HTML
- Consultez les logs pour plus de détails

### Le worker ne s'exécute pas à l'heure prévue

- Vérifiez l'heure système : `date`
- Le worker utilise l'heure locale du serveur
- Vérifiez les logs : `tail -f daily_calendar_worker.log`

## 📝 Logs

Les logs sont enregistrés dans :
- `daily_calendar_worker.log` - Logs du worker
- Console - Sortie en temps réel

### Activer les logs détaillés

Dans `start_daily_worker.py`, changez le niveau de log :

```python
logging.basicConfig(
    level=logging.DEBUG,  # Au lieu de INFO
    ...
)
```

## 🚀 Déploiement en Production

### Option 1: Serveur dédié

1. Clonez le projet sur votre serveur
2. Installez les dépendances
3. Configurez le `.env`
4. Utilisez `systemd` pour gérer le service :

```bash
# Créer un service systemd
sudo nano /etc/systemd/system/drevmbot-worker.service
```

```ini
[Unit]
Description=DrevmBot Daily Calendar Worker
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/saasDrevmbot
ExecStart=/usr/bin/python3 start_daily_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer le service
sudo systemctl enable drevmbot-worker
sudo systemctl start drevmbot-worker

# Vérifier le statut
sudo systemctl status drevmbot-worker
```

### Option 2: Docker

```dockerfile
# Dockerfile.worker
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY start_daily_worker.py .

CMD ["python", "start_daily_worker.py"]
```

```bash
# Build et run
docker build -f Dockerfile.worker -t drevmbot-worker .
docker run -d --name drevmbot-worker --env-file backend/.env drevmbot-worker
```

### Option 3: Cron Job (alternative simple)

Si vous préférez utiliser cron au lieu du worker :

```bash
# Éditer crontab
crontab -e

# Ajouter cette ligne pour exécuter à 7h00 tous les jours
0 7 * * * cd /path/to/saasDrevmbot && python test_trading_economics.py >> /var/log/drevmbot.log 2>&1
```

## 📚 API Endpoints (optionnel)

Vous pouvez également intégrer le scraper dans votre API FastAPI :

```python
# backend/app/api/routes/trading_economics.py
from fastapi import APIRouter
from app.services.economic_calendar.tradingeconomics_scraper import TradingEconomicsScraper

router = APIRouter()

@router.get("/trading-economics/today")
async def get_today_events():
    scraper = TradingEconomicsScraper()
    events = scraper.get_today_events()
    return {"events": events, "count": len(events)}
```

## 🎨 Personnalisation

### Modifier les couleurs Discord

Dans `backend/app/services/notifications/discord_notifier.py` :

```python
embed = {
    "color": 0x5865F2,  # Bleu Discord
    # Autres couleurs :
    # 0xED4245 - Rouge
    # 0x57F287 - Vert
    # 0xFEE75C - Jaune
    # 0xEB459E - Rose
}
```

### Filtrer par devise

```python
# Dans le scraper, filtrer uniquement EUR et USD
events = scraper.get_today_events()
filtered = [e for e in events if e['currency'] in ['EUR', 'USD']]
```

## 📞 Support

Pour toute question ou problème :
1. Consultez les logs
2. Vérifiez la configuration
3. Testez avec `test_trading_economics.py`

## 📄 Licence

Ce projet fait partie de SaaS DrevmBot.
