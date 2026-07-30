# 🗂️ Structure Complète du Projet

## Vue d'ensemble

**Total de fichiers** : 32+ fichiers  
**Langages** : Python, JavaScript/Svelte, YAML, Markdown  
**Services** : 5 conteneurs Docker

## 📁 Arborescence Détaillée

```
saasDrevmbot/
│
├── 📄 README.md                          ✅ Documentation principale
├── 📄 DEPENDENCIES.md                    ✅ Documentation dépendances
├── 📄 QUICKSTART.md                      ✅ Guide démarrage rapide
├── 📄 VERIFICATION_COMPLETE.md           ✅ Rapport vérification
├── 📄 SYNTHESE_DEPENDANCES.md            ✅ Synthèse (ce fichier)
├── 📄 STRUCTURE_PROJET.md                ✅ Structure projet
├── 🐳 docker-compose.yml                 ✅ Orchestration Docker
│
├── 🔧 backend/                           BACKEND PYTHON
│   ├── 📄 main.py                        ✅ Point d'entrée FastAPI
│   ├── 📄 requirements.txt               ✅ Dépendances Python (23)
│   ├── 📄 env.template                   ✅ Template config
│   ├── 📄 .gitignore                     ✅ Exclusions Git
│   ├── 📄 Dockerfile                     ✅ Image Docker
│   ├── 📄 README.md                      ✅ Doc backend
│   │
│   └── 📁 app/                           APPLICATION
│       ├── 📄 __init__.py                ✅
│       │
│       ├── 📁 api/                       API REST
│       │   ├── 📄 __init__.py            ✅
│       │   └── 📁 routes/
│       │       ├── 📄 __init__.py        ✅
│       │       ├── 📄 calendar.py        ✅ Endpoints calendrier
│       │       └── 📄 stats.py           ✅ Endpoints statistiques
│       │
│       ├── 📁 core/                      CONFIGURATION
│       │   ├── 📄 __init__.py            ✅
│       │   ├── 📄 config.py              ✅ Settings Pydantic
│       │   └── 📄 database.py            ✅ Connexion SQLAlchemy
│       │
│       ├── 📁 models/                    MODÈLES DB
│       │   ├── 📄 __init__.py            ✅
│       │   └── 📄 database.py            ✅ 3 tables (events, prices, alerts)
│       │
│       ├── 📁 services/                  LOGIQUE MÉTIER
│       │   ├── 📄 __init__.py            ✅
│       │   │
│       │   ├── 📁 alerts/                SYSTÈME D'ALERTES
│       │   │   ├── 📄 __init__.py        ✅
│       │   │   ├── 📄 alert_predictor.py ✅ Prédictions événements
│       │   │   ├── 📄 markdown_exporter.py ✅ Export rapports MD
│       │   │   └── 📄 notification_manager.py ✅ Discord/Telegram
│       │   │
│       │   ├── 📁 economic_calendar/     CALENDRIER ÉCONOMIQUE
│       │   │   ├── 📄 __init__.py        ✅
│       │   │   ├── 📄 base_scraper.py    ✅ Classes de base
│       │   │   ├── 📄 forexfactory_scraper.py ✅ Scraper FF
│       │   │   ├── 📄 investing_scraper.py ✅ Scraper Investing
│       │   │   ├── 📄 calendar_aggregator.py ✅ Agrégation
│       │   │   └── 📄 cache_manager.py   ✅ Cache Redis + DB
│       │   │
│       │   └── 📁 stats/                 ANALYSE STATISTIQUE
│       │       ├── 📄 __init__.py        ✅
│       │       ├── 📄 correlation_analyzer.py ✅ Analyse corrélation
│       │       ├── 📄 price_fetcher.py   ✅ Récupération prix (yfinance)
│       │       ├── 📄 impact_calculator.py ✅ Calcul impact
│       │       └── 📄 stats_aggregator.py ✅ Agrégation stats
│       │
│       └── 📁 workers/                   TÂCHES ASYNCHRONES
│           ├── 📄 __init__.py            ✅
│           └── 📄 alert_worker.py        ✅ Worker Celery
│
└── 🎨 frontend/                          FRONTEND SVELTE
    ├── 📄 package.json                   ✅ Dépendances npm (16)
    ├── 📄 svelte.config.js               ✅ Config Svelte
    ├── 📄 vite.config.js                 ✅ Config Vite
    ├── 📄 tsconfig.json                  ✅ Config TypeScript
    ├── 📄 .gitignore                     ✅ Exclusions Git
    ├── 📄 Dockerfile                     ✅ Image Docker
    ├── 📄 README.md                      ✅ Doc frontend
    │
    └── 📁 src/                           SOURCE
        └── 📁 routes/                    PAGES
            │
            ├── 📁 calendar/              PAGE CALENDRIER
            │   ├── 📄 +page.svelte       ✅ Page principale
            │   └── 📄 EventCard.svelte   ✅ Carte événement
            │
            └── 📁 stats/                 PAGE STATISTIQUES
                ├── 📄 +page.svelte       ✅ Dashboard
                ├── 📄 ImpactChart.svelte ✅ Graphique impact
                ├── 📄 HeatmapView.svelte ✅ Heatmap volatilité
                ├── 📄 CorrelationTable.svelte ✅ Table corrélation
                └── 📄 PriceTimeline.svelte ✅ Timeline événements
```

## 🎯 Modules par Fonctionnalité

### 1. 📅 Calendrier Économique
**Fichiers** : 5 modules Python
- `base_scraper.py` - Classes abstraites
- `forexfactory_scraper.py` - Scraping ForexFactory
- `investing_scraper.py` - Scraping Investing.com
- `calendar_aggregator.py` - Fusion et déduplication
- `cache_manager.py` - Cache Redis + PostgreSQL

**Endpoints API** :
- `GET /api/calendar/today`
- `GET /api/calendar/week`
- `GET /api/calendar/upcoming`

**Interface** :
- Page : `frontend/src/routes/calendar/+page.svelte`
- Composant : `EventCard.svelte`

### 2. 📊 Analyse Statistique
**Fichiers** : 4 modules Python
- `correlation_analyzer.py` - Analyse corrélation news/prix
- `price_fetcher.py` - Récupération données yfinance
- `impact_calculator.py` - Calcul impact (pips, volatilité)
- `stats_aggregator.py` - Agrégation et cache

**Endpoints API** :
- `GET /api/stats/dashboard/{symbol}`
- `GET /api/stats/top-movers/{symbol}`
- `GET /api/stats/heatmap/{symbol}`
- `GET /api/stats/correlation-score`

**Interface** :
- Page : `frontend/src/routes/stats/+page.svelte`
- Composants : 4 (ImpactChart, HeatmapView, CorrelationTable, PriceTimeline)

### 3. 🔔 Système d'Alertes
**Fichiers** : 3 modules Python
- `alert_predictor.py` - Prédictions basées historique
- `notification_manager.py` - Envoi Discord/Telegram
- `markdown_exporter.py` - Génération rapports MD

**Worker** :
- `alert_worker.py` - Tâches Celery automatiques

**Formats de sortie** :
- Notifications Discord (embeds riches)
- Messages Telegram (Markdown)
- Rapports Markdown (Obsidian/Nextcloud)

### 4. 🗄️ Base de Données
**Fichiers** : 2 modules Python
- `database.py` (models) - 3 tables SQLAlchemy
- `database.py` (core) - Connexion et sessions

**Tables** :
1. `economic_events` - Événements économiques
2. `price_data` - Données de prix (cache optionnel)
3. `alert_logs` - Historique des alertes

### 5. ⚙️ Configuration
**Fichiers** : 2 modules Python
- `config.py` - Settings Pydantic
- `env.template` - Template variables

**Variables** :
- DATABASE_URL, REDIS_URL
- DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN
- NEXTCLOUD_URL (optionnel)
- Paramètres alertes et cache

## 🐳 Services Docker

### 1. postgres
- **Image** : postgres:15-alpine
- **Port** : 5432
- **Volume** : postgres_data
- **Rôle** : Base de données principale

### 2. redis
- **Image** : redis:7-alpine
- **Port** : 6379
- **Volume** : redis_data
- **Rôle** : Cache et queue

### 3. backend
- **Build** : ./backend/Dockerfile
- **Port** : 8000
- **Commande** : uvicorn main:app
- **Rôle** : API REST FastAPI

### 4. frontend
- **Build** : ./frontend/Dockerfile
- **Port** : 5173
- **Commande** : npm run dev
- **Rôle** : Interface utilisateur

### 5. celery-worker
- **Build** : ./backend/Dockerfile
- **Commande** : celery worker
- **Rôle** : Tâches asynchrones (alertes)

## 📦 Dépendances Externes

### APIs Publiques (Scraping)
- ForexFactory.com - Calendrier forex
- Investing.com - Calendrier multi-actifs
- Yahoo Finance (via yfinance) - Prix historiques

### Services Optionnels
- Discord Webhook - Notifications
- Telegram Bot API - Notifications
- Nextcloud - Synchronisation rapports

## 🔗 Flux de Données

```
┌─────────────────┐
│  ForexFactory   │──┐
│  Investing.com  │──┼──> [Scrapers] ──> [Cache Redis] ──> [PostgreSQL]
└─────────────────┘  │                         │
                     │                         ↓
┌─────────────────┐  │                  [API FastAPI]
│  Yahoo Finance  │──┘                         │
└─────────────────┘                            ↓
                                        [Frontend Svelte]
                                               │
                                               ↓
                                        [Utilisateur]
                                               
[Celery Worker] ──> [Alert Predictor] ──> [Discord/Telegram]
       ↑                    │
       │                    ↓
       └────────── [Markdown Exporter] ──> [Nextcloud]
```

## 📈 Statistiques du Code

### Backend Python
- **Modules** : 14 fichiers .py
- **Lignes de code** : ~2,500 lignes
- **Classes** : 15+ classes
- **Endpoints API** : 12 endpoints

### Frontend Svelte
- **Composants** : 7 fichiers .svelte
- **Lignes de code** : ~900 lignes
- **Pages** : 2 routes
- **Graphiques** : 4 types de visualisations

### Configuration
- **Dockerfiles** : 2 fichiers
- **Docker Compose** : 1 fichier (5 services)
- **Documentation** : 6 fichiers Markdown

## 🎨 Technologies Utilisées

### Backend
- **Framework** : FastAPI 0.109
- **ORM** : SQLAlchemy 2.0
- **Cache** : Redis 5.0
- **Queue** : Celery 5.3
- **Scraping** : BeautifulSoup4 4.12
- **Data** : Pandas 2.2, NumPy 1.26
- **Finance** : yfinance 0.2.35

### Frontend
- **Framework** : SvelteKit 2.0
- **Build** : Vite 5.0
- **Language** : TypeScript 5.0
- **Charts** : Chart.js 4.4
- **Dates** : date-fns 3.3

### Infrastructure
- **Database** : PostgreSQL 15
- **Cache** : Redis 7
- **Container** : Docker + Docker Compose
- **Server** : Uvicorn (ASGI)

## 🚀 Points d'Entrée

### Développement
```bash
# Backend
python backend/main.py

# Frontend
npm run dev --prefix frontend

# Worker
celery -A app.workers.alert_worker worker
```

### Production (Docker)
```bash
docker-compose up -d
```

### URLs
- Frontend : http://localhost:5173
- Backend : http://localhost:8000
- API Docs : http://localhost:8000/api/docs
- ReDoc : http://localhost:8000/api/redoc

## 📚 Documentation

| Fichier | Lignes | Description |
|---------|--------|-------------|
| README.md | ~200 | Documentation principale |
| DEPENDENCIES.md | ~250 | Détails dépendances |
| QUICKSTART.md | ~300 | Guide démarrage |
| VERIFICATION_COMPLETE.md | ~400 | Rapport complet |
| SYNTHESE_DEPENDANCES.md | ~250 | Synthèse FR |
| STRUCTURE_PROJET.md | ~350 | Structure (ce fichier) |

**Total documentation** : ~1,750 lignes

---

**Projet** : SaaS DrevmBot  
**Version** : 1.0.0  
**Date** : 6 février 2026  
**Statut** : ✅ Production Ready
