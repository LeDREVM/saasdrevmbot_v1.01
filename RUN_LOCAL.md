# RUN_LOCAL — Pipeline de capture en natif (Windows, sans Docker)

Lancer le **système de capture minimal** en local, sans Docker :
**backend FastAPI** (`:8000`) + **screenshot-service** (`:3001`) + **n8n** (`:5678`).

```
n8n (WF5, cron 13:25 UTC)
   └─▶ POST http://localhost:3001/capture-set      (screenshot-service, Puppeteer → TradingView)
        └─▶ POST http://localhost:8000/api/vision/analyze-raw   (backend → Claude API)
             └─▶ POST http://localhost:8000/api/n8n/notify/telegram
```

Les trois process tournent chacun dans **son propre terminal PowerShell**. Commandes Windows (PowerShell).

---

## 0. Prérequis

- **Python 3.11+** (`python --version`)
- **Node.js 18+** (`node --version`) — le screenshot-service télécharge Chromium au `npm install`
- Une **clé Anthropic** (`sk-ant-...`)
- (Optionnel) le **cookie `sessionid` TradingView** pour de meilleures captures
- (Optionnel) un **bot Telegram** (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`) pour le rapport

> **Postgres/Redis ne sont PAS requis** pour la capture. Au démarrage, le backend
> tente `init_db()` et loggue une erreur si la DB est absente — c'est **sans conséquence**
> pour le pipeline vision (les autres features de l'app, elles, en ont besoin).

### Secret partagé (à générer UNE fois)

n8n s'authentifie auprès du backend via l'en-tête `X-N8N-Secret`. La **même valeur** doit
être présente côté backend (`.env`) **et** côté n8n (variable d'environnement). Génère-la :

```powershell
# PowerShell — génère une valeur aléatoire
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }))
```

Garde cette valeur sous la main : on l'appelle `<SECRET>` ci-dessous.

---

## 1. Terminal A — Backend FastAPI (`:8000`)

```powershell
cd backend

# venv + dépendances
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# config
copy env.template .env
notepad .env   # renseigner au minimum :
#   ANTHROPIC_API_KEY=sk-ant-...
#   AI_VISION_MODEL=claude-sonnet-5
#   N8N_WEBHOOK_SECRET=<SECRET>
#   TELEGRAM_BOT_TOKEN=...   (si notif Telegram)
#   TELEGRAM_CHAT_ID=...

# lancer
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Vérif (dans un autre terminal — sous PowerShell, utiliser `curl.exe`, pas `curl`) :

```powershell
curl.exe http://localhost:8000/health
# → {"status":"healthy",...}

# La route vision est montée ET le secret filtre bien (401 attendu SANS l'en-tête) :
curl.exe -X POST http://localhost:8000/api/vision/analyze-raw -H "Content-Type: application/json" -d "{}"
# → 401 Unauthorized   (preuve : route branchée + secret actif)
```

---

## 2. Terminal B — Screenshot Service (`:3001`)

```powershell
cd n8n\screenshot_service

npm install                 # installe express, puppeteer (+ Chromium), dotenv
copy .env.example .env
notepad .env                # TRADINGVIEW_SESSION_ID=...   (optionnel mais recommandé)

node index.js
# → [Screenshot Service v2] Port 3001
```

Vérif :

```powershell
curl.exe http://localhost:3001/health
# → {"status":"ok","service":"screenshot","version":2}
```

---

## 3. Terminal C — n8n (`:5678`) + import WF5

```powershell
# le secret DOIT être identique à celui du backend (.env)
$env:N8N_WEBHOOK_SECRET = "<SECRET>"

# (optionnel) surcharger les cibles ; par défaut WF5 tombe déjà sur localhost
# $env:BACKEND_URL    = "http://localhost:8000"
# $env:SCREENSHOT_URL = "http://localhost:3001"

npx n8n
# → n8n ready on http://localhost:5678
```

Puis dans l'UI **http://localhost:5678** :
1. **Workflows → Import from File** → `n8n/workflows/wf5_ny_preopen_analysis.json`
2. Ouvrir le workflow, **Activate** (toggle en haut à droite) pour le cron,
   ou **Execute Workflow** pour un test manuel immédiat.

> WF5 lit les URLs via `{{ $env.SCREENSHOT_URL || 'http://localhost:3001' }}` et
> `{{ $env.BACKEND_URL || 'http://localhost:8000' }}` : **aucune config requise en natif**,
> les valeurs par défaut pointent déjà sur localhost.

---

## 4. Test de bout en bout

Dans l'UI n8n, ouvrir WF5 et cliquer **Execute Workflow**. Chaîne attendue :

1. **📸 capture-set** → images base64 multi-TF (XAUUSD, US30)
2. **🤖 analyze-raw** → analyse structurée + `telegram_text` (200 si `<SECRET>` matche)
3. **📣 Telegram** → message reçu (si bot configuré)

En cas d'échec, vérifier dans l'ordre :

| Symptôme | Cause probable |
|----------|----------------|
| capture-set `ECONNREFUSED` | screenshot-service (Terminal B) pas lancé |
| analyze-raw **401** | `N8N_WEBHOOK_SECRET` différent entre backend `.env` et `$env` de n8n |
| analyze-raw **503** | `ANTHROPIC_API_KEY` absent/invalide dans `backend/.env` |
| Telegram **500** | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` non configurés |
| captures vides / watermark | `TRADINGVIEW_SESSION_ID` non renseigné (Terminal B) |

---

## 3 bis. Terminal C (alternative) — Orchestrateur LOCAL sans n8n ⭐

Si tu ne veux **pas** de n8n, remplace le Terminal C par l'orchestrateur Python
`scripts/ny_morning_prep.py` (stdlib pure, aucune dépendance à installer). Il fait
exactement le même travail que WF6 mais se planifie lui-même :

- déclenche **tous les jours ouvrés à 3h00 Guadeloupe (= 07:00 UTC**, UTC-4 fixe) ;
- pour **USDJPY, CADJPY, XAUUSD, XBRUSD, GBPJPY, EURUSD**, capture les TF `D1/H4/M15/M5`
  via `screenshot-service`, analyse via `/api/vision/analyze-raw` ;
- **sauvegarde chaque rapport** dans `data/ny_reports/<date>/<symbole>.md` (+ `.json`) ;
- envoie sur Telegram (best-effort, ignoré si le bot n'est pas configuré).

```powershell
# le secret est lu automatiquement depuis backend\.env (ou via $env:N8N_WEBHOOK_SECRET)
python scripts\ny_morning_prep.py --daemon      # tourne en continu, se planifie seul
#   ou, en un clic Windows :  scripts\start_ny_prep.bat
```

Tests / usages manuels :

```powershell
python scripts\ny_morning_prep.py --once                 # une passe immédiate (tous les symboles)
python scripts\ny_morning_prep.py --symbol XBRUSD        # un seul symbole
python scripts\ny_morning_prep.py --once --no-telegram   # sans notif Telegram
```

Réglages par variables d'environnement (optionnel) :

| Var | Défaut | Rôle |
|---|---|---|
| `NY_SYMBOLS` | `USDJPY,CADJPY,XAUUSD,XBRUSD,GBPJPY,EURUSD` | Liste des symboles. |
| `NY_TIMEFRAMES` | `D1,H4,M15,M5` | TF capturés (max 6). |
| `NY_RUN_HOUR_UTC` | `7` | Heure UTC du déclenchement (7 = 3h Guadeloupe). |
| `NY_WEEKDAYS_ONLY` | `1` | `0` → passe aussi le week-end (7/7). |
| `NY_MIN_GRADE` | `A` | **Filtre Telegram** : n'envoie que les setups de grade ≥ seuil (`A+` > `A` > `B` > `C` > `D`). `ALL` = tout envoyer. |
| `SCREENSHOT_URL` / `BACKEND_URL` | `localhost:3001` / `:8000` | Cibles des services. |

> **Filtrage** — `NY_MIN_GRADE` ne concerne **que Telegram** : les 6 rapports sont
> **toujours** sauvegardés dans `data/ny_reports/`. Ainsi tu n'es notifié que pour les
> setups de qualité (défaut : grade A+/A) tout en gardant la trace complète en local.
> Un grade non reconnu passe le filtre (fail-open : mieux vaut notifier à tort que rater
> un vrai setup). Exemple — n'alerter que sur les setups parfaits :
> ```powershell
> $env:NY_MIN_GRADE = "A+"
> python scripts\ny_morning_prep.py --daemon
> ```

### Planifier via l'OS plutôt qu'en daemon (mode `--once`)

- **Windows — Planificateur de tâches** : action *Démarrer un programme* →
  `python`, arguments `scripts\ny_morning_prep.py --once`, dossier de départ = racine du repo,
  déclencheur quotidien **07:00 UTC**.
- **Linux/macOS — cron** (heure machine en UTC) :
  ```cron
  0 7 * * 1-5  cd /chemin/vers/saasdrevmbot_v1.01 && python3 scripts/ny_morning_prep.py --once >> data/ny_reports/cron.log 2>&1
  ```

> Le backend (Terminal A) et le screenshot-service (Terminal B) doivent tourner
> quand l'orchestrateur se déclenche.

## 5. Notes

- **Cron WF5** : `25 13 * * 1-5` = 13:25 UTC (open NY été / EDT). En **hiver (EST)** →
  passer à `25 14 * * 1-5` dans le node Schedule Trigger.
- **Ordre de démarrage** : A (backend) → B (screenshot) → C (n8n). n8n en dernier.
- **Docker / VPS** : `vps/docker-compose.yml` reste disponible pour un déploiement conteneurisé ;
  il suffit d'y exporter `BACKEND_URL=http://backend:8000` et `SCREENSHOT_URL=http://screenshot-service:3001`.
  Le même WF5 fonctionne dans les deux mondes.
```
