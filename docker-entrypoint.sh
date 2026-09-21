#!/bin/sh
# ============================================================
# Entrypoint hub Express — seed du volume persistant data/
# Si le volume monté sur /app/data est vierge (premier démarrage), on y copie
# les données seed embarquées dans l'image (events_log.json, calendar/…).
# Idempotent : ne réécrit jamais un fichier déjà présent (cp -n).
# ============================================================
set -e

mkdir -p /app/data

if [ ! -f /app/data/events_log.json ] && [ -d /app/data-seed ]; then
  cp -rn /app/data-seed/. /app/data/ 2>/dev/null || true
  echo "[entrypoint] data/ initialisé depuis le seed de l'image"
fi

exec "$@"
