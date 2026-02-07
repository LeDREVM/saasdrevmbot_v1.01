# ⚙️ Guide de Configuration

## Création du fichier .env

### Windows
```bash
# Double-cliquer sur le fichier ou exécuter :
create_env.bat
```

### Linux/Mac
```bash
chmod +x create_env.sh
./create_env.sh
```

### Manuellement
```bash
# Copier le template
cp backend/env.template backend/.env

# Éditer avec votre éditeur préféré
nano backend/.env
# ou
code backend/.env
```

## Configuration Minimale (Développement Local)

Pour démarrer rapidement en local, seules ces variables sont nécessaires :

```env
# Base de données (PostgreSQL local)
DATABASE_URL=postgresql://drevmbot:drevmbot_password@localhost:5432/drevmbot

# Cache (Redis local)
REDIS_URL=redis://localhost:6379/0
```

Le reste est optionnel !

## Configuration avec Docker

Si vous utilisez Docker Compose, modifiez les URLs pour utiliser les noms de services :

```env
# Base de données (conteneur Docker)
DATABASE_URL=postgresql://drevmbot:drevmbot_password@postgres:5432/drevmbot

# Cache (conteneur Docker)
REDIS_URL=redis://redis:6379/0
```

## Configuration des Notifications (Optionnel)

### Discord

1. **Créer un Webhook Discord** :
   - Ouvrir Discord
   - Aller dans les paramètres du serveur
   - Intégrations → Webhooks
   - Cliquer sur "Nouveau Webhook"
   - Personnaliser le nom et l'avatar
   - Copier l'URL du webhook

2. **Ajouter dans .env** :
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop
```

### Telegram

1. **Créer un Bot Telegram** :
   - Ouvrir Telegram
   - Chercher @BotFather
   - Envoyer `/newbot`
   - Suivre les instructions
   - Copier le token fourni

2. **Obtenir votre Chat ID** :
   - Chercher @userinfobot sur Telegram
   - Envoyer `/start`
   - Copier votre ID

3. **Ajouter dans .env** :
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## Configuration Nextcloud (Optionnel)

### URL déjà configurée

Votre instance Nextcloud est déjà configurée :
```env
NEXTCLOUD_URL=https://ledream.kflw.io
NEXTCLOUD_SHARE_FOLDER=/f/33416
```

### Identifiants requis

Pour uploader automatiquement les rapports :

1. **Créer un mot de passe d'application** :
   - Se connecter à Nextcloud
   - Paramètres → Sécurité
   - Créer un nouveau mot de passe d'application
   - Nommer : "DrevmBot"
   - Copier le mot de passe généré

2. **Ajouter dans .env** :
```env
NEXTCLOUD_USERNAME=votre_username
NEXTCLOUD_PASSWORD=xxxx-xxxx-xxxx-xxxx-xxxx
```

⚠️ **Important** : Utiliser un mot de passe d'application, pas votre mot de passe principal !

## Paramètres Avancés

### Alertes

```env
# Vérifier les événements toutes les heures
ALERT_CHECK_INTERVAL=3600

# Alerter 2 heures avant l'événement
ALERT_HOURS_AHEAD=2
```

Pour des alertes plus fréquentes :
```env
# Vérifier toutes les 30 minutes
ALERT_CHECK_INTERVAL=1800

# Alerter 4 heures avant
ALERT_HOURS_AHEAD=4
```

### Cache

```env
# Cache valide pendant 1 heure
CACHE_TTL=3600
```

Pour un cache plus long (moins de requêtes API) :
```env
# Cache valide pendant 2 heures
CACHE_TTL=7200
```

## Vérification de la Configuration

### Test de connexion PostgreSQL
```bash
# Depuis le conteneur Docker
docker-compose exec postgres psql -U drevmbot -d drevmbot

# Localement
psql postgresql://drevmbot:drevmbot_password@localhost:5432/drevmbot
```

### Test de connexion Redis
```bash
# Depuis le conteneur Docker
docker-compose exec redis redis-cli ping

# Localement
redis-cli ping
```

### Test Discord Webhook
```bash
curl -X POST "VOTRE_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test depuis DrevmBot !"}'
```

### Test Telegram Bot
```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

### Test Nextcloud
```bash
curl -u username:password \
  "https://ledream.kflw.io/remote.php/dav/files/username/"
```

## Exemple Complet

Voici un exemple de fichier `.env` complet et fonctionnel :

```env
# Database
DATABASE_URL=postgresql://drevmbot:drevmbot_password@postgres:5432/drevmbot

# Redis
REDIS_URL=redis://redis:6379/0

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Nextcloud
NEXTCLOUD_URL=https://ledream.kflw.io
NEXTCLOUD_SHARE_FOLDER=/f/33416
NEXTCLOUD_USERNAME=john_doe
NEXTCLOUD_PASSWORD=xxxx-xxxx-xxxx-xxxx-xxxx

# Alertes
ALERT_CHECK_INTERVAL=3600
ALERT_HOURS_AHEAD=2

# Cache
CACHE_TTL=3600

# API
PROJECT_NAME=SaaS DrevmBot
API_V1_STR=/api
```

## Sécurité

### ⚠️ Important

1. **Ne JAMAIS commiter le fichier .env**
   - Il est déjà dans `.gitignore`
   - Contient des secrets sensibles

2. **Utiliser des mots de passe forts**
   - Générer avec un gestionnaire de mots de passe
   - Minimum 16 caractères

3. **Mots de passe d'application**
   - Pour Nextcloud : utiliser un mot de passe d'application
   - Pour Telegram : le token du bot est déjà sécurisé

4. **Permissions minimales**
   - Le compte Nextcloud doit seulement pouvoir écrire dans `ForexBot/reports/`
   - Le bot Telegram n'a besoin que d'envoyer des messages

### Production

Pour la production, ajouter :

```env
# HTTPS obligatoire
FORCE_HTTPS=true

# CORS restreint
ALLOWED_ORIGINS=https://votre-domaine.com

# Logs détaillés
LOG_LEVEL=INFO

# Backups automatiques
BACKUP_ENABLED=true
BACKUP_INTERVAL=86400
```

## Troubleshooting

### Erreur "DATABASE_URL not found"
- Vérifier que le fichier `.env` est dans `backend/`
- Vérifier qu'il n'y a pas d'espaces autour du `=`

### Erreur de connexion PostgreSQL
- Vérifier que PostgreSQL est démarré
- Vérifier le port (5432 par défaut)
- Tester la connexion manuellement

### Erreur de connexion Redis
- Vérifier que Redis est démarré
- Vérifier le port (6379 par défaut)
- Tester avec `redis-cli ping`

### Discord Webhook ne fonctionne pas
- Vérifier que l'URL est complète
- Tester avec curl
- Vérifier les permissions du webhook

### Telegram Bot ne répond pas
- Vérifier le token avec `/getMe`
- Vérifier que le chat_id est correct
- Démarrer une conversation avec le bot

### Nextcloud upload échoue
- Vérifier les identifiants
- Vérifier que le dossier existe
- Tester manuellement avec curl

## Ressources

- [Documentation PostgreSQL](https://www.postgresql.org/docs/)
- [Documentation Redis](https://redis.io/docs/)
- [Discord Webhooks](https://discord.com/developers/docs/resources/webhook)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Nextcloud WebDAV](https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html)

---

**Besoin d'aide ?** Consultez [QUICKSTART.md](QUICKSTART.md) ou [README.md](README.md)
