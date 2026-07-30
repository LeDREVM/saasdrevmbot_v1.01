"""
==============================================================================
 scoring_wyckoff_fvg_ichimoku_xbrusd.py
 Exemple de scoring Smart Money : Wyckoff + FVG + Ichimoku sur XBR/USD (Brent)
==============================================================================

 Cet exemple montre, de bout en bout, comment le bot note un setup sur
 XBRUSD (pétrole Brent, symbole Yahoo `BZ=F`) en combinant :

   • WYCKOFF  — Spring / UTAD (faux cassure d'un swing 20 bougies).
   • FVG      — Fair Value Gap (imbalance 3 bougies), à la façon de
                l'indicateur `ICT_RSI_Wyckoff.pine` (low > high[2] / high < low[2]).
   • ICHIMOKU — filtre Kijun(26) : prix au-dessus / en dessous de la Kijun.
   • (bonus)  RSI divergence, biais H4, zone M15, trigger M5 pour la confluence.

 La logique de scoring existante du projet (ny_session_interface/
 trading_ny_session.py) fait Wyckoff + Ichimoku + divergence RSI mais PAS de
 FVG. Ici on ajoute explicitement la confluence FVG, comme demandé, et on
 produit un grade A+/A/B/C + une ligne de journal.

 Le script fonctionne SANS MetaTrader5 :
   - il essaie de télécharger le Brent (BZ=F) via yfinance ;
   - si le réseau est indisponible, il bascule sur un jeu de données
     SYNTHÉTIQUE déterministe qui fabrique volontairement un setup BUY
     (Spring + FVG haussier + prix > Kijun) pour illustrer le scoring.

 Usage :
     python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py
     python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py --live      # force yfinance
     python examples/scoring_wyckoff_fvg_ichimoku_xbrusd.py --interval 15m --period 5d
==============================================================================
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

SYMBOL = "XBRUSD"          # Brent spot US Dollar
YAHOO_SYMBOL = "BZ=F"      # Brent crude oil futures (mapping du projet)


# ─────────────────────────────────────────────────────────────────────────────
# 1) DÉTECTEURS TECHNIQUES
# ─────────────────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI de Wilder (sans dépendance externe)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - 100 / (1 + rs)


def kijun(df: pd.DataFrame, period: int = 26) -> pd.Series:
    """Kijun-sen Ichimoku : (plus-haut + plus-bas) / 2 sur `period` bougies."""
    return (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2


def price_above_kijun(df: pd.DataFrame, period: int = 26) -> bool:
    """Filtre Ichimoku : dernière clôture au-dessus de la Kijun ?"""
    return float(df["close"].iloc[-1]) > float(kijun(df, period).iloc[-1])


def detect_wyckoff(df: pd.DataFrame, swing: int = 20, window: int = 6) -> Optional[str]:
    """
    Wyckoff Spring / UTAD (faux cassure d'un swing) :
      • SPRING = mèche sous le plus-bas swing mais clôture au-dessus.
      • UTAD   = mèche au-dessus du plus-haut swing mais clôture en dessous.

    On balaie les `window` dernières bougies (de la plus récente à la plus
    ancienne) : un Spring/UTAD reste pertinent quelques bougies après sa
    formation (il précède souvent le déséquilibre / FVG et le retest).
    """
    high = df["high"].rolling(swing).max()
    low = df["low"].rolling(swing).min()
    n = len(df)
    for i in range(n - 1, max(swing, n - window) - 1, -1):
        prior_high = float(high.iloc[i - 1])
        prior_low = float(low.iloc[i - 1])
        bar = df.iloc[i]
        if float(bar["low"]) < prior_low and float(bar["close"]) > prior_low:
            return "SPRING"
        if float(bar["high"]) > prior_high and float(bar["close"]) < prior_high:
            return "UTAD"
    return None


def detect_divergence(df: pd.DataFrame, lookback: int = 10) -> Optional[str]:
    """RSI divergence : compare prix et RSI sur ~`lookback` bougies."""
    r = rsi(df["close"])
    p1, p2 = float(df["close"].iloc[-lookback]), float(df["close"].iloc[-1])
    r1, r2 = float(r.iloc[-lookback]), float(r.iloc[-1])
    if p2 < p1 and r2 > r1:
        return "BULLISH"
    if p2 > p1 and r2 < r1:
        return "BEARISH"
    return None


@dataclass
class FVGSignal:
    """Fair Value Gap le plus récent + réaction du prix."""
    direction: Optional[str] = None       # "BULLISH" | "BEARISH" | None
    top: float = 0.0                      # borne haute du gap
    bottom: float = 0.0                   # borne basse du gap
    bars_ago: int = 0                     # ancienneté (0 = formé sur la dernière bougie)
    price_in_gap: bool = False            # le prix est-il revenu tester le gap ?
    is_fresh: bool = False                # gap non encore comblé (mitigé) ?


def detect_fvg(df: pd.DataFrame, scan: int = 20) -> FVGSignal:
    """
    Fair Value Gap (imbalance 3 bougies) façon `ICT_RSI_Wyckoff.pine` :

      • FVG haussier : low[i] > high[i-2]  → gap entre high[i-2] (bas) et low[i] (haut).
      • FVG baissier : high[i] < low[i-2]  → gap entre high[i] (bas) et low[i-2] (haut).

    On parcourt les `scan` dernières bougies (des plus récentes aux plus
    anciennes) et on renvoie le premier FVG encore « frais » (non totalement
    comblé par une clôture ultérieure). `price_in_gap` indique que le prix
    actuel est revenu dans la zone du gap (mitigation en cours = point d'entrée).
    """
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    n = len(df)
    last_close = closes[-1]

    start = n - 1
    stop = max(2, n - scan)
    for i in range(start, stop - 1, -1):
        # FVG haussier : la bougie i laisse un vide au-dessus de la bougie i-2
        if lows[i] > highs[i - 2]:
            top, bottom = lows[i], highs[i - 2]
            # « frais » = aucune clôture postérieure n'a comblé le gap vers le bas
            filled = any(closes[j] < bottom for j in range(i + 1, n))
            price_in_gap = bottom <= last_close <= top
            if not filled:
                return FVGSignal("BULLISH", top, bottom, (n - 1) - i, price_in_gap, True)
        # FVG baissier : la bougie i laisse un vide en dessous de la bougie i-2
        if highs[i] < lows[i - 2]:
            top, bottom = lows[i - 2], highs[i]
            filled = any(closes[j] > top for j in range(i + 1, n))
            price_in_gap = bottom <= last_close <= top
            if not filled:
                return FVGSignal("BEARISH", top, bottom, (n - 1) - i, price_in_gap, True)
    return FVGSignal()


def get_bias(df: pd.DataFrame, lookback: int = 20) -> str:
    """Biais de tendance : close actuel vs close il y a `lookback` bougies."""
    return "BULLISH" if float(df["close"].iloc[-1]) > float(df["close"].iloc[-lookback]) else "BEARISH"


# ─────────────────────────────────────────────────────────────────────────────
# 2) CONTEXTE + SCORING (Wyckoff + FVG + Ichimoku)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Context:
    wyckoff: Optional[str] = None          # "SPRING" | "UTAD"
    fvg: FVGSignal = field(default_factory=FVGSignal)
    price_above_kijun: bool = False        # Ichimoku Kijun(26)
    rsi_divergence: Optional[str] = None   # "BULLISH" | "BEARISH"
    bias: str = "BULLISH"                  # biais de tendance
    last_close: float = 0.0
    kijun_value: float = 0.0


@dataclass
class Score:
    is_valid: bool
    direction: Optional[str]     # "up" | "down"
    grade: str                   # "A+" | "A" | "B" | "C"
    points: int
    max_points: int
    breakdown: list = field(default_factory=list)   # [(label, gagné?, poids), ...]


# Barème de confluence (les 3 piliers demandés pèsent le plus).
WEIGHTS = {
    "wyckoff": 3,          # Spring / UTAD dans le sens du trade
    "fvg": 3,              # FVG frais dans le sens du trade
    "ichimoku": 2,         # filtre Kijun aligné
    "fvg_mitigation": 1,   # prix en train de tester le FVG (timing d'entrée)
    "divergence": 1,       # divergence RSI alignée
    "bias": 1,             # biais de tendance aligné
}
MAX_POINTS = sum(WEIGHTS.values())   # 11


def score_setup(ctx: Context) -> Score:
    """
    Smart signal = Wyckoff + FVG + Ichimoku alignés dans la même direction.
    Le grade dépend du total de points de confluence.
    """
    # Direction candidate : d'abord Wyckoff, sinon FVG.
    if ctx.wyckoff == "SPRING":
        direction = "up"
    elif ctx.wyckoff == "UTAD":
        direction = "down"
    elif ctx.fvg.direction == "BULLISH":
        direction = "up"
    elif ctx.fvg.direction == "BEARISH":
        direction = "down"
    else:
        direction = None

    breakdown: list = []
    points = 0

    def add(label: str, won: bool, weight: int):
        nonlocal points
        if won:
            points += weight
        breakdown.append((label, won, weight))

    if direction is None:
        return Score(False, None, "C", 0, MAX_POINTS,
                     [("aucun signal Wyckoff/FVG", False, 0)])

    want_bull = direction == "up"

    wyckoff_ok = (ctx.wyckoff == "SPRING") if want_bull else (ctx.wyckoff == "UTAD")
    fvg_ok = (ctx.fvg.direction == "BULLISH") if want_bull else (ctx.fvg.direction == "BEARISH")
    ichimoku_ok = ctx.price_above_kijun if want_bull else (not ctx.price_above_kijun)
    fvg_mitig_ok = fvg_ok and ctx.fvg.price_in_gap
    div_ok = (ctx.rsi_divergence == "BULLISH") if want_bull else (ctx.rsi_divergence == "BEARISH")
    bias_ok = (ctx.bias == "BULLISH") if want_bull else (ctx.bias == "BEARISH")

    add("Wyckoff (Spring/UTAD)", wyckoff_ok, WEIGHTS["wyckoff"])
    add("FVG frais (imbalance)", fvg_ok, WEIGHTS["fvg"])
    add("Ichimoku (filtre Kijun)", ichimoku_ok, WEIGHTS["ichimoku"])
    add("FVG en mitigation (timing)", fvg_mitig_ok, WEIGHTS["fvg_mitigation"])
    add("Divergence RSI", div_ok, WEIGHTS["divergence"])
    add("Biais de tendance", bias_ok, WEIGHTS["bias"])

    # Smart signal = les 3 piliers (Wyckoff + FVG + Ichimoku) alignés.
    is_valid = wyckoff_ok and fvg_ok and ichimoku_ok

    ratio = points / MAX_POINTS
    if is_valid and ratio >= 0.90:
        grade = "A+"
    elif is_valid and ratio >= 0.72:
        grade = "A"
    elif is_valid and ratio >= 0.55:
        grade = "B"
    else:
        grade = "C"

    return Score(is_valid, direction, grade, points, MAX_POINTS, breakdown)


def build_context(df: pd.DataFrame) -> Context:
    return Context(
        wyckoff=detect_wyckoff(df),
        fvg=detect_fvg(df),
        price_above_kijun=price_above_kijun(df),
        rsi_divergence=detect_divergence(df),
        bias=get_bias(df),
        last_close=float(df["close"].iloc[-1]),
        kijun_value=float(kijun(df).iloc[-1]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3) DONNÉES : yfinance (réel) ou synthétique (démo hors-ligne)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_yfinance(interval: str, period: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        df = yf.Ticker(YAHOO_SYMBOL).history(period=period, interval=interval)
        if df is None or df.empty or len(df) < 40:
            return None
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close"]].astype(float).reset_index(drop=True)
    except Exception as exc:  # noqa: BLE001 — démo tolérante au réseau
        print(f"  ⚠️  yfinance indisponible ({exc}); bascule en données synthétiques.")
        return None


def synthetic_brent(n: int = 120) -> pd.DataFrame:
    """
    Jeu de données Brent SYNTHÉTIQUE déterministe qui met en scène un vrai
    enchaînement Smart Money (setup BUY), bougie par bougie :

      1. Longue phase d'accumulation en range autour de 76 $ (biais qui se
         construit sous la Kijun).
      2. SPRING (bougie -5) : faux cassure sous le plancher du range, clôture
         qui repasse au-dessus → piège les vendeurs.
      3. Impulsion haussière (bougies -4 → -2) qui déchire la Kijun et laisse
         un FVG HAUSSIER (gap : low[-2] > high[-4]).
      4. Retest (bougie -1) : le prix revient MITIGER le FVG, clôture toujours
         au-dessus de la Kijun → point d'entrée BUY.

    Prix ~ 74–80 $, cohérent avec le Brent.
    """
    rng = np.random.default_rng(42)
    n_range = n - 5
    # 1) Accumulation en range ~76 $ avec un plancher net.
    closes = 76.0 + rng.normal(0, 0.25, n_range)
    closes = np.clip(closes, 75.6, 76.5)
    highs = closes + np.abs(rng.normal(0.15, 0.05, n_range))
    lows = closes - np.abs(rng.normal(0.15, 0.05, n_range))
    opens = np.concatenate([[closes[0]], closes[:-1]])

    o = list(opens); h = list(highs); l = list(lows); c = list(closes)
    floor = min(l)           # plancher du range (référence du Spring)

    # 2) SPRING (bougie -5) : mèche sous le plancher, clôture au-dessus.
    o.append(floor + 0.05); l.append(floor - 0.45)
    c.append(floor + 0.30); h.append(floor + 0.40)

    # 3) Impulsion haussière (bougies -4, -3, -2) au-dessus de la Kijun,
    #    en laissant un gap entre high[-4] et low[-2].
    base = floor + 0.30
    #    bougie -4
    o.append(base);         c.append(base + 0.90)
    l.append(base - 0.10);  h.append(base + 1.00)
    top_m4 = h[-1]
    #    bougie -3 (grande bougie de déplacement)
    o.append(c[-1]);        c.append(c[-1] + 1.30)
    l.append(o[-1] - 0.05); h.append(c[-1] + 0.15)
    #    bougie -2 : ouvre AU-DESSUS de high[-4] → crée le FVG haussier
    gap_low = top_m4 + 0.35
    o.append(gap_low + 0.05); l.append(gap_low)
    c.append(gap_low + 0.70); h.append(gap_low + 0.85)

    # 4) Retest (bougie -1) : le prix redescend et CLÔTURE dans le FVG
    #    (zone [top_m4 ; gap_low]) = mitigation → point d'entrée BUY.
    o.append(c[-1])
    l.append(top_m4 + 0.05)          # mèche jusqu'au bas du gap
    c.append((top_m4 + gap_low) / 2) # clôture au cœur du gap = mitigation
    h.append(c[-1] + 0.30)

    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4) RAPPORT
# ─────────────────────────────────────────────────────────────────────────────

def render_report(source: str, interval: str, ctx: Context, score: Score) -> str:
    fvg = ctx.fvg
    arrow = {"up": "🟢 BUY", "down": "🔴 SELL", None: "⚪ AUCUN"}[score.direction]

    lines = []
    lines.append("=" * 70)
    lines.append(f" SCORING SMART MONEY — Wyckoff + FVG + Ichimoku")
    lines.append(f" Instrument : {SYMBOL} (Brent, Yahoo {YAHOO_SYMBOL})")
    lines.append(f" Données    : {source}  |  timeframe {interval}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(" CONTEXTE TECHNIQUE")
    lines.append(f"   • Dernier prix   : {ctx.last_close:.2f} $")
    lines.append(f"   • Kijun(26)      : {ctx.kijun_value:.2f} $  "
                 f"({'prix > Kijun' if ctx.price_above_kijun else 'prix < Kijun'})")
    lines.append(f"   • Wyckoff        : {ctx.wyckoff or '—'}")
    lines.append(f"   • Divergence RSI : {ctx.rsi_divergence or '—'}")
    lines.append(f"   • Biais tendance : {ctx.bias}")
    if fvg.direction:
        state = "en mitigation (prix dans le gap)" if fvg.price_in_gap else "non testé"
        lines.append(f"   • FVG            : {fvg.direction}  "
                     f"[{fvg.bottom:.2f} – {fvg.top:.2f}]  "
                     f"il y a {fvg.bars_ago} bougie(s), {state}")
    else:
        lines.append("   • FVG            : —")
    lines.append("")
    lines.append(" DÉTAIL DU SCORE")
    for label, won, weight in score.breakdown:
        mark = "✅" if won else "❌"
        lines.append(f"   {mark}  {label:<28} {('+' + str(weight)) if won else '0'} / {weight}")
    lines.append("   " + "-" * 46)
    lines.append(f"   TOTAL : {score.points} / {score.max_points} points")
    lines.append("")
    lines.append(" DÉCISION")
    lines.append(f"   • Signal   : {arrow}")
    lines.append(f"   • Smart signal (Wyckoff+FVG+Ichimoku) : "
                 f"{'✅ VALIDE' if score.is_valid else '❌ incomplet'}")
    lines.append(f"   • GRADE    : {score.grade}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scoring Wyckoff+FVG+Ichimoku sur XBRUSD (Brent)")
    parser.add_argument("--interval", default="15m", help="timeframe yfinance (ex: 5m, 15m, 1h)")
    parser.add_argument("--period", default="5d", help="fenêtre yfinance (ex: 5d, 1mo)")
    parser.add_argument("--live", action="store_true", help="exiger les données yfinance (pas de fallback)")
    args = parser.parse_args()

    print(f"→ Récupération {SYMBOL} ({YAHOO_SYMBOL}) via yfinance [{args.interval}/{args.period}]…")
    df = fetch_yfinance(args.interval, args.period)

    if df is not None:
        source = f"yfinance {YAHOO_SYMBOL} ({len(df)} bougies)"
    elif args.live:
        raise SystemExit("❌ Données yfinance indisponibles et --live demandé.")
    else:
        print("→ Réseau/marché indisponible : données SYNTHÉTIQUES (setup BUY de démonstration).")
        df = synthetic_brent()
        source = f"synthétique ({len(df)} bougies)"

    ctx = build_context(df)
    score = score_setup(ctx)
    print()
    print(render_report(source, args.interval, ctx, score))


if __name__ == "__main__":
    main()
