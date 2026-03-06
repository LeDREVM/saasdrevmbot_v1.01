import requests
from typing import Optional
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class NextcloudUploader:
    """
    Upload des rapports Markdown vers Nextcloud
    """
    
    def __init__(self):
        self.base_url = settings.NEXTCLOUD_URL
        self.share_folder = settings.NEXTCLOUD_SHARE_FOLDER
        self.username = settings.NEXTCLOUD_USERNAME
        self.password = settings.NEXTCLOUD_PASSWORD
        
        # URL WebDAV pour upload
        if self.base_url and self.username:
            self.webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}"
        else:
            self.webdav_url = None
    
    def upload_file(self, local_path: str, remote_filename: str = None) -> bool:
        """
        Upload un fichier vers Nextcloud
        
        Args:
            local_path: Chemin local du fichier
            remote_filename: Nom du fichier sur Nextcloud (optionnel)
        
        Returns:
            True si succès, False sinon
        """
        
        if not self.webdav_url or not self.username or not self.password:
            logger.warning("Nextcloud non configuré, upload ignoré")
            return False
        
        try:
            # Lire le fichier
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Nom du fichier distant
            if remote_filename is None:
                remote_filename = Path(local_path).name
            
            # URL complète pour l'upload
            upload_url = f"{self.webdav_url}/ForexBot/reports/{remote_filename}"
            
            # Upload via WebDAV
            response = requests.put(
                upload_url,
                data=content,
                auth=(self.username, self.password),
                headers={'Content-Type': 'text/markdown'}
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ Fichier uploadé vers Nextcloud: {remote_filename}")
                return True
            else:
                logger.error(f"❌ Erreur upload Nextcloud: {response.status_code}")
                return False
                
        except FileNotFoundError:
            logger.error(f"Fichier local non trouvé: {local_path}")
            return False
        except Exception as e:
            logger.error(f"Erreur upload Nextcloud: {e}")
            return False
    
    def upload_to_share(self, local_path: str) -> Optional[str]:
        """
        Upload vers le dossier partagé public
        
        Returns:
            URL du fichier partagé si succès
        """
        
        if not self.base_url or not self.share_folder:
            logger.warning("Dossier partagé Nextcloud non configuré")
            return None
        
        try:
            filename = Path(local_path).name
            
            # Pour un dossier partagé public, utiliser l'API de partage
            # Note: Nécessite un token de partage avec permissions d'écriture
            share_url = f"{self.base_url}{self.share_folder}/{filename}"
            
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Upload vers le partage public (si configuré avec upload)
            response = requests.put(
                share_url,
                data=content,
                headers={'Content-Type': 'text/markdown'}
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ Fichier uploadé vers partage: {filename}")
                return share_url
            else:
                logger.warning(f"Upload vers partage échoué: {response.status_code}")
                # Fallback: upload normal
                return self.upload_file(local_path, filename)
                
        except Exception as e:
            logger.error(f"Erreur upload vers partage: {e}")
            return None
    
    def create_folder(self, folder_path: str) -> bool:
        """
        Crée un dossier sur Nextcloud
        
        Args:
            folder_path: Chemin du dossier (ex: "ForexBot/reports")
        
        Returns:
            True si succès ou dossier existe déjà
        """
        
        if not self.webdav_url or not self.username or not self.password:
            return False
        
        try:
            folder_url = f"{self.webdav_url}/{folder_path}"
            
            response = requests.request(
                'MKCOL',
                folder_url,
                auth=(self.username, self.password)
            )
            
            if response.status_code in [201, 405]:  # 405 = dossier existe déjà
                logger.info(f"✅ Dossier créé/existe: {folder_path}")
                return True
            else:
                logger.warning(f"Création dossier échouée: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur création dossier: {e}")
            return False
    
    def ensure_reports_folder(self):
        """S'assure que le dossier ForexBot/reports existe"""
        self.create_folder("ForexBot")
        self.create_folder("ForexBot/reports")
