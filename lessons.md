# lessons.md — Mémoire procédurale du projet

L01 — Blocs de code orphelins dans trading_bot/
Symptôme : `import telegram` (ou main.py) plante en SyntaxError/IndentationError.
Cause racine : plusieurs fichiers de trading_bot/ (telegram.py, main.py) contiennent des snippets collés au niveau module, hors de toute fonction, référençant des variables inexistantes.
Fix : envelopper les snippets dans des fonctions nommées (cf. telegram.py : notify_divergence, notify_divergences, filter_divergences, notify_smart_money). main.py contient encore un bloc orphelin après la boucle while (bias/wyckoff/execute_trade) — à traiter.
Date : 2026-07-12

L02 — Secrets en dur dans trading_bot/
Symptôme : clés API placeholders ("YOUR_TWELVEDATA_KEY", "YOUR_BOT_TOKEN") codées en dur.
Cause racine : pas de gestion d'environnement dans ce module.
Fix : os.getenv + python-dotenv (data_engine.py, telegram.py) + env.template. Toujours passer par .env pour tout nouveau secret.
Date : 2026-07-12

L03 — Router FastAPI écrit mais jamais monté / URLs Docker en localhost
Symptôme : /api/vision/analyze et /analyze-raw en 404 ; toute la chaîne capture (front + n8n WF5) morte malgré un code correct.
Cause racine : (a) vision.router jamais ajouté dans backend/main.py (import + include_router oubliés) ; (b) WF5 appelait http://localhost:3001 et :8000 → injoignables depuis le conteneur n8n sur trading-net ; (c) backend absent du vps/docker-compose.yml ; (d) N8N_WEBHOOK_SECRET non exporté côté service n8n → header X-N8N-Secret vide → 401 ; (e) fallback modèle "claude-sonnet-4-6" invalide.
Fix : monter vision.router dans main.py ; déclarer AI_VISION_MODEL dans config ; WF5 → noms de services (screenshot-service, backend) ; ajouter service backend au compose VPS ; brancher N8N_WEBHOOK_SECRET des DEUX côtés. Réflexe : tout nouveau routeur → vérifier include_router ; toute URL inter-conteneurs → nom de service, jamais localhost.
Date : 2026-07-23
