# 📅 Timeline Component - Documentation

**Composant**: `Timeline.svelte`  
**Emplacement**: `frontend/src/routes/stats/Timeline.svelte`  
**Date**: 06/02/2026  
**Status**: ✅ **Créé et Fonctionnel**

---

## 📖 Description

Le composant `Timeline` affiche une timeline verticale élégante et interactive pour visualiser une séquence d'événements chronologiques. Parfait pour afficher des alertes, des prédictions, des mouvements de marché ou tout autre événement temporel.

---

## 🎯 Fonctionnalités

- ✅ **Timeline verticale** avec ligne et marqueurs
- ✅ **Tri automatique** par date/timestamp
- ✅ **Limitation configurable** du nombre d'items
- ✅ **Couleurs dynamiques** selon l'impact
- ✅ **Icônes contextuelles** selon le type d'événement
- ✅ **Badges** pour devises et symboles
- ✅ **Métriques** (pips, confiance, risque)
- ✅ **Animation** sur le premier élément
- ✅ **Responsive** (mobile-friendly)
- ✅ **Empty state** élégant

---

## 📦 Props

### `events` (Array) - **Requis**

Liste des événements à afficher.

**Structure d'un événement**:

```javascript
{
  // Requis
  timestamp: '2026-02-06T19:47:12Z',  // ou 'date'
  event_name: 'Non-Farm Payrolls',     // ou 'name' ou 'title'
  
  // Optionnels
  currency: 'USD',                     // Badge devise
  symbol: 'EURUSD',                    // Badge symbole
  impact_level: 'High',                // 'High', 'Medium', 'Low'
  impact: 'extreme',                   // Alternative à impact_level
  type: 'alert',                       // 'alert', 'prediction', 'movement'
  
  // Métriques
  movement_pips: 45.5,                 // Mouvement réel
  expected_movement_pips: 35.0,        // Mouvement prévu
  confidence: 'high',                  // 'high', 'medium', 'low'
  risk_level: 'extreme',               // 'extreme', 'high', 'medium', 'low'
  
  // Données économiques
  forecast: '200K',
  previous: '180K',
  
  // Description
  description: 'Texte descriptif...'
}
```

### `title` (String) - Optionnel

Titre affiché au-dessus de la timeline.

**Défaut**: `''` (pas de titre)

### `maxItems` (Number) - Optionnel

Nombre maximum d'événements à afficher.

**Défaut**: `20`

---

## 🚀 Utilisation

### Exemple Basique

```svelte
<script>
  import Timeline from './Timeline.svelte';
  
  const events = [
    {
      timestamp: '2026-02-06T14:30:00Z',
      event_name: 'Non-Farm Payrolls',
      currency: 'USD',
      impact_level: 'High',
      movement_pips: 45.5
    },
    {
      timestamp: '2026-02-06T12:00:00Z',
      event_name: 'Décision BCE',
      currency: 'EUR',
      impact_level: 'High',
      movement_pips: 32.0
    }
  ];
</script>

<Timeline {events} />
```

### Exemple avec Titre et Limite

```svelte
<Timeline 
  {events} 
  title="Événements Récents"
  maxItems={10}
/>
```

### Exemple avec Données API

```svelte
<script>
  import Timeline from './Timeline.svelte';
  import { onMount } from 'svelte';
  
  let events = [];
  
  onMount(async () => {
    const response = await fetch('/api/calendar/today');
    const data = await response.json();
    events = data.events;
  });
</script>

<Timeline {events} title="Événements du Jour" />
```

### Exemple Complet

Voir `TimelineExample.svelte` pour un exemple complet avec:
- Chargement depuis l'API
- Données de fallback
- Bouton de rafraîchissement
- Statistiques

---

## 🎨 Personnalisation

### Couleurs d'Impact

Les couleurs sont automatiquement appliquées selon `impact_level`:

| Impact | Couleur | Hex |
|--------|---------|-----|
| High / Extreme | Rouge | `#ef4444` |
| Medium | Orange | `#f59e0b` |
| Low | Vert | `#10b981` |
| Default | Gris | `#64748b` |

### Icônes d'Événements

Les icônes sont sélectionnées automatiquement:

| Type / Impact | Icône |
|---------------|-------|
| `type: 'alert'` | 🔔 |
| `type: 'prediction'` | 🎯 |
| `type: 'movement'` | 📊 |
| `impact_level: 'High'` | 🔴 |
| `impact_level: 'Medium'` | 🟡 |
| `impact_level: 'Low'` | 🟢 |
| Default | 📌 |

### Badges de Confiance

```css
.confidence-high   → Vert (#d1fae5)
.confidence-medium → Jaune (#fef3c7)
.confidence-low    → Rouge (#fee2e2)
```

### Badges de Risque

```css
.risk-extreme → Rouge foncé (#fee2e2)
.risk-high    → Orange (#fed7aa)
.risk-medium  → Jaune (#fef3c7)
.risk-low     → Vert (#d1fae5)
```

---

## 🎭 Animations

### Animation du Premier Élément

Le premier événement (le plus récent) pulse pour attirer l'attention:

```css
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
}
```

### Hover Effects

- **Marker**: Scale 1.1 + shadow
- **Content**: Translate X + border color change

---

## 📱 Responsive Design

### Desktop (> 640px)

- Marker: 40px × 40px
- Padding: 2rem
- Font sizes: Standard

### Mobile (≤ 640px)

- Marker: 32px × 32px
- Padding: 1.5rem
- Font sizes: Réduits
- Timeline line: Ajustée

---

## 🔧 Méthodes Internes

### `formatDate(dateStr)`

Formate une date en format français avec heure.

**Input**: `'2026-02-06T14:30:00Z'`  
**Output**: `'06 févr., 14:30'`

### `formatShortDate(dateStr)`

Formate une date courte (jour + mois).

**Input**: `'2026-02-06T14:30:00Z'`  
**Output**: `'06 févr.'`

### `getImpactColor(impact)`

Retourne la couleur hex selon le niveau d'impact.

### `getEventIcon(event)`

Retourne l'emoji approprié pour l'événement.

### `isToday(dateStr)`

Vérifie si la date est aujourd'hui.

---

## 📊 Structure HTML

```html
<div class="timeline-container">
  <h3 class="timeline-title">Titre</h3>
  
  <div class="timeline">
    <div class="timeline-item">
      <div class="timeline-marker">
        <span class="marker-icon">🔔</span>
      </div>
      <div class="timeline-line"></div>
      <div class="timeline-content">
        <div class="timeline-header">
          <span class="timeline-date">06 févr., 14:30</span>
          <span class="currency-badge">USD</span>
          <span class="symbol-badge">EURUSD</span>
        </div>
        <div class="event-title">Non-Farm Payrolls</div>
        <p class="event-description">Description...</p>
        <div class="event-metrics">
          <span class="metric">📊 45.5 pips</span>
          <span class="metric confidence-high">💪 high</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## 🎯 Cas d'Usage

### 1. Alertes Forex

```javascript
const alerts = [
  {
    timestamp: '2026-02-06T14:30:00Z',
    event_name: 'Non-Farm Payrolls',
    currency: 'USD',
    symbol: 'EURUSD',
    impact_level: 'High',
    movement_pips: 45.5,
    expected_movement_pips: 35.0,
    confidence: 'high',
    risk_level: 'extreme',
    type: 'alert'
  }
];
```

### 2. Prédictions

```javascript
const predictions = [
  {
    timestamp: '2026-02-06T12:00:00Z',
    event_name: 'Décision BCE',
    currency: 'EUR',
    impact_level: 'High',
    expected_movement_pips: 30.0,
    confidence: 'medium',
    risk_level: 'high',
    type: 'prediction'
  }
];
```

### 3. Mouvements de Marché

```javascript
const movements = [
  {
    timestamp: '2026-02-06T10:00:00Z',
    event_name: 'Ventes au Détail',
    currency: 'GBP',
    impact_level: 'Medium',
    movement_pips: 18.5,
    forecast: '0.5%',
    previous: '0.3%',
    type: 'movement'
  }
];
```

---

## 🔗 Intégration

### Dans une Page Stats

```svelte
<!-- frontend/src/routes/stats/+page.svelte -->
<script>
  import Timeline from './Timeline.svelte';
  
  let events = [];
  
  async function loadEvents() {
    const response = await fetch('/api/calendar/today');
    const data = await response.json();
    events = data.events;
  }
</script>

<div class="stats-page">
  <Timeline {events} title="Événements du Jour" maxItems={15} />
</div>
```

### Dans un Dashboard

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script>
  import Timeline from './stats/Timeline.svelte';
  
  let recentEvents = [];
</script>

<section class="dashboard-section">
  <Timeline 
    events={recentEvents} 
    title="Activité Récente"
    maxItems={5}
  />
</section>
```

---

## 🐛 Dépannage

### Les événements ne s'affichent pas

**Vérifications**:
1. ✅ `events` est un array ?
2. ✅ Chaque événement a un `timestamp` ou `date` ?
3. ✅ Le format de date est valide (ISO 8601) ?

### Les couleurs ne s'affichent pas

**Vérifications**:
1. ✅ `impact_level` ou `impact` est défini ?
2. ✅ La valeur est 'High', 'Medium' ou 'Low' ?

### Les métriques ne s'affichent pas

**Vérifications**:
1. ✅ Les propriétés existent (`movement_pips`, `confidence`, etc.) ?
2. ✅ Les valeurs ne sont pas `undefined` ou `null` ?

---

## 📈 Améliorations Futures

### Court Terme

- [ ] Filtrage par type d'événement
- [ ] Filtrage par devise
- [ ] Recherche dans les événements
- [ ] Export en PDF/Image

### Moyen Terme

- [ ] Zoom sur une période
- [ ] Groupement par jour
- [ ] Comparaison de périodes
- [ ] Graphiques inline

### Long Terme

- [ ] Timeline horizontale (option)
- [ ] Mode compact
- [ ] Thème sombre
- [ ] Animations personnalisables

---

## 📚 Ressources

### Fichiers Associés

- **Composant**: `frontend/src/routes/stats/Timeline.svelte`
- **Exemple**: `frontend/src/routes/stats/TimelineExample.svelte`
- **PriceTimeline**: `frontend/src/routes/stats/PriceTimeline.svelte`

### Documentation

- **Svelte**: https://svelte.dev/docs
- **Date Formatting**: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date

---

## ✅ Checklist d'Intégration

- [x] Composant créé
- [x] Props documentées
- [x] Styles responsive
- [x] Animations ajoutées
- [x] Empty state géré
- [x] Exemple créé
- [ ] Tests unitaires
- [ ] Intégré dans l'app
- [ ] Documentation utilisateur

---

**Créé le**: 06/02/2026 à 20:00  
**Version**: 1.0.0  
**Status**: ✅ **Prêt à l'emploi**
