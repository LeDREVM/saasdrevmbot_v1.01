"""
==============================================================================
 setup_validator.py — AI SETUP VALIDATOR (v1 déterministe, sans ML)
==============================================================================

 Implémente le maillon « AI SETUP VALIDATOR » de l'architecture cible :

   OHLC → Feature Engine (vecteur de features)
        → Sous-scores (Trend / Wyckoff / Momentum / Liquidity / Volatility / News)
        → GLOBAL SCORE pondéré
        → Décision EXECUTE / WATCHLIST / IGNORE

 C'est la version « règles codées » (v1). Elle est DÉTERMINISTE (pas
 d'entraînement) et sert deux buts :
   1. Produire un score exploitable tout de suite pour le pipeline n8n.
   2. Émettre le VECTEUR DE FEATURES + un enregistrement label-ready
      (`to_training_record`) qui alimentera plus tard le classifieur ML / PPO
      (dataset : features → WIN/LOSS).

 Poids du GLOBAL SCORE (tels que spécifiés) :
   Trend 0.30 · Wyckoff 0.20 · Momentum 0.15 · Liquidity 0.15 · Volatility 0.10 · News 0.10

 Le sous-score Liquidity intègre l'ORDER FLOW INSTITUTIONNEL (concepts smart
 money, price-action pur — aucune donnée DOM/tick requise) : order blocks +
 mitigation, zones premium/discount (accumulation/distribution), breaker blocks,
 en plus des sweeps de liquidité et pools (equal highs/lows) déjà présents.

 Réutilise les détecteurs du moteur live (ny_session_bot) — pas de logique
 dupliquée. Read-only : n'ouvre aucun trade.

 Usage :
     python ny_session_interface/setup_validator.py            # démo XBRUSD
     python ny_session_interface/setup_validator.py --json     # sortie JSON
==============================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ny_session_bot import (  # noqa: E402
    rsi, atr, ema, detect_wyckoff, detect_divergence, price_above_kijun, detect_fvg,
)
logging.getLogger("ny_bot").setLevel(logging.CRITICAL)

GLOBAL_WEIGHTS = {
    "trend": 0.30, "wyckoff": 0.20, "momentum": 0.15,
    "liquidity": 0.15, "volatility": 0.10, "news": 0.10,
}


# ─────────────────────────────────────────────────────────────────────────────
# 1) FEATURE ENGINE — vecteur de caractéristiques
# ─────────────────────────────────────────────────────────────────────────────

def _ichimoku(df: pd.DataFrame):
    high, low = df["high"], df["low"]
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (high.rolling(52).max() + low.rolling(52).min()) / 2
    return tenkan, kijun, senkou_a, senkou_b


def _trend(series: pd.Series, fast: int, slow: int) -> int:
    """-1 baissier / 0 neutre / +1 haussier via croisement + pente EMA."""
    if len(series) < slow + 2:
        return 0
    ef, es = ema(series, fast), ema(series, slow)
    slope = float(es.iloc[-1] - es.iloc[-3])
    if ef.iloc[-1] > es.iloc[-1] and slope > 0:
        return 1
    if ef.iloc[-1] < es.iloc[-1] and slope < 0:
        return -1
    return 0


def _swings(df: pd.DataFrame, left: int = 2, right: int = 2):
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    highs, lows = [], []
    for i in range(left, len(df) - right):
        if h[i] == max(h[i - left:i + right + 1]):
            highs.append((i, h[i]))
        if l[i] == min(l[i - left:i + right + 1]):
            lows.append((i, l[i]))
    return highs, lows


def _bos(df: pd.DataFrame) -> int:
    """Break of structure : dernière clôture au-delà du dernier swing opposé."""
    highs, lows = _swings(df.iloc[:-1])
    last = float(df["close"].iloc[-1])
    up = highs and last > highs[-1][1]
    dn = lows and last < lows[-1][1]
    return 1 if up else -1 if dn else 0


def _equal_levels(levels, atr_val: float, tol: float = 0.35) -> bool:
    """Deux extrêmes ~égaux (liquidité) à moins de tol×ATR."""
    if len(levels) < 2 or atr_val <= 0:
        return False
    a, b = levels[-1][1], levels[-2][1]
    return abs(a - b) <= tol * atr_val


def _liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> int:
    """Mèche au-delà d'un extrême récent puis clôture en-deçà (sweep)."""
    prior_high = float(df["high"].iloc[-(lookback + 1):-1].max())
    prior_low = float(df["low"].iloc[-(lookback + 1):-1].min())
    bar = df.iloc[-1]
    if float(bar["high"]) > prior_high and float(bar["close"]) < prior_high:
        return -1  # sweep du haut → pression baissière
    if float(bar["low"]) < prior_low and float(bar["close"]) > prior_low:
        return 1   # sweep du bas → pression haussière
    return 0


# ── Order flow institutionnel — concepts "smart money" (price-action pur) ──────
# Aucune donnée nouvelle (pas de DOM/ticks) : on lit l'empreinte des institutions
# dans la structure des bougies OHLC. Ces features nourrissent le sous-score
# Liquidity et le vote de direction.

def _dealing_range(df: pd.DataFrame, lookback: int = 40):
    """Range de négociation récent (hors bougie courante). None si dégénéré."""
    seg = df.iloc[-(lookback + 1):-1]
    if len(seg) < 2:
        return None
    lo, hi = float(seg["low"].min()), float(seg["high"].max())
    return (lo, hi) if hi > lo else None


def _premium_discount(df: pd.DataFrame, lookback: int = 40) -> float:
    """Position du prix dans le range : 0 = discount profond · 0.5 = équilibre
    (50 % du range) · 1 = premium profond. Les institutions accumulent en
    discount (<0.5) et distribuent en premium (>0.5)."""
    rng = _dealing_range(df, lookback)
    if rng is None:
        return 0.5
    lo, hi = rng
    price = float(df["close"].iloc[-1])
    return max(0.0, min(1.0, (price - lo) / (hi - lo)))


def _order_block(df: pd.DataFrame, atr_val: float, lookback: int = 30,
                 disp_mult: float = 1.2) -> dict:
    """Order block institutionnel = dernière bougie de sens OPPOSÉ juste avant une
    bougie de *displacement* (corps > disp_mult×ATR, empreinte d'un ordre
    institutionnel). Renvoie le plus récent : {dir, top, bottom, mitigating}
    (`mitigating` = le prix courant est revenu dans la zone de l'OB)."""
    n = len(df)
    if n < 6 or atr_val <= 0:
        return {"dir": None, "mitigating": False}
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    price = float(c[-1])
    found = {"dir": None, "mitigating": False}
    for i in range(max(1, n - lookback), n - 1):
        if (c[i] - o[i]) > disp_mult * atr_val:           # displacement haussier
            for j in range(i - 1, max(-1, i - 4), -1):
                if c[j] < o[j]:                            # → OB haussier
                    found = {"dir": "BULLISH", "top": float(max(o[j], c[j])),
                             "bottom": float(l[j])}
                    break
        elif (o[i] - c[i]) > disp_mult * atr_val:          # displacement baissier
            for j in range(i - 1, max(-1, i - 4), -1):
                if c[j] > o[j]:                            # → OB baissier
                    found = {"dir": "BEARISH", "top": float(h[j]),
                             "bottom": float(min(o[j], c[j]))}
                    break
    if found["dir"]:
        found["mitigating"] = bool(found["bottom"] <= price <= found["top"])
    return found


def _breaker(df: pd.DataFrame) -> int:
    """Breaker block = order block invalidé : liquidité balayée puis structure
    cassée dans l'autre sens → le niveau s'inverse (support↔résistance).
    +1 haussier / -1 baissier / 0."""
    sweep = _liquidity_sweep(df)
    bos = _bos(df)
    if sweep == 1 and bos > 0:
        return 1
    if sweep == -1 and bos < 0:
        return -1
    return 0


def build_features(df: pd.DataFrame, news_score: float = 100.0,
                   spread: float = 0.0, session_active: bool = True) -> dict:
    """
    Construit le vecteur de features à partir d'un DataFrame OHLC (single-TF).
    Les tendances multi-TF sont dérivées de trois horizons EMA (proxy H4/M15/M5
    quand une seule série est fournie ; brancher un vrai MTF plus tard).
    """
    close = df["close"]
    price = float(close.iloc[-1])
    tenkan, kijun, sen_a, sen_b = _ichimoku(df)
    a = atr(df)
    cloud_top = float(max(sen_a.iloc[-1], sen_b.iloc[-1]))
    cloud_bot = float(min(sen_a.iloc[-1], sen_b.iloc[-1]))
    fvg = detect_fvg(df)
    ob = _order_block(df, a)
    highs, lows = _swings(df)
    r = rsi(close)
    body = abs(float(df["close"].iloc[-1]) - float(df["open"].iloc[-1]))
    vol = df["volume"] if "volume" in df.columns else None

    return {
        "trend_h4": _trend(close, 20, 200),
        "trend_m15": _trend(close, 10, 50),
        "trend_m5": _trend(close, 5, 20),
        "distance_kijun": (price - float(kijun.iloc[-1])) / a if a else 0.0,
        "distance_cloud": (price - cloud_top) / a if (a and price > cloud_top)
                          else (price - cloud_bot) / a if a else 0.0,
        "cloud_thickness": (cloud_top - cloud_bot) / a if a else 0.0,
        "rsi": float(r.iloc[-1]),
        "rsi_divergence": detect_divergence(df) or "none",
        "volume_spike": bool(vol is not None and len(vol) > 20
                             and float(vol.iloc[-1]) > 1.8 * float(vol.iloc[-20:].mean())),
        "spring_detected": detect_wyckoff(df) == "SPRING",
        "utad_detected": detect_wyckoff(df) == "UTAD",
        "bos": _bos(df),
        "choch": -_bos(df.iloc[:-3]) if len(df) > 6 else 0,  # flip récent de structure
        "equal_highs": _equal_levels(highs, a),
        "equal_lows": _equal_levels(lows, a),
        "liquidity_sweep": _liquidity_sweep(df),
        # ── Order flow institutionnel (smart money) ──
        "premium_discount": round(_premium_discount(df), 3),
        "ob_dir": ob["dir"],
        "ob_mitigation": bool(ob.get("mitigating")),
        "breaker": _breaker(df),
        "atr": a,
        "spread": spread,
        "news_score": news_score,
        "session": 1 if session_active else 0,
        "fvg_dir": fvg.get("direction"),
        "fvg_mitigation": bool(fvg.get("price_in_gap")),
        "price_above_kijun": price_above_kijun(df),
        "displacement": body / a if a else 0.0,
        "price": price,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2) DIRECTION CANDIDATE + SOUS-SCORES (0..100)
# ─────────────────────────────────────────────────────────────────────────────

def candidate_direction(f: dict) -> Optional[str]:
    """Vote pondéré structure/tendance pour BUY/SELL."""
    score = 0
    score += f["trend_m15"] + 0.5 * f["trend_h4"] + 0.5 * f["trend_m5"]
    score += 1 if f["spring_detected"] else -1 if f["utad_detected"] else 0
    score += 1 if f["fvg_dir"] == "BULLISH" else -1 if f["fvg_dir"] == "BEARISH" else 0
    score += 0.5 * f["bos"] + 0.5 * f["liquidity_sweep"]
    # Order flow institutionnel : OB mitigé (fort), breaker (moyen), zone
    # premium/discount (léger — accumulation en discount / distribution en premium).
    if f["ob_mitigation"] and f["ob_dir"]:
        score += 1 if f["ob_dir"] == "BULLISH" else -1
    score += 0.5 * f["breaker"]
    pd_bias = 0.5 - f["premium_discount"]           # >0 = discount (favorise BUY)
    score += 0.4 * (1 if pd_bias > 0.15 else -1 if pd_bias < -0.15 else 0)
    if score > 0.75:
        return "up"
    if score < -0.75:
        return "down"
    return None


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def sub_scores(f: dict, direction: str) -> dict:
    up = direction == "up"

    # TREND : alignement multi-TF + bon côté de la Kijun / du nuage.
    aligned = sum(1 for t in (f["trend_h4"], f["trend_m15"], f["trend_m5"])
                  if (t > 0) == up and t != 0)
    trend = 20 + 22 * aligned  # 0..86
    if (f["price_above_kijun"] == up):
        trend += 8
    if ((f["distance_cloud"] > 0) == up):
        trend += 6
    trend = _clip(trend)

    # WYCKOFF : Spring/UTAD + FVG frais aligné + mitigation + BOS.
    wy = 30.0
    if (up and f["spring_detected"]) or (not up and f["utad_detected"]):
        wy += 35
    if (f["fvg_dir"] == "BULLISH") == up and f["fvg_dir"]:
        wy += 20
    if f["fvg_mitigation"]:
        wy += 10
    if (f["bos"] > 0) == up and f["bos"] != 0:
        wy += 5
    wy = _clip(wy)

    # MOMENTUM : RSI dans une zone porteuse + divergence + displacement.
    rsi_v = f["rsi"]
    rsi_ok = (50 <= rsi_v <= 72) if up else (28 <= rsi_v <= 50)
    mom = 45.0 + (25 if rsi_ok else -10)
    if (f["rsi_divergence"] == "BULLISH") == up and f["rsi_divergence"] != "none":
        mom += 20
    mom += min(15.0, 15.0 * f["displacement"])  # bougie de déplacement
    mom = _clip(mom)

    # LIQUIDITY (order flow institutionnel) : sweep + FVG + pools de liquidité
    # (equal highs/lows) + order block mitigé dans le bon sens + zone
    # premium/discount favorable + breaker aligné.
    liq = 28.0
    if (f["liquidity_sweep"] > 0) == up and f["liquidity_sweep"] != 0:
        liq += 16
    if f["fvg_dir"]:
        liq += 10
    if (up and f["equal_lows"]) or (not up and f["equal_highs"]):
        liq += 14  # liquidité reposant sous/sur des égalités → cible logique
    if f["ob_dir"] and (f["ob_dir"] == "BULLISH") == up and f["ob_mitigation"]:
        liq += 18  # institution : entrée sur order block mitigé, dans le sens
    if (up and f["premium_discount"] <= 0.45) or (not up and f["premium_discount"] >= 0.55):
        liq += 12  # achat en discount / vente en premium
    if (f["breaker"] > 0) == up and f["breaker"] != 0:
        liq += 8   # breaker block inversé dans le sens
    liq = _clip(liq)

    # VOLATILITY : ATR dans une bande saine (ni mort ni chaotique) + spread OK.
    atr_pct = (f["atr"] / f["price"] * 100) if f["price"] else 0.0
    if 0.05 <= atr_pct <= 0.9:
        vola = 85.0
    elif atr_pct < 0.05:
        vola = 45.0     # marché trop plat
    else:
        vola = 40.0     # trop volatil / risqué
    if f["spread"] and f["atr"] and f["spread"] > 0.3 * f["atr"]:
        vola -= 20
    vola = _clip(vola)

    # NEWS : fourni (100 = pas d'annonce imminente).
    news = _clip(f["news_score"])

    return {"trend": round(trend), "wyckoff": round(wy), "momentum": round(mom),
            "liquidity": round(liq), "volatility": round(vola), "news": round(news)}


# ─────────────────────────────────────────────────────────────────────────────
# 3) VALIDATOR — GLOBAL SCORE + décision
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Validation:
    symbol: str
    direction: Optional[str]
    decision: str                 # EXECUTE | WATCHLIST | IGNORE
    confidence: int               # = GLOBAL SCORE
    scores: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)

    def to_training_record(self, trade_result: Optional[str] = None) -> dict:
        """Enregistrement label-ready pour le futur dataset ML (features → WIN/LOSS)."""
        return {"symbol": self.symbol, "direction": self.direction,
                "confidence": self.confidence, "scores": self.scores,
                "features": self.features, "result": trade_result}


def validate(df: pd.DataFrame, symbol: str = "?", news_score: float = 100.0,
             spread: float = 0.0, session_active: bool = True,
             execute_at: int = 80, watch_at: int = 60) -> Validation:
    f = build_features(df, news_score=news_score, spread=spread, session_active=session_active)
    direction = candidate_direction(f)
    if direction is None:
        return Validation(symbol, None, "IGNORE", 0, {}, f,
                          ["Pas de setup directionnel (structure/tendance neutres)."])

    sc = sub_scores(f, direction)
    global_score = sum(sc[k] * w for k, w in GLOBAL_WEIGHTS.items())
    confidence = round(global_score)

    reasons = []
    up = direction == "up"
    if f["ob_dir"] and (f["ob_dir"] == "BULLISH") == up and f["ob_mitigation"]:
        reasons.append("order block institutionnel mitigé dans le sens")
    if (up and f["premium_discount"] <= 0.45) or (not up and f["premium_discount"] >= 0.55):
        reasons.append("zone " + ("discount (accumulation)" if up else "premium (distribution)"))
    if (f["breaker"] > 0) == up and f["breaker"] != 0:
        reasons.append("breaker block inversé")
    if not session_active:
        reasons.append("hors session")
    if f["news_score"] < 60:
        reasons.append("news à fort impact imminente")

    hard_ok = session_active and f["news_score"] >= 60
    if confidence >= execute_at and hard_ok:
        decision = "EXECUTE"
    elif confidence >= watch_at:
        decision = "WATCHLIST"
    else:
        decision = "IGNORE"

    return Validation(symbol, direction, decision, confidence, sc, f, reasons)


# ─────────────────────────────────────────────────────────────────────────────
# 4) DONNÉES (démo) + CLI
# ─────────────────────────────────────────────────────────────────────────────

def _synthetic(n: int = 200, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    price, drift, vol, run = 78.0, 0.0, 0.2, 0
    closes = []
    for i in range(n):
        if run <= 0:
            drift = float(rng.choice([0.06, -0.06, 0.0], p=[0.45, 0.25, 0.30]))
            vol = float(rng.uniform(0.12, 0.28)); run = int(rng.integers(30, 70))
        price = max(20.0, price + drift + rng.normal(0, vol)); closes.append(price); run -= 1
    closes = np.array(closes)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) + np.abs(rng.normal(0.13, 0.06, n))
    lows = np.minimum(opens, closes) - np.abs(rng.normal(0.13, 0.06, n))
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes})


def render(v: Validation) -> str:
    L = ["=" * 52, f" AI SETUP VALIDATOR — {v.symbol}", "=" * 52]
    if v.direction:
        L.append(f" Direction candidate : {'BUY' if v.direction == 'up' else 'SELL'}")
        L.append("")
        for k in ("trend", "wyckoff", "momentum", "liquidity", "volatility", "news"):
            bar = "█" * (v.scores[k] // 5)
            L.append(f"   {k.capitalize():<11} {v.scores[k]:>3}%  {bar}")
        L.append("   " + "-" * 30)
        L.append(f"   {'Confidence':<11} {v.confidence:>3}%")
    else:
        L.append(" Aucun setup directionnel.")
    L.append("")
    L.append(f"   → {v.decision}")
    if v.reasons:
        L.append("   (" + " · ".join(v.reasons) + ")")
    L.append("=" * 52)
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description="AI Setup Validator (v1 déterministe) — démo XBRUSD")
    p.add_argument("--symbol", default="XBRUSD")
    p.add_argument("--news", type=float, default=100.0, help="news_score 0..100 (100 = RAS)")
    p.add_argument("--json", action="store_true", help="sortie JSON (features + scores)")
    args = p.parse_args()

    df = _synthetic()
    v = validate(df, symbol=args.symbol, news_score=args.news)
    if args.json:
        print(json.dumps(asdict(v), ensure_ascii=False, indent=2))
    else:
        print(render(v))


if __name__ == "__main__":
    main()
