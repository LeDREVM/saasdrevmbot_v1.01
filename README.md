# 🤖 SaaS DrevmBot

Bot d'analyse de corrélation entre événements économiques et mouvements de prix pour le trading.

## 📋 Vue d'ensemble

DrevmBot est un système complet qui :
- 📅 Scrape les calendriers économiques (ForexFactory, Investing.com)
- 📊 Analyse l'impact réel des événements sur les prix (via yfinance)
- 🎯 Prédit l'impact potentiel des événements à venir
- 🔔 Envoie des alertes prédictives (Discord, Telegram)
- 📈 Fournit un dashboard de statistiques détaillées
- 📝 Génère des rapports Markdown pour Obsidian/Nextcloud

## 🏗️ Architecture

```
saasDrevmbot/
├── backend/              # API FastAPI + Workers
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── services/    # Logique métier
│   │   ├── models/      # Modèles DB
│   │   └── workers/     # Tâches Celery
│   └── main.py
├── frontend/            # Interface SvelteKit
│   └── src/
│       └── routes/
│           ├── calendar/  # Calendrier économique
│           └── stats/     # Dashboard statistiques
└── docker-compose.yml
```

## 🚀 Installation rapide (Docker)

### Prérequis
- Docker & Docker Compose
- Clé API Discord Webhook (optionnel)
- Token Telegram Bot (optionnel)

### Lancement

1. Cloner le repo :
```bash
git clone <repo-url>
cd saasDrevmbot
```

2. Configurer les variables d'environnement :
```bash
cp backend/.env.example backend/.env
# Éditer backend/.env avec vos tokens
```

3. Lancer avec Docker Compose :
```bash
docker-compose up -d
```

4. Accéder aux services :
- **Frontend** : http://localhost:5173
- **Backend API** : http://localhost:8000
- **API Docs** : http://localhost:8000/api/docs

## 📦 Installation manuelle

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurer .env
cp .env.example .env

# Lancer PostgreSQL et Redis localement
# Puis démarrer l'API
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🔌 Endpoints API principaux

### Calendrier économique
- `GET /api/calendar/today` - Événements du jour
- `GET /api/calendar/week` - Événements de la semaine
- `GET /api/calendar/upcoming?hours=2` - Événements à venir (high impact)

### Statistiques
- `GET /api/stats/dashboard/{symbol}?days_back=30` - Stats complètes
- `GET /api/stats/top-movers/{symbol}` - Top événements impactants
- `GET /api/stats/heatmap/{symbol}` - Heatmap volatilité
- `GET /api/stats/correlation-score?event_type=NFP&symbol=EURUSD` - Score corrélation

## 🤖 Système d'alertes

Le worker Celery vérifie automatiquement les événements à venir et envoie des alertes prédictives.

### Lancer le worker
```bash
cd backend
celery -A app.workers.alert_worker worker --loglevel=info
```

### Configuration Discord
1. Créer un webhook Discord
2. Ajouter l'URL dans `.env` : `DISCORD_WEBHOOK_URL=https://...`

### Configuration Telegram
1. Créer un bot via @BotFather
2. Récupérer le token et chat_id
3. Ajouter dans `.env`

## 📊 Fonctionnalités

### Dashboard Statistiques
- **KPIs** : Taux d'impact réel, pips moyens, volatilité post-event
- **Graphiques** : Top événements, distribution direction
- **Heatmap** : Volatilité par jour × heure
- **Timeline** : Événements chronologiques
- **Table corrélation** : Stats par type d'événement

### Prédictions
- Analyse historique des événements similaires
- Calcul du mouvement attendu (en pips)
- Probabilité de direction (up/down/neutral)
- Niveau de risque (extreme/high/medium/low)
- Recommandations actionnables

### Export Markdown
- Rapports quotidiens des prédictions
- Stats complètes par symbole
- Résumés hebdomadaires
- Compatible Obsidian/Nextcloud

## 🛠️ Technologies

### Backend
- **FastAPI** - API REST moderne
- **SQLAlchemy** - ORM
- **PostgreSQL** - Base de données
- **Redis** - Cache & queue
- **Celery** - Tâches asynchrones
- **BeautifulSoup** - Web scraping
- **yfinance** - Données de prix
- **pandas/numpy** - Analyse de données

### Frontend
- **SvelteKit** - Framework web
- **Chart.js** - Visualisations
- **Vite** - Build tool

## 📝 Configuration avancée

### Symboles supportés
- **Forex** : EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, etc.
- **Indices** : SPX, NDX, DJI, DAX
- **Commodités** : XAUUSD (Gold), XBRUSD (Oil)

### Personnalisation des alertes
Éditer `backend/app/services/alerts/alert_predictor.py` :
```python
self.HIGH_IMPACT_THRESHOLD = 20  # pips
self.MEDIUM_IMPACT_THRESHOLD = 10
self.CONFIDENCE_THRESHOLD = 3  # min samples
```

## 🧪 Tests

```bash
cd backend
pytest
```

## 📄 Licence

Propriétaire - Tous droits réservés

## 🤝 Support

Pour toute question ou problème, ouvrir une issue sur GitHub.

---

**⚠️ Disclaimer** : Ce système est fourni à titre informatif uniquement. Les prédictions ne constituent pas un conseil financier. Tradez à vos propres risques.
