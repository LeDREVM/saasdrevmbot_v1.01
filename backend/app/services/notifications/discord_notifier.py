"""
Service de notification Discord
Envoie des notifications formatées vers Discord via webhook
"""

import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Service pour envoyer des notifications Discord"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialise le notifier Discord
        
        Args:
            webhook_url: URL du webhook Discord (ou utilise DISCORD_WEBHOOK_URL de l'env)
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        
        if not self.webhook_url:
            logger.warning("⚠️ DISCORD_WEBHOOK_URL non configuré")
    
    def send_daily_calendar(self, events: List[Dict]) -> bool:
        """
        Envoie le calendrier économique quotidien
        
        Args:
            events: Liste des événements économiques
            
        Returns:
            True si l'envoi a réussi
        """
        if not self.webhook_url:
            logger.error("❌ Webhook Discord non configuré")
            return False
        
        if not events:
            logger.info("ℹ️ Aucun événement à envoyer")
            return True
        
        # Grouper les événements par impact
        high_impact = [e for e in events if e.get('impact') == 'high']
        medium_impact = [e for e in events if e.get('impact') == 'medium']
        low_impact = [e for e in events if e.get('impact') == 'low']
        
        # Créer l'embed Discord
        embed = self._create_calendar_embed(events, high_impact, medium_impact, low_impact)
        
        # Envoyer la notification
        return self._send_embed(embed)
    
    def send_high_impact_alert(self, event: Dict) -> bool:
        """
        Envoie une alerte pour un événement à fort impact
        
        Args:
            event: Événement économique
            
        Returns:
            True si l'envoi a réussi
        """
        if not self.webhook_url:
            return False
        
        embed = self._create_alert_embed(event)
        return self._send_embed(embed, content="🚨 **ALERTE ÉVÉNEMENT À FORT IMPACT** 🚨")
    
    def send_upcoming_events(self, events: List[Dict], minutes: int = 30) -> bool:
        """
        Envoie une notification pour les événements à venir
        
        Args:
            events: Liste des événements
            minutes: Nombre de minutes avant l'événement
            
        Returns:
            True si l'envoi a réussi
        """
        if not self.webhook_url or not events:
            return False
        
        embed = self._create_upcoming_embed(events, minutes)
        return self._send_embed(embed, content=f"⏰ **Événements dans {minutes} minutes**")
    
    def _create_calendar_embed(self, all_events: List[Dict], high: List[Dict], 
                               medium: List[Dict], low: List[Dict]) -> Dict:
        """Crée un embed pour le calendrier quotidien"""
        
        today = datetime.now().strftime("%d/%m/%Y")
        
        embed = {
            "title": f"📊 Calendrier Économique - {today}",
            "description": f"**{len(all_events)} événements** prévus aujourd'hui",
            "color": 0x5865F2,  # Bleu Discord
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Trading Economics • SaaS DrevmBot"
            },
            "fields": []
        }
        
        # Résumé
        summary = f"🔴 **{len(high)}** Fort impact\n"
        summary += f"🟡 **{len(medium)}** Impact moyen\n"
        summary += f"🟢 **{len(low)}** Faible impact"
        
        embed["fields"].append({
            "name": "📈 Résumé",
            "value": summary,
            "inline": False
        })
        
        # Événements à fort impact
        if high:
            high_text = ""
            for event in high[:5]:  # Limiter à 5 événements
                time_str = event.get('time', '00:00')
                currency = event.get('currency', 'USD')
                event_name = event.get('event', 'Unknown')
                forecast = event.get('forecast', '-')
                previous = event.get('previous', '-')
                
                high_text += f"**{time_str}** | {currency} | {event_name}\n"
                high_text += f"Prévision: `{forecast}` | Précédent: `{previous}`\n\n"
            
            if len(high) > 5:
                high_text += f"*... et {len(high) - 5} autres événements*\n"
            
            embed["fields"].append({
                "name": "🔴 Événements à Fort Impact",
                "value": high_text or "Aucun",
                "inline": False
            })
        
        # Événements à impact moyen (limité)
        if medium:
            medium_text = ""
            for event in medium[:3]:
                time_str = event.get('time', '00:00')
                currency = event.get('currency', 'USD')
                event_name = event.get('event', 'Unknown')
                
                medium_text += f"**{time_str}** | {currency} | {event_name}\n"
            
            if len(medium) > 3:
                medium_text += f"*... et {len(medium) - 3} autres*\n"
            
            embed["fields"].append({
                "name": "🟡 Événements à Impact Moyen",
                "value": medium_text,
                "inline": False
            })
        
        # Lien vers le site
        embed["fields"].append({
            "name": "🔗 Plus d'informations",
            "value": "[Voir le calendrier complet](https://tradingeconomics.com/calendar)",
            "inline": False
        })
        
        return embed
    
    def _create_alert_embed(self, event: Dict) -> Dict:
        """Crée un embed pour une alerte d'événement"""
        
        embed = {
            "title": f"🚨 {event.get('event', 'Événement Important')}",
            "description": f"**{event.get('currency', 'USD')}** - {event.get('country', 'Unknown')}",
            "color": 0xED4245,  # Rouge
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "⏰ Heure",
                    "value": event.get('time', '00:00'),
                    "inline": True
                },
                {
                    "name": "💱 Devise",
                    "value": event.get('currency', 'USD'),
                    "inline": True
                },
                {
                    "name": "📊 Impact",
                    "value": "🔴 ÉLEVÉ",
                    "inline": True
                },
                {
                    "name": "📈 Prévision",
                    "value": event.get('forecast', '-'),
                    "inline": True
                },
                {
                    "name": "📉 Précédent",
                    "value": event.get('previous', '-'),
                    "inline": True
                },
                {
                    "name": "✅ Actuel",
                    "value": event.get('actual', '-'),
                    "inline": True
                }
            ],
            "footer": {
                "text": "Trading Economics • Alerte automatique"
            }
        }
        
        return embed
    
    def _create_upcoming_embed(self, events: List[Dict], minutes: int) -> Dict:
        """Crée un embed pour les événements à venir"""
        
        embed = {
            "title": f"⏰ Événements dans {minutes} minutes",
            "color": 0xFEE75C,  # Jaune
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [],
            "footer": {
                "text": "Trading Economics • Rappel automatique"
            }
        }
        
        for event in events[:5]:
            impact_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(event.get('impact', 'low'), '🟢')
            
            field_value = f"{impact_emoji} **{event.get('currency', 'USD')}** - {event.get('event', 'Unknown')}\n"
            field_value += f"Prévision: `{event.get('forecast', '-')}` | Précédent: `{event.get('previous', '-')}`"
            
            embed["fields"].append({
                "name": f"{event.get('time', '00:00')} - {event.get('country', 'Unknown')}",
                "value": field_value,
                "inline": False
            })
        
        return embed
    
    def _send_embed(self, embed: Dict, content: str = "") -> bool:
        """
        Envoie un embed vers Discord
        
        Args:
            embed: Embed Discord
            content: Contenu texte optionnel
            
        Returns:
            True si l'envoi a réussi
        """
        try:
            payload = {
                "embeds": [embed]
            }
            
            if content:
                payload["content"] = content
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info("✅ Notification Discord envoyée avec succès")
                return True
            else:
                logger.error(f"❌ Erreur Discord: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi Discord: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Teste la connexion au webhook Discord"""
        
        if not self.webhook_url:
            logger.error("❌ Webhook non configuré")
            return False
        
        test_embed = {
            "title": "✅ Test de connexion",
            "description": "Le bot SaaS DrevmBot est correctement configuré !",
            "color": 0x57F287,  # Vert
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "SaaS DrevmBot • Test"
            }
        }
        
        return self._send_embed(test_embed, content="🤖 **Test du bot**")
