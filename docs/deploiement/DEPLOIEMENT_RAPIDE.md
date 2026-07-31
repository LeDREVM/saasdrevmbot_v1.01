# 🚀 Guide de Déploiement Rapide - Netlify

**Site**: https://saasdrevmbot.netlify.app/

---

## ✅ Build Réussi !

Le projet est maintenant prêt pour le déploiement sur Netlify.

### 📦 Fichiers Modifiés pour Netlify

1. ✅ `frontend/svelte.config.js` - Adapter static configuré
2. ✅ `frontend/src/routes/+layout.js` - Mode SPA activé
3. ✅ `frontend/package.json` - Adapter static ajouté
4. ✅ `frontend/netlify.toml` - Configuration Netlify
5. ✅ `frontend/src/app.html` - Favicon retiré temporairement

---

## 🎯 Options de Déploiement

### Option 1: Via Git (Recommandé - Déploiement Automatique)

```bash
# 1. Commit les changements
git add .
git commit -m "fix: configure static adapter for Netlify"

# 2. Push sur GitHub/GitLab
git push origin main
```

Netlify détectera automatiquement les changements et redéploiera le site.

---

### Option 2: Netlify CLI

```bash
# 1. Installer Netlify CLI (si pas déjà fait)
npm install -g netlify-cli

# 2. Se connecter
netlify login

# 3. Déployer
cd frontend
netlify deploy --prod
```

---

### Option 3: Drag & Drop Manuel

```bash
# 1. Le dossier build est déjà créé
cd frontend/build

# 2. Aller sur https://app.netlify.com/
# 3. Glisser-déposer le dossier "build"
```

---

## 🧪 Test Local

Le build a été testé et fonctionne :

```bash
cd frontend
npm run preview
# Ouvrir http://localhost:4173/
```

**Status**: ✅ Le site se charge correctement en local

---

## ⚙️ Configuration Netlify

### Variables d'Environnement à Configurer

Dans **Netlify Dashboard** → **Site settings** → **Environment variables** :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `BACKEND_API_URL` | `https://your-backend-api.com` | Base du backend **FastAPI**, sans slash final. **Requise** : c'est elle qui câble `/api/*` et `/health`. |
| `EXPRESS_API_URL` | `https://your-express.com` | Base du backend Express « GoldyXbOT » (page Stats → corrélations). Optionnelle : à défaut, retombe sur `BACKEND_API_URL`. |
| `PROXY_TIMEOUT_MS` | `9000` | Optionnelle. Timeout amont, gardé sous la limite Netlify de 10 s. |

**Comment ça marche** : le site est en **MODE A (reverse-proxy)**. `netlify.toml` fixe
`VITE_API_URL = ""`, donc le front appelle `/api/...` en **relatif** ; la fonction
`netlify/functions/api-proxy.js` relaie ensuite vers `BACKEND_API_URL`. Aucune URL backend
n'est figée dans le bundle et il n'y a pas de CORS à gérer.

**Important** : `netlify.toml` n'interpole **pas** les variables d'environnement — c'est
précisément pourquoi le proxy passe par une fonction et non par un `[[redirects]]` vers une URL
en dur. Tant que `BACKEND_API_URL` n'est pas définie, `/api/*` et `/health` répondent
`503 {"error":"BACKEND_API_URL non configurée"}`. Après avoir ajouté la variable, **redéploie**
(les env vars ne sont lues qu'au démarrage de la fonction).

> Ne définis `VITE_API_URL` que si tu veux repasser en **MODE B (CORS direct)** — il faut alors
> retirer les redirects proxy de `netlify.toml` et ouvrir CORS côté FastAPI (section suivante).

---

## 🔧 Configuration Backend (CORS)

Pour que le frontend puisse communiquer avec le backend, configurez CORS :

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://saasdrevmbot.netlify.app",
        "http://localhost:5173",  # Dev local
        "http://localhost:4173"   # Preview local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📋 Checklist de Déploiement

### Avant le Déploiement
- [x] Build réussi (`npm run build`)
- [x] Test local réussi (`npm run preview`)
- [x] Adapter static configuré
- [x] Mode SPA activé
- [x] `netlify.toml` configuré

### Après le Déploiement
- [ ] Vérifier que le site se charge sur https://saasdrevmbot.netlify.app/
- [ ] Configurer `VITE_API_URL` dans Netlify
- [ ] Déployer le backend
- [ ] Configurer CORS sur le backend
- [ ] Tester les appels API
- [ ] Vérifier toutes les pages (/, /calendar, /stats, /alerts)

---

## 🐛 Problèmes Résolus

### ✅ Problème 1: "adapter-auto" ne fonctionnait pas
**Solution**: Utilisation de `@sveltejs/adapter-static` avec configuration SPA

### ✅ Problème 2: TypeScript dans stats/+page.svelte
**Solution**: Suppression des annotations de type

### ✅ Problème 3: Import Timeline.svelte incorrect
**Solution**: Correction du chemin d'import

### ✅ Problème 4: Favicon manquant
**Solution**: Retrait temporaire du favicon de app.html

---

## 📊 Résultat du Build

```
Build Size:
- Total: ~350 KB (gzipped: ~115 KB)
- Largest chunk: nodes/4.js (236 KB)
- CSS: ~42 KB total

Build Time: ~4.5s
Status: ✅ Success
```

---

## 🚀 Commandes Utiles

```bash
# Build de production
cd frontend
npm run build

# Preview local
npm run preview

# Dev mode
npm run dev

# Déploiement Netlify CLI
netlify deploy --prod

# Voir les logs Netlify
netlify logs

# Ouvrir le site
netlify open:site
```

---

## 📚 Documentation Complète

- **Guide Complet**: [NETLIFY_DEPLOYMENT_GUIDE.md](./NETLIFY_DEPLOYMENT_GUIDE.md)
- **README**: [README_NETLIFY.md](./README_NETLIFY.md)
- **Scripts**: `deploy-netlify.sh` / `deploy-netlify.bat`

---

## 🎉 Prochaines Étapes

1. **Déployer** le site (choisir une option ci-dessus)
2. **Configurer** VITE_API_URL dans Netlify
3. **Déployer** le backend (Render/Docker)
4. **Tester** le site en production

---

**Créé le**: 07/02/2026 à 01:12  
**Status**: ✅ **Prêt pour le déploiement**  
**Site**: https://saasdrevmbot.netlify.app/
