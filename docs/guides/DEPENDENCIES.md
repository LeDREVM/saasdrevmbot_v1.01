# 📦 Documentation des Dépendances

## Backend (Python)

### Framework Web
- **fastapi** (0.109.0) - Framework web moderne pour API REST
- **uvicorn[standard]** (0.27.0) - Serveur ASGI haute performance
- **python-multipart** (0.0.6) - Support multipart/form-data

### Base de données
- **sqlalchemy** (2.0.25) - ORM Python
- **psycopg2-binary** (2.9.9) - Driver PostgreSQL
- **alembic** (1.13.1) - Migrations de base de données

### Cache & Queue
- **redis** (5.0.1) - Client Redis pour cache
- **celery** (5.3.6) - Tâches asynchrones distribuées

### HTTP & Web Scraping
- **requests** (2.31.0) - Requêtes HTTP
- **beautifulsoup4** (4.12.3) - Parsing HTML
- **lxml** (5.1.0) - Parser XML/HTML rapide

### Traitement de données
- **pandas** (2.2.0) - Manipulation de données tabulaires
- **numpy** (1.26.3) - Calculs numériques

### Données financières
- **yfinance** (0.2.35) - API Yahoo Finance pour prix

### Utilitaires
- **python-dotenv** (1.0.1) - Gestion variables d'environnement
- **pydantic** (2.5.3) - Validation de données
- **pydantic-settings** (2.1.0) - Configuration via Pydantic
- **python-json-logger** (2.0.7) - Logging JSON structuré

### Tests (optionnel)
- **pytest** (7.4.4) - Framework de tests
- **pytest-asyncio** (0.23.3) - Support async pour pytest
- **httpx** (0.26.0) - Client HTTP async pour tests

## Frontend (Node.js)

### Framework
- **@sveltejs/kit** (^2.0.0) - Framework web Svelte
- **svelte** (^4.2.7) - Framework UI réactif
- **@sveltejs/adapter-auto** (^3.0.0) - Adaptateur de déploiement
- **@sveltejs/vite-plugin-svelte** (^3.0.0) - Plugin Vite pour Svelte

### Build Tools
- **vite** (^5.0.3) - Build tool moderne
- **typescript** (^5.0.0) - Support TypeScript
- **tslib** (^2.4.1) - Helpers TypeScript

### Qualité de code
- **eslint** (^8.56.0) - Linter JavaScript
- **eslint-config-prettier** (^9.1.0) - Config ESLint pour Prettier
- **eslint-plugin-svelte** (^2.35.1) - Plugin ESLint pour Svelte
- **prettier** (^3.1.1) - Formateur de code
- **prettier-plugin-svelte** (^3.1.2) - Plugin Prettier pour Svelte
- **svelte-check** (^3.6.0) - Vérification de types Svelte

### Dépendances runtime
- **chart.js** (^4.4.1) - Bibliothèque de graphiques
- **date-fns** (^3.3.1) - Manipulation de dates

## Services externes requis

### Infrastructure
- **PostgreSQL** (15+) - Base de données relationnelle
- **Redis** (7+) - Cache en mémoire et queue de messages

### APIs externes (scraping)
- **ForexFactory** (https://www.forexfactory.com) - Calendrier économique
- **Investing.com** (https://www.investing.com) - Calendrier économique
- **Yahoo Finance** (via yfinance) - Données de prix

### Notifications (optionnel)
- **Discord Webhook** - Alertes Discord
- **Telegram Bot API** - Alertes Telegram
- **Nextcloud** (optionnel) - Synchronisation rapports Markdown

## Installation

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

### Docker (recommandé)
```bash
docker-compose up -d
```

## Versions minimales requises

- **Python** : 3.10+
- **Node.js** : 18+
- **PostgreSQL** : 15+
- **Redis** : 7+
- **Docker** : 20.10+ (si utilisation Docker)
- **Docker Compose** : 2.0+ (si utilisation Docker)

## Notes de sécurité

### Variables sensibles à configurer
- `DATABASE_URL` - Connexion PostgreSQL
- `REDIS_URL` - Connexion Redis
- `DISCORD_WEBHOOK_URL` - Webhook Discord (si alertes)
- `TELEGRAM_BOT_TOKEN` - Token bot Telegram (si alertes)
- `TELEGRAM_CHAT_ID` - ID chat Telegram (si alertes)

### Recommandations production
1. Utiliser des mots de passe forts pour PostgreSQL
2. Activer l'authentification Redis
3. Restreindre CORS dans FastAPI
4. Utiliser HTTPS pour toutes les communications
5. Limiter les rate limits sur les endpoints publics
6. Configurer des backups automatiques de la DB

## Mises à jour

Pour mettre à jour les dépendances :

### Backend
```bash
pip install --upgrade -r requirements.txt
```

### Frontend
```bash
npm update
```

## Dépendances de développement

### Backend
- Éditeur Python avec support LSP (VS Code, PyCharm)
- Extensions recommandées : Python, Pylance, Black Formatter

### Frontend
- Extensions recommandées : Svelte for VS Code, ESLint, Prettier

## Troubleshooting

### Erreur psycopg2
Si erreur lors de l'installation de `psycopg2-binary` :
```bash
# Linux
sudo apt-get install libpq-dev

# macOS
brew install postgresql
```

### Erreur lxml
Si erreur lors de l'installation de `lxml` :
```bash
# Linux
sudo apt-get install libxml2-dev libxslt1-dev

# macOS
brew install libxml2
```

### Erreur yfinance
Si problèmes de connexion Yahoo Finance, vérifier :
- Connexion internet
- Pas de blocage firewall
- Rate limiting Yahoo (attendre quelques minutes)
