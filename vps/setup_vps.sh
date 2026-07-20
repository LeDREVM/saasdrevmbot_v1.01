#!/bin/bash
# ============================================================
# Setup VPS Hostinger — Ubuntu 22.04
# Lance en root : bash setup_vps.sh
# ============================================================
set -e

echo "=== [1/5] Mise à jour système ==="
apt update && apt upgrade -y

echo "=== [2/5] Installation Docker ==="
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

echo "=== [3/5] Installation Docker Compose ==="
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
     -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo "=== [4/5] Ouverture des ports firewall ==="
ufw allow 22     # SSH
ufw allow 5678   # n8n interface
ufw allow 5001   # MT5 bridge TCP
ufw --force enable

echo "=== [5/5] Clone du projet ==="
if [ ! -d "/opt/saasdrevmbot" ]; then
  git clone https://github.com/ledrevm/saasdrevmbot_v1.01.git /opt/saasdrevmbot
fi

cd /opt/saasdrevmbot/vps

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  IMPORTANT : Edite /opt/saasdrevmbot/vps/.env avec tes vraies clés API"
  echo "   nano /opt/saasdrevmbot/vps/.env"
  echo ""
fi

echo "=== Démarrage des services ==="
docker-compose up -d --build

echo ""
echo "✅ Installation terminée !"
echo "   n8n:             http://$(curl -s ifconfig.me):5678"
echo "   Signal server:   port 5000 (interne)"
echo "   MT5 bridge:      port 5001 (TCP, configurer dans l'EA)"
echo ""
echo "Prochaines étapes :"
echo "  1. Editer .env avec les vraies valeurs"
echo "  2. Ouvrir n8n et importer n8n/tradingview_ai_workflow.json"
echo "  3. Configurer les credentials Supabase et Anthropic dans n8n"
echo "  4. Copier metatrader/ea/AISignalReceiver.mq5 dans MT5"
echo "  5. Créer l'alerte TradingView → webhook n8n"
