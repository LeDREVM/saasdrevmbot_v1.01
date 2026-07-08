# NY Session Bot — Console de pilotage

Interface web **autonome** pour piloter le bot full-auto NY Session (US30 + USDJPY)
sur MetaTrader 5. Contrôle complet (start/stop, DRY RUN, profil, kill switch,
fermeture de positions) + monitoring temps réel (équité, drawdown, positions,
signaux, logs).

## Architecture

```
ny_session_interface/
├── api.py                 # Serveur FastAPI : REST + sert l'UI
├── ny_session_bot.py      # Moteur pilotable (boucle de trading en thread)
├── sim_mt5.py             # Simulateur MT5 (mode démo, sans terminal)
├── trading_ny_session.py  # ⚠️ PLACEHOLDER — remplace par ta vraie Trading Bible
├── backtest_xbrusd.py     # Algo automatique (backtest) Wyckoff+FVG+Ichimoku, compte départ 100
├── requirements.txt
└── static/                # UI (index.html + app.js + style.css)
```

Le moteur (`BotEngine`) tourne dans un thread de fond ; l'API lit son état via
`snapshot()` / `positions()` et lui envoie des commandes thread-safe. L'UI
interroge l'API toutes les 2 s (REST polling).

## Démarrage rapide (mode démo, sans MT5)

```bash
cd ny_session_interface
pip install -r requirements.txt
python api.py
# → http://127.0.0.1:8800
```

Sans le paquet `MetaTrader5`, le moteur bascule automatiquement en **SIMULATION**
(faux marché) : tu peux exercer toute l'interface (démarrer, voir des positions
fictives, des signaux, l'équité bouger) sans aucun risque.

## Production (VPS Windows avec terminal MT5)

1. Copie **ta vraie** `trading_ny_session.py` à la place du placeholder (ou
   rends-la importable via `app.services.trading_ny_session`).
2. `pip install MetaTrader5` et connecte le terminal Fusion Markets.
3. Renseigne au besoin `MT5_LOGIN/PASSWORD/SERVER` dans `ny_session_bot.py`.
4. `python api.py`, puis ouvre la console.
5. **Reste en DRY RUN** jusqu'à validation, puis bascule en compte démo, et
   seulement ensuite en live.

## Stratégie — Smart Money Trading System

La décision suit la config fournie (multi-timeframe + Wyckoff + divergence) :

| Étage | Rôle | Fichier |
|---|---|---|
| **H4** | Biais (`close` vs `close[-20]`) | `ny_session_bot.get_bias_h4` |
| **M15** | Zone de liquidité (extrême range 30) | `zone_touched_m15` |
| **M5** | Déclencheur bougie | `entry_trigger_m5` |
| **Wyckoff** | Spring / UTAD (faux cassure swing 20) | `detect_wyckoff` |
| **RSI** | Divergence prix / RSI(14) | `detect_divergence` |
| **Ichimoku** | Filtre Kijun(26) | `price_above_kijun` |
| **Décision** | Smart signal + scoring A+/A/B/C | `trading_ny_session.classify_setup` |

- **Smart signal** (entrée) : divergence haussière + Spring + prix > Kijun → **BUY** ;
  divergence baissière + UTAD + prix < Kijun → **SELL**.
- **Grade** = confluence de la « logique finale » (biais H4 + zone M15 + trigger M5) :
  3/3 → **A+**, 2 → **A**, 1 → **B**, 0 → **C**. Chaque profil n'entre qu'à partir
  de son `min_grade`.
- **SL/TP** : gérés par le moteur (SL = ATR × `sl_atr_mult`, TP = `rr_target`).

> Le snippet Wyckoff du PDF était contradictoire (`last < low` ET `close > low`
> avec `last == close`) : il a été corrigé en détection de faux cassure (mèche
> au-delà du swing, clôture en deçà).

## Alertes Telegram (section 8)

Optionnel. Définis les deux variables d'environnement puis relance :

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="987654321"
python api.py
```

À chaque signal exécuté, le bot envoie un message (sens, grade, entrée/SL/TP,
DRY/LIVE, divergence/Wyckoff). L'envoi est non bloquant. Le badge « Telegram ✓ »
apparaît dans la console quand c'est actif.

## Sécurité ⚠️

Ce serveur peut envoyer des **ordres réels** (quand DRY RUN est OFF).

- Écoute par défaut sur `127.0.0.1` uniquement. Pour un accès distant, **passe par
  un tunnel SSH** (`ssh -L 8800:127.0.0.1:8800 user@vps`) plutôt que d'exposer le port.
- Protège les commandes avec un token : `export API_TOKEN="secret"` (le token se
  saisit dans l'UI, champ « API token »).
- Variables : `NY_BOT_HOST`, `NY_BOT_PORT`, `API_TOKEN`.
- Le **kill switch** crée/supprime le fichier `STOP.flag` (compatible avec le bot
  d'origine) : aucune nouvelle entrée tant qu'il est actif.

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| GET  | `/api/state` | snapshot complet (statut, compte, profil, DD…) |
| GET  | `/api/positions` | positions ouvertes + PnL |
| GET  | `/api/signals` | derniers signaux / entrées de journal |
| GET  | `/api/scan` | confluence courante par symbole (Wyckoff · FVG · Ichimoku), lecture seule |
| POST | `/api/scan/ai` `{symbol}` | proxifie l'agent de scoring IA du backend sur le setup courant du symbole |
| GET  | `/api/logs?after=<i>` | logs incrémentaux |
| POST | `/api/control/start` · `/stop` | démarre / arrête le moteur |
| POST | `/api/control/dry-run` `{enabled}` | bascule DRY RUN |
| POST | `/api/control/kill-switch` `{enabled}` | active / désactive le kill switch |
| POST | `/api/control/profile` `{profile}` | change de profil |
| POST | `/api/control/close-all` | ferme toutes les positions du bot |
| POST | `/api/control/close/{ticket}` | ferme une position |

Les routes `POST` exigent l'en-tête `X-Api-Token` si `API_TOKEN` est défini.

### Scoring IA sur le panneau de scan

Chaque carte du panneau « Scan des setups » a un bouton **🤖 Analyser (IA)**. Au clic,
la console appelle `POST /api/scan/ai {symbol}`, qui :

1. récupère le contexte courant du symbole via `scan_setups()` (grade, phase HTF, sens) ;
2. proxifie vers l'**agent de scoring IA** du backend (`POST /api/scoring/analyze`,
   Claude tool use) ;
3. retourne le score **/100** + recommandation **TRADE / WAIT / SKIP** + raisonnement,
   affichés sur la carte.

Config : `BACKEND_URL` (défaut `http://127.0.0.1:8000`) doit pointer sur le backend
FastAPI principal, et ce backend a besoin de `ANTHROPIC_API_KEY`. Si le backend est
injoignable ou la clé absente, la carte affiche « IA indisponible » (dégradation
propre, le reste du panneau continue de fonctionner).

## Backtest — algo automatique (compte départ 100)

`backtest_xbrusd.py` simule l'algo Wyckoff + FVG + Ichimoku sur **XBR/USD (Brent)**
en partant d'un capital de **100**. Il réutilise **les mêmes détecteurs** que le
moteur live (`detect_wyckoff`, `detect_fvg`, filtre Kijun, divergence RSI,
`score_confluence`), donc il teste la vraie stratégie.

**Règle d'entrée** (une position à la fois, flat → flat) :

1. **Structure** — un FVG frais donne le sens et la zone.
2. **Tendance** — filtre Ichimoku : Kijun alignée avec le sens du FVG.
3. **Timing** — mitigation : le prix est revenu dans le gap.

Les 3 gates ci-dessus **sont la stratégie de base** (ils valent déjà 6/11 :
FVG 3 + Ichimoku 2 + mitigation 1). Wyckoff (Spring/UTAD), divergence et biais
ajoutent des points ; `--min-confluence` (/11) permet d'exiger ces bonus :
`≤6` = base (gates seuls), `7` = +biais H4 ou divergence favorable, `8+` = +Wyckoff aligné.

**Money-management** : `--risk` (défaut 1 %) du capital risqué par trade
(une perte au SL = −1R exact), SL en `--sl-atr` × ATR, TP en `--rr`,
break-even à `--breakeven` R, compounding. Winrate affiché hors trades à break-even.

```bash
python backtest_xbrusd.py                          # Brent via yfinance, sinon synthétique
python backtest_xbrusd.py --interval 1h --period 6mo
python backtest_xbrusd.py --risk 0.01 --rr 2.0 --min-confluence 6
```

Sans réseau, une série **synthétique déterministe** (régimes trend/range) permet de
tourner hors-ligne. ⚠️ Résultats sur données synthétiques = démonstration mécanique
(pas d'edge réel) ; lance sur données Brent réelles pour évaluer la performance.
