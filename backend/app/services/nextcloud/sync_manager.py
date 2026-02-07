from typing import Dict, Optional
import os
from datetime import datetime
import logging

from app.services.nextcloud.nextcloud_client import NextcloudClient
from app.services.alerts.markdown_exporter import MarkdownExporter

logger = logging.getLogger(__name__)

class NextcloudSyncManager:
    """
    Gère la synchronisation automatique avec Nextcloud
    """
    
    def __init__(
        self,
        nextcloud_url: str,
        username: str,
        password: str
    ):
        self.nc_client = NextcloudClient(nextcloud_url, username, password)
        self.exporter = MarkdownExporter()
    
    def sync_daily_alert_report(
        self,
        predictions: list,
        symbol: str,
        date: str = None
    ) -> Dict:
        """
        Génère et upload le rapport quotidien d'alertes
        
        Returns: {
            'local_path': str,
            'remote_path': str,
            'uploaded': bool,
            'share_link': str
        }
        """
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # 1. Générer le rapport MD en local
            local_path = self.exporter.export_daily_predictions(
                predictions=predictions,
                symbol=symbol,
                date=date
            )
            
            # 2. Définir chemin distant
            filename = os.path.basename(local_path)
            remote_path = f"/TradingBot/alerts/daily/{filename}"
            
            # 3. Upload vers Nextcloud
            uploaded = self.nc_client.upload_file(local_path, remote_path)
            
            # 4. Créer lien de partage (optionnel)
            share_link = None
            if uploaded:
                share_link = self.nc_client.get_share_link(remote_path)
            
            result = {
                'local_path': local_path,
                'remote_path': remote_path,
                'uploaded': uploaded,
                'share_link': share_link,
                'symbol': symbol,
                'date': date
            }
            
            if uploaded:
                logger.info(f"✅ Rapport quotidien synchronisé: {symbol} - {date}")
            else:
                logger.error(f"❌ Échec sync rapport quotidien: {symbol} - {date}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur sync_daily_alert_report: {e}")
            return {
                'uploaded': False,
                'error': str(e)
            }
    
    def sync_weekly_summary(
        self,
        predictions: list,
        symbol: str
    ) -> Dict:
        """Upload résumé hebdomadaire"""
        
        try:
            # Générer rapport
            local_path = self.exporter.export_weekly_summary(predictions, symbol)
            
            # Chemin distant
            filename = os.path.basename(local_path)
            remote_path = f"/TradingBot/alerts/weekly/{filename}"
            
            # Upload
            uploaded = self.nc_client.upload_file(local_path, remote_path)
            
            return {
                'local_path': local_path,
                'remote_path': remote_path,
                'uploaded': uploaded,
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Erreur sync_weekly_summary: {e}")
            return {'uploaded': False, 'error': str(e)}
    
    def sync_stats_report(
        self,
        stats: Dict,
        symbol: str,
        period_days: int = 30
    ) -> Dict:
        """Upload rapport stats"""
        
        try:
            # Générer rapport
            local_path = self.exporter.export_stats_report(stats, symbol, period_days)
            
            # Chemin distant
            filename = os.path.basename(local_path)
            remote_path = f"/TradingBot/stats/{filename}"
            
            # Upload
            uploaded = self.nc_client.upload_file(local_path, remote_path)
            
            return {
                'local_path': local_path,
                'remote_path': remote_path,
                'uploaded': uploaded,
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Erreur sync_stats_report: {e}")
            return {'uploaded': False, 'error': str(e)}
    
    def sync_calendar_data(
        self,
        events: list,
        filename: str = None
    ) -> Dict:
        """Upload données calendrier économique"""
        
        if filename is None:
            filename = f"calendar_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        try:
            import json
            
            # Convertir événements en JSON
            events_data = [
                {
                    'date': e.date,
                    'time': e.time,
                    'currency': e.currency,
                    'event': e.event,
                    'impact': e.impact.value,
                    'actual': e.actual,
                    'forecast': e.forecast,
                    'previous': e.previous
                }
                for e in events
            ]
            
            content = json.dumps(events_data, indent=2, ensure_ascii=False)
            
            # Upload direct
            remote_path = f"/TradingBot/calendar/{filename}"
            uploaded = self.nc_client.upload_content(
                content=content,
                remote_path=remote_path,
                content_type='application/json'
            )
            
            return {
                'remote_path': remote_path,
                'uploaded': uploaded,
                'events_count': len(events)
            }
            
        except Exception as e:
            logger.error(f"Erreur sync_calendar_data: {e}")
            return {'uploaded': False, 'error': str(e)}
    
    def sync_alert_log(
        self,
        alert_log: Dict
    ) -> Dict:
        """
        Upload log d'une alerte individuelle
        Utilisé pour historique détaillé
        """
        
        try:
            # Créer MD pour cette alerte
            md_content = self._format_alert_log_md(alert_log)
            
            # Filename avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alert_{alert_log['symbol']}_{timestamp}.md"
            
            remote_path = f"/TradingBot/alerts/logs/{filename}"
            
            # Upload
            uploaded = self.nc_client.upload_content(
                content=md_content,
                remote_path=remote_path,
                content_type='text/markdown'
            )
            
            return {
                'remote_path': remote_path,
                'uploaded': uploaded
            }
            
        except Exception as e:
            logger.error(f"Erreur sync_alert_log: {e}")
            return {'uploaded': False, 'error': str(e)}
    
    def _format_alert_log_md(self, log: Dict) -> str:
        """Formate un log d'alerte en Markdown"""
        
        md = f"""---
alert_id: {log.get('id', 'N/A')}
date: {datetime.now().strftime('%Y-%m-%d')}
symbol: {log.get('symbol', 'N/A')}
---

# 🔔 Log Alerte - {log.get('event_name', 'N/A')}

**Événement:** {log.get('event_name')}  
**Date/Heure:** {log.get('event_date')} {log.get('event_time')}  
**Devise:** {log.get('currency')}  
**Symbole:** {log.get('symbol')}

## 🎯 Prédiction

- **Mouvement prédit:** {log.get('predicted_pips', 0)} pips
- **Direction prédite:** {log.get('predicted_direction', 'N/A').upper()}
- **Niveau de risque:** {log.get('risk_level', 'N/A').upper()}
- **Confiance:** {log.get('confidence', 'N/A').upper()}

## 📊 Résultat Réel

"""
        
        if log.get('actual_pips'):
            md += f"""- **Mouvement réel:** {log.get('actual_pips')} pips
- **Direction réelle:** {log.get('actual_direction', 'N/A').upper()}
- **Prédiction correcte:** {'✅ OUI' if log.get('prediction_accurate') else '❌ NON'}
"""
        else:
            md += "*Résultat pas encore disponible*\n"
        
        md += f"""
## 📨 Envoi

- **Envoyé le:** {log.get('sent_at', 'N/A')}
- **Canaux:** {', '.join(log.get('channels_sent', []))}
- **Statut:** {log.get('delivery_status', 'N/A')}

---

*Log généré automatiquement par TradingBot*
"""
        
        return md
    
    def test_sync(self) -> Dict:
        """
        Test la connexion et upload un fichier de test
        """
        
        # Test connexion
        connected = self.nc_client.test_connection()
        
        if not connected:
            return {
                'success': False,
                'message': 'Connexion Nextcloud échouée'
            }
        
        # Upload fichier test
        test_content = f"""# Test Sync TradingBot

Date: {datetime.now().isoformat()}

✅ Connexion Nextcloud OK
✅ Upload fonctionnel

Ce fichier peut être supprimé.
"""
        
        remote_path = f"/TradingBot/test_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        uploaded = self.nc_client.upload_content(
            content=test_content,
            remote_path=remote_path
        )
        
        return {
            'success': uploaded,
            'message': 'Test sync réussi ✅' if uploaded else 'Test sync échoué ❌',
            'remote_path': remote_path if uploaded else None
        }