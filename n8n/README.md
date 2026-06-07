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
