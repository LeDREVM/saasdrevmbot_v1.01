from typing import Dict, List, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class MarkdownExporter:
    """
    Génère des rapports Markdown formatés pour Obsidian/Nextcloud
    """
    
    def __init__(self, output_dir: str = "/tmp/trading_reports", auto_upload: bool = True):
        self.output_dir = output_dir
        self.auto_upload = auto_upload
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialiser l'uploader Nextcloud si configuré
        if auto_upload:
            try:
                from .nextcloud_uploader import NextcloudUploader
                self.uploader = NextcloudUploader()
                self.uploader.ensure_reports_folder()
            except Exception as e:
                logger.warning(f"Nextcloud uploader non disponible: {e}")
                self.uploader = None
        else:
            self.uploader = None
    
    def export_daily_predictions(
        self,
        predictions: List[Dict],
        symbol: str,
        date: str = None
    ) -> str:
        """
        Génère rapport quotidien des prédictions
        
        Returns: chemin du fichier .md créé
        """
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        filename = f"predictions_{symbol}_{date}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        # Générer contenu
        md_content = self._generate_predictions_markdown(predictions, symbol, date)
        
        # Écrire fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Upload vers Nextcloud si configuré
        if self.uploader:
            try:
                self.uploader.upload_file(filepath)
                logger.info(f"📤 Rapport uploadé vers Nextcloud: {filename}")
            except Exception as e:
                logger.warning(f"Erreur upload Nextcloud: {e}")
        
        return filepath
    
    def export_stats_report(
        self,
        stats: Dict,
        symbol: str,
        period_days: int = 30
    ) -> str:
        """
        Génère rapport stats complet
        
        Returns: chemin du fichier .md créé
        """
        
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"stats_report_{symbol}_{date}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        md_content = self._generate_stats_markdown(stats, symbol, period_days)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Upload vers Nextcloud si configuré
        if self.uploader:
            try:
                self.uploader.upload_file(filepath)
                logger.info(f"📤 Rapport stats uploadé vers Nextcloud: {filename}")
            except Exception as e:
                logger.warning(f"Erreur upload Nextcloud: {e}")
        
        return filepath
    
    def _generate_predictions_markdown(
        self,
        predictions: List[Dict],
        symbol: str,
        date: str
    ) -> str:
        """Génère le contenu Markdown pour prédictions"""
        
        md = f"""---
title: Prédictions {symbol} - {date}
date: {date}
tags: [trading, predictions, {symbol.lower()}]
---

# 🎯 PRÉDICTIONS ÉVÉNEMENTS ÉCONOMIQUES

**Symbole:** {symbol}  
**Date:** {datetime.strptime(date, '%Y-%m-%d').strftime('%A %d %B %Y')}  
**Généré:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}

---

## 📊 RÉSUMÉ EXÉCUTIF

Total événements analysés: **{len(predictions)}**

"""
        
        # Stats rapides
        extreme_count = sum(1 for p in predictions if p['prediction']['risk_level'] == 'extreme')
        high_count = sum(1 for p in predictions if p['prediction']['risk_level'] == 'high')
        
        if extreme_count > 0:
            md += f"- 🔴 **{extreme_count} ALERTE(S) EXTRÊME** - Trading déconseillé\n"
        if high_count > 0:
            md += f"- 🟠 **{high_count} risque(s) élevé(s)** - Prudence requise\n"
        
        md += "\n---\n\n"
        
        # Trier par heure
        sorted_preds = sorted(predictions, key=lambda x: x['event']['time'])
        
        # Grouper par niveau de risque
        by_risk = {'extreme': [], 'high': [], 'medium': [], 'low': []}
        for pred in sorted_preds:
            risk = pred['prediction']['risk_level']
            by_risk[risk].append(pred)
        
        # Sections par risque
        risk_labels = {
            'extreme': '🔴 RISQUE EXTRÊME',
            'high': '🟠 RISQUE ÉLEVÉ',
            'medium': '🟡 RISQUE MODÉRÉ',
            'low': '🟢 RISQUE FAIBLE'
        }
        
        for risk_level in ['extreme', 'high', 'medium', 'low']:
            if by_risk[risk_level]:
                md += f"## {risk_labels[risk_level]}\n\n"
                
                for pred in by_risk[risk_level]:
                    md += self._format_prediction_block(pred)
                    md += "\n---\n\n"
        
        # Footer
        md += """
## 📚 NOTES

- Les prédictions sont basées sur l'analyse historique des événements similaires
- Le nombre de samples indique la fiabilité (>10 = haute confiance)
- Ces informations ne constituent pas un conseil financier
- Toujours vérifier les données économiques sur ForexFactory/Investing.com

## 🔗 LIENS UTILES

- [ForexFactory Calendar](https://www.forexfactory.com/calendar)
- [Investing.com Economic Calendar](https://www.investing.com/economic-calendar/)
- [TradingView {symbol}](https://www.tradingview.com/symbols/{symbol}/)

"""
        
        return md
    
    def _format_prediction_block(self, pred: Dict) -> str:
        """Formate un bloc de prédiction individuel"""
        
        event = pred['event']
        prediction = pred['prediction']
        
        # Direction dominante
        dir_probs = prediction['direction_probability']
        dominant_dir = max(dir_probs, key=dir_probs.get)
        dominant_prob = dir_probs[dominant_dir]
        
        dir_arrows = {'up': '📈', 'down': '📉', 'neutral': '↔️'}
        dir_text = {'up': 'HAUSSIER', 'down': 'BAISSIER', 'neutral': 'NEUTRE'}
        
        block = f"""### {event['time']} - {event['event_name']}

**💱 Devise:** {event['currency']} | **Impact:** {event['impact_level']}

#### 📊 Données Économiques

| Indicateur | Valeur |
|------------|--------|
| Prévu | `{event['forecast'] or 'N/A'}` |
| Précédent | `{event['previous'] or 'N/A'}` |

#### 🎯 PRÉDICTION

**Mouvement attendu:** `{prediction['expected_movement_pips']} pips`  
**Confiance:** {prediction['confidence'].upper()} (basé sur {prediction['historical_samples']} événements)  
**Volatilité attendue:** +{prediction['volatility_increase_expected']}%

**Direction probable:**
- {dir_arrows['up']} Haussier: {dir_probs['up']}%
- {dir_arrows['down']} Baissier: {dir_probs['down']}%
- {dir_arrows['neutral']} Neutre: {dir_probs['neutral']}%

> {dir_arrows[dominant_dir]} **Tendance dominante:** {dir_text[dominant_dir]} ({dominant_prob}%)

#### 💡 RECOMMANDATION

{pred['recommendation']}

**⏰ Timing:** {pred['time_until_event']}

"""
        
        return block
    
    def _generate_stats_markdown(
        self,
        stats: Dict,
        symbol: str,
        period_days: int
    ) -> str:
        """Génère le contenu Markdown pour stats"""
        
        date = datetime.now().strftime("%Y-%m-%d")
        summary = stats.get('summary', {})
        
        md = f"""---
title: Rapport Stats {symbol}
date: {date}
period: {period_days} jours
tags: [trading, stats, analysis, {symbol.lower()}]
---

# 📈 RAPPORT STATISTIQUES - {symbol}

**Période analysée:** {period_days} jours  
**Généré le:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}

---

## 📊 MÉTRIQUES GLOBALES

| Métrique | Valeur |
|----------|--------|
| Total événements | **{summary.get('total_events', 0)}** |
| Taux d'impact réel | **{summary.get('impact_rate', 0)}%** |
| Mouvement moyen | **{summary.get('avg_movement_pips', 0)} pips** |
| Augmentation volatilité | **+{summary.get('volatility_increase', 0)}%** |

---

## 📈 DISTRIBUTION DIRECTION

"""
        
        # Direction stats avec barres ASCII
        dir_stats = summary.get('direction_stats', {})
        total = summary.get('total_events', 1)
        
        for direction, count in dir_stats.items():
            percentage = (count / total * 100) if total > 0 else 0
            bar_length = int(percentage / 2)  # Max 50 chars
            bar = '█' * bar_length
            
            emoji = {'up': '🟢', 'down': '🔴', 'neutral': '⚪'}.get(direction, '⚪')
            label = direction.upper()
            
            md += f"**{emoji} {label}:** {count} événements ({percentage:.1f}%)\n"
            md += f"`{bar}`\n\n"
        
        md += "\n---\n\n"
        
        # Top events par type
        by_event = summary.get('by_event_type', {})
        
        if by_event:
            md += "## 🏆 TOP 10 ÉVÉNEMENTS PAR IMPACT\n\n"
            md += "| # | Événement | Occurrences | Mouvement Moyen | Impact Moyen |\n"
            md += "|---|-----------|-------------|-----------------|---------------|\n"
            
            for idx, (event_name, data) in enumerate(list(by_event.items())[:10], 1):
                md += f"| {idx} | {event_name[:40]} | {data['count']} | {data['avg_pips']} pips | {data['avg_impact']:.4f} |\n"
            
            md += "\n"
        
        # Top movers
        top_events = stats.get('top_impact_events', [])
        
        if top_events:
            md += "\n---\n\n## 🚀 TOP 10 MOUVEMENTS LES PLUS IMPORTANTS\n\n"
            
            for idx, evt in enumerate(top_events[:10], 1):
                event_data = evt['event']
                impact_data = evt['impact']
                
                dir_emoji = {'up': '📈', 'down': '📉', 'neutral': '↔️'}.get(impact_data['direction'], '↔️')
                
                md += f"### {idx}. {event_data['date']} - {event_data['event_name']}\n\n"
                md += f"- **Mouvement:** {impact_data['movement_pips']} pips {dir_emoji}\n"
                md += f"- **Direction:** {impact_data['direction'].upper()}\n"
                md += f"- **Variation 1h:** {impact_data['price_change_1h']}%\n"
                md += f"- **Variation 4h:** {impact_data['price_change_4h']}%\n\n"
        
        # Heatmap texte
        heatmap = stats.get('heatmap_data', {})
        
        if heatmap:
            md += "\n---\n\n## 🌡️ HEATMAP VOLATILITÉ (Jour × Heure)\n\n"
            md += "_Volatilité moyenne par session (en pips)_\n\n"
            
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            hours_display = [0, 6, 9, 12, 15, 18, 21]  # Heures clés
            
            # Header
            md += "| Jour | "
            for hour in hours_display:
                md += f"{hour:02d}h | "
            md += "\n|------|"
            md += "------|" * len(hours_display)
            md += "\n"
            
            # Lignes
            for day in days_order:
                if day in heatmap:
                    md += f"| **{day[:3]}** | "
                    for hour in hours_display:
                        val = heatmap[day].get(hour, 0)
                        md += f"{val:.1f} | "
                    md += "\n"
            
            md += "\n"
        
        # Footer
        md += """
---

## 📝 INTERPRÉTATION

### Taux d'impact réel
Pourcentage d'événements qui ont réellement causé une augmentation significative de la volatilité (>1.5x la volatilité pré-event).

### Mouvement moyen
Amplitude moyenne du mouvement de prix dans les 4h suivant l'événement, mesurée en pips.

### Direction
- **Haussier:** Prix a clôturé >0.1% au-dessus du prix d'événement après 4h
- **Baissier:** Prix a clôturé >0.1% en-dessous
- **Neutre:** Variation <0.1%

---

## 🔗 EXPORT & SYNCHRONISATION

Ce rapport est automatiquement sauvegardé sur:
- 📁 Nextcloud: `/ForexBot/reports/`
- 💾 Base de données locale
- 📊 Cache Redis (1h)

Pour forcer une régénération: `POST /api/stats/refresh/{symbol}`

---

*Rapport généré automatiquement par le système d'analyse de corrélation.*
*Ces données ne constituent pas un conseil en investissement.*
"""
        
        return md
    
    def export_weekly_summary(
        self,
        weekly_predictions: List[Dict],
        symbol: str
    ) -> str:
        """Génère résumé hebdomadaire"""
        
        # Grouper par jour
        by_day = {}
        for pred in weekly_predictions:
            day = pred['event']['date']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(pred)
        
        filename = f"weekly_summary_{symbol}_{datetime.now().strftime('%Y-W%W')}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        md = f"""---
title: Résumé Hebdomadaire {symbol}
week: {datetime.now().strftime('%Y-W%W')}
tags: [trading, weekly, {symbol.lower()}]
---

# 📅 RÉSUMÉ HEBDOMADAIRE - {symbol}

**Semaine:** {datetime.now().strftime('%Y-W%W')}  
**Généré:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}

---

## 📊 VUE D'ENSEMBLE

Total événements à surveiller: **{len(weekly_predictions)}**

"""
        
        # Stats rapides
        extreme_total = sum(1 for p in weekly_predictions if p['prediction']['risk_level'] == 'extreme')
        high_total = sum(1 for p in weekly_predictions if p['prediction']['risk_level'] == 'high')
        
        md += f"- 🔴 Risque EXTRÊME: {extreme_total}\n"
        md += f"- 🟠 Risque ÉLEVÉ: {high_total}\n"
        md += f"- 🟡 Risque MODÉRÉ: {len(weekly_predictions) - extreme_total - high_total}\n\n"
        
        md += "---\n\n"
        
        # Par jour
        for day in sorted(by_day.keys()):
            day_name = datetime.strptime(day, '%Y-%m-%d').strftime('%A %d %B')
            predictions = by_day[day]
            
            md += f"## {day_name}\n\n"
            
            for pred in sorted(predictions, key=lambda x: x['event']['time']):
                event = pred['event']
                prediction = pred['prediction']
                
                risk_emoji = {
                    'extreme': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(prediction['risk_level'], '⚪')
                
                md += f"- **{event['time']}** {risk_emoji} {event['event_name']}\n"
                md += f"  - {event['currency']} | {prediction['expected_movement_pips']} pips attendus\n"
            
            md += "\n"
        
        md += """
---

## 💡 CONSEILS DE LA SEMAINE

1. **Planifier les trades** en évitant les 2h autour des événements 🔴 EXTRÊME
2. **Réduire la taille** des positions les jours à haute volatilité
3. **Surveiller** particulièrement les événements US (USD impact majeur)
4. **Préparer** des plans de contingence pour les annonces surprise

---

*Alertes individuelles seront envoyées 2h avant chaque événement high/extreme.*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        # Upload vers Nextcloud si configuré
        if self.uploader:
            try:
                self.uploader.upload_file(filepath)
                logger.info(f"📤 Résumé hebdomadaire uploadé vers Nextcloud: {filename}")
            except Exception as e:
                logger.warning(f"Erreur upload Nextcloud: {e}")
        
        return filepath