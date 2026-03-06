# SaaS DrevmBot - Frontend

Interface web pour visualiser les corrélations entre événements économiques et mouvements de prix.

## 🚀 Installation

### Prérequis

- Node.js 18+
- npm ou pnpm

### Configuration

1. Installer les dépendances :
```bash
npm install
```

2. Configurer l'URL de l'API backend (si nécessaire) :
Éditer `vite.config.js` pour pointer vers votre backend.

## 🏃 Lancement

### Mode développement
```bash
npm run dev
```

L'application sera accessible sur http://localhost:5173

### Build production
```bash
npm run build
npm run preview
```

## 📁 Structure

```
frontend/
├── src/
│   ├── routes/
│   │   ├── calendar/        # Page calendrier économique
│   │   │   ├── +page.svelte
│   │   │   └── EventCard.svelte
│   │   └── stats/           # Page statistiques
│   │       ├── +page.svelte
│   │       ├── ImpactChart.svelte
│   │       ├── HeatmapView.svelte
│   │       ├── CorrelationTable.svelte
│   │       └── PriceTimeline.svelte
│   └── lib/                 # Composants réutilisables
└── static/                  # Assets statiques
```

## 🎨 Fonctionnalités

### Page Calendrier
- Affichage des événements économiques du jour/semaine
- Filtrage par devise et niveau d'impact
- Cartes événements avec détails (forecast, actual, previous)

### Page Statistiques
- Dashboard avec KPIs (taux d'impact, pips moyens, volatilité)
- Graphiques d'impact des événements
- Heatmap volatilité (jour × heure)
- Timeline des événements
- Table de corrélation par type d'événement

## 🔧 Technologies

- **SvelteKit** - Framework web
- **Chart.js** - Graphiques
- **date-fns** - Manipulation de dates
- **Vite** - Build tool

## 📝 Licence

Propriétaire
