# Integrations — sources récupérées

Composants importés depuis d'autres dépôts DREVM et branchables sur le pipeline
(`ny_session_interface` : `/api/signal`, validator, `/api/execute`).

## `goldyxrogers-scraper/` — scraper de signaux (Node.js)

Récupéré de **`LeDREVM/goldyxrogers`** (v2 — assistant scalping session NY,
symboles US30 / USDJPY / XBRUSD / XAUUSD).

Scrape et agrège, puis envoie des alertes Telegram :
- **calendrier économique** ForexFactory (XML this/next week) — `src/scraper.js`
- **COT** (positionnement) — `src/cot.js`
- **sentiment** retail — `src/sentiment.js`
- **options / niveaux** — `src/options.js`
- **prix marché** (Twelve Data) — `src/price.js`, `src/market.js`
- filtres, formatage, planif, persistance sqlite, export Nextcloud

Lancement :
```bash
cd integrations/goldyxrogers-scraper
cp .env.example .env      # renseigner Telegram + Twelve Data
npm install && npm start
```

**Branchement pipeline** : ce scraper fournit le **contexte news / événements**
qui alimente le `news_score` et l'`event_context` de l'AI Setup Validator
(pénalité « annonce imminente » du GLOBAL SCORE). À terme : exposer ses
événements au format consommé par `/api/signal` (ou par le calendrier backend).

## `goldrogers-mt5/` — pont MT5 (Python)

Récupéré de **`LeDREVM/goldrogers-trading-bot`** (`scripts/mt5_data_sender.py`) —
le seul maillon vraiment complémentaire : il lit l'OHLC MT5 (M5, 100 bougies,
7 symboles) et le pousse toutes les 5 min vers une API. C'est la brique
**« MT5 Data Collector »** de l'architecture cible.

**À configurer** : l'URL de collecte se définit via la variable d'environnement
`MARKET_DATA_API_URL` (ex. `http://localhost:8800/api/market-data`). Sans elle, le
script s'arrête avec un message. Le reste du dépôt `goldrogers-trading-bot` (indicateurs Wyckoff/
Ichimoku/RSI, bots, dashboards) **duplique** ce que le pipeline `ny_session_interface`
fait déjà en plus propre → volontairement **non importé**.

## Ce qui a été volontairement EXCLU
- 🔒 `docs/Storj-S3-Credentials-*.txt` de `goldrogers-trading-bot` (**credentials en
  clair** — à supprimer du repo source **et révoquer/roter**).
- Bases sqlite (`data/*.db*`), `node_modules/`, et les valeurs de secrets du
  `.env.example` (assainies en placeholders).
