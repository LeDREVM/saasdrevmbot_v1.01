# 📁 Intégration Nextcloud

## Configuration

Votre instance Nextcloud est configurée pour recevoir automatiquement les rapports Markdown générés par le bot.

### Paramètres

- **URL Nextcloud** : `https://ledream.kflw.io`
- **Dossier partagé** : `/f/33416`
- **Dossier de destination** : `ForexBot/reports/`

## Configuration dans `.env`

```env
# Nextcloud
NEXTCLOUD_URL=https://ledream.kflw.io
NEXTCLOUD_SHARE_FOLDER=/f/33416
NEXTCLOUD_USERNAME=votre_username
NEXTCLOUD_PASSWORD=votre_password
```

## Types de rapports uploadés

### 1. Prédictions quotidiennes
**Fichier** : `predictions_{SYMBOL}_{DATE}.md`

Contenu :
- Résumé exécutif
- Événements par niveau de risque (extreme, high, medium, low)
- Prédictions détaillées (mouvement attendu, direction, recommandations)
- Liens utiles

**Exemple** : `predictions_EURUSD_2026-02-06.md`

### 2. Rapports statistiques
**Fichier** : `stats_report_{SYMBOL}_{DATE}.md`

Contenu :
- Métriques globales (total événements, taux d'impact, mouvement moyen)
- Distribution des directions (haussier/baissier/neutre)
- Top 10 événements par impact
- Top 10 mouvements les plus importants
- Heatmap volatilité (jour × heure)

**Exemple** : `stats_report_EURUSD_2026-02-06.md`

### 3. Résumés hebdomadaires
**Fichier** : `weekly_summary_{SYMBOL}_{WEEK}.md`

Contenu :
- Vue d'ensemble de la semaine
- Événements par jour
- Conseils de trading pour la semaine

**Exemple** : `weekly_summary_EURUSD_2026-W06.md`

## Utilisation

### Upload automatique

Les rapports sont automatiquement uploadés vers Nextcloud lors de leur génération :

```python
from app.services.alerts.markdown_exporter import MarkdownExporter

# Créer l'exporter (auto_upload=True par défaut)
exporter = MarkdownExporter()

# Générer et uploader un rapport
filepath = exporter.export_daily_predictions(predictions, "EURUSD")
# Le fichier est automatiquement uploadé vers Nextcloud
```

### Upload manuel

Si vous voulez désactiver l'upload automatique :

```python
# Désactiver l'upload auto
exporter = MarkdownExporter(auto_upload=False)

# Générer le rapport
filepath = exporter.export_daily_predictions(predictions, "EURUSD")

# Upload manuel si besoin
from app.services.alerts.nextcloud_uploader import NextcloudUploader
uploader = NextcloudUploader()
uploader.upload_file(filepath)
```

## Structure des dossiers sur Nextcloud

```
ForexBot/
└── reports/
    ├── predictions_EURUSD_2026-02-06.md
    ├── predictions_GBPUSD_2026-02-06.md
    ├── stats_report_EURUSD_2026-02-06.md
    ├── stats_report_GBPUSD_2026-02-06.md
    ├── weekly_summary_EURUSD_2026-W06.md
    └── weekly_summary_GBPUSD_2026-W06.md
```

## Accès aux rapports

### Via l'interface web
1. Accéder à https://ledream.kflw.io
2. Se connecter avec vos identifiants
3. Naviguer vers `ForexBot/reports/`

### Via le dossier partagé
Accès direct : https://ledream.kflw.io/f/33416

### Synchronisation Obsidian

Pour synchroniser avec Obsidian :

1. **Option 1 : Client Nextcloud**
   - Installer le client Nextcloud Desktop
   - Synchroniser le dossier `ForexBot/reports/`
   - Ajouter ce dossier comme vault Obsidian

2. **Option 2 : Plugin Obsidian**
   - Installer le plugin "Remotely Save"
   - Configurer avec WebDAV :
     - URL : `https://ledream.kflw.io/remote.php/dav/files/USERNAME/`
     - Path : `ForexBot/reports/`

3. **Option 3 : Sync manuel**
   - Télécharger les fichiers depuis Nextcloud
   - Les placer dans votre vault Obsidian

## API WebDAV

Les uploads utilisent l'API WebDAV de Nextcloud :

```
Endpoint : https://ledream.kflw.io/remote.php/dav/files/{username}/
Méthode : PUT
Auth : Basic (username:password)
```

## Sécurité

### Authentification
- Les credentials sont stockés dans `.env` (jamais commités)
- Utilisation de Basic Auth sur HTTPS
- Mot de passe chiffré en transit

### Permissions
Le compte Nextcloud doit avoir :
- ✅ Accès en écriture au dossier `ForexBot/reports/`
- ✅ Permission de créer des dossiers
- ✅ Permission d'uploader des fichiers

### Recommandations
1. Utiliser un mot de passe d'application dédié
2. Limiter les permissions au strict nécessaire
3. Activer l'authentification 2FA sur Nextcloud
4. Surveiller les logs d'accès

## Logs

Les uploads sont loggés dans l'application :

```
✅ Fichier uploadé vers Nextcloud: predictions_EURUSD_2026-02-06.md
📤 Rapport uploadé vers Nextcloud: predictions_EURUSD_2026-02-06.md
❌ Erreur upload Nextcloud: 401 Unauthorized
```

## Troubleshooting

### Erreur 401 (Unauthorized)
- Vérifier `NEXTCLOUD_USERNAME` et `NEXTCLOUD_PASSWORD`
- Vérifier que le compte existe et est actif
- Essayer de se connecter manuellement sur l'interface web

### Erreur 404 (Not Found)
- Vérifier que le dossier `ForexBot/reports/` existe
- Le créer manuellement ou laisser l'application le créer
- Vérifier l'URL WebDAV

### Erreur 403 (Forbidden)
- Vérifier les permissions du compte
- S'assurer que le compte peut écrire dans le dossier
- Vérifier les quotas de stockage

### Pas d'upload
- Vérifier que `NEXTCLOUD_URL` est configuré dans `.env`
- Vérifier les logs de l'application
- Tester manuellement avec curl :

```bash
curl -u username:password -T rapport.md \
  "https://ledream.kflw.io/remote.php/dav/files/username/ForexBot/reports/rapport.md"
```

### Timeout
- Vérifier la connexion internet
- Augmenter le timeout dans le code si nécessaire
- Vérifier que Nextcloud est accessible

## Fonctionnalités avancées

### Versioning
Nextcloud garde automatiquement les versions des fichiers :
- Les rapports quotidiens écrasent les précédents
- Les anciennes versions sont accessibles dans l'historique

### Partage
Vous pouvez partager les rapports :
1. Clic droit sur le fichier → Partager
2. Créer un lien de partage
3. Définir les permissions (lecture seule recommandé)

### Notifications
Configurer des notifications Nextcloud :
1. Paramètres → Activité
2. Activer les notifications pour le dossier `ForexBot/reports/`
3. Recevoir un email/notification à chaque nouveau rapport

## Intégration avec les alertes

Les rapports sont générés et uploadés automatiquement par le worker Celery :

```python
# Dans alert_worker.py
from app.services.alerts.markdown_exporter import MarkdownExporter

exporter = MarkdownExporter(auto_upload=True)

# Rapport quotidien (uploadé automatiquement)
exporter.export_daily_predictions(predictions, symbol)

# Rapport stats (uploadé automatiquement)
exporter.export_stats_report(stats, symbol, period_days=30)

# Résumé hebdomadaire (uploadé automatiquement)
exporter.export_weekly_summary(weekly_predictions, symbol)
```

## Exemple de workflow complet

```
1. Worker Celery détecte des événements à venir
2. AlertPredictor génère des prédictions
3. MarkdownExporter crée le rapport .md
4. NextcloudUploader upload vers Nextcloud
5. Le fichier apparaît dans ForexBot/reports/
6. Obsidian synchronise (si configuré)
7. Vous consultez le rapport dans Obsidian
```

## Ressources

- [Documentation Nextcloud WebDAV](https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html)
- [API Nextcloud](https://docs.nextcloud.com/server/latest/developer_manual/client_apis/WebDAV/index.html)
- [Obsidian + Nextcloud](https://help.obsidian.md/Obsidian+Sync/Introduction+to+Obsidian+Sync)

---

**Configuration** : ✅ Prête à l'emploi  
**URL** : https://ledream.kflw.io  
**Dossier** : ForexBot/reports/
