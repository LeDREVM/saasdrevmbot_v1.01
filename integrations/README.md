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
cp .env.example .env      # au minimum TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
npm install && npm start
```

Au démarrage il affiche sa bannière, désactive proprement ce qui n'est pas
configuré (Twelve Data, Nextcloud), puis exige `TELEGRAM_BOT_TOKEN` pour lancer
le bot. Il récupère ensuite le calendrier ForexFactory
(`nfs.faireconomy.media`) — accès Internet direct requis.

> ⚠️ Deps upstream : ce scraper tiers dépend de `node-telegram-bot-api` /
> `node-cron` qui tirent des paquets avec vulnérabilités connues (`request`,
> `ws`…) sans release corrigée. `node_modules/` n'est pas versionné ; à isoler
> (conteneur dédié) si tu l'exposes.

**Branchement pipeline** : ce scraper fournit le **contexte news / événements**
qui alimente le `news_score` et l'`event_context` de l'AI Setup Validator
(pénalité « annonce imminente » du GLOBAL SCORE). À terme : exposer ses
événements au format consommé par `/api/signal` (ou par le calendrier backend).

## `goldrogers-mt5/` — pont MT5 (Python)

Récupéré de **`LeDREVM/goldrogers-trading-bot`** (`scripts/mt5_data_sender.py`) —
le seul maillon vraiment complémentaire : il lit l'OHLC MT5 (**H4 + M15 + M5**,
7 symboles) et le pousse toutes les 5 min vers la console. C'est la brique
**« MT5 Data Collector »** de l'architecture cible.

### Accès au dashboard depuis Linux/cloud (le paquet `MetaTrader5` est Windows-only)

Le pont permet à la console — hébergée sur **Linux/cloud**, où `MetaTrader5`
n'existe pas — de tourner sur les **vraies bougies MT5**. Flux complet :

```
VPS Windows (MT5 + terminal ouvert)          Console Linux/cloud
  mt5_data_sender.py  ──POST /api/market-data──▶  _market_data (par TF)
     (H4/M15/M5)                                        │
                                                        ▼  PRICE_SOURCE=mt5bridge
                                          get_rates → provider "mt5bridge"
                                          → scan + signal sur données MT5 réelles
```

**Branchement (2 côtés) :**
1. **VPS Windows** : `MARKET_DATA_API_URL=http://<console>:8800/api/market-data`
   puis `python mt5_data_sender.py` (envoie les 3 timeframes, taggés `timeframe`).
2. **Console** : `PRICE_SOURCE=mt5bridge` (ou en cascade, ex.
   `mt5bridge,twelvedata`). Le moteur consomme alors les bougies du pont ;
   `GET /api/market-data` expose l'état (timeframes reçus, `received_at`) pour le
   monitoring.

> ⚠️ Le pont fournit les **PRIX** (scan/signal/analyse). Le **compte, les
> positions et l'exécution d'ordres** restent côté Windows (terminal MT5) — la
> console en cloud reste en `SIMULATION` pour ces aspects tant qu'elle n'a pas
> de terminal MT5 local. (Extension possible : pousser aussi compte/positions.)

Le reste du dépôt `goldrogers-trading-bot` (indicateurs Wyckoff/Ichimoku/RSI,
bots, dashboards) **duplique** ce que le pipeline `ny_session_interface` fait déjà
en plus propre → volontairement **non importé**.

## Ce qui a été volontairement EXCLU
- 🔒 `docs/Storj-S3-Credentials-*.txt` de `goldrogers-trading-bot` (**credentials en
  clair** — à supprimer du repo source **et révoquer/roter**).
- Bases sqlite (`data/*.db*`), `node_modules/`, et les valeurs de secrets du
  `.env.example` (assainies en placeholders).
