#!/bin/bash
# SessionStart hook — saasDrevmBot
# Installe les dépendances des 3 services (Node.js, Python, SvelteKit)
# pour que tests et linters fonctionnent dans Claude Code sur le web.
set -euo pipefail

# Ne s'exécute que dans l'environnement distant (Claude Code sur le web)
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

echo "==> [1/4] Node.js — dépendances racine (GoldyXbOT)"
npm install --no-audit --no-fund

echo "==> [2/4] Node.js — dépendances frontend (SvelteKit)"
npm install --no-audit --no-fund --prefix frontend

echo "==> [3/4] Python — backend FastAPI"
pip3 install --break-system-packages --quiet -r backend/requirements.txt

echo "==> [4/4] Python — interface session NY"
pip3 install --break-system-packages --quiet -r ny_session_interface/requirements.txt

echo "==> Dépendances installées avec succès."
