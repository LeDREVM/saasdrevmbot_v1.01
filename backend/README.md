# SaaS DrevmBot - Backend

Bot d'analyse de corrélation entre événements économiques et mouvements de prix.

## 🚀 Installation

### Prérequis

- Python 3.10+
- PostgreSQL
- Redis

### Configuration

1. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

4. Initialiser la base de données :
```bash
python -c "from app.core.database import init_db; init_db()"
```

## 🏃 Lancement

### Mode développement
```bash
python main.py
```

### Mode production (avec Uvicorn)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Avec Docker
```bash
docker-compose up -d
```

## 📚 Documentation API

Une fois l'application lancée, accéder à :
- Swagger UI : http://localhost:8000/api/docs
- ReDoc : http://localhost:8000/api/redoc

## 🔧 Architecture

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # Endpoints FastAPI
│   ├── core/                # Configuration & DB
│   ├── models/              # Modèles SQLAlchemy
│   ├── services/
│   │   ├── alerts/          # Système d'alertes
│   │   ├── economic_calendar/  # Scrapers
│   │   └── stats/           # Analyse corrélation
│   └── workers/             # Tâches background (Celery)
└── main.py                  # Point d'entrée
```

## 🔌 Endpoints principaux

### Calendrier économique
- `GET /api/calendar/today` - Événements du jour
- `GET /api/calendar/week` - Événements de la semaine
- `GET /api/calendar/upcoming` - Événements à venir (high impact)

### Statistiques
- `GET /api/stats/dashboard/{symbol}` - Stats complètes
- `GET /api/stats/top-movers/{symbol}` - Top événements impactants
- `GET /api/stats/heatmap/{symbol}` - Heatmap volatilité

## 🤖 Workers

Lancer le worker Celery pour les alertes automatiques :
```bash
celery -A app.workers.alert_worker worker --loglevel=info
```

## 🧪 Tests

```bash
pytest
```

## 📝 Licence

Propriétaire
