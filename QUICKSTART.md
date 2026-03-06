# 🚀 Guide de Démarrage Rapide

## Installation en 5 minutes avec Docker

### 1. Prérequis
```bash
# Vérifier que Docker est installé
docker --version
docker-compose --version
```

### 2. Configuration
```bash
# Créer le fichier .env
cp backend/.env.example backend/.env

# Éditer avec vos configurations (optionnel pour démarrage rapide)
# Les valeurs par défaut fonctionnent pour le développement local
```

### 3. Lancement
```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier que tout fonctionne
docker-compose ps
```

### 4. Accès
- **Frontend** : http://localhost:5173
- **Backend API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/api/docs

### 5. Test rapide
```bash
# Tester l'API
curl http://localhost:8000/health

# Récupérer le calendrier du jour
curl http://localhost:8000/api/calendar/today

# Stats pour EUR/USD
curl "http://localhost:8000/api/stats/dashboard/EURUSD?days_back=30"
```

## Installation manuelle (sans Docker)

### Backend

1. **Installer PostgreSQL et Redis**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql redis-server

# macOS
brew install postgresql redis

# Démarrer les services
sudo service postgresql start
sudo service redis-server start
```

2. **Configurer Python**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configurer la base de données**
```bash
# Créer la base
sudo -u postgres psql
CREATE DATABASE drevmbot;
CREATE USER drevmbot WITH PASSWORD 'drevmbot_password';
GRANT ALL PRIVILEGES ON DATABASE drevmbot TO drevmbot;
\q

# Initialiser les tables
python -c "from app.core.database import init_db; init_db()"
```

4. **Lancer le backend**
```bash
python main.py
```

### Frontend

1. **Installer Node.js** (si pas déjà installé)
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node
```

2. **Installer les dépendances**
```bash
cd frontend
npm install
```

3. **Lancer le frontend**
```bash
npm run dev
```

### Worker Celery (optionnel - pour alertes)

```bash
cd backend
source venv/bin/activate
celery -A app.workers.alert_worker worker --loglevel=info
```

## Configuration des alertes (optionnel)

### Discord

1. Créer un webhook Discord :
   - Aller dans les paramètres du serveur
   - Intégrations → Webhooks → Nouveau Webhook
   - Copier l'URL

2. Ajouter dans `backend/.env` :
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### Telegram

1. Créer un bot :
   - Parler à @BotFather sur Telegram
   - `/newbot` et suivre les instructions
   - Copier le token

2. Obtenir votre chat_id :
   - Parler à @userinfobot
   - Copier votre ID

3. Ajouter dans `backend/.env` :
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Utilisation

### Page Calendrier
1. Aller sur http://localhost:5173/calendar
2. Voir les événements économiques du jour
3. Filtrer par devise (USD, EUR, etc.)
4. Filtrer par impact (High, Medium, Low)

### Page Statistiques
1. Aller sur http://localhost:5173/stats
2. Sélectionner un symbole (EURUSD, GBPUSD, etc.)
3. Choisir la période d'analyse (7-90 jours)
4. Explorer les graphiques et statistiques

### API REST

#### Calendrier
```bash
# Événements du jour
GET /api/calendar/today

# Événements de la semaine
GET /api/calendar/week

# Événements high impact à venir (2h)
GET /api/calendar/upcoming?hours=2
```

#### Statistiques
```bash
# Dashboard complet
GET /api/stats/dashboard/{symbol}?days_back=30

# Top événements impactants
GET /api/stats/top-movers/{symbol}?days_back=30&limit=10

# Heatmap volatilité
GET /api/stats/heatmap/{symbol}?days_back=30

# Score de corrélation
GET /api/stats/correlation-score?event_type=NFP&symbol=EURUSD
```

## Commandes utiles

### Docker

```bash
# Voir les logs
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend

# Redémarrer un service
docker-compose restart backend

# Arrêter tout
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v

# Reconstruire les images
docker-compose build --no-cache
```

### Base de données

```bash
# Se connecter à PostgreSQL
docker-compose exec postgres psql -U drevmbot -d drevmbot

# Voir les tables
\dt

# Voir les événements
SELECT * FROM economic_events LIMIT 10;

# Quitter
\q
```

### Redis

```bash
# Se connecter à Redis
docker-compose exec redis redis-cli

# Voir toutes les clés
KEYS *

# Voir une valeur
GET calendar:today:USD,EUR:High

# Vider le cache
FLUSHALL

# Quitter
exit
```

## Troubleshooting

### Port déjà utilisé
```bash
# Changer les ports dans docker-compose.yml
# Exemple : "8001:8000" au lieu de "8000:8000"
```

### Erreur de connexion DB
```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres

# Voir les logs
docker-compose logs postgres

# Recréer le conteneur
docker-compose down
docker-compose up -d postgres
```

### Erreur yfinance (pas de données)
- Vérifier la connexion internet
- Attendre quelques minutes (rate limiting Yahoo)
- Essayer un autre symbole

### Frontend ne charge pas
```bash
# Vérifier que le backend est accessible
curl http://localhost:8000/health

# Vérifier les logs frontend
docker-compose logs frontend

# Reconstruire
docker-compose build frontend
docker-compose up -d frontend
```

## Prochaines étapes

1. **Personnaliser les alertes**
   - Éditer `backend/app/services/alerts/alert_predictor.py`
   - Ajuster les seuils d'impact

2. **Ajouter des symboles**
   - Éditer `backend/app/services/stats/price_fetcher.py`
   - Ajouter dans `SYMBOL_MAP`

3. **Configurer Nextcloud** (optionnel)
   - Pour synchroniser les rapports Markdown
   - Ajouter les credentials dans `.env`

4. **Déployer en production**
   - Utiliser un reverse proxy (Nginx)
   - Configurer HTTPS
   - Utiliser des secrets sécurisés
   - Configurer les backups DB

## Support

- 📖 Documentation complète : `README.md`
- 📦 Détails dépendances : `DEPENDENCIES.md`
- ✅ Vérification : `VERIFICATION_COMPLETE.md`
- 🐛 Issues : GitHub Issues

---

**Bon trading ! 📈📉**
