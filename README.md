# saasDrevmBot v2.0 — Plateforme de Trading Algorithmique

Plateforme complète de surveillance des marchés financiers, composée de trois services interconnectés : un bot Discord / dashboard Node.js, un backend FastAPI Python, et un frontend analytique SvelteKit.

---

## ⚙ Architecture — 3 services

| Service | Technologie | Port | Rôle |
|---|---|---|---|
| **GoldyXbOT** | Node.js · Express · Socket.io | `3000` | Dashboard principal, bot Discord, scrapers, corrélations |
| **saasDrevmBot API** | Python · FastAPI · SQLAlchemy | `8000` | API REST, alertes, stats, Nextcloud, session NYSE |
| **Analytics** | SvelteKit · Chart.js · Vite | `5173` | Dashboard analytique, corrélations, alertes configurables |

---

## ✅ Fonctionnalités principales

### GoldyXbOT (Node.js)
- **Scraping automatique** : ForexFactory, Investing.com, Alpha Vantage (calendrier économique)
- **Alertes Discord** : embeds colorés avec rappels avant événement et résultats en temps réel
- **Filtrage** par niveau d'impact (🔴 Fort / 🟠 Moyen / 🟡 Faible) et par devise
- **Dashboard web** temps réel avec Socket.io (US30, VIX, événements)
- **Moteur de corrélation** : analyse l'impact des événements économiques sur les prix via Yahoo Finance
- **Briefing matinal** à 8h00 chaque jour de semaine
- **Export Nextcloud** automatique des calendriers journaliers

### saasDrevmBot API (FastAPI)
- **6 routers** : calendar, stats, alerts, alert_config, nextcloud, trading_economics
- **Session NYSE** : suivi Pre-Market / Regular / After-Hours
- **Alertes configurables** avec base PostgreSQL + SQLAlchemy
- **Watchlist** et statistiques historiques
- **Documentation interactive** : `/api/docs` (Swagger UI)

### Analytics (SvelteKit)
- **4 pages** : Calendrier, Statistiques, Corrélations, Alertes
- **Graphiques** Chart.js : heatmap, timeline prix, impact par type d'événement
- **CorrelationTable**, **HeatmapView**, **ImpactChart**, **PriceTimeline**

---

## 🚀 Démarrage rapide

```bash
# 1. Dépendances Node.js
npm install

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env (voir section Configuration)

# 3. Lancer GoldyXbOT + Dashboard (port 3000)
npm start

# 4. Mode bot seul (sans Express)
npm run bot-only

# 5. Backend FastAPI (port 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 6. Frontend SvelteKit (port 5173)
cd frontend
npm install
npm run dev
```

---

## ⚙ Configuration (.env)

### Discord
| Variable | Défaut | Description |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | — | **Obligatoire** — URL du webhook Discord |
| `DISCORD_WEBHOOK_URLS` | — | Plusieurs webhooks séparés par `,` |

### Filtrage événements
| Variable | Défaut | Description |
|---|---|---|
| `MIN_IMPACT` | `3` | Impact minimum (1=faible, 2=moyen, 3=fort) |
| `CURRENCIES` | vide (toutes) | Devises à surveiller, ex: `USD,EUR,GBP,JPY` |
| `CHECK_INTERVAL` | `5` | Intervalle de scan en minutes |
| `REMINDER_MINUTES` | `15` | Minutes avant rappel (0 = désactivé) |
| `TIMEZONE` | `Europe/Paris` | Fuseau horaire |

### Sources de données
| Variable | Défaut | Description |
|---|---|---|
| `ENABLE_FOREXFACTORY` | `true` | Activer le scraper ForexFactory |
| `ENABLE_INVESTING` | `true` | Activer le scraper Investing.com |
| `ENABLE_ALPHAVANTAGE` | `false` | Activer l'API Alpha Vantage |
| `ALPHA_VANTAGE_API_KEY` | — | Clé API Alpha Vantage (gratuite) |
| `ALPHA_VANTAGE_HORIZON` | `3month` | Fenêtre : `3month` / `6month` / `12month` |
| `ENABLE_SAAS_API` | `true` | Utiliser saasDrevmBot API comme source principale |

### Intégrations
| Variable | Défaut | Description |
|---|---|---|
| `ENABLE_NEXTCLOUD` | `false` | Export automatique vers Nextcloud |
| `NEXTCLOUD_URL` | — | URL de l'instance Nextcloud |
| `NEXTCLOUD_USERNAME` | — | Nom d'utilisateur Nextcloud |
| `NEXTCLOUD_PASSWORD` | — | Mot de passe ou token d'application |
| `NEXTCLOUD_FOLDER` | — | Dossier distant de stockage |

---

## 📁 Structure du projet

```
GoldyXbOT/
├── src/                        # GoldyXbOT — Node.js
│   ├── server.js               # Point d'entrée principal (Express + Socket.io)
│   ├── index.js                # Mode bot seul (sans serveur web)
│   ├── public/                 # Centre de contrôle (home.html) + Dashboard
│   ├── scrapers/
│   │   ├── forexfactory.js     # Scraper ForexFactory
│   │   ├── investing.js        # Scraper Investing.com
│   │   └── alphavantage.js     # API Alpha Vantage (calendrier)
│   ├── services/
│   │   ├── correlationEngine.js  # Analyse corrélation événements / prix
│   │   ├── marketData.js         # US30 + VIX via Yahoo Finance
│   │   ├── saasApi.js            # Client HTTP vers FastAPI
│   │   └── nextcloudExport.js    # Export WebDAV Nextcloud
│   └── utils/
│       ├── discord.js          # Formatage et envoi des embeds Discord
│       ├── eventStore.js       # Store en mémoire + déduplication
│       └── timeUtils.js        # Utilitaires de temps / timezone
│
├── backend/                    # saasDrevmBot API — Python / FastAPI
│   ├── main.py
│   ├── requirements.txt
│   └── app/
│       ├── api/routes/         # calendar, stats, alerts, nextcloud, trading_economics
│       ├── services/           # alerts, economic_calendar, nextcloud, stats, watchlist
│       └── models/             # SQLAlchemy ORM
│
├── frontend/                   # Analytics — SvelteKit
│   ├── src/routes/             # /, /calendar, /stats, /alerts
│   └── src/lib/                # Composants Chart.js
│
└── data/                       # Cache local
    ├── events_log.json         # Historique 90 jours (corrélation)
    └── price_cache/            # Cache OHLCV Yahoo Finance (25h)
```

---

## 💬 Créer un Webhook Discord

1. Dans Discord, clic droit sur ton canal → **Modifier le canal**
2. **Intégrations** → **Webhooks** → **Nouveau webhook**
3. Copier l'URL et la coller dans `.env` (`DISCORD_WEBHOOK_URL`)

---

## 🐳 Docker

```bash
# Démarrage complet (Node + FastAPI + PostgreSQL)
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🌐 URLs

| URL | Description |
|---|---|
| `http://localhost:3000` | Centre de contrôle (steampunk tropical) |
| `http://localhost:3000/dashboard` | Dashboard calendrier économique |
| `http://localhost:5173` | Analytics SvelteKit |
| `http://localhost:8000/api/docs` | Swagger UI FastAPI |
