# 🚀 Guide de Déploiement Netlify - SaaS DrevmBot

**Site**: https://vocal-belekoy-c953e0.netlify.app/  
**Date**: 06/02/2026  
**Status**: 📝 **Prêt pour le déploiement**

---

## 📋 Prérequis

- [x] Compte Netlify (gratuit)
- [x] Repository Git (GitHub, GitLab, ou Bitbucket)
- [x] Code frontend dans le dossier `frontend/`
- [x] `netlify.toml` configuré
- [x] Build testé localement

---

## 🎯 Méthode 1: Déploiement via Git (Recommandé)

### Étape 1: Préparer le Repository

```bash
# Initialiser Git (si pas déjà fait)
git init

# Ajouter tous les fichiers
git add .

# Commit
git commit -m "feat: prepare for Netlify deployment"

# Ajouter le remote (GitHub/GitLab)
git remote add origin https://github.com/votre-username/saasDrevmbot.git

# Push
git push -u origin main
```

### Étape 2: Connecter à Netlify

1. **Se connecter** à https://app.netlify.com/
2. **Cliquer** sur "Add new site" → "Import an existing project"
3. **Choisir** votre provider Git (GitHub/GitLab/Bitbucket)
4. **Autoriser** Netlify à accéder à vos repos
5. **Sélectionner** le repository `saasDrevmbot`

### Étape 3: Configurer le Build

Netlify devrait détecter automatiquement la configuration depuis `netlify.toml`:

```
Base directory: frontend
Build command: npm run build
Publish directory: frontend/build
```

Si ce n'est pas le cas, entrer manuellement ces valeurs.

### Étape 4: Variables d'Environnement

1. **Aller** dans "Site settings" → "Environment variables"
2. **Ajouter** la variable:
   ```
   Key: VITE_API_URL
   Value: https://your-backend-api.com
   ```

### Étape 5: Déployer

1. **Cliquer** sur "Deploy site"
2. **Attendre** la fin du build (2-5 minutes)
3. **Vérifier** le site sur l'URL fournie

---

## 🎯 Méthode 2: Déploiement Manuel (Drag & Drop)

### Étape 1: Build Local

```bash
cd frontend
npm install
npm run build
```

Cela crée un dossier `frontend/build/` avec les fichiers statiques.

### Étape 2: Déployer sur Netlify

1. **Se connecter** à https://app.netlify.com/
2. **Glisser-déposer** le dossier `frontend/build/` sur la zone de drop
3. **Attendre** le déploiement (quelques secondes)

**⚠️ Note**: Cette méthode ne permet pas les déploiements automatiques.

---

## 🎯 Méthode 3: Netlify CLI

### Installation

```bash
npm install -g netlify-cli
```

### Connexion

```bash
netlify login
```

### Déploiement

```bash
cd frontend

# Build
npm run build

# Déploiement de test
netlify deploy

# Déploiement en production
netlify deploy --prod
```

---

## ⚙️ Configuration Netlify

### netlify.toml

Le fichier `frontend/netlify.toml` contient toute la configuration:

```toml
[build]
  command = "npm run build"
  publish = "build"
  base = "frontend"

[build.environment]
  NODE_VERSION = "20"
  VITE_API_URL = "https://your-backend-api.com"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Variables d'Environnement

**Dans Netlify Dashboard**:
- Site settings → Environment variables
- Ajouter: `VITE_API_URL=https://your-backend-api.com`

**Localement** (pour le dev):
- Créer `frontend/.env`
- Ajouter: `VITE_API_URL=http://localhost:8000`

---

## 🔧 Configuration du Domaine

### Domaine Netlify (Gratuit)

Par défaut: `vocal-belekoy-c953e0.netlify.app`

**Pour changer**:
1. Site settings → Domain management
2. Options → Edit site name
3. Entrer le nouveau nom: `saasdrevmbot.netlify.app`

### Domaine Personnalisé

1. **Acheter** un domaine (ex: `drevmbot.com`)
2. **Dans Netlify**: Site settings → Domain management
3. **Cliquer** sur "Add custom domain"
4. **Entrer** votre domaine: `drevmbot.com`
5. **Configurer** les DNS:

**Chez votre registrar**:
```
Type: A
Name: @
Value: 75.2.60.5

Type: CNAME
Name: www
Value: vocal-belekoy-c953e0.netlify.app
```

### HTTPS/SSL

Netlify active automatiquement HTTPS avec Let's Encrypt:
- Gratuit
- Automatique
- Renouvellement auto

---

## 📊 Optimisations

### Build Optimization

**Dans `package.json`**:
```json
{
  "scripts": {
    "build": "vite build",
    "build:prod": "vite build --mode production"
  }
}
```

### Asset Optimization

Les headers de cache sont configurés dans `netlify.toml`:
- Assets: 1 an
- Images: 1 jour
- HTML: Pas de cache

### Performance

**Activer dans Netlify**:
1. Site settings → Build & deploy
2. Post processing:
   - ✅ Asset optimization
   - ✅ Bundle CSS
   - ✅ Minify CSS
   - ✅ Minify JS
   - ✅ Compress images

---

## 🔄 Déploiements Automatiques

### Branches

**Configuration**:
1. Site settings → Build & deploy → Continuous deployment
2. Branch deploys:
   - Production: `main` ou `master`
   - Preview: toutes les branches

### Deploy Previews

Netlify crée automatiquement des previews pour:
- ✅ Pull Requests
- ✅ Branches

Chaque PR obtient une URL unique: `deploy-preview-123--vocal-belekoy-c953e0.netlify.app`

### Deploy Hooks

**Créer un webhook**:
1. Site settings → Build & deploy → Build hooks
2. Add build hook
3. Nom: "Manual Deploy"
4. Branch: `main`
5. Copier l'URL

**Déclencher un build**:
```bash
curl -X POST -d {} https://api.netlify.com/build_hooks/YOUR_HOOK_ID
```

---

## 🐛 Dépannage

### Build Failed

**Erreur commune**: `Command failed with exit code 1`

**Solutions**:
1. Vérifier `netlify.toml`
2. Tester le build localement: `npm run build`
3. Vérifier les logs dans Netlify
4. Vérifier la version de Node.js

### 404 sur les Routes

**Problème**: Les routes SvelteKit retournent 404

**Solution**: Vérifier la redirection dans `netlify.toml`:
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Variables d'Environnement Non Chargées

**Problème**: `import.meta.env.VITE_API_URL` est undefined

**Solutions**:
1. Vérifier que la variable commence par `VITE_`
2. Vérifier dans Netlify: Site settings → Environment variables
3. Redéployer après ajout de variables

### API CORS Errors

**Problème**: Erreurs CORS lors des appels API

**Solution**: Configurer CORS sur le backend:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vocal-belekoy-c953e0.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📈 Monitoring

### Analytics

**Activer Netlify Analytics**:
1. Site settings → Analytics
2. Enable analytics (payant: $9/mois)

**Alternative gratuite**: Google Analytics
```html
<!-- frontend/src/app.html -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
```

### Logs

**Accéder aux logs**:
1. Deploys → Cliquer sur un deploy
2. Deploy log → Voir les détails

### Notifications

**Configurer les notifications**:
1. Site settings → Build & deploy → Deploy notifications
2. Ajouter:
   - Email
   - Slack
   - Webhook

---

## 🔐 Sécurité

### Headers de Sécurité

Configurés dans `netlify.toml`:
```toml
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    X-XSS-Protection = "1; mode=block"
```

### Authentification

**Pour protéger le site**:
1. Site settings → Access control
2. Visitor access:
   - Password protection
   - JWT-based authentication
   - OAuth (GitHub, GitLab, etc.)

### Variables Sensibles

**⚠️ Important**:
- Ne jamais commiter de secrets dans Git
- Utiliser les Environment Variables de Netlify
- Préfixer par `VITE_` uniquement les variables publiques

---

## 📋 Checklist de Déploiement

### Avant le Déploiement

- [ ] Code testé localement
- [ ] Build réussi: `npm run build`
- [ ] `netlify.toml` configuré
- [ ] Variables d'environnement identifiées
- [ ] Backend API accessible publiquement
- [ ] CORS configuré sur le backend

### Déploiement

- [ ] Repository Git créé et pushé
- [ ] Site Netlify créé
- [ ] Build settings configurés
- [ ] Variables d'environnement ajoutées
- [ ] Premier déploiement réussi
- [ ] Site accessible et fonctionnel

### Après le Déploiement

- [ ] Tester toutes les pages
- [ ] Vérifier les appels API
- [ ] Tester sur mobile
- [ ] Configurer le domaine (optionnel)
- [ ] Activer HTTPS
- [ ] Configurer les notifications
- [ ] Ajouter analytics (optionnel)

---

## 🚀 Commandes Rapides

```bash
# Build local
cd frontend && npm run build

# Test du build
cd build && python -m http.server 8080

# Déploiement CLI
netlify deploy --prod

# Voir les logs
netlify logs

# Ouvrir le site
netlify open:site

# Ouvrir l'admin
netlify open:admin
```

---

## 📚 Ressources

### Documentation

- **Netlify Docs**: https://docs.netlify.com/
- **SvelteKit Adapter**: https://kit.svelte.dev/docs/adapter-static
- **Vite Env Variables**: https://vitejs.dev/guide/env-and-mode.html

### Support

- **Netlify Community**: https://answers.netlify.com/
- **Netlify Status**: https://www.netlifystatus.com/
- **SvelteKit Discord**: https://svelte.dev/chat

---

## 🎯 Prochaines Étapes

1. ✅ Configuration Netlify terminée
2. ⏳ Déployer le site
3. ⏳ Configurer les variables d'environnement
4. ⏳ Tester le site en production
5. ⏳ Configurer un domaine personnalisé (optionnel)
6. ⏳ Activer les analytics (optionnel)

---

**Créé le**: 06/02/2026 à 20:10  
**Site**: https://vocal-belekoy-c953e0.netlify.app/  
**Status**: 📝 **Prêt pour le déploiement**
