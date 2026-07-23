# 📥 INSTALLATION — DREVM MT5 Kit sur VPS Windows

## 1. Prérequis VPS (Hostinger Windows)

- MT5 Fusion Markets installé, compte connecté (live ou démo)
- Python 3.8+ (`python --version`)
- NSSM dans le PATH (déjà en place pour saasDrevmBot)
- Git pour Windows (pour le hook bare repo)

## 2. Copier le kit

**Option A — Git (recommandé, workflow Termux existant) :**
```bash
# Depuis Termux (dossier saasdrevmbot_v1.01)
cp -r DREVM_MT5_Kit ./ && git add DREVM_MT5_Kit && git commit -m "feat: DREVM MT5 Kit v1.0" && git push vps main
```
Le hook `post-receive` (voir `06_Deploy/post-receive.sample`) déploie automatiquement vers MQL5.

**Option B — Copie directe :** RDP → coller le dossier n'importe où → `06_Deploy/install_kit.ps1`.

## 3. Installer dans MQL5

Clic droit `06_Deploy/install_kit.ps1` → **Exécuter avec PowerShell**.
Le script localise l'instance MT5 et copie tout au bon endroit (`Experts\DREVM`, `Indicators\DREVM`, `Presets`).

## 4. Compiler

MT5 → **F4** (MetaEditor) → ouvrir chaque fichier → **F7** :
- `Experts\DREVM\DREVM_FiboSniper_Auto_EA.mq5`
- `Experts\DREVM\DREVM_FiboSniper_Martingale_EA.mq5`
- `Indicators\DREVM\DREVM_FiboSniper_Indicator.mq5`

Zéro erreur attendue. Le `.mqh` est compilé automatiquement avec les EAs.

## 5. Options MT5 (une seule fois)

**Outils → Options → Expert Advisors :**
- ✅ Autoriser le trading algorithmique
- ✅ Autoriser WebRequest pour les URL listées → ajouter `https://api.telegram.org`

**Outils → Options → Notifications :**
- ✅ Activer les notifications Push → MetaQuotes ID du téléphone (app MT5 → Paramètres → Messages) → **Test**

## 6. Magic numbers (CRITIQUE)

Chaque instance d'EA = un magic UNIQUE. Convention DREVM :

| Instrument | EA Prop Firm | EA Martingale |
|-----------|--------------|---------------|
| XAUUSD    | 20260717     | 20260718      |
| USDJPY    | 20260727     | 20260728      |
| US30      | 20260737     | 20260738      |
| CADJPY    | 20260747     | 20260748      |
| USDCAD    | 20260757     | 20260758      |

⚠️ Ne jamais utiliser le même magic pour deux EAs / deux charts.

## 7. Attacher

- **Indicateur** → tous les charts d'analyse (desktop + les zones apparaissent)
- **EA** → uniquement le(s) chart(s) d'exécution, TF M5 recommandé pour l'affichage
- Vérifier le smiley 😊 en haut à droite du chart (algo trading actif)
- Défaut : `MODE_ALERT_ONLY` → alertes sans exécution

## 8. Python advisor

```powershell
pip install MetaTrader5 requests
cd DREVM_MT5_Kit\05_Python
copy env.template .env      # puis remplir les 3 clés
python drevm_ai_advisor.py  # test unique
```

Service permanent : PowerShell **ADMIN** → `06_Deploy/nssm_services.ps1` (boucle 15 min).

## 9. Optimisation (avant tout live)

Strategy Tester (Ctrl+R) :
- Symbole XAUUSD, période M5, modélisation **ticks réels**, dépôt 200, forward **1/3**
- Paramètres → clic droit → **Charger** → `Presets\DREVM_Martingale_Optim.set`
- Algorithme génétique → classer par **Recovery Factor** (jamais par profit)
- Filtres : DD < 25 %, séries de pertes ≤ 4, ≥ 100 trades

## 10. Dépannage rapide

| Symptôme | Cause probable |
|----------|----------------|
| Pas d'alerte Telegram | URL non autorisée dans WebRequest, ou token/chat_id faux |
| Pas de push mobile | MetaQuotes ID absent ou test non validé |
| EA n'affiche rien | Non compilé (F7) ou algo trading désactivé |
| `MetaTrader5` import error | Python non-Windows — le package est Windows-only |
| Zones absentes | `InpDrawZones=false` ou swing non détecté (historique H1 insuffisant) |
| Deux EAs se battent | Magic numbers identiques — corriger immédiatement |
