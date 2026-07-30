# Exemple de scoring — Wyckoff + FVG + Ichimoku (XBRUSD / Brent)

`scoring_wyckoff_fvg_ichimoku_xbrusd.py` montre, de bout en bout, comment noter
un setup Smart Money sur **XBR/USD (Brent, Yahoo `BZ=F`)** en combinant les trois
piliers demandés :

| Pilier | Détecteur | Règle |
|--------|-----------|-------|
| **Wyckoff** | `detect_wyckoff` | Spring / UTAD = faux cassure d'un swing 20 (mèche au-delà, clôture au-dedans) |
| **FVG** | `detect_fvg` | Fair Value Gap (imbalance 3 bougies) façon `ICT_RSI_Wyckoff.pine` : `low[i] > high[i-2]` (haussier) / `high[i] < low[i-2]` (baissier) |
| **Ichimoku** | `price_above_kijun` | Filtre Kijun(26) : prix au-dessus / en dessous |

Le moteur de scoring existant (`ny_session_interface/trading_ny_session.py`) fait
Wyckoff + Ichimoku + divergence RSI mais **pas** de FVG. Cet exemple ajoute
explicitement la confluence FVG (gap frais + mitigation).

## Barème

Le **smart signal** est valide quand les 3 piliers (Wyckoff + FVG + Ichimoku)
pointent dans la même direction. Le **grade** dépend du total de confluence :

| Confluence | Poids |
|-----------|:-----:|
| Wyckoff (Spring/UTAD) | 3 |
| FVG frais (imbalance) | 3 |
| Ichimoku (filtre Kijun) | 2 |
| FVG en mitigation (timing d'entrée) | 1 |
| Divergence RSI | 1 |
| Biais de tendance | 1 |
| **Total max** | **11** |

Grade : **A+** ≥ 90 %, **A** ≥ 72 %, **B** ≥ 55 % (smart signal requis), sinon **C**.

## Lancer

```bash
python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py            # yfinance, sinon démo synthétique
python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py --live     # exige les données réelles (BZ=F)
python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py --interval 1h --period 1mo
```

Sans réseau / marché fermé, le script bascule sur un jeu de données **synthétique
déterministe** qui met en scène un setup BUY complet (accumulation → Spring →
impulsion + FVG haussier → retest/mitigation), produisant un grade **A+**.

Dépendances : `pandas`, `numpy` (et `yfinance` pour les données réelles).
