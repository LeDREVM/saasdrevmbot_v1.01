# 🐳 Guide de Déploiement Docker

## Repository Docker Hub

**Username**: `ledrevm`  
**Image**: `goldyxrodgersbot`  
**URL**: https://hub.docker.com/r/ledrevm/goldyxrodgersbot

---

## 📦 Build et Push vers Docker Hub

### Prérequis

1. **Compte Docker Hub**
   - Créer un compte sur https://hub.docker.com
   - Username: `ledrevm`

2. **Docker installé**
   ```bash
   docker --version
   ```

3. **Connexion Docker Hub**
   ```bash
   docker login
   # Username: ledrevm
   # Password: [votre mot de passe]
   ```

### Build et Push Automatique

#### Windows
```bash
# Exécuter le script
.\docker-build-push.bat
```

#### Linux/Mac
```bash
# Rendre le script exécutable
chmod +x docker-build-push.sh

# Exécuter
./docker-build-push.sh
```

### Build et Push Manuel

#### Backend
```bash
# Build
docker build -t ledrevm/goldyxrodgersbot:backend-1.0.0 ./backend
docker tag ledrevm/goldyxrodgersbot:backend-1.0.0 ledrevm/goldyxrodgersbot:backend-latest

# Push
docker push ledrevm/goldyxrodgersbot:backend-1.0.0
docker push ledrevm/goldyxrodgersbot:backend-latest
```

#### Frontend
```bash
# Build
docker build -t ledrevm/goldyxrodgersbot:frontend-1.0.0 ./frontend
docker tag ledrevm/goldyxrodgersbot:frontend-1.0.0 ledrevm/goldyxrodgersbot:frontend-latest

# Push
docker push ledrevm/goldyxrodgersbot:frontend-1.0.0
docker push ledrevm/goldyxrodgersbot:frontend-latest
```

---

## 🚀 Déploiement en Production

### Option 1 : Docker Compose (Recommandé)

1. **Créer un fichier `.env`**
```bash
# Copier le template
cp backend/env.template .env

# Éditer avec vos configurations
nano .env
```

2. **Variables d'environnement requises**
```env
# Database
POSTGRES_USER=drevmbot
POSTGRES_PASSWORD=votre_mot_de_passe_fort
POSTGRES_DB=drevmbot

# Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_CHAT_ID=123456789

# Nextcloud
NEXTCLOUD_URL=https://ledream.kflw.io
NEXTCLOUD_SHARE_FOLDER=/f/33416
NEXTCLOUD_USERNAME=votre_username
NEXTCLOUD_PASSWORD=votre_app_password
```

3. **Lancer avec Docker Compose**
```bash
# Télécharger les images et démarrer
docker-compose -f docker-compose.prod.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.prod.yml logs -f

# Vérifier le statut
docker-compose -f docker-compose.prod.yml ps
```

### Option 2 : Docker Run Manuel

#### PostgreSQL
```bash
docker run -d \
  --name goldyxrodgers-postgres \
  -e POSTGRES_USER=drevmbot \
  -e POSTGRES_PASSWORD=votre_password \
  -e POSTGRES_DB=drevmbot \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine
```

#### Redis
```bash
docker run -d \
  --name goldyxrodgers-redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine
```

#### Backend
```bash
docker run -d \
  --name goldyxrodgers-backend \
  -e DATABASE_URL=postgresql://drevmbot:password@postgres:5432/drevmbot \
  -e REDIS_URL=redis://redis:6379/0 \
  -e DISCORD_WEBHOOK_URL=https://... \
  -p 8000:8000 \
  --link goldyxrodgers-postgres:postgres \
  --link goldyxrodgers-redis:redis \
  ledrevm/goldyxrodgersbot:backend-latest
```

#### Frontend
```bash
docker run -d \
  --name goldyxrodgers-frontend \
  -p 5173:5173 \
  --link goldyxrodgers-backend:backend \
  ledrevm/goldyxrodgersbot:frontend-latest
```

---

## 🔄 Mise à Jour

### Mettre à jour les images

```bash
# Pull les dernières versions
docker-compose -f docker-compose.prod.yml pull

# Redémarrer les services
docker-compose -f docker-compose.prod.yml up -d

# Ou en une commande
docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d
```

### Rollback vers une version précédente

```bash
# Modifier docker-compose.prod.yml
# Changer :latest en :1.0.0 (par exemple)

# Redémarrer
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📊 Monitoring

### Vérifier les logs

```bash
# Tous les services
docker-compose -f docker-compose.prod.yml logs -f

# Service spécifique
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### Vérifier le statut

```bash
# Statut des conteneurs
docker-compose -f docker-compose.prod.yml ps

# Utilisation des ressources
docker stats

# Santé des services
docker-compose -f docker-compose.prod.yml exec backend curl http://localhost:8000/health
```

---

## 🔒 Sécurité Production

### 1. Variables d'environnement

⚠️ **Ne JAMAIS commiter le fichier `.env`**

```bash
# Créer un .env sécurisé
touch .env
chmod 600 .env
```

### 2. Mots de passe forts

```bash
# Générer un mot de passe fort
openssl rand -base64 32
```

### 3. Restreindre les ports

```yaml
# Dans docker-compose.prod.yml
ports:
  - "127.0.0.1:5432:5432"  # PostgreSQL accessible uniquement en local
  - "127.0.0.1:6379:6379"  # Redis accessible uniquement en local
```

### 4. Utiliser un reverse proxy

```bash
# Installer Nginx
sudo apt install nginx

# Configurer pour le frontend et backend
# Activer HTTPS avec Let's Encrypt
```

### 5. Backups automatiques

```bash
# Script de backup PostgreSQL
docker exec goldyxrodgers-postgres pg_dump -U drevmbot drevmbot > backup_$(date +%Y%m%d).sql
```

---

## 🌐 Déploiement sur un VPS

### Prérequis VPS

- Ubuntu 22.04 LTS (recommandé)
- 2 GB RAM minimum
- 20 GB stockage
- Docker et Docker Compose installés

### Installation Docker

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo apt install docker-compose-plugin

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
```

### Déploiement

```bash
# Cloner le projet (ou juste le docker-compose.prod.yml)
git clone https://github.com/votre-repo/goldyxrodgersbot.git
cd goldyxrodgersbot

# Créer le fichier .env
nano .env
# (Copier les variables d'environnement)

# Lancer
docker-compose -f docker-compose.prod.yml up -d

# Vérifier
docker-compose -f docker-compose.prod.yml ps
```

### Configuration Nginx (optionnel)

```nginx
# /etc/nginx/sites-available/goldyxrodgers

server {
    listen 80;
    server_name votre-domaine.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🧪 Tests

### Test de l'API

```bash
# Health check
curl http://localhost:8000/health

# Calendrier
curl http://localhost:8000/api/calendar/today

# Nextcloud status
curl http://localhost:8000/api/nextcloud/status
```

### Test du Frontend

```bash
# Ouvrir dans le navigateur
http://localhost:5173
```

---

## 📝 Commandes Utiles

### Gestion des conteneurs

```bash
# Démarrer
docker-compose -f docker-compose.prod.yml up -d

# Arrêter
docker-compose -f docker-compose.prod.yml down

# Redémarrer
docker-compose -f docker-compose.prod.yml restart

# Supprimer tout (⚠️ données incluses)
docker-compose -f docker-compose.prod.yml down -v
```

### Nettoyage

```bash
# Supprimer les images non utilisées
docker image prune -a

# Supprimer les volumes non utilisés
docker volume prune

# Nettoyage complet
docker system prune -a --volumes
```

### Accès aux conteneurs

```bash
# Shell dans le backend
docker-compose -f docker-compose.prod.yml exec backend bash

# Shell dans PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U drevmbot -d drevmbot

# Shell dans Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli
```

---

## 🆘 Troubleshooting

### Erreur de connexion DB

```bash
# Vérifier que PostgreSQL est démarré
docker-compose -f docker-compose.prod.yml ps postgres

# Vérifier les logs
docker-compose -f docker-compose.prod.yml logs postgres

# Tester la connexion
docker-compose -f docker-compose.prod.yml exec postgres psql -U drevmbot -d drevmbot
```

### Erreur de connexion Redis

```bash
# Vérifier Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Images non trouvées

```bash
# Pull manuellement
docker pull ledrevm/goldyxrodgersbot:backend-latest
docker pull ledrevm/goldyxrodgersbot:frontend-latest
```

---

## 📚 Ressources

- **Docker Hub** : https://hub.docker.com/r/ledrevm/goldyxrodgersbot
- **Documentation Docker** : https://docs.docker.com
- **Docker Compose** : https://docs.docker.com/compose/

---

**Version** : 1.0.0  
**Repository** : ledrevm/goldyxrodgersbot  
**Dernière mise à jour** : 6 février 2026
