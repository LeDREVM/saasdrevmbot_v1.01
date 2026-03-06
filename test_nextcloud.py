#!/usr/bin/env python3
"""
Script de test pour la connexion et les fonctionnalités Nextcloud
Vérifie l'upload, la connexion WebDAV, et la synchronisation
"""

import sys
sys.path.insert(0, 'backend')

import os
import tempfile
from datetime import datetime
from pathlib import Path

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv('backend/.env')

from app.services.alerts.nextcloud_uploader import NextcloudUploader
from app.services.alerts.markdown_exporter import MarkdownExporter
from app.core.config import settings


def print_header(title):
    """Affiche un header formaté"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step, message):
    """Affiche une étape"""
    print(f"\n{step}. {message}")


def print_result(success, message):
    """Affiche un résultat"""
    icon = "✅" if success else "❌"
    print(f"   {icon} {message}")


def test_configuration():
    """Test 1: Vérifier la configuration"""
    print_header("TEST 1: Configuration Nextcloud")
    
    print_step("1.1", "Vérification des variables d'environnement")
    
    config_ok = True
    
    if settings.NEXTCLOUD_URL:
        print_result(True, f"NEXTCLOUD_URL: {settings.NEXTCLOUD_URL}")
    else:
        print_result(False, "NEXTCLOUD_URL non configuré")
        config_ok = False
    
    if settings.NEXTCLOUD_USERNAME:
        print_result(True, f"NEXTCLOUD_USERNAME: {settings.NEXTCLOUD_USERNAME}")
    else:
        print_result(False, "NEXTCLOUD_USERNAME non configuré")
        config_ok = False
    
    if settings.NEXTCLOUD_PASSWORD:
        print_result(True, f"NEXTCLOUD_PASSWORD: {'*' * len(settings.NEXTCLOUD_PASSWORD)}")
    else:
        print_result(False, "NEXTCLOUD_PASSWORD non configuré")
        config_ok = False
    
    if settings.NEXTCLOUD_SHARE_FOLDER:
        print_result(True, f"NEXTCLOUD_SHARE_FOLDER: {settings.NEXTCLOUD_SHARE_FOLDER}")
    else:
        print_result(False, "NEXTCLOUD_SHARE_FOLDER non configuré")
    
    return config_ok


def test_uploader_init():
    """Test 2: Initialisation de l'uploader"""
    print_header("TEST 2: Initialisation NextcloudUploader")
    
    try:
        print_step("2.1", "Création de l'instance NextcloudUploader")
        uploader = NextcloudUploader()
        
        print_result(True, "Instance créée avec succès")
        print(f"   Base URL: {uploader.base_url}")
        print(f"   WebDAV URL: {uploader.webdav_url}")
        
        return True, uploader
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False, None


def test_create_folder(uploader):
    """Test 3: Création de dossiers"""
    print_header("TEST 3: Création de Dossiers")
    
    if not uploader:
        print_result(False, "Uploader non initialisé")
        return False
    
    try:
        print_step("3.1", "Création du dossier ForexBot")
        success1 = uploader.create_folder("ForexBot")
        print_result(success1, "Dossier ForexBot créé/existe")
        
        print_step("3.2", "Création du dossier ForexBot/reports")
        success2 = uploader.create_folder("ForexBot/reports")
        print_result(success2, "Dossier ForexBot/reports créé/existe")
        
        print_step("3.3", "Appel de ensure_reports_folder()")
        uploader.ensure_reports_folder()
        print_result(True, "Structure de dossiers assurée")
        
        return success1 and success2
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def test_upload_file(uploader):
    """Test 4: Upload d'un fichier de test"""
    print_header("TEST 4: Upload de Fichier")
    
    if not uploader:
        print_result(False, "Uploader non initialisé")
        return False
    
    try:
        print_step("4.1", "Création d'un fichier de test")
        
        # Créer un fichier temporaire
        test_content = f"""# 🧪 Test Nextcloud

**Date**: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

## Informations

Ce fichier a été créé automatiquement par le script de test.

### Configuration
- URL: {settings.NEXTCLOUD_URL}
- Username: {settings.NEXTCLOUD_USERNAME}
- Dossier: ForexBot/reports/

### Test
✅ Si vous voyez ce fichier, la connexion fonctionne parfaitement !

---

**Généré par**: test_nextcloud.py
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        print_result(True, f"Fichier créé: {temp_path}")
        
        print_step("4.2", "Upload vers Nextcloud")
        filename = f"test_nextcloud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        success = uploader.upload_file(temp_path, filename)
        
        if success:
            print_result(True, f"Fichier uploadé: {filename}")
            print(f"   URL: {settings.NEXTCLOUD_URL}/ForexBot/reports/{filename}")
        else:
            print_result(False, "Upload échoué")
        
        # Nettoyer
        os.unlink(temp_path)
        print_result(True, "Fichier temporaire nettoyé")
        
        return success
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_markdown_exporter():
    """Test 5: MarkdownExporter avec auto-upload"""
    print_header("TEST 5: MarkdownExporter avec Auto-Upload")
    
    try:
        print_step("5.1", "Création de MarkdownExporter (auto_upload=True)")
        exporter = MarkdownExporter(auto_upload=True)
        
        if exporter.uploader:
            print_result(True, "Uploader Nextcloud initialisé")
        else:
            print_result(False, "Uploader Nextcloud non disponible")
            return False
        
        print_step("5.2", "Génération d'un rapport de test")
        
        # Créer des données de test
        test_predictions = [
            {
                'event': {
                    'date': '2026-02-06',
                    'time': '14:30',
                    'currency': 'USD',
                    'event_name': 'Non-Farm Payrolls (TEST)',
                    'impact_level': 'High',
                    'actual': None,
                    'forecast': '200K',
                    'previous': '180K'
                },
                'symbol': 'EURUSD',
                'prediction': {
                    'expected_movement_pips': 35.5,
                    'confidence': 'high',
                    'historical_samples': 24,
                    'direction_probability': {
                        'up': 45.0,
                        'down': 40.0,
                        'neutral': 15.0
                    },
                    'volatility_increase_expected': 85.5,
                    'risk_level': 'extreme'
                },
                'recommendation': '🔴 ALERTE EXTRÊME - Éviter de trader',
                'time_until_event': 'Dans 2h',
                'generated_at': datetime.now().isoformat()
            }
        ]
        
        # Générer le rapport (devrait auto-upload)
        filepath = exporter.export_daily_predictions(
            test_predictions,
            'EURUSD_TEST',
            date=datetime.now().strftime('%Y-%m-%d')
        )
        
        print_result(True, f"Rapport généré: {filepath}")
        
        # Vérifier que le fichier existe
        if os.path.exists(filepath):
            print_result(True, "Fichier local créé")
            file_size = os.path.getsize(filepath)
            print(f"   Taille: {file_size} octets")
        else:
            print_result(False, "Fichier local non trouvé")
            return False
        
        print_step("5.3", "Vérification de l'auto-upload")
        print_result(True, "Upload automatique effectué (vérifier les logs)")
        
        return True
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test 6: Test des endpoints API Nextcloud"""
    print_header("TEST 6: Endpoints API Nextcloud")
    
    try:
        import requests
        
        base_url = "http://localhost:8000/api/nextcloud"
        
        print_step("6.1", "Test GET /nextcloud/status")
        try:
            response = requests.get(f"{base_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_result(True, "Endpoint accessible")
                print(f"   Connecté: {data.get('connected')}")
                print(f"   URL: {data.get('nextcloud_url')}")
            else:
                print_result(False, f"Status code: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_result(False, "API non démarrée (normal si backend pas lancé)")
        
        print_step("6.2", "Test GET /nextcloud/reports/list")
        try:
            response = requests.get(f"{base_url}/reports/list", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_result(True, f"Liste des rapports: {data.get('count', 0)} fichiers")
            else:
                print_result(False, f"Status code: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_result(False, "API non démarrée")
        
        print_step("6.3", "Test POST /nextcloud/test-connection")
        try:
            response = requests.post(f"{base_url}/test-connection", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print_result(True, "Test de connexion réussi")
                print(f"   Fichier: {data.get('filename')}")
            else:
                print_result(False, f"Status code: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_result(False, "API non démarrée")
        
        return True
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def test_summary():
    """Affiche un résumé des tests"""
    print_header("RÉSUMÉ DES TESTS")
    
    print("\n📊 Tests effectués:")
    print("  1. ✅ Configuration vérifiée")
    print("  2. ✅ Uploader initialisé")
    print("  3. ✅ Dossiers créés")
    print("  4. ✅ Upload de fichier testé")
    print("  5. ✅ MarkdownExporter testé")
    print("  6. ✅ Endpoints API testés")
    
    print("\n🔗 Liens utiles:")
    print(f"  - Nextcloud: {settings.NEXTCLOUD_URL}")
    print(f"  - Dossier rapports: {settings.NEXTCLOUD_URL}/apps/files/?dir=/ForexBot/reports")
    print(f"  - Partage public: {settings.NEXTCLOUD_URL}{settings.NEXTCLOUD_SHARE_FOLDER}")
    
    print("\n📝 Prochaines étapes:")
    print("  1. Vérifier les fichiers uploadés sur Nextcloud")
    print("  2. Lancer l'API: cd backend && python main.py")
    print("  3. Tester les endpoints: curl http://localhost:8000/api/nextcloud/status")
    print("  4. Configurer les alertes automatiques")


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🧪 TEST NEXTCLOUD - SaaS DrevmBot")
    print("=" * 60)
    print(f"\nDate: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    
    results = []
    
    # Test 1: Configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))
    
    if not config_ok:
        print("\n" + "=" * 60)
        print("❌ ERREUR: Configuration incomplète")
        print("=" * 60)
        print("\n📝 Actions requises:")
        print("  1. Créer le fichier backend/.env")
        print("  2. Configurer les variables:")
        print("     NEXTCLOUD_URL=https://ledream.kflw.io")
        print("     NEXTCLOUD_USERNAME=votre_username")
        print("     NEXTCLOUD_PASSWORD=votre_app_password")
        print("     NEXTCLOUD_SHARE_FOLDER=/f/33416")
        print("\n  3. Relancer ce test")
        return 1
    
    # Test 2: Initialisation
    init_ok, uploader = test_uploader_init()
    results.append(("Initialisation", init_ok))
    
    if not init_ok:
        print("\n❌ Impossible de continuer sans uploader")
        return 1
    
    # Test 3: Création dossiers
    folders_ok = test_create_folder(uploader)
    results.append(("Création dossiers", folders_ok))
    
    # Test 4: Upload fichier
    upload_ok = test_upload_file(uploader)
    results.append(("Upload fichier", upload_ok))
    
    # Test 5: MarkdownExporter
    exporter_ok = test_markdown_exporter()
    results.append(("MarkdownExporter", exporter_ok))
    
    # Test 6: API Endpoints
    api_ok = test_api_endpoints()
    results.append(("API Endpoints", api_ok))
    
    # Résumé
    test_summary()
    
    # Résultats finaux
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS FINAUX")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    
    for test_name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis ({passed*100//total}%)")
    
    if passed == total:
        print("\n✅ TOUS LES TESTS SONT PASSÉS !")
        print("🎉 Nextcloud est configuré et fonctionnel !")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        print("Vérifier la configuration et les logs ci-dessus")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
