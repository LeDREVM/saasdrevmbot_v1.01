# 🎯 PROTOCOLE DREVM — Référence rapide

## Pipeline de signal (identique EA / Indicateur / Skill Claude)

```
Close M5 (no-repaint)
  → Swing fractal H1 (lookback 120, force 3)
  → Fibo auto : jambe + % de retracement
  → Biais EMA50/200 H1
  → Sweep de liquidité M5 (mèche > extrême 20 barres + close en-deçà)
  → BOS M5 (close > / < structure 10 barres)
  → Scoring 6 confluences → grade → action
```

## Les 6 confluences

1. Biais EMA aligné avec la jambe (EMA50 vs EMA200 H1)
2. Prix en zone sniper Fibonacci **61.8 → 95 %**
3. Sweep de liquidité du bon côté (validité 12 bougies M5)
4. BOS M5 dans le sens du trade
5. Non invalidé (retracement < 100 %)
6. R/R ≥ cible (2.0 prop firm / 1.5 martingale)

## Grades & couleurs

| Score | Grade | Couleur | Action |
|-------|-------|---------|--------|
| 6/6 | A+ | `#10b981` | Trade |
| 5/6 | A  | `#22c55e` | Trade |
| 4/6 | B  | `#eab308` | Trade (seuil minimum) |
| 3/6 | C  | `#f97316` | WAIT |
| <3  | D  | `#ef4444` | WAIT |

## Niveaux Fibonacci sniper

**61.8 / 71 / 81 / 88.6 / 95 %** — le 71 % est la zone de référence.
Zone Deep 81→95 % : reprise imminente ou invalidation proche — trigger obligatoire.

## Gestion de position

- Partial 50 % à 1R → SL breakeven +20 pts → trailing ATR(14) × 2
- Position contre-tendance HTF en profit = cadeau → sécuriser immédiatement
- Jamais déplacer un SL dans le mauvais sens

## Guardrails

**Prop firm (buffers internes)** : lock jour 3.5 % · lock total 7 % · cible phase 8 % (lock protecteur)
**Compte perso 200$** : stop jour 30$ · 4 trades/jour max · hard stop equity < 140$ · cap lot 0.08 · martingale ≤ 3 doublements + cooldown 2h

## Corrélations (CorrGuard)

- Matrice Pearson H1 rolling 4 jours, cache 1h
- Corrélation **effective** = r × sens_candidat × sens_position (cumul vs hedge)
- |r| ≥ 0.70 → lot -50 % · |r| ≥ 0.40 → lot -25 %
- Cap exposition devise : 0.06 lots pondérés (XAU ×2.5, US30 ×2.0)
- Veto si le trade **aggrave** une exposition au cap

## Sessions & temps

- Session cible : **New York** (EDT, UTC-4)
- Serveur Fusion Markets : **GMT+3** (été) — conversion via ff_to_newstimes.py
- Guadeloupe : UTC-4 sans DST
