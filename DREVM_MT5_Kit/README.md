# 🎯 DREVM MT5 Kit — Gestion complète MetaTrader

**GoldXrodgers / DREVM — Négus Dja**
Broker : Fusion Markets (MT5, serveur GMT+3 été) | VPS : Hostinger Windows | Instruments : XAUUSD, US30, USDJPY, CADJPY, USDCAD

---

## 📁 Structure du kit

```
DREVM_MT5_Kit/
├── 01_Experts/
│   ├── DREVM_FiboSniper_Auto_EA.mq5        → EA prop firm (The5ers/FTMO, buffers 3.5/7/8%)
│   └── DREVM_FiboSniper_Martingale_EA.mq5  → EA compte perso 200$ (martingale contrôlée)
├── 02_Indicators/
│   └── DREVM_FiboSniper_Indicator.mq5      → Indicateur pur (zones + signaux, sans exécution)
├── 03_Include/
│   └── DREVM_CorrelationGuard.mqh          → Module corrélation (include partagé)
├── 04_Presets/
│   └── DREVM_Martingale_Optim.set          → Plages d'optimisation Strategy Tester
├── 05_Python/
│   ├── drevm_ai_advisor.py                 → Pont MT5 → Claude API → Telegram
│   └── env.template                        → Modèle .env (clés API)
├── 06_Deploy/
│   ├── install_kit.ps1                     → Installation auto dans MQL5 (PowerShell)
│   ├── nssm_services.ps1                   → Création des services Windows NSSM
│   └── post-receive.sample                 → Hook Git bare VPS (auto-déploiement)
└── 07_Docs/
    ├── INSTALLATION.md                     → Pas-à-pas complet VPS
    ├── CHECKLIST_LIVE.md                   → Checklist avant passage en réel
    └── PROTOCOLE_DREVM.md                  → Rappel méthodo (grades, guardrails)
```

---

## ⚡ Démarrage rapide

1. **Copier le kit sur le VPS** (Git push depuis Termux ou copie directe)
2. **Installer** : clic droit `06_Deploy/install_kit.ps1` → *Exécuter avec PowerShell*
3. **Compiler** : MetaEditor (F4 depuis MT5) → ouvrir chaque .mq5 → F7
4. **Autoriser Telegram** : MT5 → Outils → Options → Expert Advisors → WebRequest → ajouter `https://api.telegram.org`
5. **Push mobile** : Options → Notifications → MetaQuotes ID du téléphone
6. **Attacher** : indicateur sur charts d'analyse, EA sur chart d'exécution (magic différent par instrument !)
7. **Python** : `pip install MetaTrader5 requests` → remplir `.env` → tester `python drevm_ai_advisor.py`

Détail complet : `07_Docs/INSTALLATION.md`

---

## 🔑 Règles d'or (non négociables)

- **MODE_ALERT_ONLY par défaut** — le passage en MODE_MARKET est une escalade volontaire après validation
- **No-repaint** : tout signal évalué sur clôture M5 uniquement
- **Magic numbers uniques** par instrument ET par EA (voir tableau dans INSTALLATION.md)
- **Disjoncteurs jamais optimisés** ni contournés (30$/jour, 4 trades, hard stop 140$, cap 0.08)
- **Guardrails prop firm internes** : 3.5% jour / 7% total / cible 8% (buffers, pas les limites réelles)
- **Jamais de martingale contre-tendance**
- **Pas de `$` dans les identifiants MQL5** (`riskAmount`, pas `risk$`)

---

## 🔄 Versions

| Version | Date | Contenu |
|---------|------|---------|
| 1.0 | 2026-07-17 | Kit initial : 2 EAs, indicateur, CorrGuard, advisor IA, .set, déploiement |
