# 📡 Documentation des Endpoints API

## Base URL
```
http://localhost:8000/api
```

## Documentation Interactive
- **Swagger UI** : http://localhost:8000/api/docs
- **ReDoc** : http://localhost:8000/api/redoc

---

## 📅 Calendrier Économique

### `GET /calendar/today`
Récupère les événements économiques du jour

**Query Parameters:**
- `currencies` (optional): USD,EUR,JPY
- `impact` (optional): High,Medium,Low

**Response:**
```json
{
  "source": "fresh",
  "date": "2026-02-06",
  "events": [...],
  "count": 15
}
```

### `GET /calendar/week`
Récupère les événements de la semaine (7 jours)

### `GET /calendar/upcoming`
Événements HIGH IMPACT dans les N prochaines heures

**Query Parameters:**
- `hours` (default: 2): Heures à l'avance

### `POST /calendar/sync`
Force le refresh du calendrier (invalide cache)

### `GET /calendar/history`
Historique des événements d'un jour passé

**Query Parameters:**
- `date` (required): YYYY-MM-DD

---

## 📊 Statistiques

### `GET /stats/dashboard/{symbol}`
Stats complètes pour le dashboard

**Path Parameters:**
- `symbol`: EURUSD, GBPUSD, XAUUSD, SPX, etc.

**Query Parameters:**
- `days_back` (default: 30): Période d'analyse (7-90)

**Response:**
```json
{
  "summary": {
    "total_events": 45,
    "impact_rate": 68.5,
    "avg_movement_pips": 15.3,
    "direction_stats": {...}
  },
  "top_impact_events": [...],
  "heatmap_data": {...},
  "timeline": [...]
}
```

### `GET /stats/top-movers/{symbol}`
Top événements qui ont le plus bougé le marché

**Query Parameters:**
- `days_back` (default: 30)
- `limit` (default: 10)

### `GET /stats/heatmap/{symbol}`
Heatmap volatilité par jour × heure

### `GET /stats/correlation-score`
Score de corrélation entre type d'événement et symbole

**Query Parameters:**
- `event_type` (required): NFP, FOMC, CPI, etc.
- `symbol` (required): EURUSD, etc.

**Response:**
```json
{
  "event_type": "NFP",
  "symbol": "EURUSD",
  "sample_size": 24,
  "avg_movement_pips": 35.2,
  "impact_rate": 85.5,
  "correlation_score": 7.8,
  "interpretation": "🔥 FORT - Cet événement bouge systématiquement le marché"
}
```

### `POST /stats/refresh/{symbol}`
Force le recalcul des stats (invalide cache)

---

## 🔔 Alertes

### `GET /alerts/active/{user_id}`
Liste des alertes actives pour un utilisateur

**Response:**
```json
{
  "alerts": [
    {
      "event": {...},
      "prediction": {...},
      "recommendation": "...",
      "time_until_event": "Dans 1h 30min"
    }
  ],
  "count": 5
}
```

### `GET /alerts/history/{user_id}`
Historique des alertes envoyées

**Query Parameters:**
- `limit` (default: 20)
- `days_back` (default: 30)

### `POST /alerts/test/{user_id}`
Envoie une alerte de test

**Request Body:**
```json
{
  "channels": ["discord", "telegram"]
}
```

---

## ⚙️ Configuration Alertes

### `GET /alert-config/settings/{user_id}`
Récupère les paramètres d'alerte d'un utilisateur

**Response:**
```json
{
  "user_id": "negus_dja",
  "watched_symbols": ["EURUSD", "GBPUSD", "XAUUSD"],
  "risk_levels": ["extreme", "high"],
  "channels": {
    "discord": {
      "enabled": true,
      "webhook_url": "https://..."
    },
    "telegram": {
      "enabled": true,
      "bot_token": "...",
      "chat_id": "..."
    }
  },
  "advanced": {
    "advance_notice_hours": 2,
    "min_confidence": "medium",
    "min_movement_pips": 10
  }
}
```

### `PATCH /alert-config/settings/{user_id}`
Met à jour les paramètres

**Request Body:**
```json
{
  "watched_symbols": ["EURUSD", "XAUUSD"],
  "risk_levels": ["extreme"],
  "channels": {
    "discord": {
      "enabled": true
    }
  }
}
```

### `GET /alert-config/active-alerts/{user_id}`
Alertes actives basées sur les paramètres utilisateur

### `GET /alert-config/history/{user_id}`
Historique des alertes avec filtres

**Query Parameters:**
- `limit` (default: 20)
- `symbol` (optional)
- `risk_level` (optional)

### `GET /alert-config/stats/{user_id}`
Statistiques des alertes

**Query Parameters:**
- `days_back` (default: 30)

**Response:**
```json
{
  "summary": {
    "total_alerts_sent": 45,
    "accuracy_rate": 78.5,
    "avg_movement_actual": 18.3,
    "by_risk_level": {...}
  }
}
```

---

## ☁️ Nextcloud

### `GET /nextcloud/status`
Vérifie le statut de connexion Nextcloud

**Response:**
```json
{
  "connected": true,
  "nextcloud_url": "https://ledream.kflw.io",
  "configured": true,
  "username": "user",
  "share_folder": "/f/33416",
  "message": "✅ Connexion réussie"
}
```

### `POST /nextcloud/sync/all`
Synchronise tous les rapports vers Nextcloud

Lance la synchronisation en arrière-plan.

**Response:**
```json
{
  "status": "started",
  "message": "Synchronisation lancée en arrière-plan"
}
```

### `POST /nextcloud/sync/report/{filename}`
Synchronise un rapport spécifique

**Path Parameters:**
- `filename`: predictions_EURUSD_2026-02-06.md

### `GET /nextcloud/reports/list`
Liste tous les rapports locaux disponibles

**Response:**
```json
{
  "reports": [
    {
      "filename": "predictions_EURUSD_2026-02-06.md",
      "size": 12345,
      "created": "2026-02-06T10:30:00",
      "type": "predictions"
    }
  ],
  "count": 10,
  "directory": "/tmp/trading_reports"
}
```

### `POST /nextcloud/generate-and-sync/predictions`
Génère un rapport de prédictions et le synchronise

**Query Parameters:**
- `symbol` (required): EURUSD, GBPUSD, etc.

### `POST /nextcloud/test-connection`
Teste la connexion Nextcloud

Crée un fichier de test et tente de l'uploader.

**Response:**
```json
{
  "status": "success",
  "message": "✅ Connexion réussie !",
  "filename": "test_connection_20260206_103000.md",
  "url": "https://ledream.kflw.io/ForexBot/reports/test_connection_20260206_103000.md"
}
```

### `DELETE /nextcloud/reports/{filename}`
Supprime un rapport local

⚠️ Ne supprime PAS le fichier sur Nextcloud

---

## 🏥 Health & Info

### `GET /`
Endpoint racine

**Response:**
```json
{
  "message": "SaaS DrevmBot API",
  "version": "1.0.0",
  "docs": "/api/docs"
}
```

### `GET /health`
Health check pour monitoring

**Response:**
```json
{
  "status": "healthy",
  "service": "SaaS DrevmBot"
}
```

---

## 🔒 Authentification

Actuellement, l'API utilise un `user_id` simple (ex: `negus_dja`).

**À implémenter en production:**
- JWT tokens
- OAuth2
- API Keys
- Rate limiting

---

## 📝 Codes de Statut HTTP

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé |
| 400 | Requête invalide |
| 404 | Non trouvé |
| 500 | Erreur serveur |

---

## 🧪 Exemples d'Utilisation

### cURL

```bash
# Calendrier du jour
curl http://localhost:8000/api/calendar/today

# Stats EURUSD
curl "http://localhost:8000/api/stats/dashboard/EURUSD?days_back=30"

# Statut Nextcloud
curl http://localhost:8000/api/nextcloud/status

# Test connexion Nextcloud
curl -X POST http://localhost:8000/api/nextcloud/test-connection

# Sync tous les rapports
curl -X POST http://localhost:8000/api/nextcloud/sync/all
```

### JavaScript (Fetch)

```javascript
// Récupérer les alertes actives
const response = await fetch('http://localhost:8000/api/alert-config/active-alerts/negus_dja');
const data = await response.json();

// Mettre à jour les paramètres
await fetch('http://localhost:8000/api/alert-config/settings/negus_dja', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    watched_symbols: ['EURUSD', 'XAUUSD'],
    risk_levels: ['extreme', 'high']
  })
});

// Synchroniser vers Nextcloud
await fetch('http://localhost:8000/api/nextcloud/sync/all', {
  method: 'POST'
});
```

### Python (requests)

```python
import requests

# Calendrier
response = requests.get('http://localhost:8000/api/calendar/today')
events = response.json()

# Stats
response = requests.get('http://localhost:8000/api/stats/dashboard/EURUSD', 
                       params={'days_back': 30})
stats = response.json()

# Nextcloud status
response = requests.get('http://localhost:8000/api/nextcloud/status')
status = response.json()
```

---

## 🔗 Ressources

- **Swagger UI** : http://localhost:8000/api/docs (documentation interactive)
- **ReDoc** : http://localhost:8000/api/redoc (documentation alternative)
- **OpenAPI Schema** : http://localhost:8000/api/openapi.json

---

**Version** : 1.0.0  
**Dernière mise à jour** : 6 février 2026
