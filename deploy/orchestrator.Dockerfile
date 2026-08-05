# ============================================================
# Orchestrateur prep session NY — daemon Python (stdlib pure)
# Déclenche tous les jours ouvrés à 07:00 UTC (3h Guadeloupe) :
# capture multi-TF → analyse vision → Telegram + récap.
# Aucune dépendance pip (urllib/json/datetime uniquement).
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Seul le script est nécessaire (REPO_ROOT = /app → data/ny_reports sous /app/data).
COPY scripts/ny_morning_prep.py scripts/ny_morning_prep.py

# Config par défaut (surchargée par docker-compose / env) :
#   BACKEND_URL, SCREENSHOT_URL, N8N_WEBHOOK_SECRET, NY_MIN_GRADE, NY_NEWS_BLACKOUT…
ENV NY_RUN_HOUR_UTC=7

CMD ["python", "scripts/ny_morning_prep.py", "--daemon"]
