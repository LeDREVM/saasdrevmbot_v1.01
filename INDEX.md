# 📚 Index de la Documentation

Bienvenue dans la documentation du projet **SaaS DrevmBot** !

## 🎯 Par où commencer ?

### 🚀 Vous voulez démarrer rapidement ?
➡️ **[QUICKSTART.md](QUICKSTART.md)** - Guide de démarrage en 5 minutes

### 📖 Vous voulez comprendre le projet ?
➡️ **[README.md](README.md)** - Documentation principale complète

### 📦 Vous voulez vérifier les dépendances ?
➡️ **[SYNTHESE_DEPENDANCES.md](SYNTHESE_DEPENDANCES.md)** - Synthèse en français  
➡️ **[DEPENDENCIES.md](DEPENDENCIES.md)** - Documentation détaillée

### 🗂️ Vous voulez voir la structure ?
➡️ **[STRUCTURE_PROJET.md](STRUCTURE_PROJET.md)** - Arborescence complète

### ✅ Vous voulez le rapport de vérification ?
➡️ **[VERIFICATION_COMPLETE.md](VERIFICATION_COMPLETE.md)** - Rapport complet

## 📋 Documents par Catégorie

### 🎯 Démarrage
| Document | Description | Niveau |
|----------|-------------|--------|
| [QUICKSTART.md](QUICKSTART.md) | Installation en 5 minutes | ⭐ Débutant |
| [README.md](README.md) | Documentation complète | ⭐⭐ Intermédiaire |
| [backend/README.md](backend/README.md) | Documentation backend | ⭐⭐ Intermédiaire |
| [frontend/README.md](frontend/README.md) | Documentation frontend | ⭐⭐ Intermédiaire |

### 📦 Dépendances
| Document | Description | Détail |
|----------|-------------|--------|
| [SYNTHESE_DEPENDANCES.md](SYNTHESE_DEPENDANCES.md) | Synthèse en français | ✅ Complet |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Liste détaillée + troubleshooting | ✅ Complet |
| [backend/requirements.txt](backend/requirements.txt) | Dépendances Python | 23 packages |
| [frontend/package.json](frontend/package.json) | Dépendances Node.js | 16 packages |

### 🏗️ Architecture
| Document | Description | Contenu |
|----------|-------------|---------|
| [STRUCTURE_PROJET.md](STRUCTURE_PROJET.md) | Arborescence complète | 32+ fichiers |
| [VERIFICATION_COMPLETE.md](VERIFICATION_COMPLETE.md) | Rapport vérification | Checklist |
| [docker-compose.yml](docker-compose.yml) | Services Docker | 5 conteneurs |

### ⚙️ Configuration
| Fichier | Description | Emplacement |
|---------|-------------|-------------|
| [backend/env.template](backend/env.template) | Variables d'environnement | Backend |
| [CONFIGURATION.md](CONFIGURATION.md) | Guide configuration complet | Racine |
| [NEXTCLOUD_INTEGRATION.md](NEXTCLOUD_INTEGRATION.md) | Intégration Nextcloud | Racine |
| [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) | Déploiement Docker Hub | Racine |
| [backend/.gitignore](backend/.gitignore) | Exclusions Git backend | Backend |
| [frontend/.gitignore](frontend/.gitignore) | Exclusions Git frontend | Frontend |
| [backend/Dockerfile](backend/Dockerfile) | Image Docker backend | Backend |
| [frontend/Dockerfile](frontend/Dockerfile) | Image Docker frontend | Frontend |

## 🔍 Recherche Rapide

### Par Technologie

#### Python / Backend
- **FastAPI** : [backend/main.py](backend/main.py)
- **Configuration** : [backend/app/core/config.py](backend/app/core/config.py)
- **Database** : [backend/app/core/database.py](backend/app/core/database.py)
- **Modèles** : [backend/app/models/database.py](backend/app/models/database.py)
- **API Routes** : [backend/app/api/routes/](backend/app/api/routes/)
- **Services** : [backend/app/services/](backend/app/services/)

#### Svelte / Frontend
- **Configuration** : [frontend/svelte.config.js](frontend/svelte.config.js)
- **Vite** : [frontend/vite.config.js](frontend/vite.config.js)
- **Pages** : [frontend/src/routes/](frontend/src/routes/)
- **Calendrier** : [frontend/src/routes/calendar/](frontend/src/routes/calendar/)
- **Statistiques** : [frontend/src/routes/stats/](frontend/src/routes/stats/)

#### Docker
- **Compose Dev** : [docker-compose.yml](docker-compose.yml)
- **Compose Prod** : [docker-compose.prod.yml](docker-compose.prod.yml)
- **Backend Image** : [backend/Dockerfile](backend/Dockerfile)
- **Frontend Image** : [frontend/Dockerfile](frontend/Dockerfile)
- **Build & Push** : [docker-build-push.sh](docker-build-push.sh) / [docker-build-push.bat](docker-build-push.bat)
- **Guide Déploiement** : [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Par Fonctionnalité

#### 📅 Calendrier Économique
- **Scrapers** : [backend/app/services/economic_calendar/](backend/app/services/economic_calendar/)
- **API** : [backend/app/api/routes/calendar.py](backend/app/api/routes/calendar.py)
- **Interface** : [frontend/src/routes/calendar/](frontend/src/routes/calendar/)

#### 📊 Statistiques & Analyse
- **Corrélation** : [backend/app/services/stats/correlation_analyzer.py](backend/app/services/stats/correlation_analyzer.py)
- **Prix** : [backend/app/services/stats/price_fetcher.py](backend/app/services/stats/price_fetcher.py)
- **Impact** : [backend/app/services/stats/impact_calculator.py](backend/app/services/stats/impact_calculator.py)
- **API** : [backend/app/api/routes/stats.py](backend/app/api/routes/stats.py)
- **Interface** : [frontend/src/routes/stats/](frontend/src/routes/stats/)

#### 🔔 Alertes & Notifications
- **Prédictions** : [backend/app/services/alerts/alert_predictor.py](backend/app/services/alerts/alert_predictor.py)
- **Notifications** : [backend/app/services/alerts/notification_manager.py](backend/app/services/alerts/notification_manager.py)
- **Export MD** : [backend/app/services/alerts/markdown_exporter.py](backend/app/services/alerts/markdown_exporter.py)
- **Worker** : [backend/app/workers/alert_worker.py](backend/app/workers/alert_worker.py)

## 🎓 Tutoriels

### Installation
1. Lire [QUICKSTART.md](QUICKSTART.md)
2. Suivre les étapes Docker ou manuelle
3. Configurer les variables d'environnement
4. Tester les endpoints

### Développement
1. Lire [backend/README.md](backend/README.md) et [frontend/README.md](frontend/README.md)
2. Installer les dépendances
3. Lancer en mode développement
4. Consulter [STRUCTURE_PROJET.md](STRUCTURE_PROJET.md) pour l'architecture

### Déploiement
1. Configurer les variables de production
2. Utiliser Docker Compose
3. Configurer un reverse proxy (Nginx)
4. Activer HTTPS

## 📊 Statistiques du Projet

- **Total fichiers** : 32+ fichiers
- **Lignes de code** : ~3,400 lignes
- **Lignes documentation** : ~1,750 lignes
- **Dépendances Python** : 23 packages
- **Dépendances Node.js** : 16 packages
- **Services Docker** : 5 conteneurs
- **Endpoints API** : 12 endpoints
- **Pages frontend** : 2 routes principales
- **Composants Svelte** : 7 composants

## 🔗 Liens Utiles

### Documentation Externe
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SvelteKit Docs](https://kit.svelte.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Redis Docs](https://redis.io/docs/)
- [Celery Docs](https://docs.celeryq.dev/)

### APIs Utilisées
- [ForexFactory](https://www.forexfactory.com/calendar)
- [Investing.com](https://www.investing.com/economic-calendar/)
- [Yahoo Finance](https://finance.yahoo.com/)

### Outils
- [Discord Webhooks](https://discord.com/developers/docs/resources/webhook)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## ❓ FAQ

### Comment installer le projet ?
➡️ Voir [QUICKSTART.md](QUICKSTART.md)

### Quelles sont les dépendances ?
➡️ Voir [DEPENDENCIES.md](DEPENDENCIES.md) ou [SYNTHESE_DEPENDANCES.md](SYNTHESE_DEPENDANCES.md)

### Comment configurer les alertes ?
➡️ Voir [QUICKSTART.md](QUICKSTART.md) section "Configuration des alertes"

### Où sont les endpoints API ?
➡️ Voir [backend/app/api/routes/](backend/app/api/routes/) ou http://localhost:8000/api/docs

### Comment ajouter un symbole ?
➡️ Éditer [backend/app/services/stats/price_fetcher.py](backend/app/services/stats/price_fetcher.py)

### Comment personnaliser les seuils d'alerte ?
➡️ Éditer [backend/app/services/alerts/alert_predictor.py](backend/app/services/alerts/alert_predictor.py)

## 🆘 Support

En cas de problème :
1. Consulter [QUICKSTART.md](QUICKSTART.md) section "Troubleshooting"
2. Vérifier les logs : `docker-compose logs -f`
3. Consulter [DEPENDENCIES.md](DEPENDENCIES.md) section "Troubleshooting"
4. Ouvrir une issue sur GitHub

## 📝 Contribution

Pour contribuer au projet :
1. Lire [STRUCTURE_PROJET.md](STRUCTURE_PROJET.md) pour comprendre l'architecture
2. Suivre les conventions de code
3. Tester les modifications
4. Mettre à jour la documentation si nécessaire

---

**Dernière mise à jour** : 6 février 2026  
**Version** : 1.0.0  
**Statut** : ✅ Production Ready
