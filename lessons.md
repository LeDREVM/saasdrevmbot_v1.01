# lessons.md — mémoire procédurale saasDrevmBot

Leçons apprises sur CE projet : bugs récurrents, pièges connus, causes racines.
Format : `L## — Titre / Symptôme / Cause racine / Fix / Date`

---

## L01 — Le contrat d'API du calendrier est `impact` (chaîne), jamais `impact_level`

- **Symptôme** : message Discord quotidien envoyé mais vide — « 🔴 0 Fort | 🟡 0 Moyen » alors que `count > 0`.
- **Cause racine** : le nœud Code n8n filtrait sur `e.impact_level === 3`. Ce champ n'existe pas. Les deux backends renvoient une **chaîne capitalisée** : `backend/app/services/economic_calendar/base_scraper.py:50` (`'impact': self.impact.value` → `"High"`) et `netlify/functions/n8n-calendar-today.js:50` (`mapImpact()` → `"High"`).
- **Fix** : `e.impact === 'High'` / `e.impact === 'Medium'`.
- **Règle à retenir** : le contrat de l'événement calendrier est figé — `{source, date, time, currency, event, impact, actual, forecast, previous}` avec `impact ∈ {High, Medium, Low}`. Ne jamais inventer un champ dérivé côté n8n.
- **Date** : 2026-07-23

## L02 — Un nœud n8n sans `typeVersion` retombe en v1 et ignore les paramètres v4

- **Symptôme** : filtres d'URL non appliqués, corps de requête ignoré, sans aucune erreur.
- **Cause racine** : les workflows exportés à la main n'avaient aucun `typeVersion`. n8n retombe alors sur la v1 du nœud, alors que les paramètres écrits (`sendBody`, `contentType`, `queryParameters`) sont ceux de la v4.x. Échec **silencieux**.
- **Fix** : `typeVersion` explicite sur chaque nœud — scheduleTrigger `1.3`, httpRequest `4.4`, if `2.2`, code `2`, noOp `1`.
- **Règle à retenir** : ne jamais écrire un workflow n8n à la main sans `typeVersion`. Et si on met `if` en `2.x`, les conditions doivent être au format v2 (`conditions.conditions[]` avec `leftValue`/`operator`), pas au format v1 (`conditions.number[]` avec `value1`/`operation`/`value2`).
- **Date** : 2026-07-23

## L03 — `queryParameters` ne part pas sans `sendQuery: true`

- **Symptôme** : l'API renvoyait tous les événements, y compris Low impact, malgré `?impact=High,Medium`.
- **Cause racine** : dans le nœud HTTP Request v3+, `sendQuery` est l'interrupteur qui autorise l'envoi des paramètres d'URL. Sans lui, `queryParameters` est ignoré. Même logique pour `sendHeaders` / `sendBody`.
- **Fix** : ajouter `"sendQuery": true` à côté de `queryParameters`.
- **Date** : 2026-07-23

## L04 — Telegram `parse_mode: HTML` casse sur `&`, `<`, `>` non échappés

- **Symptôme** : notification Telegram perdue silencieusement (400 Bad Request côté API Telegram), aucune trace côté n8n.
- **Cause racine** : les noms d'événements sont **scrapés**. Des valeurs comme `M&A Activity` ou `Retail Sales <MoM>` étaient injectées brutes dans le HTML. Telegram refuse les balises inconnues et les `&` nus.
- **Fix** : échappement `& < >` avant insertion — `_esc()` dans `backend/app/api/routes/n8n.py`, `esc()` dans `netlify/functions/n8n-notify-telegram.js`.
- **Règle à retenir** : toute donnée scrapée insérée dans du HTML Telegram/Discord doit passer par un échappement. Le corollaire : les deux implémentations (FastAPI et Netlify Function) doivent être corrigées **ensemble**, elles sont interchangeables par conception.
- **Date** : 2026-07-23

## L05 — Un nœud avec `authentication: genericCredentialType` exige un bloc `credentials`

- **Symptôme** : « Credentials not set » à l'exécution.
- **Cause racine** : le nœud déclarait `authentication` + `genericAuthType` sans le bloc `credentials` correspondant.
- **Fix** : deux voies selon le besoin — soit ajouter le bloc `credentials` (obligatoire pour Basic Auth, cf. Nextcloud), soit retirer `authentication`/`genericAuthType` et poser l'en-tête manuellement via `$env` (suffisant pour `X-N8N-Secret`, évite de créer une credential).
- **Date** : 2026-07-23

## L06 — Deux routeurs FastAPI existent mais ne sont pas montés

- **Symptôme** : `POST /api/n8n/scoring` et `GET /api/n8n/upcoming` → 404.
- **Cause racine** : `app/api/routes/scoring.py` définit bien `APIRouter(prefix="/scoring")` mais `backend/main.py` ne l'importe ni ne l'inclut. Et `/api/n8n/upcoming` n'a jamais existé — la route réelle est `/api/trading-economics/upcoming`.
- **État** : non corrigé. Le workflow qui en dépendait (`workflow_pre_event_alerts.json`) est archivé dans `n8n/_archive/` avec la procédure de remise en service.
- **Règle à retenir** : avant d'écrire un appel HTTP dans un workflow n8n, vérifier que la route est **montée** dans `main.py`, pas seulement qu'elle est définie dans un fichier de routes.
- **Date** : 2026-07-23

## L07 — Les endpoints Netlify sont déployés mais AUCUNE variable d'env n'est configurée

- **Symptôme** : les workflows n8n n'auraient rien pu faire même correctement câblés.
- **Constat mesuré en prod le 2026-07-23** :
  - `GET /api/n8n/calendar/today` → `500 {"error":"TE_API_KEY manquante"}`
  - `POST /api/n8n/notify/telegram` → `500 {"error":"TELEGRAM_BOT_TOKEN non configuré"}`
  - `GET /api/n8n/notify/telegram` → `405` (la redirection et la function sont bien déployées)
- **Cause racine** : les redirections `netlify.toml` et les functions sont en ligne, mais les variables d'environnement Netlify n'ont jamais été renseignées.
- **Piège de séquencement (le plus important)** : un **faux** `X-N8N-Secret` renvoie le même 500 qu'aucun secret — donc `N8N_WEBHOOK_SECRET` n'est pas défini et la vérification est **entièrement contournée** (`if (expected)` est faux → le contrôle est sauté). Or `/notify/telegram` accepte un champ `text` libre envoyé tel quel à Telegram. Le jour où `TELEGRAM_BOT_TOKEN` est renseigné **sans** `N8N_WEBHOOK_SECRET`, l'endpoint devient un relais Telegram public : n'importe qui peut poster ce qu'il veut sur le canal.
- **Règle à retenir** : **toujours définir `N8N_WEBHOOK_SECRET` en premier**, avant `TELEGRAM_BOT_TOKEN` et `TE_API_KEY`. Le secret désactivé par variable vide est un choix de dev qui devient une faille en prod.
- **Date** : 2026-07-23

## L08 — Câbler le pipeline de capture (vision) : router monté, URLs inter-process, secret des deux côtés

- **Symptôme** : `/api/vision/analyze` et `/api/vision/analyze-raw` → 404 ; en Docker, WF5 n'atteint ni le screenshot-service ni le backend ; `analyze-raw` → 401 même avec un secret configuré côté backend.
- **Causes racines** (même famille que L06/L07, appliquée à la capture) :
  - `vision.router` défini dans `app/api/routes/vision.py` mais **jamais monté** dans `backend/main.py` (import + `include_router` oubliés — cf. L06) → 404.
  - URLs `localhost` codées en dur dans les nœuds n8n HTTP : injoignables depuis le conteneur n8n (là `localhost` = le conteneur n8n lui-même).
  - `N8N_WEBHOOK_SECRET` présent côté backend mais **pas exporté côté service n8n** → en-tête `X-N8N-Secret` vide → 401. Complète L07 : là c'était *fail-open* (secret absent des deux côtés), ici c'est *fail-closed* (présent d'un seul côté).
  - `backend/env.template` : `N8N_WEBHOOK_SECRET` **en double** avec deux valeurs différentes → dotenv garde la dernière (piège silencieux).
  - Fallback modèle `claude-sonnet-4-6` **invalide** dans `vision_analyst.py`.
- **Fix** : monter `vision.router` dans `main.py` ; déclarer `AI_VISION_MODEL` (ID valide `claude-sonnet-5`) dans `Settings` ; URLs n8n via `{{ $env.BACKEND_URL || 'http://localhost:8000' }}` et `{{ $env.SCREENSHOT_URL || 'http://localhost:3001' }}` (marche en natif sans config ET en Docker en exportant les vars) ; exporter `N8N_WEBHOOK_SECRET` **des deux côtés** ; dédupliquer le secret dans `env.template`.
- **Règle à retenir** : tout nouveau routeur → vérifier `include_router` dans `main.py` (L06) ; toute URL inter-process dans n8n → `$env` avec fallback localhost, jamais un host en dur ; tout secret partagé → présent des deux côtés ET jamais dupliqué dans le `.env`.
- **Date** : 2026-07-23

---

## Héritées (module `trading_bot/`, format d'origine)

## L09 — Blocs de code orphelins dans `trading_bot/`

- **Symptôme** : `import telegram` (ou `main.py`) plante en SyntaxError/IndentationError.
- **Cause racine** : plusieurs fichiers de `trading_bot/` (`telegram.py`, `main.py`) contiennent des snippets collés au niveau module, hors de toute fonction, référençant des variables inexistantes.
- **Fix** : envelopper les snippets dans des fonctions nommées (cf. `telegram.py` : `notify_divergence`, `notify_divergences`, `filter_divergences`, `notify_smart_money`). `main.py` contient encore un bloc orphelin après la boucle while (bias/wyckoff/execute_trade) — à traiter.
- **Date** : 2026-07-12

## L10 — Secrets en dur dans `trading_bot/`

- **Symptôme** : clés API placeholders (`"YOUR_TWELVEDATA_KEY"`, `"YOUR_BOT_TOKEN"`) codées en dur.
- **Cause racine** : pas de gestion d'environnement dans ce module.
- **Fix** : `os.getenv` + `python-dotenv` (`data_engine.py`, `telegram.py`) + `env.template`. Toujours passer par `.env` pour tout nouveau secret.
- **Date** : 2026-07-12

## L11 — `npm install` fait remonter des vulnérabilités transitives préexistantes (hook post-deps-audit)

- **Symptôme** : après un `npm install` (même sans toucher `package.json`), le hook `post-deps-audit` bloque avec des CVE `undici` (high) et `uuid`/`node-cron` (moderate).
- **Cause racine** : ces failles sont **transitives et déjà présentes dans `package-lock.json` committé** (undici via discord.js/axios/yahoo-finance2 ; uuid via `node-cron@3`). `npm install` ne fait que matérialiser `node_modules` (gitignored) à partir du lock existant — il n'ajoute aucune dépendance. `git status` sur `package.json`/`package-lock.json` = inchangés.
- **Fix / décision** : ne PAS lancer `npm audit fix --force` à l'occasion d'une tâche sans rapport — il bumpe `node-cron 3→4` (**breaking**). Résolution retenue = **justification documentée** : le correctif dépendances est un chantier de maintenance à part entière (bump `node-cron` + revalidation des crons), à traiter sur sa propre branche/brief, pas embarqué dans une feature UI. `node_modules` n'étant pas versionné, rien de vulnérable n'est committé.
- **Date** : 2026-07-30

## L12 — Deux `declarative_base()` distincts : `create_all` doit viser la metadata du modèle

- **Symptôme** : script d'import écrivant en DB → `sqlite3.OperationalError: no such table: economic_events`, alors que `Base.metadata.create_all()` a été appelé.
- **Cause racine** : `backend/app/core/database.py` définit `Base = declarative_base()` MAIS `backend/app/models/database.py` en définit un **second, indépendant** (`EconomicEventDB(Base)` y est enregistré). `create_all` sur le Base de `core` ne connaît donc pas la table du modèle.
- **Fix** : créer les tables via la metadata **du modèle** : `EconomicEventDB.metadata.create_all(bind=engine)` (et non `core.database.Base.metadata`). En run normal, c'est la migration/bootstrap de l'app qui crée les tables ; tout script autonome touchant la DB doit cibler la bonne metadata.
- **Date** : 2026-07-30

## L13 — Netlify : le backend « pas reconnu » = placeholders dans `netlify.toml` (qui n'interpole pas les env vars)

- **Symptôme** : sur `saasdrevmbot.netlify.app`, tous les appels `/api/*` échouent et le badge backend de la page d'accueil reste « offline ». Seuls `/api/calendar` et `/api/n8n/*` répondent.
- **Cause racine** : `netlify.toml` proxifiait vers des URLs placeholder jamais remplacées (`https://REMPLACE-fastapi.onrender.com`, `REMPLACE-express.onrender.com`). Avec `VITE_API_URL = ""` (MODE A), le front appelle `/api/...` en relatif → Netlify proxifie vers un domaine inexistant → échec opaque. Ce qui survivait, ce sont les 3 routes servies par des Netlify Functions, dont les redirects sont listés **avant** la règle générale `/api/*` (premier match gagnant).
- **Piège de fond** : **`netlify.toml` n'interpole PAS les variables d'environnement**. Écrire l'URL backend dans un `[[redirects]]` la fige dans le repo et impose commit + redéploiement à chaque changement — c'est exactement ce qui a laissé les placeholders pourrir en prod. Même famille que L07 : déployé ≠ configuré.
- **Fix** : `netlify/functions/api-proxy.js` — proxy générique lisant `BACKEND_API_URL` / `EXPRESS_API_URL` dans les env vars Netlify ; `netlify.toml` réécrit `/api/*` et `/health` vers cette fonction. Variable absente → `503` JSON explicite au lieu d'une erreur de proxy illisible ; timeout à 9 s (< la limite Netlify de 10 s) → `504` lisible au lieu du « task timed out » opaque.
- **Détail qui coince** : derrière une réécriture, ce que Netlify expose dans `event.path` / `event.rawUrl` (URL d'origine ou URL réécrite) n'est pas garanti. Le chemin amont est donc **répété dans la cible du redirect** (`to = "/.netlify/functions/api-proxy/api/:splat"`) et la fonction retire son propre préfixe — les deux cas retombent sur le bon chemin.
- **Règle à retenir** : jamais d'URL d'infrastructure en dur dans `netlify.toml` — toute cible variable passe par une fonction + env var. Et tout placeholder `REMPLACE-…` committé est un bug en prod en attente : le rendre **bruyant** (erreur explicite) plutôt que silencieux.
- **Date** : 2026-07-31
