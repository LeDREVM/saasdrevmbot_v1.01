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
     (H4/M15/M5)              │                          │
                             │                          ▼  PRICE_SOURCE=mt5bridge
                             │            get_rates → provider "mt5bridge"
                             │            → scan + signal sur données MT5 réelles
                             │
     account_info()          └─POST /api/mt5-state──▶  _mt5_state (frais < TTL)
     positions_get()                                        │
                                                            ▼
                                       /api/state (account) + /api/positions
                                       → équité / solde / positions RÉELLES
```

**Branchement (2 côtés) :**
1. **VPS Windows** : `MARKET_DATA_API_URL=http://<console>:8800/api/market-data`
   puis `python mt5_data_sender.py`. À chaque cycle il envoie les 3 timeframes
   (taggés `timeframe`) **et** pousse le compte + les positions ouvertes vers
   `/api/mt5-state` (URL dérivée automatiquement d'`MARKET_DATA_API_URL`, ou
   forcée par `MT5_STATE_API_URL`). Si la console tourne avec `REQUIRE_TOKEN=1`,
   renseigner `MARKET_DATA_API_TOKEN` (envoyé en `X-Api-Token` sur les deux POST).
2. **Console** : `PRICE_SOURCE=mt5bridge` (ou en cascade, ex.
   `mt5bridge,twelvedata`). Le moteur consomme alors les bougies du pont ;
   `GET /api/market-data` et `GET /api/mt5-state` exposent l'état (timeframes
   reçus, fraîcheur compte/positions) pour le monitoring.

**Compte + positions réels sur le dashboard cloud :** `/api/state` renvoie le
compte poussé (équité, solde, levier, drawdown journalier dérivé côté console)
avec `account_source: "mt5bridge"`, et `/api/positions` renvoie les positions
ouvertes réelles (`source: "mt5bridge"`). Au-delà de `MT5_STATE_TTL` (15 min par
défaut) sans nouvel envoi, le dashboard retombe proprement sur la `SIMULATION`.

> ⚠️ Le pont fournit désormais **PRIX + COMPTE + POSITIONS** (lecture seule).
> L'**exécution d'ordres** (ouverture/fermeture, gestion SL/TP) reste côté
> Windows (terminal MT5) : le bouton « Fermer » du dashboard cloud ne peut pas
> agir sur une position réelle tant que la console n'a pas de terminal MT5 local.

Le reste du dépôt `goldrogers-trading-bot` (indicateurs Wyckoff/Ichimoku/RSI,
bots, dashboards) **duplique** ce que le pipeline `ny_session_interface` fait déjà
en plus propre → volontairement **non importé**.

## Ce qui a été volontairement EXCLU
- 🔒 `docs/Storj-S3-Credentials-*.txt` de `goldrogers-trading-bot` (**credentials en
  clair** — à supprimer du repo source **et révoquer/roter**).
- Bases sqlite (`data/*.db*`), `node_modules/`, et les valeurs de secrets du
  `.env.example` (assainies en placeholders).
