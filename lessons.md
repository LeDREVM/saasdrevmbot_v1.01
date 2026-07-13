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
