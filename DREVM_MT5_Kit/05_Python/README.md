# 05_Python — Toolkit d'audit quantitatif DREVM

Scripts nés de l'audit de juillet 2026 (session Claude). Tous : Python 3.8+,
`pip install MetaTrader5 pandas numpy` sauf mention contraire. Le terminal
MT5 Fusion Markets doit être ouvert et connecté pour tout script qui charge
des bougies.

## 📊 Conclusions de l'audit (à lire avant de retoucher le scoring)

Testé sur 60 000 bougies M5 (5 instruments) + 6,8 ans de H1 XAUUSD :

| Hypothèse | Verdict |
|---|---|
| Clusters jaunes de volatilité volume (article MQL5 #16555) | ❌ artefact d'ouverture NY (16h30 serveur = 09h30 NY) |
| Delta de volume au sweep de liquidité | ❌ Spearman ≈ 0 sur 5 000 sweeps |
| Scoring 7 facteurs v2 | ❌ Spearman(score, R) = −0.005 ; 85 % des signaux notés A+/A |
| Scoring corrigé v3 (FVG/OB en zone, points morts retirés) | ❌ pas mieux — les facteurs n'ont pas de pouvoir prédictif M5 |
| Edge M5 XAUUSD +0.10R | ❌ artefact de fenêtre (2025 fort, 2026 = −0.21R) |
| Entrées vs aléatoire M15 | ❌ p = 0.32 |
| Entrées vs aléatoire H1 | ⚠️ p = 0.09 mais échoue en out-of-sample |
| Gestion de position (partiel 1R + BE + trailing ATR) | ✅ seul module qui crée de la valeur |
| Biais directionnel M15 | BUY +0.09R / SELL −0.05R → beta long or, pas un edge |
| Point mort des coûts | ≈ 0.04R/trade : l'edge brut est mangé par spread+commission |

**Question ouverte** : le moteur automatique n'approxime pas la lecture
discrétionnaire DREVM (sous-phases Wyckoff, MSS, multi-TF). L'edge humain
n'a jamais été mesuré → c'est le rôle de `journal_drevm.py`.

**Règle apprise** : tout facteur candidat doit passer (1) baseline honnête,
(2) contrôle de confondant horaire, (3) out-of-sample chronologique,
(4) comparaison à des entrées aléatoires avec la même gestion.

## 🗂️ Scripts

### `journal_drevm.py` ⭐ (workflow actif — stdlib pur, marche sur Termux)
Journal des décisions discrétionnaires sur les alertes `MODE_ALERT_ONLY`.
```
python journal_drevm.py add --rapide XAUUSD BUY A+ 2410.5
python journal_drevm.py close 12 --r 2.5
python journal_drevm.py close 13 --r -1 --refuse   # résultat hypothétique d'un refus
python journal_drevm.py stats                       # verdict à 40 décisions closes
python journal_drevm.py export
```
Règles : saisir TOUTES les alertes (même refusées), grade humain donné AVANT
le résultat, résultats en R. Données : `journal_trades.csv` (à côté du script).

### `backtest_grades.py`
Rejoue le moteur de confluence (`--version v2` = origine 7 pts,
`--version v3` = corrigé 5 pts) et mesure expectancy/WR/PF **par grade**,
avec monotonie, permutation, out-of-sample et contrôle horaire.
```
python backtest_grades.py --version v3 --symbols XAUUSD --timeframe H1
```

### `test_entrees_aleatoires.py`
Le juge de paix : signal réel vs entrées aléatoires appariées (mêmes heures,
mêmes distances de SL, même proportion BUY/SELL) vs bras beta (sens conservé,
dates aléatoires) — même gestion de position partout.
```
python test_entrees_aleatoires.py --signaux resultats_grades/XAUUSD_v2_H1_signaux.csv --symbol XAUUSD --timeframe H1 --n-sim 200
```

### `test_sweep_volume.py`
Sweeps de liquidité (no-repaint, fractal confirmé) + delta de volume par
quintile, évaluation économique SL/TP. Design conditionné à l'événement
structurel pour éviter les artefacts de session.

### `backtest_clusters_jaunes.py`
Test de la thèse « volatilité de volume → retournement » avec baseline et
permutation. Conservé comme référence méthodologique (l'hypothèse est morte).

### `drevm_ai_advisor.py`
(Antérieur à l'audit — advisor IA, indépendant du toolkit.)

## 📁 Sorties
Chaque script écrit dans son dossier `resultats_*/` : synthèses + détail par
signal/bougie (CSV). Ces CSV sont le format d'échange pour les analyses
approfondies (sessions Claude).
