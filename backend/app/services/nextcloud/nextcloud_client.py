import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, List
import os
import logging
from datetime import datetime
from pathlib import Path
import mimetypes

logger = logging.getLogger(__name__)

class NextcloudClient:
    """
    Client Nextcloud utilisant WebDAV pour upload automatique
    """
    
    def __init__(
        self, 
        base_url: str,
        username: str,
        password: str,
        root_folder: str = "TradingBot"
    ):
        """
        Args:
            base_url: https://ledream.kflw.io
            username: Ton username Nextcloud
            password: App password (généré dans Nextcloud Settings > Security)
            root_folder: Dossier racine pour le bot
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.root_folder = root_folder
        
        # WebDAV endpoint
        self.webdav_url = f"{self.base_url}/remote.php/dav/files/{username}"
        
        # Session avec auth
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.headers.update({
            'User-Agent': 'TradingBot/1.0',
            'OCS-APIRequest': 'true'
        })
        
        # Créer structure de dossiers
        self._init_folder_structure()
    
    def _init_folder_structure(self):
        """Crée la structure de dossiers initiale"""
        
        folders = [
            f"/{self.root_folder}",
            f"/{self.root_folder}/alerts",
            f"/{self.root_folder}/alerts/daily",
            f"/{self.root_folder}/alerts/weekly",
            f"/{self.root_folder}/alerts/logs",
            f"/{self.root_folder}/stats",
            f"/{self.root_folder}/stats/monthly",
            f"/{self.root_folder}/calendar",
            f"/{self.root_folder}/calendar/daily",
            f"/{self.root_folder}/calendar/weekly",
            f"/{self.root_folder}/exports",
        ]
        
        for folder in folders:
            self.create_folder(folder)
    
    def create_folder(self, path: str) -> bool:
        """
        Crée un dossier sur Nextcloud (via MKCOL WebDAV)
        
        Returns: True si créé ou existe déjà
        """
        url = f"{self.webdav_url}{path}"
        
        try:
            response = self.session.request("MKCOL", url)
            
            # 201 = créé, 405 = existe déjà
            if response.status_code in [201, 405]:
                logger.debug(f"✅ Dossier OK: {path}")
                return True
            else:
                logger.warning(f"Erreur création dossier {path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur création dossier {path}: {e}")
            return False
    
    def upload_file(
        self, 
        local_path: str, 
        remote_path: str,
        overwrite: bool = True
    ) -> bool:
        """
        Upload un fichier vers Nextcloud
        
        Args:
            local_path: Chemin local du fichier
            remote_path: Chemin distant (ex: /TradingBot/alerts/daily/report.md)
            overwrite: Écraser si existe
        
        Returns: True si succès
        """
        
        if not os.path.exists(local_path):
            logger.error(f"Fichier local introuvable: {local_path}")
            return False
        
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            # Lire le fichier
            with open(local_path, 'rb') as f:
                file_content = f.read()
            
            # Déterminer le Content-Type
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            headers = {'Content-Type': content_type}
            
            # Upload via PUT
            response = self.session.put(
                url,
                data=file_content,
                headers=headers
            )
            
            if response.status_code in [200, 201, 204]:
                file_size = os.path.getsize(local_path)
                logger.info(f"✅ Upload réussi: {remote_path} ({file_size} bytes)")
                return True
            else:
                logger.error(f"Erreur upload {remote_path}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception upload {remote_path}: {e}")
            return False
    
    def upload_content(
        self,
        content: str,
        remote_path: str,
        content_type: str = 'text/markdown'
    ) -> bool:
        """
        Upload du contenu directement (sans fichier local)
        
        Args:
            content: Contenu à uploader (str ou bytes)
            remote_path: Chemin distant
            content_type: MIME type
        """
        
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            headers = {'Content-Type': content_type}
            
            response = self.session.put(
                url,
                data=content,
                headers=headers
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ Upload contenu réussi: {remote_path}")
                return True
            else:
                logger.error(f"Erreur upload contenu {remote_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception upload contenu: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Télécharge un fichier depuis Nextcloud
        """
        
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"✅ Download réussi: {remote_path} -> {local_path}")
                return True
            else:
                logger.error(f"Erreur download {remote_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception download: {e}")
            return False
    
    def list_folder(self, remote_path: str) -> List[Dict]:
        """
        Liste le contenu d'un dossier
        
        Returns: Liste de dicts avec {name, type, size, modified}
        """
        
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            # PROPFIND WebDAV pour lister
            response = self.session.request(
                "PROPFIND",
                url,
                headers={'Depth': '1'}
            )
            
            if response.status_code == 207:  # Multi-Status
                # Parser XML response (simplification)
                # En production, utiliser xml.etree.ElementTree
                logger.info(f"✅ Liste dossier: {remote_path}")
                return []  # TODO: Parser XML
            else:
                logger.error(f"Erreur liste {remote_path}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Exception liste dossier: {e}")
            return []
    
    def delete_file(self, remote_path: str) -> bool:
        """Supprime un fichier sur Nextcloud"""
        
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            response = self.session.delete(url)
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Fichier supprimé: {remote_path}")
                return True
            else:
                logger.error(f"Erreur suppression {remote_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception suppression: {e}")
            return False
    
    def get_share_link(self, remote_path: str, password: Optional[str] = None) -> Optional[str]:
        """
        Crée un lien de partage public pour un fichier
        
        Returns: URL du lien de partage
        """
        
        # API OCS Share
        share_url = f"{self.base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
        
        data = {
            'path': remote_path,
            'shareType': 3,  # Public link
        }
        
        if password:
            data['password'] = password
        
        try:
            response = self.session.post(
                share_url,
                data=data,
                headers={'OCS-APIRequest': 'true'}
            )
            
            if response.status_code == 200:
                # Parser XML response pour extraire l'URL
                # Simplification - en prod, parser correctement
                logger.info(f"✅ Lien de partage créé: {remote_path}")
                return f"{self.base_url}/s/XXXXX"  # Placeholder
            else:
                logger.error(f"Erreur création lien: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception création lien: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test la connexion à Nextcloud
        
        Returns: True si connecté
        """
        
        url = f"{self.webdav_url}/"
        
        try:
            response = self.session.request("PROPFIND", url, headers={'Depth': '0'})
            
            if response.status_code == 207:
                logger.info(f"✅ Connexion Nextcloud OK: {self.base_url}")
                return True
            else:
                logger.error(f"Connexion Nextcloud échouée: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception test connexion: {e}")
            return False