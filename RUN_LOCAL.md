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

## 5. Notes

- **Cron WF5** : `25 13 * * 1-5` = 13:25 UTC (open NY été / EDT). En **hiver (EST)** →
  passer à `25 14 * * 1-5` dans le node Schedule Trigger.
- **Ordre de démarrage** : A (backend) → B (screenshot) → C (n8n). n8n en dernier.
- **Docker / VPS** : `vps/docker-compose.yml` reste disponible pour un déploiement conteneurisé ;
  il suffit d'y exporter `BACKEND_URL=http://backend:8000` et `SCREENSHOT_URL=http://screenshot-service:3001`.
  Le même WF5 fonctionne dans les deux mondes.
```
