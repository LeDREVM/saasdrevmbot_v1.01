@echo off
REM Script de création du fichier .env pour SaaS DrevmBot (Windows)

echo 🔧 Création du fichier .env...

(
echo # ===================================
echo # CONFIGURATION SAASDREVMBOT
echo # ===================================
echo.
echo # Database PostgreSQL
echo DATABASE_URL=postgresql://drevmbot:drevmbot_password@localhost:5432/drevmbot
echo.
echo # Redis Cache ^& Queue
echo REDIS_URL=redis://localhost:6379/0
echo.
echo # ===================================
echo # NOTIFICATIONS ^(Optionnel^)
echo # ===================================
echo.
echo # Discord Webhook
echo # Créer un webhook : Paramètres serveur -^> Intégrations -^> Webhooks
echo DISCORD_WEBHOOK_URL=
echo.
echo # Telegram Bot
echo # Créer un bot : @BotFather sur Telegram
echo TELEGRAM_BOT_TOKEN=
echo TELEGRAM_CHAT_ID=
echo.
echo # ===================================
echo # NEXTCLOUD ^(Optionnel^)
echo # ===================================
echo.
echo # URL de votre instance Nextcloud
echo NEXTCLOUD_URL=https://ledream.kflw.io
echo.
echo # Dossier partagé public
echo NEXTCLOUD_SHARE_FOLDER=/f/33416
echo.
echo # Identifiants Nextcloud ^(pour upload WebDAV^)
echo # Recommandé : utiliser un mot de passe d'application
echo NEXTCLOUD_USERNAME=
echo NEXTCLOUD_PASSWORD=
echo.
echo # ===================================
echo # PARAMÈTRES ALERTES
echo # ===================================
echo.
echo # Intervalle de vérification des événements ^(en secondes^)
echo # 3600 = 1 heure
echo ALERT_CHECK_INTERVAL=3600
echo.
echo # Envoyer une alerte X heures avant l'événement
echo ALERT_HOURS_AHEAD=2
echo.
echo # ===================================
echo # CACHE
echo # ===================================
echo.
echo # Durée de vie du cache ^(en secondes^)
echo # 3600 = 1 heure
echo CACHE_TTL=3600
echo.
echo # ===================================
echo # API SETTINGS
echo # ===================================
echo.
echo # Nom du projet
echo PROJECT_NAME=SaaS DrevmBot
echo.
echo # Préfixe API
echo API_V1_STR=/api
) > backend\.env

echo.
echo ✅ Fichier backend\.env créé avec succès !
echo.
echo 📝 Prochaines étapes :
echo 1. Éditer backend\.env et remplir les valeurs manquantes
echo 2. Configurer Discord Webhook ^(optionnel^)
echo 3. Configurer Telegram Bot ^(optionnel^)
echo 4. Configurer Nextcloud ^(optionnel^)
echo.
echo Pour Docker, modifier les URLs :
echo   DATABASE_URL=postgresql://drevmbot:drevmbot_password@postgres:5432/drevmbot
echo   REDIS_URL=redis://redis:6379/0
echo.
pause
