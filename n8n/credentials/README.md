# Credentials n8n — DREVM

`credentials.example.json` documente la **structure** des credentials attendus
par les workflows (`../workflows`). Ce sont des **placeholders** — pas de vrais
secrets.

## Règle de sécurité

- **Ne jamais committer de vrais credentials.** Les exports réels (avec `data`
  chiffré ou en clair) sont ignorés par git (voir `.gitignore` de ce dossier :
  tout sauf `credentials.example.json` et ce README).
- **Créer les credentials dans l'UI n8n** : *Settings → Credentials → New*.
  n8n les chiffre au repos avec `N8N_ENCRYPTION_KEY`. Un import de JSON en clair
  n'est possible que si la clé de chiffrement correspond — préférer la création
  manuelle.

## Credentials utilisés

| Nom | Type n8n | Sert à |
|---|---|---|
| Console API Token | `httpHeaderAuth` (`X-Api-Token`) | `/api/execute` de la console (alternative à `NY_BOT_TOKEN`). |
| Telegram Bot | `telegramApi` | Notifications WF2 (si nœud Telegram natif). |
| TimescaleDB | `postgres` | Store features (WF1) + experiences (WF3). |
| Backend scoring | `httpHeaderAuth` (`X-N8N-Secret`) | Optionnel, si le backend est protégé. |

> Les workflows livrés utilisent aujourd'hui des **variables d'environnement**
> (`NY_BOT_URL`, `NY_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) plutôt
> que ces credentials. Ceux-ci sont fournis pour passer à une auth « propre »
> par credentials n8n si tu préfères.
