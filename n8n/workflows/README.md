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
