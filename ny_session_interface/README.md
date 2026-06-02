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
| GET  | `/api/logs?after=<i>` | logs incrémentaux |
| POST | `/api/control/start` · `/stop` | démarre / arrête le moteur |
| POST | `/api/control/dry-run` `{enabled}` | bascule DRY RUN |
| POST | `/api/control/kill-switch` `{enabled}` | active / désactive le kill switch |
| POST | `/api/control/profile` `{profile}` | change de profil |
| POST | `/api/control/close-all` | ferme toutes les positions du bot |
| POST | `/api/control/close/{ticket}` | ferme une position |

Les routes `POST` exigent l'en-tête `X-Api-Token` si `API_TOKEN` est défini.
