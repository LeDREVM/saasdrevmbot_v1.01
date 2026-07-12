# 📊 Guide - Affichage Trading Economics sur le Dashboard

## ✅ Ce qui a été créé

### 1. **Route API Backend** 
`backend/app/api/routes/trading_economics.py`

Routes disponibles :
- `GET /api/trading-economics/today` - Événements du jour
- `GET /api/trading-economics/week` - Événements de la semaine
- `GET /api/trading-economics/stats` - Statistiques
- `GET /api/trading-economics/upcoming?minutes=60` - Événements à venir
- `POST /api/trading-economics/refresh` - Rafraîchir le cache

**Fonctionnalités :**
- ✅ Cache automatique (5 minutes)
- ✅ Filtrage par devise et impact
- ✅ Statistiques en temps réel
- ✅ Gestion des erreurs

### 2. **Composant Frontend**
`frontend/src/routes/TradingEconomicsWidget.svelte`

**Fonctionnalités :**
- ✅ Affichage des événements en temps réel
- ✅ Statistiques visuelles (total, fort/moyen/faible impact)
- ✅ Filtres par devise et impact
- ✅ Auto-refresh toutes les 5 minutes
- ✅ Design responsive et moderne
- ✅ Indicateurs de couleur par impact

### 3. **Intégration Dashboard**
Le widget est maintenant intégré dans la page d'accueil (`frontend/src/routes/+page.svelte`)

## 🚀 Comment Démarrer

### 1. Démarrer le Backend

```bash
cd backend

# Activer l'environnement virtuel
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Installer les dépendances si nécessaire
pip install requests beautifulsoup4 lxml

# Démarrer le serveur
python main.py
```

Le backend sera accessible sur : `http://localhost:8000`

### 2. Démarrer le Frontend

```bash
cd frontend

# Installer les dépendances si nécessaire
npm install

# Démarrer le serveur de développement
npm run dev
```

Le frontend sera accessible sur : `http://localhost:5173`

### 3. Tester l'API

#### Test avec curl (Windows PowerShell)

```powershell
# Événements du jour
Invoke-WebRequest -Uri "http://localhost:8000/api/trading-economics/today" | ConvertFrom-Json

# Statistiques
Invoke-WebRequest -Uri "http://localhost:8000/api/trading-economics/stats" | ConvertFrom-Json

# Filtrer par devise
Invoke-WebRequest -Uri "http://localhost:8000/api/trading-economics/today?currency=USD" | ConvertFrom-Json

# Filtrer par impact
Invoke-WebRequest -Uri "http://localhost:8000/api/trading-economics/today?impact=high" | ConvertFrom-Json
```

#### Test avec curl (Linux/Mac)

```bash
# Événements du jour
curl http://localhost:8000/api/trading-economics/today | jq

# Statistiques
curl http://localhost:8000/api/trading-economics/stats | jq

# Filtrer par devise
curl "http://localhost:8000/api/trading-economics/today?currency=USD" | jq

# Filtrer par impact
curl "http://localhost:8000/api/trading-economics/today?impact=high" | jq
```

#### Test dans le navigateur

Ouvrez directement dans votre navigateur :
- http://localhost:8000/api/trading-economics/today
- http://localhost:8000/api/trading-economics/stats
- http://localhost:8000/api/trading-economics/week

### 4. Tester le Dashboard

1. Ouvrez `http://localhost:5173` dans votre navigateur
2. Vous devriez voir le widget Trading Economics sur la page d'accueil
3. Le widget affiche :
   - Statistiques en haut (total, fort/moyen/faible impact)
   - Filtres par devise et impact
   - Liste des événements avec toutes les informations

## 📊 Fonctionnalités du Widget

### Statistiques

```
┌─────────────┬──────────────┬──────────────┬──────────────┐
│ 45          │ 🔴 8         │ 🟡 15        │ 🟢 22        │
│ Événements  │ Fort Impact  │ Impact Moyen │ Faible Impact│
└─────────────┴──────────────┴──────────────┴──────────────┘
```

### Filtres

- **Impact** : Tous / 🔴 Fort / 🟡 Moyen / 🟢 Faible
- **Devise** : Toutes / USD / EUR / GBP / JPY / etc.

### Carte d'Événement

Chaque événement affiche :
- ⏰ **Heure** : 14:30
- 🎯 **Impact** : Badge coloré (🔴/🟡/🟢)
- 💱 **Devise** : USD
- 🌍 **Pays** : United States
- 📝 **Nom** : Non-Farm Payrolls
- 📈 **Prévision** : 180K
- 📉 **Précédent** : 216K
- ✅ **Actuel** : 216K (si disponible)

### Auto-Refresh

Le widget se rafraîchit automatiquement toutes les 5 minutes pour obtenir les dernières données.

## 🎨 Personnalisation

### Changer l'intervalle de rafraîchissement

Dans `frontend/src/routes/TradingEconomicsWidget.svelte` :

```javascript
// Ligne ~109 - Changer 5 minutes en autre chose
refreshInterval = setInterval(async () => {
    await fetchEvents();
    await fetchStats();
}, 10 * 60 * 1000);  // 10 minutes au lieu de 5
```

### Modifier les couleurs d'impact

Dans `frontend/src/routes/TradingEconomicsWidget.svelte` :

```javascript
function getImpactColor(impact) {
    switch(impact) {
        case 'high': return '#ef4444';    // Rouge
        case 'medium': return '#f59e0b';  // Orange
        case 'low': return '#10b981';     // Vert
        default: return '#6b7280';        // Gris
    }
}
```

### Changer le nombre maximum d'événements affichés

Dans `frontend/src/routes/TradingEconomicsWidget.svelte`, ajoutez un filtre :

```javascript
// Limiter à 20 événements
$: filteredEvents = events
    .filter(event => {
        if (selectedImpact !== 'all' && event.impact !== selectedImpact) return false;
        if (selectedCurrency !== 'all' && event.currency !== selectedCurrency) return false;
        return true;
    })
    .slice(0, 20);  // Ajouter cette ligne
```

### Modifier la durée du cache API

Dans `backend/app/api/routes/trading_economics.py` :

```python
# Ligne ~16 - Changer le TTL du cache
_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 600  # 10 minutes au lieu de 5
}
```

## 🔧 Dépannage

### Erreur "Failed to fetch"

**Problème** : Le frontend ne peut pas se connecter au backend

**Solutions** :
1. Vérifiez que le backend est démarré : `http://localhost:8000`
2. Vérifiez la configuration CORS dans `backend/main.py`
3. Vérifiez la variable d'environnement `VITE_API_URL` dans `frontend/.env`

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

### Aucun événement affiché

**Problème** : Le widget est vide

**Solutions** :
1. Vérifiez que Trading Economics est accessible
2. Testez l'API directement : `http://localhost:8000/api/trading-economics/today`
3. Consultez les logs du backend
4. Vérifiez votre connexion internet

### Erreur 500 Internal Server Error

**Problème** : L'API retourne une erreur 500

**Solutions** :
1. Consultez les logs du backend
2. Vérifiez que BeautifulSoup4 est installé : `pip install beautifulsoup4`
3. Le site Trading Economics peut avoir changé sa structure HTML
4. Testez manuellement le scraper :

```bash
python test_trading_economics.py
```

### Le cache ne se rafraîchit pas

**Problème** : Les données sont toujours les mêmes

**Solutions** :
1. Utilisez l'endpoint de rafraîchissement :
```bash
curl -X POST http://localhost:8000/api/trading-economics/refresh
```

2. Redémarrez le backend

3. Vérifiez le TTL du cache dans le code

## 📚 Endpoints API Détaillés

### GET /api/trading-economics/today

Récupère les événements d'aujourd'hui

**Paramètres** :
- `currency` (optionnel) : Filtrer par devise (ex: USD, EUR)
- `impact` (optionnel) : Filtrer par impact (low, medium, high)

**Réponse** :
```json
{
  "success": true,
  "count": 45,
  "date": "2024-02-07",
  "events": [
    {
      "date": "2024-02-07T14:30:00",
      "time": "14:30",
      "currency": "USD",
      "country": "United States",
      "event": "Non-Farm Payrolls",
      "impact": "high",
      "actual": "",
      "forecast": "180K",
      "previous": "216K",
      "source": "tradingeconomics"
    }
  ],
  "cache_info": {
    "cached": true,
    "cache_age_seconds": 120.5
  }
}
```

### GET /api/trading-economics/stats

Récupère les statistiques des événements

**Réponse** :
```json
{
  "success": true,
  "date": "2024-02-07",
  "total_events": 45,
  "by_impact": {
    "high": 8,
    "medium": 15,
    "low": 22
  },
  "by_currency": {
    "USD": 12,
    "EUR": 10,
    "GBP": 5
  },
  "top_currencies": [
    ["USD", 12],
    ["EUR", 10],
    ["GBP", 5]
  ]
}
```

### GET /api/trading-economics/upcoming

Récupère les événements à venir

**Paramètres** :
- `minutes` (optionnel, défaut: 60) : Événements dans les X prochaines minutes

**Réponse** :
```json
{
  "success": true,
  "count": 3,
  "minutes": 60,
  "events": [
    {
      "date": "2024-02-07T14:30:00",
      "time": "14:30",
      "currency": "USD",
      "event": "Non-Farm Payrolls",
      "impact": "high",
      "minutes_until": 25
    }
  ]
}
```

## 🎯 Intégration dans d'Autres Pages

Pour ajouter le widget sur d'autres pages :

```svelte
<script>
  import TradingEconomicsWidget from './TradingEconomicsWidget.svelte';
</script>

<div class="my-page">
  <h1>Ma Page</h1>
  
  <!-- Ajouter le widget -->
  <TradingEconomicsWidget />
</div>
```

## 📈 Prochaines Améliorations Possibles

- [ ] Notifications push pour les événements à venir
- [ ] Graphiques de l'impact historique
- [ ] Export des données en CSV/Excel
- [ ] Favoris et alertes personnalisées
- [ ] Comparaison avec les prévisions passées
- [ ] Intégration avec les graphiques de prix
- [ ] Mode sombre
- [ ] Traduction multilingue

## ✅ Checklist de Déploiement

Avant de déployer en production :

- [ ] Configurer `VITE_API_URL` dans Netlify
- [ ] Vérifier que le backend est accessible publiquement
- [ ] Tester les CORS pour le domaine de production
- [ ] Optimiser le cache (augmenter le TTL en production)
- [ ] Ajouter un rate limiting sur l'API
- [ ] Configurer les logs de monitoring
- [ ] Tester sur mobile et tablette
- [ ] Vérifier les performances avec Lighthouse

## 🎉 Conclusion

Le système est maintenant **100% fonctionnel** !

**Avantages** :
- ✅ Données en temps réel depuis Trading Economics
- ✅ Interface moderne et responsive
- ✅ Filtres puissants
- ✅ Cache optimisé
- ✅ Auto-refresh automatique
- ✅ Facile à personnaliser

**Pour commencer** :
1. Démarrer le backend : `python backend/main.py`
2. Démarrer le frontend : `npm run dev` (dans le dossier frontend)
3. Ouvrir `http://localhost:5173`
4. Profiter des données en temps réel ! 📊

**Bon trading ! 📈💰**
