#!/bin/bash

# Script de création du fichier .env pour SaaS DrevmBot

echo "🔧 Création du fichier .env..."

cat > backend/.env << 'EOF'
# ===================================
# CONFIGURATION SAASDREVMBOT
# ===================================

# Database PostgreSQL
DATABASE_URL=postgresql://drevmbot:drevmbot_password@localhost:5432/drevmbot

# Redis Cache & Queue
REDIS_URL=redis://localhost:6379/0

# ===================================
# NOTIFICATIONS (Optionnel)
# ===================================

# Discord Webhook
# Créer un webhook : Paramètres serveur → Intégrations → Webhooks
DISCORD_WEBHOOK_URL=

# Telegram Bot
# Créer un bot : @BotFather sur Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ===================================
# NEXTCLOUD (Optionnel)
# ===================================

# URL de votre instance Nextcloud
NEXTCLOUD_URL=https://ledream.kflw.io

# Dossier partagé public
NEXTCLOUD_SHARE_FOLDER=/f/33416

# Identifiants Nextcloud (pour upload WebDAV)
# Recommandé : utiliser un mot de passe d'application
NEXTCLOUD_USERNAME=
NEXTCLOUD_PASSWORD=

# ===================================
# PARAMÈTRES ALERTES
# ===================================

# Intervalle de vérification des événements (en secondes)
# 3600 = 1 heure
ALERT_CHECK_INTERVAL=3600

# Envoyer une alerte X heures avant l'événement
ALERT_HOURS_AHEAD=2

# ===================================
# CACHE
# ===================================

# Durée de vie du cache (en secondes)
# 3600 = 1 heure
CACHE_TTL=3600

# ===================================
# API SETTINGS
# ===================================

# Nom du projet
PROJECT_NAME=SaaS DrevmBot

# Préfixe API
API_V1_STR=/api
EOF

echo "✅ Fichier backend/.env créé avec succès !"
echo ""
echo "📝 Prochaines étapes :"
echo "1. Éditer backend/.env et remplir les valeurs manquantes"
echo "2. Configurer Discord Webhook (optionnel)"
echo "3. Configurer Telegram Bot (optionnel)"
echo "4. Configurer Nextcloud (optionnel)"
echo ""
echo "Pour Docker, modifier les URLs :"
echo "  DATABASE_URL=postgresql://drevmbot:drevmbot_password@postgres:5432/drevmbot"
echo "  REDIS_URL=redis://redis:6379/0"
