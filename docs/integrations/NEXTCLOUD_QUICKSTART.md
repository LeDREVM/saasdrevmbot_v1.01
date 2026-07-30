# ☁️ Nextcloud - Guide de Démarrage Rapide

## 🎯 Configuration Actuelle

```
✅ URL: https://ledream.kflw.io
✅ Username: ledream
✅ Status: CONNECTÉ
✅ Dossier: ForexBot/
✅ Tests: 4/4 réussis (100%)
```

---

## 🚀 Démarrage Rapide

### 1. Vérifier la Connexion

```bash
python test_nextcloud_simple.py
```

**Résultat attendu**: 4/4 tests réussis ✅

### 2. Lancer l'API Backend

```bash
cd backend
python main.py
```

**URL**: http://localhost:8000

### 3. Tester les Endpoints

```bash
# Status
curl http://localhost:8000/api/nextcloud/status

# Liste des rapports
curl http://localhost:8000/api/nextcloud/reports/list

# Test connexion
curl -X POST http://localhost:8000/api/nextcloud/test-connection
```

### 4. Lancer le Frontend

```bash
cd frontend
npm run dev
```

**URL**: http://localhost:5173

---

## 📁 Accès aux Fichiers

### Interface Web Nextcloud

**Dossier ForexBot**:
```
https://ledream.kflw.io/apps/files/?dir=/ForexBot
```

**Partage Public**:
```
https://ledream.kflw.io/f/33416
```

---

## 🔧 Commandes Utiles

### Test Rapide

```bash
# Test simple (sans dépendances)
python test_nextcloud_simple.py

# Test complet (nécessite les dépendances)
python test_nextcloud.py
```

### Upload Manuel

```python
from app.services.alerts.nextcloud_uploader import NextcloudUploader

uploader = NextcloudUploader()
uploader.upload_file("fichier.md", "nom_destination.md")
```

### Export avec Auto-Upload

```python
from app.services.alerts.markdown_exporter import MarkdownExporter

exporter = MarkdownExporter(auto_upload=True)
filepath = exporter.export_daily_predictions(predictions, "EURUSD")
```

---

## 📊 Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/nextcloud/status` | Statut de la connexion |
| GET | `/api/nextcloud/reports/list` | Liste des rapports |
| POST | `/api/nextcloud/test-connection` | Test de connexion |
| POST | `/api/nextcloud/sync/all` | Sync tous les rapports |
| POST | `/api/nextcloud/upload` | Upload un fichier |

---

## 🎨 Interface Frontend

### Accès

1. Ouvrir: http://localhost:5173/alerts
2. Onglet: **Overview**
3. Section: **☁️ Synchronisation Nextcloud**

### Fonctionnalités

- 📤 **Sync Maintenant**: Lance la synchronisation
- ℹ️ **Statut**: Affiche l'état de la connexion
- 🕒 **Dernière Sync**: Horodatage de la dernière sync

---

## 🔐 Configuration

### Fichier .env

```env
NEXTCLOUD_URL=https://ledream.kflw.io
NEXTCLOUD_USERNAME=ledream
NEXTCLOUD_PASSWORD=votre_app_password
NEXTCLOUD_SHARE_FOLDER=/f/33416
```

### Créer le fichier .env

```bash
# Windows
.\create_env.bat

# Linux/Mac
./create_env.sh
```

---

## 🐛 Dépannage Rapide

### Erreur: Module 'pydantic_settings' not found

```bash
cd backend
pip install -r requirements.txt
```

### Erreur: Connexion échouée (401)

- Vérifier le username et password dans `.env`
- Utiliser un **App Password** Nextcloud

### Erreur: Timeout

- Vérifier la connexion internet
- Vérifier l'URL Nextcloud

---

## 📚 Documentation Complète

- **Rapport de Vérification**: `NEXTCLOUD_VERIFICATION.md`
- **Déploiement Docker**: `DOCKER_DEPLOYMENT.md`
- **API Documentation**: http://localhost:8000/api/docs

---

## ✅ Checklist

- [x] Configuration Nextcloud
- [x] Test de connexion
- [x] Upload de fichier test
- [x] Création de dossiers
- [ ] Lancer l'API Backend
- [ ] Tester les endpoints
- [ ] Tester l'interface frontend
- [ ] Configurer les alertes automatiques

---

**Dernière mise à jour**: 06/02/2026  
**Status**: ✅ Opérationnel
