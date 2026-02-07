#!/usr/bin/env python3
"""
Test simple de connexion Nextcloud (sans dépendances complexes)
"""

import os
import requests
from datetime import datetime
import tempfile

# Charger les variables d'environnement depuis .env
def load_env():
    """Charge les variables depuis backend/.env"""
    env_vars = {}
    env_file = 'backend/.env'
    
    if not os.path.exists(env_file):
        print(f"❌ Fichier {env_file} non trouvé")
        return None
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_configuration(env):
    """Test 1: Vérifier la configuration"""
    print_header("TEST 1: Configuration")
    
    required = ['NEXTCLOUD_URL', 'NEXTCLOUD_USERNAME', 'NEXTCLOUD_PASSWORD']
    all_ok = True
    
    for key in required:
        value = env.get(key, '')
        if value and value != '':
            icon = "✅"
            display = value if key != 'NEXTCLOUD_PASSWORD' else '*' * 10
            print(f"  {icon} {key}: {display}")
        else:
            icon = "❌"
            print(f"  {icon} {key}: NON CONFIGURÉ")
            all_ok = False
    
    return all_ok


def test_webdav_connection(env):
    """Test 2: Test connexion WebDAV"""
    print_header("TEST 2: Connexion WebDAV")
    
    url = env.get('NEXTCLOUD_URL')
    username = env.get('NEXTCLOUD_USERNAME')
    password = env.get('NEXTCLOUD_PASSWORD')
    
    if not all([url, username, password]):
        print("  ❌ Configuration incomplète")
        return False
    
    # URL WebDAV
    webdav_url = f"{url}/remote.php/dav/files/{username}/"
    
    print(f"\n  Tentative de connexion à:")
    print(f"  {webdav_url}")
    
    try:
        response = requests.request(
            'PROPFIND',
            webdav_url,
            auth=(username, password),
            timeout=10
        )
        
        if response.status_code in [200, 207]:  # 207 = Multi-Status (WebDAV)
            print(f"\n  ✅ Connexion réussie ! (Status: {response.status_code})")
            return True
        elif response.status_code == 401:
            print(f"\n  ❌ Authentification échouée (401)")
            print(f"  Vérifier username et password")
            return False
        else:
            print(f"\n  ⚠️  Status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n  ❌ Impossible de se connecter à {url}")
        print(f"  Vérifier que l'URL est correcte")
        return False
    except Exception as e:
        print(f"\n  ❌ Erreur: {e}")
        return False


def test_create_folder(env):
    """Test 3: Créer un dossier"""
    print_header("TEST 3: Création de Dossier")
    
    url = env.get('NEXTCLOUD_URL')
    username = env.get('NEXTCLOUD_USERNAME')
    password = env.get('NEXTCLOUD_PASSWORD')
    
    webdav_url = f"{url}/remote.php/dav/files/{username}/ForexBot"
    
    print(f"\n  Création du dossier: ForexBot")
    
    try:
        response = requests.request(
            'MKCOL',
            webdav_url,
            auth=(username, password),
            timeout=10
        )
        
        if response.status_code == 201:
            print(f"  ✅ Dossier créé avec succès")
            return True
        elif response.status_code == 405:
            print(f"  ✅ Dossier existe déjà")
            return True
        else:
            print(f"  ⚠️  Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def test_upload_file(env):
    """Test 4: Upload un fichier de test"""
    print_header("TEST 4: Upload de Fichier")
    
    url = env.get('NEXTCLOUD_URL')
    username = env.get('NEXTCLOUD_USERNAME')
    password = env.get('NEXTCLOUD_PASSWORD')
    
    # Créer un fichier de test
    test_content = f"""# 🧪 Test Nextcloud

**Date**: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

## Test de Connexion

✅ Si vous voyez ce fichier, la connexion fonctionne !

### Configuration
- URL: {url}
- Username: {username}
- Dossier: ForexBot/reports/

---

**Généré par**: test_nextcloud_simple.py
"""
    
    filename = f"test_connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    webdav_url = f"{url}/remote.php/dav/files/{username}/ForexBot/{filename}"
    
    print(f"\n  Upload du fichier: {filename}")
    
    try:
        response = requests.put(
            webdav_url,
            data=test_content.encode('utf-8'),
            auth=(username, password),
            headers={'Content-Type': 'text/markdown'},
            timeout=15
        )
        
        if response.status_code in [200, 201, 204]:
            print(f"  ✅ Fichier uploadé avec succès !")
            print(f"\n  📁 Accès au fichier:")
            print(f"  {url}/apps/files/?dir=/ForexBot")
            return True
        else:
            print(f"  ❌ Upload échoué (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🧪 TEST NEXTCLOUD - Version Simple")
    print("=" * 60)
    print(f"\nDate: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
    
    # Charger la configuration
    print("📝 Chargement de la configuration...")
    env = load_env()
    
    if not env:
        print("\n❌ ERREUR: Impossible de charger backend/.env")
        print("\n📝 Actions requises:")
        print("  1. Exécuter: .\\create_env.bat")
        print("  2. Éditer backend\\.env")
        print("  3. Configurer:")
        print("     NEXTCLOUD_URL=https://ledream.kflw.io")
        print("     NEXTCLOUD_USERNAME=votre_username")
        print("     NEXTCLOUD_PASSWORD=votre_app_password")
        return 1
    
    results = []
    
    # Test 1: Configuration
    config_ok = test_configuration(env)
    results.append(("Configuration", config_ok))
    
    if not config_ok:
        print("\n❌ Configuration incomplète. Impossible de continuer.")
        return 1
    
    # Test 2: Connexion WebDAV
    connection_ok = test_webdav_connection(env)
    results.append(("Connexion WebDAV", connection_ok))
    
    if not connection_ok:
        print("\n❌ Connexion échouée. Vérifier les credentials.")
        return 1
    
    # Test 3: Création dossier
    folder_ok = test_create_folder(env)
    results.append(("Création dossier", folder_ok))
    
    # Test 4: Upload fichier
    upload_ok = test_upload_file(env)
    results.append(("Upload fichier", upload_ok))
    
    # Résultats
    print_header("RÉSULTATS")
    
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    
    for test_name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis ({passed*100//total}%)")
    
    if passed == total:
        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS SONT PASSÉS !")
        print("=" * 60)
        print("\n🎉 Nextcloud est configuré et fonctionnel !")
        print("\n📁 Accès à vos fichiers:")
        print(f"  {env.get('NEXTCLOUD_URL')}/apps/files/?dir=/ForexBot")
        print("\n📝 Prochaines étapes:")
        print("  1. Lancer l'API: cd backend && python main.py")
        print("  2. Tester: curl http://localhost:8000/api/nextcloud/status")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        return 1


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
