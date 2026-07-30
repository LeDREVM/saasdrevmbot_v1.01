#!/bin/bash
# ===========================================================================
#  start-all.sh  -  Démarre les 2 backends de saasDrevmBot (Linux / macOS / VPS)
#    - Express "GoldyXbOT"    -> http://localhost:3000  (dashboard corrélation)
#    - FastAPI "saasDrevmbot" -> http://localhost:8000  (alertes, scoring, config)
#  Ctrl+C arrête les deux serveurs.
# ===========================================================================
set -e
cd "$(dirname "$0")/.."

echo "==========================================================="
echo "  saasDrevmBot - Démarrage des backends"
echo "==========================================================="

# --- 1) Backend Express (port 3000) ---------------------------------------
if [ ! -d node_modules ]; then
  echo "[deps] Installation npm..."
  npm install --no-audit --no-fund
fi
echo "[1/2] Express GoldyXbOT -> :3000"
npm start &
EXPRESS_PID=$!

# --- 2) Backend FastAPI (port 8000) ---------------------------------------
cd backend
if [ ! -d .venv ]; then
  echo "[deps] Création venv + installation Python (1-2 min)..."
  python3 -m venv .venv
  ./.venv/bin/pip install -r requirements.txt
fi
echo "[2/2] FastAPI saasDrevmbot -> :8000"
./.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!
cd ..

echo ""
echo "  Dashboard Express : http://localhost:3000"
echo "  API FastAPI       : http://localhost:8000/api/docs"
echo "  Ctrl+C pour tout arrêter."

# Arrêt propre des deux process
trap "kill $EXPRESS_PID $FASTAPI_PID 2>/dev/null" INT TERM
wait
