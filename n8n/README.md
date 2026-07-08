# Workflows n8n

## `calendrier-economique-telegram.json`

Workflow planifié qui récupère le calendrier économique du jour depuis l'API
SaaS DrevmBot et envoie un résumé formaté sur Telegram.

### Flux

1. **Chaque jour 07:00** — Schedule Trigger (déclenchement quotidien à 07h00).
2. **GET /api/n8n/calendar/today** — appelle `{{ $env.SAAS_API_URL }}/api/n8n/calendar/today?impact=High,Medium`.
3. **Formater le message** — construit un message HTML trié par heure (emoji par
   niveau d'impact, heure, devise, événement, prévision/précédent/réel).
4. **Envoyer sur Telegram** — poste le message dans le chat configuré.

### Import

1. Dans n8n : **Workflows → Import from File** → sélectionner
   `calendrier-economique-telegram.json`.
2. Configurer les variables d'environnement n8n :
   - `SAAS_API_URL` — URL de base de l'API (ex. `https://api.mondomaine.com`),
     **sans** slash final.
   - `TELEGRAM_CHAT_ID` — ID du chat/canal Telegram de destination.
3. Ouvrir le nœud **Envoyer sur Telegram** et sélectionner (ou créer) une
   credential **Telegram API** avec le token du bot. Le champ `credentials.id`
   du JSON (`REPLACE_WITH_TELEGRAM_CREDENTIAL_ID`) sera remplacé automatiquement
   lors de la sélection.
4. Activer le workflow.

### Notes

- L'endpoint `GET /api/n8n/calendar/today` doit renvoyer la même forme que
  `/api/calendar/today` :
  `{ "source", "date", "events": [...], "count" }`, chaque événement contenant
  `date, time, currency, event, impact, actual, forecast, previous`.
- Le filtre `impact=High,Medium` est modifiable dans les *Query Parameters* du
  nœud HTTP Request.
- L'heure de déclenchement (07:00) se règle dans le nœud Schedule Trigger.

## `calendrier-economique-multicanal.json`

Version complète : récupère le calendrier du jour, et si des événements à fort
impact existent, diffuse vers **Discord**, **Telegram** (via l'API SaaS) et
archive le JSON sur **Nextcloud**.

### Flux

1. **⏰ Cron 06h00** — du lundi au vendredi (`0 6 * * 1-5`).
2. **📥 Fetch calendrier** — `GET {{ $env.SAAS_API_URL }}/api/n8n/calendar/today?impact=High,Medium`
   (auth par credential *Header Auth* → en-tête `X-N8N-Secret`).
3. **🔍 A des événements ?** — IF `count > 0` ; sinon → **📭 Pas d'événements** (NoOp).
4. Sur la branche « vrai », en parallèle :
   - **🎨 Formater Discord** (Code) → **💬 Envoyer Discord** (webhook `DISCORD_WEBHOOK_URL`).
   - **📱 Notifier Telegram** → `POST {{ $env.SAAS_API_URL }}/api/n8n/notify/telegram`
     (le backend formate et envoie le message Telegram).
   - **☁️ Upload Nextcloud** → `PUT` du JSON brut dans
     `…/saasDrevmBot/calendriers/AAAA-MM-JJ.json` (auth *Basic Auth*).

### Variables d'environnement n8n

| Variable | Usage |
| --- | --- |
| `SAAS_API_URL` | URL de base de l'API (sans slash final) |
| `DISCORD_WEBHOOK_URL` | Webhook Discord de destination |
| `NEXTCLOUD_URL` | URL de base Nextcloud |
| `NEXTCLOUD_USER` | Utilisateur Nextcloud (chemin WebDAV) |

> Le secret `X-N8N-Secret` n'est **pas** une variable d'env ici : il est stocké
> dans la credential n8n *Header Auth* (voir ci-dessous).

### Credentials n8n à sélectionner après import

1. **Header Auth** — nommée *SaaS DrevmBot — X-N8N-Secret* :
   - *Name* = `X-N8N-Secret`
   - *Value* = la même valeur que `N8N_WEBHOOK_SECRET` côté backend.
   - Utilisée par les nœuds **📥 Fetch calendrier** et **📱 Notifier Telegram**.
2. **Basic Auth** — nommée *Nextcloud DrevmBot* : identifiants Nextcloud
   (utilisée par **☁️ Upload Nextcloud**).

Les `id` de credential dans le JSON (`REPLACE_HEADER_AUTH_CREDENTIAL_ID`,
`REPLACE_NEXTCLOUD_BASIC_AUTH_CREDENTIAL_ID`) sont des placeholders : à l'import,
n8n demandera de sélectionner/créer la credential correspondante.

### Où héberger les endpoints ? → Netlify (déployé)

Le domaine `https://saasdrevmbot.netlify.app` n'héberge **que** le frontend +
des Netlify Functions (le backend FastAPI n'y tourne pas). Les endpoints n8n
sont donc fournis en **Netlify Functions** :

| URL publique | Function | Redirect (`netlify.toml`) |
| --- | --- | --- |
| `/api/n8n/calendar/today` | `netlify/functions/n8n-calendar-today.js` | ✅ |
| `/api/n8n/notify/telegram` | `netlify/functions/n8n-notify-telegram.js` | ✅ |

➡️ Dans n8n, mettre **`SAAS_API_URL = https://saasdrevmbot.netlify.app`**
(sans slash final). Les appels deviennent
`https://saasdrevmbot.netlify.app/api/n8n/calendar/today` etc.

**Variables d'env à définir sur Netlify** (Site settings → Environment variables) :

| Variable | Usage |
| --- | --- |
| `TE_API_KEY` / `TE_API_SECRET` | Clé Trading Economics (calendrier) |
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat/canal de destination |
| `N8N_WEBHOOK_SECRET` | Secret partagé : si défini, l'en-tête `X-N8N-Secret` est exigé (401 sinon) |

> Les fonctions Netlify renvoient l'impact capitalisé (`High/Medium/Low`) et la
> même forme `{ source, date, events, count }` que la route FastAPI, donc le
> workflow fonctionne sans modification.

### Côté backend FastAPI (alternative auto-hébergée)

- `GET /api/n8n/calendar/today` — calendrier du jour (vérifie `X-N8N-Secret`).
- `POST /api/n8n/notify/telegram` — formate et envoie sur Telegram
  (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`).
- Variable `N8N_WEBHOOK_SECRET` (cf. `backend/env.template`) : si définie, les
  appels n8n sans en-tête `X-N8N-Secret` correct reçoivent **401**. Laisser vide
  pour désactiver la vérification (dev).
