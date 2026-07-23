# Kyrrah Assist — Dashboard scoring GoldXrodgers

Dashboard live qui note 5 paires (XAU/USD, USD/JPY, CAD/JPY, EUR/USD, XBR/USD) sur
**5 piliers** : Wyckoff · ICT/SMC · Ichimoku · Fibonacci · RSI/CCI → score `/10` +
signal BUY/SELL/WAIT avec entrée/SL/TP calculés par ATR.

## Deux modes d'analyse

### 1. Scan automatique (données réelles Finnhub)
- Bouton **Scanner** → récupère les bougies via l'API Finnhub gratuite (`finnhub.io`)
- Calcule le score localement en JS (aucun backend requis)
- Sans clé API → mode démo (données figées)

### 2. Analyse par capture d'écran (IA — template GoldXrodgers) 🆕
Gestionnaire de capture intégré :
- **Glisser-déposer**, **clic pour parcourir**, ou **Ctrl+V** pour coller une capture
- Fonctionne avec TradingView, MT5, Fusion Markets
- Envoie l'image (base64) au **webhook n8n** → Claude Vision analyse selon le
  template DREVM/GoldXrodgers → renvoie le score et l'affiche dans l'UI 5 piliers

## Connexion au pipeline (carte « Connexion pipeline »)

| Champ | Rôle |
|---|---|
| **Supabase URL / key** | Pousse chaque scan dans la table `trade_signals` |
| **Signal server URL** | `http://VPS_IP:5000/signal` — bouton « Envoyer à MetaTrader » |
| **Webhook n8n IA** | `http://VPS_IP:5678/webhook/screenshot-score` — analyse capture |
| **Auto-push** | Envoie automatiquement chaque scan vers Supabase |

Toute la config est persistée en `localStorage` (rien n'est envoyé ailleurs).

## Format attendu du webhook IA (réponse)

Le webhook n8n doit renvoyer un JSON de ce type (le dashboard le mappe automatiquement) :

```json
{
  "score": 8.2,
  "direction": "BUY",
  "entry_price": 3352.4,
  "stop_loss": 3344.1,
  "take_profit_1": 3368.9,
  "take_profit_2": 3380.0,
  "risk_reward": 3.0,
  "rsi": 58,
  "pillars": { "wyckoff": 8, "ict": 9, "ichimoku": 7, "fibonacci": 9, "rsi": 8 },
  "ai_analysis": "MSS haussier confirmé, FVG H1 comblé, entrée sur OB + Fib 0.618..."
}
```

Si `pillars` est absent, le dashboard répartit le score global sur les 5 piliers.

## Déploiement

Fichier **100 % statique** — aucune build step :
- Ouvre `index.html` directement, ou
- Sers-le via Netlify / le `frontend/` existant du projet, ou
- Ajoute-le derrière le n8n du VPS Hostinger

## Intégration n8n

Le workflow dédié `n8n/kyrrah_screenshot_workflow.json` reçoit la capture base64,
la donne à Claude Vision avec le prompt GoldXrodgers, et renvoie le score au format
ci-dessus. Voir `N8N_TRADINGVIEW_AI_GUIDE.md` pour l'installation complète.
