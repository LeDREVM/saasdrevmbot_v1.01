# Workflows archivés — ne pas importer dans n8n

Ces workflows sont conservés pour référence mais **ne fonctionnent pas en l'état**.

## `workflow_pre_event_alerts.json` — archivé le 2026-07-23

Alertes 30 min avant une annonce économique fort impact (Discord + Telegram + scoring IA).

### Pourquoi archivé

| Problème | Détail |
| --- | --- |
| Endpoint inexistant | Appelle `GET /api/n8n/upcoming` → 404. Le routeur n8n n'expose que `/calendar/today` et `/notify/telegram`. La route réelle la plus proche est `GET /api/trading-economics/upcoming` (paramètre `minutes`, pas de filtre `impact`). |
| Endpoint inexistant | Appelle `POST /api/n8n/scoring` → 404. La route réelle serait `POST /api/scoring/analyze`, **mais le routeur `scoring` n'est pas monté** dans `backend/main.py`. |
| Condition impossible | Le nœud IF teste `$json.has_events === true`. Ce champ n'existe nulle part dans le backend — `/api/trading-economics/upcoming` renvoie `{success, count, minutes, events}`. La branche « annonce imminente » ne se déclenche jamais. |
| Payload inventé | Le nœud « Déclencher scoring IA » envoie `symbol: 'US30'`, `setup_grade: 'A'`, `htf_phase: 'markup'`, `direction: 'BUY'` **en dur**. L'agent IA scorerait un setup fictif sans rapport avec le marché. |
| `continueOnFail` inopérant | Placé dans `parameters` au lieu du niveau nœud → ignoré par n8n. |
| `typeVersion` absents | Aucun nœud n'a de `typeVersion` → n8n retombe sur la v1 alors que les paramètres écrits sont ceux de la v4. |
| `sendQuery` manquant | `queryParameters` déclarés sans `sendQuery: true` → les filtres `minutes` et `impact` ne partent pas. |

### Pour le remettre en service

1. Monter le routeur scoring : ajouter `scoring` à l'import et un `app.include_router(scoring.router, prefix=settings.API_V1_STR)` dans `backend/main.py`.
2. Soit créer `GET /api/n8n/upcoming` dans `backend/app/api/routes/n8n.py` (avec `has_events` dans la réponse), soit recâbler le workflow sur `/api/trading-economics/upcoming` et remplacer la condition par `count > 0`.
3. Remplacer le payload de scoring en dur par les vraies données de marché.
4. Appliquer les mêmes corrections que `workflow_daily_calendar.json` : `typeVersion`, `sendQuery: true`, credentials, `continueOnFail` au niveau nœud.
