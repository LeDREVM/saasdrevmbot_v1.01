# GoldyXbOT — Calendrier Économique Discord

Bot Discord qui scanne les annonces économiques de **ForexFactory** et **Investing.com** et les envoie automatiquement sur Discord.

## Fonctionnalités

- **Scraping automatique** toutes les X minutes (ForexFactory + Investing.com)
- **Filtrage par impact** : rouge 🔴, orange 🟠, jaune 🟡
- **Filtrage par devise** : USD, EUR, GBP, JPY, etc.
- **Rappels** : notification N minutes avant une annonce
- **Résultats** : mise à jour quand l'actual est publié
- **Briefing matinal** : résumé à 8h00 en semaine
- **Embeds Discord** colorés et structurés

## Installation

```bash
# 1. Installer les dépendances
npm install

# 2. Configurer
cp .env.example .env
# Éditer .env avec ton webhook Discord

# 3. Lancer
npm start
```

## Configuration (.env)

| Variable | Défaut | Description |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | — | **Obligatoire** — URL du webhook Discord |
| `MIN_IMPACT` | `3` | Impact minimum (1=faible, 2=moyen, 3=fort) |
| `CURRENCIES` | vide (toutes) | Devises à surveiller, ex: `USD,EUR,GBP,JPY` |
| `CHECK_INTERVAL` | `5` | Intervalle de scan en minutes |
| `REMINDER_MINUTES` | `15` | Minutes avant rappel (0 = désactivé) |
| `TIMEZONE` | `Europe/Paris` | Fuseau horaire |
| `ENABLE_FOREXFACTORY` | `true` | Activer ForexFactory |
| `ENABLE_INVESTING` | `true` | Activer Investing.com |

## Créer un Webhook Discord

1. Dans Discord, clic droit sur ton canal → **Modifier le canal**
2. **Intégrations** → **Webhooks** → **Nouveau webhook**
3. Copier l'URL et la coller dans `.env`

## Structure du projet

```
src/
  index.js              # Point d'entrée, scheduler, logique principale
  scrapers/
    forexfactory.js     # Scraper ForexFactory
    investing.js        # Scraper Investing.com
  utils/
    discord.js          # Formatage et envoi Discord
    eventStore.js       # Store en mémoire (déduplication)
    timeUtils.js        # Utilitaires de temps
```

## Exemple de message Discord

```
🔴 Non-Farm Payrolls
Devise: USD | Impact: Fort 🔴 | Heure: 8:30am
📊 Prévision: 200K  |  📈 Précédent: 185K  |  ✅ Résultat: 215K
Source: ForexFactory
```
