# 📚 Index de la Documentation — SaaS DrevmBot

> Documentation réorganisée le 12 juillet 2026 : tous les guides sont désormais dans `docs/`.

## 🎯 Par où commencer ?

➡️ **[docs/guides/QUICKSTART.md](docs/guides/QUICKSTART.md)** — Installation en 5 minutes
➡️ **[docs/guides/GUIDE_DEMARRAGE_RAPIDE.md](docs/guides/GUIDE_DEMARRAGE_RAPIDE.md)** — Trading Economics en 5 minutes
➡️ **[README.md](README.md)** — Documentation principale complète

## 🗂️ Arborescence du projet

```
saasdrevmbot_v1.01/
├── backend/               FastAPI (port 8000)
├── frontend/              SvelteKit (port 5173)
├── src/                   Node/Express/Socket.io — bot Discord + dashboard (port 3000)
├── trading_bot/           Bot Python (backtest, MT5, divergences)
├── ny_session_interface/  Bot session NY + PineScript
├── mql/                   Experts MQL5 (MT5)
├── n8n/                   Workflows n8n (calendrier éco, alertes, retrain)
├── calendar/              Calendrier économique
├── data/                  Données (events_log.json, watchlist CSV)
├── deploy/                Services systemd + setup VPS
├── scripts/               Scripts utilitaires (.sh / .bat / .py)
├── docs/                  📚 Toute la documentation
│   ├── guides/            Guides d'utilisation et référence technique
│   ├── deploiement/       Docker, Netlify, déploiement rapide
│   ├── integrations/      Discord, Telegram, Nextcloud, Trading Economics
│   └── reports/           Rapports de test et de vérification
├── resources/             Ressources trading (PDF, template xlsx FTMO)
├── archive/               Zips d'intégration en attente (copy trading, comptes)
├── examples/              Exemples de scoring
├── netlify/ · supabase/   Functions & migrations
└── claude-config-kit-drevm/  Config Claude
```

## 📋 Documents par catégorie

### 🚀 Démarrage & référence (`docs/guides/`)
| Document | Description |
|----------|-------------|
| [QUICKSTART.md](docs/guides/QUICKSTART.md) | Installation en 5 minutes |
| [GUIDE_DEMARRAGE_RAPIDE.md](docs/guides/GUIDE_DEMARRAGE_RAPIDE.md) | Trading Economics rapide |
| [STRUCTURE_PROJET.md](docs/guides/STRUCTURE_PROJET.md) | Arborescence complète |
| [API_ENDPOINTS.md](docs/guides/API_ENDPOINTS.md) | Endpoints de l'API |
| [CONFIGURATION.md](docs/guides/CONFIGURATION.md) | Guide de configuration |
| [DEPENDENCIES.md](docs/guides/DEPENDENCIES.md) | Dépendances détaillées + troubleshooting |
| [SYNTHESE_DEPENDANCES.md](docs/guides/SYNTHESE_DEPENDANCES.md) | Synthèse des dépendances (FR) |
| [GUIDE_DASHBOARD_TRADING_ECONOMICS.md](docs/guides/GUIDE_DASHBOARD_TRADING_ECONOMICS.md) | Dashboard Trading Economics |
| [GUIDE_NAVIGATION_RESPONSIVE.md](docs/guides/GUIDE_NAVIGATION_RESPONSIVE.md) | Navigation responsive |
| [TIMELINE_COMPONENT_DOC.md](docs/guides/TIMELINE_COMPONENT_DOC.md) | Composant Timeline |

### 🚢 Déploiement (`docs/deploiement/`)
| Document | Description |
|----------|-------------|
| [DEPLOIEMENT_RAPIDE.md](docs/deploiement/DEPLOIEMENT_RAPIDE.md) | Déploiement express |
| [DOCKER_DEPLOYMENT.md](docs/deploiement/DOCKER_DEPLOYMENT.md) | Déploiement Docker Hub |
| [NETLIFY_DEPLOYMENT_GUIDE.md](docs/deploiement/NETLIFY_DEPLOYMENT_GUIDE.md) | Guide Netlify |
| [README_NETLIFY.md](docs/deploiement/README_NETLIFY.md) | Référence Netlify |

### 🔌 Intégrations (`docs/integrations/`)
| Document | Description |
|----------|-------------|
| [DISCORD_SETUP_GUIDE.md](docs/integrations/DISCORD_SETUP_GUIDE.md) | Setup Discord |
| [TELEGRAM_SETUP_GUIDE.md](docs/integrations/TELEGRAM_SETUP_GUIDE.md) | Setup Telegram |
| [NEXTCLOUD_INTEGRATION.md](docs/integrations/NEXTCLOUD_INTEGRATION.md) | Intégration Nextcloud |
| [NEXTCLOUD_QUICKSTART.md](docs/integrations/NEXTCLOUD_QUICKSTART.md) | Nextcloud rapide |
| [TRADING_ECONOMICS_SETUP.md](docs/integrations/TRADING_ECONOMICS_SETUP.md) | Setup Trading Economics |

### ✅ Rapports (`docs/reports/`)
| Document | Description |
|----------|-------------|
| [VERIFICATION_COMPLETE.md](docs/reports/VERIFICATION_COMPLETE.md) | Vérification complète |
| [VERIFICATION_BASE_SCRAPER.md](docs/reports/VERIFICATION_BASE_SCRAPER.md) | Vérification scraper |
| [INSTALLATION_SUCCESS.md](docs/reports/INSTALLATION_SUCCESS.md) | Rapport d'installation |
| [DISCORD_TEST_REPORT.md](docs/reports/DISCORD_TEST_REPORT.md) | Tests Discord |
| [TELEGRAM_TEST_REPORT.md](docs/reports/TELEGRAM_TEST_REPORT.md) | Tests Telegram |
| [FRONTEND_TEST_REPORT.md](docs/reports/FRONTEND_TEST_REPORT.md) | Tests frontend |
| [RESUME_TRADING_ECONOMICS.md](docs/reports/RESUME_TRADING_ECONOMICS.md) | Résumé Trading Economics |

## 🛠️ Scripts utilitaires (`scripts/`)

| Script | Usage |
|--------|-------|
| `deploy-netlify.sh` / `.bat` | Déploiement Netlify |
| `docker-build-push.sh` / `.bat` | Build & push Docker |
| `setup-termux.sh` | Installation Termux (Android) |
| `start_daily_worker.py` / `.bat` | Worker quotidien |
| `test_trading_economics.py` / `.bat` | Test API Trading Economics |

## 🔍 Recherche rapide

### Python / Backend
- **FastAPI** : [backend/main.py](backend/main.py)
- **Configuration** : [backend/app/core/config.py](backend/app/core/config.py)
- **API Routes** : [backend/app/api/routes/](backend/app/api/routes/)
- **Services** : [backend/app/services/](backend/app/services/)

### Svelte / Frontend
- **Configuration** : [frontend/svelte.config.js](frontend/svelte.config.js)
- **Pages** : [frontend/src/routes/](frontend/src/routes/)

### Docker
- **Compose Dev** : [docker-compose.yml](docker-compose.yml)
- **Compose Prod** : [docker-compose.prod.yml](docker-compose.prod.yml)
- **Build & Push** : [scripts/docker-build-push.sh](scripts/docker-build-push.sh)

### Fonctionnalités
- **Calendrier éco** : [backend/app/services/economic_calendar/](backend/app/services/economic_calendar/) · [backend/app/api/routes/calendar.py](backend/app/api/routes/calendar.py)
- **Stats & corrélations** : [backend/app/services/stats/](backend/app/services/stats/)
- **Alertes** : [backend/app/services/alerts/](backend/app/services/alerts/) · [backend/app/workers/alert_worker.py](backend/app/workers/alert_worker.py)

## 📦 Notes de réorganisation (12/07/2026)

- **Watchlist CSV** → `data/Portefeuille_Watchlist_03162026.csv` (chemin mis à jour dans `backend/app/core/config.py`)
- **PineScript** `ICT_RSI_Wyckoff.pine` → `ny_session_interface/pinescripttradingview/`
- **MQL5** `NY_Wyckoff_FVG_OB_Fib.mq5` → `mql/`
- **PDF & xlsx trading** → `resources/`
- **`workflown8n/ufu.json`** → `n8n/workflows/` (dossier `workflown8n/` vide, à supprimer manuellement)
- **`archive/`** : `files.zip` (module copy trading) et `files done.zip` (gestion de comptes) — code d'intégration **pas encore présent dans le repo**, à intégrer ou supprimer

---

**Dernière mise à jour** : 12 juillet 2026
**Version** : 1.0.1
