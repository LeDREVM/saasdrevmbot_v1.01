# Workflows n8n — pipeline DREVM

Orchestration bout-en-bout du pipeline de trading, branchée sur la console
`ny_session_interface` (endpoints `/api/signal` et `/api/execute`).

```
MT5 → Feature Engine → AI Setup Validator → /api/signal
                                                 │
                              ┌──────────────────┼───────────────────┐
                            WF1                 WF2                  WF3
                       (snapshot)         (filtres → trade)      (feedback)
                                                 │
                                          /api/execute (gardé)
                                                 │
                                         MT5 + Telegram + Journal
                                                 │
                                                WF4 (retrain nocturne — stub RL)
```

| Workflow | Déclencheur | Rôle |
|---|---|---|
| **WF1** `wf1_signal_poll.json` | chaque minute | `GET /api/signal` → aplatit chaque signal (scores/features) → store (DB/TimescaleDB). |
| **WF2** `wf2_signal_to_trade.json` | chaque minute | `GET /api/signal` → garde les signaux `executable` (conf ≥ 80, NY session, news, risk) → `POST /api/execute` (gardé) → Telegram. |
| **WF3** `wf3_feedback_reward.json` | 5 min | `GET /api/stats` → transforme les trades fermés en `experience` (reward = PnL) → replay buffer. |
| **WF4** `wf4_retrain_nightly.json` | 22h (cron) | **STUB RL** : Dataset → Validation → Retrain PPO → Backtest → *si meilleur* Deploy, sinon Keep. Nœuds « STUB » à brancher sur le `trainer/` réel. |
| **WF5** `wf5_ny_preopen_analysis.json` | 13:25 UTC lun-ven | Pré-open NY (9:25 Guadeloupe, 5 min avant open) : XAUUSD/US30, TF D1/H4/M15/M5 → `capture-set` → `/api/vision/analyze-raw` → Telegram. |
| **WF6** `wf6_ny_morning_prep.json` | **07:00 UTC lun-ven** | **Prep session NY à 3h Guadeloupe** (UTC-4 sans DST) : USDJPY/CADJPY/XAUUSD/XBRUSD/GBPJPY/EURUSD, TF D1/H4/M15/M5 → `capture-set` → `/api/vision/analyze-raw` → 1 message Telegram par symbole. |

### WF6 — prep matinale session NY (3h Guadeloupe)

Automatisation quotidienne (lun-ven) déclenchée à **3h00 heure Guadeloupe = 07:00 UTC**
(la Guadeloupe est en UTC-4 toute l'année, sans changement d'heure été/hiver — le cron
`0 7 * * 1-5` est donc correct en permanence). Pour chaque symbole
(**USDJPY, CADJPY, XAUUSD, XBRUSD, GBPJPY, EURUSD**), le workflow capture les TF nécessaires
à la session NY (**D1 → H4 → M15 → M5**, top-down SMC/ICT) via le `screenshot_service`
(`POST /capture-set`), envoie le lot à `POST /api/vision/analyze-raw`, puis pousse le rapport
sur Telegram (un message par symbole).

- Passer en 7/7 : cron `0 7 * * *`. Ajouter/retirer un symbole : nœud **🧮 Config symboles + TF**.
- **XBRUSD (Brent)** est mappé sur `TVC:UKOIL` dans `n8n/screenshot_service/index.js` (`SYMBOL_MAP`) ;
  les 5 autres symboles y sont déjà présents.
- Variables d'env n8n requises : `SCREENSHOT_URL`, `BACKEND_URL`, `N8N_WEBHOOK_SECRET`
  (mêmes que WF5).

## Variables d'environnement (n8n)

| Var | Exemple | Usage |
|---|---|---|
| `NY_BOT_URL` | `http://localhost:8800` | Console `ny_session_interface`. |
| `NY_BOT_TOKEN` | `secret` | En-tête `X-Api-Token` (si `API_TOKEN` défini côté console). |
| `TELEGRAM_BOT_TOKEN` | `123:ABC` | Notifications WF2. |
| `TELEGRAM_CHAT_ID` | `-100…` | Destinataire Telegram. |

## Sécurité / garde-fous (IMPORTANT)

- **`POST /api/execute` n'envoie un ordre que si TOUT est vert** : la console doit
  tourner avec `ALLOW_EXECUTION=1`, un token valide, `confirm=true`, un signal
  courant `EXECUTE`, et les garde-fous moteur (kill switch, halt drawdown, une
  position/symbole, `DRY_RUN`). Tant que `DRY_RUN` est ON, **aucun ordre réel**.
- **WF4 ne déploie jamais un modèle automatiquement sans validation** : la branche
  Deploy est conditionnée à « performance meilleure » et reste un stub tant que le
  `trainer/` RL n'est pas implémenté.

## Import dans n8n

Importer chaque `.json` via *Workflows → Import from File*. Renseigner les
variables d'environnement ci-dessus, puis activer les workflows un par un
(commencer par WF1/WF3 en observation avant d'activer WF2 qui peut trader).
