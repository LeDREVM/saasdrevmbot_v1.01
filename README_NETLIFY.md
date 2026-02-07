# 🚀 SaaS DrevmBot - Déployé sur Netlify

[![Netlify Status](https://api.netlify.com/api/v1/badges/YOUR-BADGE-ID/deploy-status)](https://app.netlify.com/sites/saasdrevmbot/deploys)

**Site en production**: https://saasdrevmbot.netlify.app/

---

## 📋 À Propos

**SaaS DrevmBot** est un système d'alertes intelligent pour le trading Forex qui analyse automatiquement le calendrier économique et envoie des notifications prédictives basées sur l'IA.

### 🎯 Fonctionnalités Principales

- 📅 **Calendrier Économique** - Événements en temps réel de ForexFactory et Investing.com
- 🔔 **Alertes Intelligentes** - Notifications prédictives sur Discord et Telegram
- 📊 **Analyse Statistique** - Corrélation et impact des événements économiques
- ☁️ **Synchronisation Nextcloud** - Sauvegarde automatique des rapports
- 🎨 **Interface Moderne** - UI responsive avec SvelteKit

---

## 🛠️ Stack Technique

### Frontend (Déployé sur Netlify)
- **Framework**: SvelteKit
- **Build Tool**: Vite
- **Styling**: CSS personnalisé
- **Hosting**: Netlify

### Backend (À déployer séparément)
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Tasks**: Celery
- **Storage**: Nextcloud (WebDAV)

---

## 🚀 Déploiement Netlify

### Configuration Automatique

Le site est configuré pour se déployer automatiquement via `netlify.toml`:

```toml
[build]
  command = "npm run build"
  publish = "build"
  base = "frontend"

[build.environment]
  NODE_VERSION = "20"
```

### Variables d'Environnement

Configurez dans **Netlify Dashboard** → **Site settings** → **Environment variables**:

| Variable | Description | Exemple |
|----------|-------------|---------|
| `VITE_API_URL` | URL de l'API Backend | `https://api.drevmbot.com` |

### Déploiement Manuel

```bash
# 1. Installer les dépendances
cd frontend
npm install

# 2. Build de production
npm run build

# 3. Déployer via Netlify CLI
netlify deploy --prod
```

---

## 🔧 Configuration Backend

Le frontend nécessite un backend FastAPI déployé. Options recommandées:

### Option 1: Railway.app
```bash
railway login
railway init
railway up
```

### Option 2: Render.com
1. Connecter le repository GitHub
2. Créer un nouveau Web Service
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option 3: Docker (VPS)
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📊 Performances

- ⚡ **Lighthouse Score**: 95+
- 🚀 **First Contentful Paint**: < 1.5s
- 📦 **Bundle Size**: < 200KB
- 🌍 **CDN**: Netlify Edge Network

---

## 🔐 Sécurité

### Headers Configurés
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### HTTPS
- ✅ Certificat SSL automatique (Let's Encrypt)
- ✅ Redirection HTTP → HTTPS
- ✅ HSTS activé

---

## 📱 Responsive Design

Le site est optimisé pour:
- 📱 Mobile (320px+)
- 📱 Tablet (768px+)
- 💻 Desktop (1024px+)
- 🖥️ Large Desktop (1440px+)

---

## 🧪 Tests Locaux

```bash
# Installer les dépendances
cd frontend
npm install

# Créer le fichier .env
cp env.template .env
# Éditer .env avec votre API URL

# Lancer en mode dev
npm run dev

# Build de production
npm run build

# Prévisualiser le build
npm run preview
```

---

## 📚 Documentation

- **Guide de Déploiement**: [NETLIFY_DEPLOYMENT_GUIDE.md](./NETLIFY_DEPLOYMENT_GUIDE.md)
- **API Documentation**: https://saasdrevmbot.netlify.app/api/docs (si backend déployé)
- **Nextcloud Setup**: [NEXTCLOUD_QUICKSTART.md](./NEXTCLOUD_QUICKSTART.md)
- **Telegram Setup**: [TELEGRAM_SETUP_GUIDE.md](./TELEGRAM_SETUP_GUIDE.md)
- **Discord Setup**: [DISCORD_SETUP_GUIDE.md](./DISCORD_SETUP_GUIDE.md)

---

## 🐛 Dépannage

### Le site ne charge pas l'API

**Problème**: Les appels API échouent avec des erreurs CORS

**Solution**:
1. Vérifier que `VITE_API_URL` est configuré dans Netlify
2. Vérifier que le backend est déployé et accessible
3. Vérifier la configuration CORS du backend:

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://saasdrevmbot.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Build Failed sur Netlify

**Problème**: Le build échoue avec une erreur de dépendances

**Solution**:
1. Vérifier `frontend/package.json`
2. Tester le build localement: `npm run build`
3. Vérifier les logs dans Netlify Dashboard

### 404 sur les routes

**Problème**: Les routes SvelteKit retournent 404

**Solution**: Vérifier la configuration de redirection dans `netlify.toml`:
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## 🔄 CI/CD

### Déploiements Automatiques

- ✅ **Production**: Push sur `main` → Déploiement automatique
- ✅ **Preview**: Pull Request → Deploy Preview unique
- ✅ **Branches**: Toutes les branches → Deploy Preview

### Notifications

Configurez les notifications dans **Netlify Dashboard**:
- 📧 Email sur échec de build
- 💬 Slack/Discord webhooks
- 🔔 GitHub status checks

---

## 📈 Analytics

### Netlify Analytics (Optionnel - $9/mois)
- Trafic en temps réel
- Pages vues
- Sources de trafic
- Pas de cookies, conforme RGPD

### Alternative Gratuite: Plausible.io
```html
<!-- frontend/src/app.html -->
<script defer data-domain="saasdrevmbot.netlify.app" 
        src="https://plausible.io/js/script.js"></script>
```

---

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créer une branche: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Ouvrir une Pull Request

---

## 📝 Changelog

### v2.0.0 (06/02/2026)
- ✨ Nouvelle page d'accueil moderne
- 🚀 Déploiement sur Netlify
- 📊 Composant Timeline
- 🔔 Tests Discord et Telegram
- ☁️ Intégration Nextcloud

### v1.0.0 (01/02/2026)
- 🎉 Version initiale
- 📅 Calendrier économique
- 📊 Statistiques
- 🔔 Alertes de base

---

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](./LICENSE) pour plus de détails.

---

## 👥 Auteurs

- **DrevmBot Team** - *Développement initial*

---

## 🙏 Remerciements

- [Netlify](https://netlify.com) pour l'hébergement
- [SvelteKit](https://kit.svelte.dev) pour le framework
- [FastAPI](https://fastapi.tiangolo.com) pour l'API
- [ForexFactory](https://www.forexfactory.com) pour les données
- [Investing.com](https://www.investing.com) pour les données

---

## 🔗 Liens Utiles

- 🌐 **Site Web**: https://saasdrevmbot.netlify.app/
- 📚 **Documentation**: https://saasdrevmbot.netlify.app/api/docs
- 💻 **GitHub**: https://github.com/yourusername/saasDrevmbot
- 💬 **Support**: [Ouvrir une issue](https://github.com/yourusername/saasDrevmbot/issues)

---

**Déployé avec ❤️ sur Netlify**
