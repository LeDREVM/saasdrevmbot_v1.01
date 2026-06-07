# Workflows n8n — saasDrevmBot

## Variables d'environnement n8n (Settings → Variables)

| Variable | Valeur |
|---|---|
| `SAAS_API_URL` | `http://localhost:8000` (ou URL de prod) |
| `N8N_WEBHOOK_SECRET` | Même valeur que `N8N_WEBHOOK_SECRET` dans `.env` backend |
| `DISCORD_WEBHOOK_URL` | URL webhook Discord principal |
| `DISCORD_WEBHOOK_ALERTS_URL` | URL webhook Discord canal alertes (peut être identique) |
| `NEXTCLOUD_URL` | `https://ledream.kflw.io` |
| `NEXTCLOUD_USER` | Username Nextcloud |

Pour les credentials Nextcloud (Basic Auth), créer une credential de type **HTTP Basic Auth** dans n8n.

## Importer les workflows

1. Ouvrir n8n → **Workflows** → **Import from file**
2. Sélectionner `workflow_daily_calendar.json`
3. Répéter avec `workflow_pre_event_alerts.json`
4. Activer les deux workflows

## Workflow 1 — Calendrier Quotidien

**Déclencheur :** Lundi–Vendredi à 06h00 (Europe/Paris)

```
Cron 06h00
  → GET /api/n8n/calendar/today
  → [si events > 0]
      → Format embed Discord + POST webhook
      → POST /api/n8n/notify/telegram
      → PUT Nextcloud /saasDrevmBot/calendriers/YYYY-MM-DD.json
```

## Workflow 2 — Alertes Pré-Événement + Scoring IA

**Déclencheur :** Toutes les 15 min (07h–22h Paris, lun–ven)

```
Toutes les 15 min
  → Vérifier session active (heure + jour)
  → GET /api/n8n/upcoming?minutes=30&impact=High
  → [si annonce imminente détectée]
      → Alerte Discord embed rouge
      → Alerte Telegram
      → POST /api/n8n/scoring  ← agent IA Claude
          → Score /100 + TRADE/WAIT/SKIP
          → Auto-notifie Discord + Telegram
```

## Endpoints Backend disponibles

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/n8n/health` | Healthcheck |
| GET | `/api/n8n/calendar/today` | Calendrier du jour (filtrable par currency/impact) |
| GET | `/api/n8n/upcoming?minutes=30` | Annonces dans N minutes |
| POST | `/api/n8n/scoring` | Scoring IA d'un setup |
| POST | `/api/n8n/notify/discord` | Envoi Discord custom |
| POST | `/api/n8n/notify/telegram` | Envoi Telegram custom |

Tous les endpoints acceptent le header `X-N8N-Secret` pour l'authentification.
