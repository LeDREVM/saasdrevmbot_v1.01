"""
==============================================================================
 backtest_xbrusd.py — Algo automatique (backtest) Wyckoff + FVG + Ichimoku
                      sur XBR/USD (Brent). Compte de départ : 100.
==============================================================================

 Backtest bougie par bougie qui prend des trades quand la confluence
 Wyckoff + FVG + Ichimoku est alignée (même smart signal que le scan du bot),
 gère SL (ATR) / TP (R:R) + break-even à 1R, et fait ÉVOLUER un compte qui
 démarre à 100 (money-management 1 % du capital risqué par trade, compounding).

 Il réutilise EXACTEMENT les mêmes détecteurs que le moteur live
 (ny_session_bot) : detect_wyckoff, detect_fvg, price_above_kijun,
 detect_divergence, get_bias_h4, score_confluence, atr — pas de logique
 dupliquée, le backtest teste la vraie stratégie.

 Données :
   • yfinance (BZ=F, Brent) si le réseau est dispo ;
   • sinon série SYNTHÉTIQUE déterministe (régimes trend/range) pour tourner
     hors-ligne et rester reproductible.

 Usage :
     python ny_session_interface/backtest_xbrusd.py
     python ny_session_interface/backtest_xbrusd.py --interval 1h --period 3mo
     python ny_session_interface/backtest_xbrusd.py --capital 100 --risk 0.01 --rr 2.0
==============================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd

# Détecteurs partagés avec le moteur live (même dossier).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ny_session_bot import (  # noqa: E402
    atr, detect_wyckoff, detect_divergence, price_above_kijun,
    get_bias_h4, detect_fvg, score_confluence,
)

# On importe le bot uniquement pour ses fonctions : coupe son logging bavard.
logging.getLogger("ny_bot").setLevel(logging.CRITICAL)

SYMBOL = "XBRUSD"
YAHOO_SYMBOL = "BZ=F"


# ─────────────────────────────────────────────────────────────────────────────
# 1) SIGNAL : confluence Wyckoff + FVG + Ichimoku sur une fenêtre de bougies
# ─────────────────────────────────────────────────────────────────────────────

def signal_at(window: pd.DataFrame, min_confluence: int) -> Optional[dict]:
    """
    Calcule le signal à la dernière bougie de `window`.

    Règle d'entrée (fidèle au trading réel de ces confluences — les 3 piliers
    ne culminent pas sur la même bougie : le Spring PUIS le déséquilibre PUIS
    le retest) :

      1. STRUCTURE  — un FVG frais donne le sens et la zone.
      2. TENDANCE   — filtre Ichimoku : Kijun alignée avec le sens du FVG.
      3. TIMING     — mitigation : le prix est revenu dans le gap (point d'entrée).

    Wyckoff (Spring/UTAD), divergence RSI et biais ajoutent des points de
    confluence ; `min_confluence` filtre sur le total /11 (sélectivité).
    Retourne None si pas de setup, sinon {direction, points, ...}.
    """
    if len(window) < 40:
        return None
    fvg = detect_fvg(window)
    fdir = fvg.get("direction")
    if fdir is None:                       # 1) pas de structure FVG → pas d'entrée
        return None
    direction = "up" if fdir == "BULLISH" else "down"

    above = price_above_kijun(window)
    ichimoku_ok = above if direction == "up" else (not above)
    if not ichimoku_ok:                    # 2) filtre de tendance
        return None
    if not fvg.get("price_in_gap"):        # 3) entrée seulement sur la mitigation
        return None

    ctx = SimpleNamespace(
        wyckoff=detect_wyckoff(window),
        price_above_kijun=above,
        rsi_divergence=detect_divergence(window),
        h4_bias=get_bias_h4(window),       # biais close vs close[-20] sur la même série
    )
    conf = score_confluence(ctx, fvg, direction)
    if conf["points"] < min_confluence:
        return None
    return {"direction": direction, "points": conf["points"], "max": conf["max"],
            "wyckoff": ctx.wyckoff, "fvg": fdir, "pillars": conf["pillars_aligned"]}


# ─────────────────────────────────────────────────────────────────────────────
# 2) BACKTEST
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    idx_in: int
    idx_out: int
    direction: str
    entry: float
    sl: float
    tp: float
    size: float
    exit: float
    pnl: float
    r_multiple: float
    reason: str          # "TP" | "SL" | "BE" | "EOD"
    capital_after: float


@dataclass
class BacktestResult:
    start_capital: float
    end_capital: float
    trades: list = field(default_factory=list)
    equity: list = field(default_factory=list)   # [(idx, capital), ...]


def run_backtest(df: pd.DataFrame, capital: float = 100.0, risk: float = 0.01,
                 rr: float = 2.0, sl_atr: float = 1.5, min_confluence: int = 6,
                 breakeven_at_r: float = 1.0, warmup: int = 40) -> BacktestResult:
    """
    Parcourt `df` bougie par bougie. Une seule position à la fois (flat→flat),
    sizing en fractions d'unité (type CFD) : risque = `risk` × capital, taille =
    risque / distance au SL → une perte au SL coûte exactement `risk` × capital.
    Capital composé après chaque clôture.
    """
    start_capital = capital
    equity = [(warmup, capital)]
    trades: list[Trade] = []

    pos: Optional[dict] = None
    n = len(df)
    highs = df["high"].to_numpy(float)
    lows = df["low"].to_numpy(float)
    closes = df["close"].to_numpy(float)

    for i in range(warmup, n):
        # ── Gestion d'une position ouverte ──────────────────────────────────
        if pos is not None:
            hit = None
            exit_px = None
            long = pos["direction"] == "up"

            # SL prioritaire si SL et TP touchés sur la même bougie (conservateur).
            if long:
                if lows[i] <= pos["sl"]:
                    hit, exit_px = ("SL" if pos["sl"] < pos["entry"] else "BE"), pos["sl"]
                elif highs[i] >= pos["tp"]:
                    hit, exit_px = "TP", pos["tp"]
            else:
                if highs[i] >= pos["sl"]:
                    hit, exit_px = ("SL" if pos["sl"] > pos["entry"] else "BE"), pos["sl"]
                elif lows[i] <= pos["tp"]:
                    hit, exit_px = "TP", pos["tp"]

            if hit is not None:
                pnl = pos["size"] * ((exit_px - pos["entry"]) if long else (pos["entry"] - exit_px))
                capital += pnl
                r_mult = pnl / pos["risk_amount"] if pos["risk_amount"] else 0.0
                trades.append(Trade(
                    idx_in=pos["idx_in"], idx_out=i, direction=pos["direction"],
                    entry=round(pos["entry"], 5), sl=round(pos["sl_init"], 5),
                    tp=round(pos["tp"], 5), size=round(pos["size"], 5),
                    exit=round(exit_px, 5), pnl=round(pnl, 4),
                    r_multiple=round(r_mult, 2), reason=hit, capital_after=round(capital, 4)))
                equity.append((i, capital))
                pos = None
                if capital <= 0:
                    break
                continue   # pas de ré-entrée sur la bougie de clôture
            else:
                # Break-even : dès +breakeven_at_r × R latent, SL → entrée.
                if breakeven_at_r and not pos["be_done"]:
                    r_dist = abs(pos["entry"] - pos["sl_init"])
                    reached = (highs[i] >= pos["entry"] + breakeven_at_r * r_dist) if long \
                        else (lows[i] <= pos["entry"] - breakeven_at_r * r_dist)
                    if reached:
                        pos["sl"] = pos["entry"]
                        pos["be_done"] = True
                continue  # une seule position : on n'ouvre pas tant qu'on est en position

        # ── Recherche d'une entrée (si flat) ────────────────────────────────
        window = df.iloc[: i + 1]
        sig = signal_at(window, min_confluence)
        if sig is None:
            continue
        a = atr(window)
        if not np.isfinite(a) or a <= 0:
            continue
        entry = closes[i]
        long = sig["direction"] == "up"
        sl = entry - sl_atr * a if long else entry + sl_atr * a
        sl_dist = abs(entry - sl)
        if sl_dist <= 0:
            continue
        tp = entry + rr * sl_dist if long else entry - rr * sl_dist
        risk_amount = capital * risk
        size = risk_amount / sl_dist
        pos = {
            "direction": sig["direction"], "entry": entry, "sl": sl, "sl_init": sl,
            "tp": tp, "size": size, "risk_amount": risk_amount,
            "idx_in": i, "be_done": False,
        }

    # Clôture d'une éventuelle position encore ouverte au dernier close.
    if pos is not None:
        i = n - 1
        long = pos["direction"] == "up"
        exit_px = closes[i]
        pnl = pos["size"] * ((exit_px - pos["entry"]) if long else (pos["entry"] - exit_px))
        capital += pnl
        r_mult = pnl / pos["risk_amount"] if pos["risk_amount"] else 0.0
        trades.append(Trade(
            idx_in=pos["idx_in"], idx_out=i, direction=pos["direction"],
            entry=round(pos["entry"], 5), sl=round(pos["sl_init"], 5),
            tp=round(pos["tp"], 5), size=round(pos["size"], 5),
            exit=round(exit_px, 5), pnl=round(pnl, 4), r_multiple=round(r_mult, 2),
            reason="EOD", capital_after=round(capital, 4)))
        equity.append((i, capital))

    return BacktestResult(start_capital, capital, trades, equity)


# ─────────────────────────────────────────────────────────────────────────────
# 3) STATISTIQUES
# ─────────────────────────────────────────────────────────────────────────────

def compute_stats(res: BacktestResult) -> dict:
    trades = res.trades
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    ret_pct = (res.end_capital / res.start_capital - 1) * 100 if res.start_capital else 0.0

    # Max drawdown sur la courbe d'équité (compte réalisé).
    peak = res.start_capital
    max_dd = 0.0
    for _, c in res.equity:
        peak = max(peak, c)
        max_dd = max(max_dd, (peak - c) / peak * 100 if peak else 0.0)

    r_values = [t.r_multiple for t in trades]
    return {
        "trades": n,
        "wins": len(wins), "losses": len(losses),
        "winrate": (len(wins) / n * 100) if n else 0.0,
        "return_pct": ret_pct,
        "profit_factor": (gross_win / gross_loss) if gross_loss else float("inf"),
        "avg_r": (sum(r_values) / n) if n else 0.0,
        "expectancy_r": (sum(r_values) / n) if n else 0.0,
        "max_dd_pct": max_dd,
        "best_r": max(r_values) if r_values else 0.0,
        "worst_r": min(r_values) if r_values else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4) DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

def fetch_yfinance(interval: str, period: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        df = yf.Ticker(YAHOO_SYMBOL).history(period=period, interval=interval)
        if df is None or df.empty or len(df) < 80:
            return None
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close"]].astype(float).reset_index(drop=True)
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️  yfinance indisponible ({exc}); série synthétique.")
        return None


def synthetic_brent(n: int = 1500, seed: int = 7) -> pd.DataFrame:
    """
    Série Brent SYNTHÉTIQUE déterministe avec régimes alternés (tendance haussière,
    tendance baissière, range) et volatilité variable. Produit naturellement des
    Spring/UTAD, des FVG et des franchissements de Kijun → plusieurs setups.
    """
    rng = np.random.default_rng(seed)
    price = 78.0
    closes = np.empty(n)
    regime_len = 0
    drift = 0.0
    vol = 0.18
    for i in range(n):
        if regime_len <= 0:
            regime = rng.choice(["up", "down", "range"], p=[0.4, 0.3, 0.3])
            regime_len = int(rng.integers(40, 130))
            drift = {"up": 0.05, "down": -0.05, "range": 0.0}[regime]
            vol = float(rng.uniform(0.12, 0.30))
        price = max(20.0, price + drift + rng.normal(0, vol))
        closes[i] = price
        regime_len -= 1

    # Mèches réalistes autour de chaque close.
    hi_w = np.abs(rng.normal(0.14, 0.07, n))
    lo_w = np.abs(rng.normal(0.14, 0.07, n))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) + hi_w
    lows = np.minimum(opens, closes) - lo_w
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes})


# ─────────────────────────────────────────────────────────────────────────────
# 5) RAPPORT
# ─────────────────────────────────────────────────────────────────────────────

def render(source: str, args, res: BacktestResult, stats: dict) -> str:
    L = []
    L.append("=" * 70)
    L.append(" BACKTEST — Algo Wyckoff + FVG + Ichimoku · XBRUSD (Brent)")
    L.append(f" Données : {source}  |  timeframe {args.interval}")
    L.append(f" Money-management : {args.risk*100:.0f}% risqué/trade · R:R {args.rr} · "
             f"SL {args.sl_atr}×ATR · BE à {args.breakeven}R · confluence ≥ {args.min_confluence}/11")
    L.append("=" * 70)
    L.append("")
    L.append(" COMPTE")
    L.append(f"   • Capital départ : {res.start_capital:.2f}")
    L.append(f"   • Capital final  : {res.end_capital:.2f}")
    sign = "+" if stats["return_pct"] >= 0 else ""
    L.append(f"   • Rendement      : {sign}{stats['return_pct']:.2f} %")
    L.append(f"   • Max drawdown   : -{stats['max_dd_pct']:.2f} %")
    L.append("")
    L.append(" PERFORMANCE")
    L.append(f"   • Trades         : {stats['trades']}  ({stats['wins']}W / {stats['losses']}L)")
    L.append(f"   • Winrate        : {stats['winrate']:.1f} %")
    pf = stats["profit_factor"]
    L.append(f"   • Profit factor  : {'∞' if pf == float('inf') else f'{pf:.2f}'}")
    L.append(f"   • Espérance      : {stats['expectancy_r']:+.2f} R / trade")
    L.append(f"   • Meilleur / pire: {stats['best_r']:+.2f} R / {stats['worst_r']:+.2f} R")
    L.append("")
    if res.trades:
        L.append(" DERNIERS TRADES")
        L.append("   #   sens  entrée →  sortie   motif   R      capital")
        for k, t in enumerate(res.trades[-12:], 1):
            d = "BUY " if t.direction == "up" else "SELL"
            L.append(f"   {k:>2}  {d}  {t.entry:>7.2f} → {t.exit:>7.2f}  "
                     f"{t.reason:<4}  {t.r_multiple:>+5.2f}  {t.capital_after:>8.2f}")
    else:
        L.append(" Aucun trade déclenché sur la période "
                 "(confluence jamais complète — essaie --min-confluence 6).")
    L.append("=" * 70)
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description="Backtest Wyckoff+FVG+Ichimoku XBRUSD, compte départ 100")
    p.add_argument("--capital", type=float, default=100.0)
    p.add_argument("--risk", type=float, default=0.01, help="fraction du capital risquée/trade (0.01 = 1%)")
    p.add_argument("--rr", type=float, default=2.0, help="objectif R:R")
    p.add_argument("--sl-atr", dest="sl_atr", type=float, default=1.5, help="SL en multiples d'ATR")
    p.add_argument("--breakeven", type=float, default=1.0, help="passe le SL à BE à ce multiple de R (0=off)")
    p.add_argument("--min-confluence", dest="min_confluence", type=int, default=6, help="points min /11")
    p.add_argument("--interval", default="1h")
    p.add_argument("--period", default="3mo")
    p.add_argument("--live", action="store_true", help="exiger yfinance (pas de synthétique)")
    args = p.parse_args()

    print(f"→ Chargement {SYMBOL} ({YAHOO_SYMBOL}) [{args.interval}/{args.period}]…")
    df = fetch_yfinance(args.interval, args.period)
    if df is not None:
        source = f"yfinance {YAHOO_SYMBOL} ({len(df)} bougies)"
    elif args.live:
        raise SystemExit("❌ yfinance indisponible et --live demandé.")
    else:
        print("→ Réseau indisponible : série synthétique déterministe.")
        df = synthetic_brent()
        source = f"synthétique ({len(df)} bougies)"

    res = run_backtest(
        df, capital=args.capital, risk=args.risk, rr=args.rr,
        sl_atr=args.sl_atr, min_confluence=args.min_confluence,
        breakeven_at_r=args.breakeven,
    )
    stats = compute_stats(res)
    print()
    print(render(source, args, res, stats))


if __name__ == "__main__":
    main()
