#!/usr/bin/env bash
# =============================================================================
#  setup-vps-linux.sh  —  Déploiement VPS Linux (Ubuntu/Debian)
#  Installe et lance en services systemd :
#    • GoldyXbOT (dashboard Node)        → port 3000
#    • Console NY Session Bot (FastAPI)  → port 8800 (SIMULATION, pas de MT5)
#
#  Usage (root) :   sudo bash deploy/setup-vps-linux.sh
#  Variables :      BRANCH=...  APP_DIR=...  RUN_USER=...
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/LeDREVM/saasdrevmbot_v1.01.git"
BRANCH="${BRANCH:-claude/trading-session-performance-6Ex86}"
APP_DIR="${APP_DIR:-/opt/goldyxbotdrevm}"
RUN_USER="${RUN_USER:-${SUDO_USER:-root}}"

log() { printf "\n\033[1;36m▶ %s\033[0m\n" "$1"; }

[ "$(id -u)" -eq 0 ] || { echo "Lance avec sudo : sudo bash $0"; exit 1; }

log "Paquets système"
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv curl ca-certificates

log "Node.js 20 LTS"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | sed 's/v//;s/\..*//')" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

log "Clone / mise à jour ($BRANCH) dans $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull origin "$BRANCH"
else
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR"

log "Dépendances Node (dashboard GoldyXbOT)"
sudo -u "$RUN_USER" bash -c "cd '$APP_DIR' && npm install --omit=dev"
[ -f "$APP_DIR/.env" ] || sudo -u "$RUN_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"

log "Environnement Python (console NY Session)"
sudo -u "$RUN_USER" python3 -m venv "$APP_DIR/ny_session_interface/.venv"
VENV_PIP="$APP_DIR/ny_session_interface/.venv/bin/pip"
sudo -u "$RUN_USER" "$VENV_PIP" install --upgrade pip
sudo -u "$RUN_USER" "$VENV_PIP" install fastapi "uvicorn[standard]" pandas numpy

log "Installation des services systemd"
for unit in goldyxbot ny-console; do
  sed -e "s#__APP_DIR__#$APP_DIR#g" -e "s#__USER__#$RUN_USER#g" \
      "$APP_DIR/deploy/$unit.service" > "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
systemctl enable --now goldyxbot.service ny-console.service

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
cat <<EOF

✅ Déploiement terminé.
   Dashboard GoldyXbOT : http://${IP:-<IP_VPS>}:3000   (ouvre le port 3000 au pare-feu)
   Console NY Session  : http://127.0.0.1:8800         (localhost — voir sécurité)

📋 Commandes utiles :
   systemctl status goldyxbot ny-console
   journalctl -u goldyxbot -f
   journalctl -u ny-console -f
   systemctl restart ny-console      # après un git pull

🔒 Sécurité console (port 8800) :
   Elle reste en localhost. Pour y accéder depuis ton PC :
      ssh -L 8800:127.0.0.1:8800 ${RUN_USER}@${IP:-<IP_VPS>}
   puis ouvre http://127.0.0.1:8800 sur ton PC.
   (Sur Linux, pas de MT5 → la console tourne en SIMULATION, aucun ordre réel.)

ℹ️  Pour le calendrier économique Discord : édite $APP_DIR/.env (DISCORD_WEBHOOK_URL)
    puis : systemctl restart goldyxbot
EOF
