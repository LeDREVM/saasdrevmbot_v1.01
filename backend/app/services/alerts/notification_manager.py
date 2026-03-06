import requests
from typing import Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Gère l'envoi de notifications multi-canal (Discord, Telegram)
    """
    
    def __init__(self, discord_webhook: str, telegram_token: str = None, telegram_chat_id: str = None):
        self.discord_webhook = discord_webhook
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
    
    def send_predictive_alert(
        self,
        prediction: Dict,
        channels: List[str] = ['discord']
    ):
        """
        Envoie une alerte prédictive formatée
        
        channels: ['discord', 'telegram']
        """
        
        if 'discord' in channels and self.discord_webhook:
            self._send_discord_alert(prediction)
        
        if 'telegram' in channels and self.telegram_token:
            self._send_telegram_alert(prediction)
    
    def _send_discord_alert(self, prediction: Dict):
        """Envoie alerte Discord avec embed riche"""
        
        event = prediction['event']
        pred = prediction['prediction']
        symbol = prediction['symbol']
        
        # Couleur selon risk level
        colors = {
            'extreme': 0xFF0000,  # Rouge
            'high': 0xFF9900,     # Orange
            'medium': 0xFFCC00,   # Jaune
            'low': 0x00FF00       # Vert
        }
        color = colors.get(pred['risk_level'], 0x0099FF)
        
        # Icône selon risk
        risk_icons = {
            'extreme': '🔴🔴🔴',
            'high': '🟠🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        risk_icon = risk_icons.get(pred['risk_level'], '⚪')
        
        # Direction dominante
        dir_probs = pred['direction_probability']
        dominant_dir = max(dir_probs, key=dir_probs.get)
        dir_emojis = {'up': '📈', 'down': '📉', 'neutral': '↔️'}
        
        embed = {
            "title": f"{risk_icon} ALERTE PRÉDICTIVE - {event['event_name']}",
            "description": f"**{symbol}** | {prediction['time_until_event']}",
            "color": color,
            "fields": [
                {
                    "name": "⏰ Timing",
                    "value": f"📅 {event['date']}\n🕐 {event['time']}",
                    "inline": True
                },
                {
                    "name": "💱 Devise",
                    "value": f"**{event['currency']}**\nImpact: {event['impact_level']}",
                    "inline": True
                },
                {
                    "name": "📊 Données Économiques",
                    "value": (
                        f"Prévu: `{event['forecast'] or 'N/A'}`\n"
                        f"Précédent: `{event['previous'] or 'N/A'}`"
                    ),
                    "inline": True
                },
                {
                    "name": "🎯 PRÉDICTION",
                    "value": (
                        f"**Mouvement attendu:** {pred['expected_movement_pips']} pips\n"
                        f"**Confiance:** {pred['confidence'].upper()} ({pred['historical_samples']} samples)\n"
                        f"**Volatilité:** +{pred['volatility_increase_expected']}%"
                    ),
                    "inline": False
                },
                {
                    "name": "📈 Direction Probable",
                    "value": (
                        f"{dir_emojis['up']} Haussier: {dir_probs['up']}%\n"
                        f"{dir_emojis['down']} Baissier: {dir_probs['down']}%\n"
                        f"{dir_emojis['neutral']} Neutre: {dir_probs['neutral']}%"
                    ),
                    "inline": True
                },
                {
                    "name": "⚠️ Niveau de Risque",
                    "value": f"**{pred['risk_level'].upper()}**",
                    "inline": True
                },
                {
                    "name": "💡 RECOMMANDATION",
                    "value": prediction['recommendation'],
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Prédiction basée sur analyse historique • Ne constitue pas un conseil financier"
            }
        }
        
        payload = {
            "username": "📊 Trading Alert System",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",  # Icon trading
            "embeds": [embed]
        }
        
        try:
            response = requests.post(self.discord_webhook, json=payload)
            response.raise_for_status()
            logger.info(f"✅ Alerte Discord envoyée: {event['event_name']}")
        except Exception as e:
            logger.error(f"Erreur envoi Discord: {e}")
    
    def _send_telegram_alert(self, prediction: Dict):
        """Envoie alerte Telegram formatée"""
        
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        event = prediction['event']
        pred = prediction['prediction']
        symbol = prediction['symbol']
        
        # Format message Telegram (Markdown)
        message = f"""
🔔 **ALERTE PRÉDICTIVE**

**{event['event_name']}**
{symbol} • {prediction['time_until_event']}

📅 {event['date']} à {event['time']}
💱 {event['currency']} • Impact {event['impact_level']}

**🎯 PRÉDICTION:**
- Mouvement attendu: **{pred['expected_movement_pips']} pips**
- Confiance: {pred['confidence'].upper()}
- Volatilité: +{pred['volatility_increase_expected']}%

**📈 Direction:**
- Haussier: {pred['direction_probability']['up']}%
- Baissier: {pred['direction_probability']['down']}%

**⚠️ Risque: {pred['risk_level'].upper()}**

**💡 CONSEIL:**
{prediction['recommendation']}

_Basé sur {pred['historical_samples']} événements historiques_
        """.strip()
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"✅ Alerte Telegram envoyée: {event['event_name']}")
        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")
    
    def send_daily_summary(
        self,
        upcoming_events: List[Dict],
        channels: List[str] = ['discord']
    ):
        """Envoie un résumé quotidien des événements à venir"""
        
        if not upcoming_events:
            return
        
        # Trier par niveau de risque
        sorted_events = sorted(
            upcoming_events,
            key=lambda x: ['extreme', 'high', 'medium', 'low'].index(x['prediction']['risk_level'])
        )
        
        # Grouper par niveau de risque
        by_risk = {}
        for event in sorted_events:
            risk = event['prediction']['risk_level']
            if risk not in by_risk:
                by_risk[risk] = []
            by_risk[risk].append(event)
        
        if 'discord' in channels:
            self._send_discord_daily_summary(by_risk)
    
    def _send_discord_daily_summary(self, events_by_risk: Dict):
        """Résumé quotidien Discord"""
        
        embed = {
            "title": "📅 CALENDRIER ÉCONOMIQUE DU JOUR",
            "description": f"Résumé des événements à fort impact • {datetime.now().strftime('%d/%m/%Y')}",
            "color": 0x0099FF,
            "fields": []
        }
        
        risk_emojis = {
            'extreme': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        for risk_level in ['extreme', 'high', 'medium', 'low']:
            if risk_level in events_by_risk:
                events = events_by_risk[risk_level]
                
                value = ""
                for event in events[:5]:  # Max 5 par niveau
                    evt = event['event']
                    pred = event['prediction']
                    value += f"• **{evt['time']}** - {evt['currency']} - {evt['event_name'][:40]}\n"
                    value += f"  ↳ {pred['expected_movement_pips']} pips attendus\n"
                
                embed['fields'].append({
                    "name": f"{risk_emojis[risk_level]} Risque {risk_level.upper()} ({len(events)} événements)",
                    "value": value or "Aucun",
                    "inline": False
                })
        
        embed['footer'] = {
            "text": "Alertes individuelles seront envoyées 2h avant chaque événement high/extreme"
        }
        
        payload = {
            "username": "📊 Trading Alert System",
            "embeds": [embed]
        }
        
        try:
            response = requests.post(self.discord_webhook, json=payload)
            response.raise_for_status()
            logger.info("✅ Résumé quotidien envoyé")
        except Exception as e:
            logger.error(f"Erreur envoi résumé: {e}")