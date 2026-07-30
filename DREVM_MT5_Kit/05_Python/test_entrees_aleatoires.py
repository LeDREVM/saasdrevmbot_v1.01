#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_entrees_aleatoires.py — DREVM / GoldXrodgers
==================================================
QUESTION : l'edge residuel vient-il du SIGNAL ou de la GESTION de position ?

Principe : on garde EXACTEMENT la meme mecanique de trade (ordre limite,
SL/TP, partiel a 1R, breakeven, trailing ATR) mais on remplace les entrees
du moteur DREVM par des entrees ALEATOIRES appariees :
  - meme instrument, meme timeframe, meme periode
  - meme distribution d'heures (on tire dans les memes creneaux)
  - meme distribution de distance de SL (en ATR)
  - meme proportion BUY/SELL  (mode --apparie)
  ou proportion 50/50        (mode --neutre)

Trois bras compares :
  1. REEL      : les signaux du moteur DREVM (CSV existant)
  2. ALEATOIRE : entrees au hasard, meme gestion
  3. BETA      : meme sens que le reel mais dates tirees au hasard
                 -> isole la part expliquee par la tendance de fond

INTERPRETATION
  reel >> aleatoire            -> le signal apporte quelque chose
  reel ~= aleatoire            -> 100% de l'edge vient de la gestion
  aleatoire ~= beta ~= reel    -> tout vient de la tendance de l'instrument

Prerequis : Windows + MT5 (pour les bougies) OU --ohlc fichier.csv
  pip install MetaTrader5 pandas numpy

Exemples :
  python test_entrees_aleatoires.py --signaux XAUUSD_v2_M15_signaux.csv \
      --symbol XAUUSD --timeframe M15
  python test_entrees_aleatoires.py --signaux XAUUSD_v2_H1_signaux.csv \
      --symbol XAUUSD --timeframe H1 --n-sim 200
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser(description="Entrees aleatoires vs signal DREVM")
    p.add_argument("--signaux", required=True, help="CSV de signaux produit par backtest_grades.py")
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="M15", choices=["M5", "M15", "M30", "H1"])
    p.add_argument("--bars", type=int, default=200000)
    p.add_argument("--ohlc", default=None, help="CSV OHLC au lieu de MT5 (time,open,high,low,close)")
    p.add_argument("--n-sim", type=int, default=100, help="Nombre de simulations aleatoires")
    p.add_argument("--mode", default="apparie", choices=["apparie", "neutre"],
                   help="apparie = meme proportion BUY/SELL | neutre = 50/50")
    p.add_argument("--expiry", type=int, default=24)
    p.add_argument("--horizon", type=int, default=96)
    p.add_argument("--tp-rr", type=float, default=2.5)
    p.add_argument("--partial-at-r", type=float, default=1.0)
    p.add_argument("--partial-pct", type=float, default=50.0)
    p.add_argument("--trail-atr-mult", type=float, default=1.5)
    p.add_argument("--gestion", default="complete", choices=["simple", "complete"])
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# ---------------------------------------------------------------- donnees
def atr_wilder(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def charger_ohlc(a):
    if a.ohlc:
        df = pd.read_csv(a.ohlc, parse_dates=["time"])
        return df.reset_index(drop=True)
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("\u274c MetaTrader5 introuvable. Utilise --ohlc fichier.csv sinon.")
    if not mt5.initialize():
        sys.exit(f"\u274c Echec init MT5 : {mt5.last_error()}")
    tf = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
          "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1}[a.timeframe]
    mt5.symbol_select(a.symbol, True)
    mt5.copy_rates_from_pos(a.symbol, tf, 0, 100)
    r = None
    for p in (a.bars, 100000, 60000, 30000, 10000):
        r = mt5.copy_rates_from_pos(a.symbol, tf, 0, p)
        if r is not None and len(r) > 5000:
            break
    mt5.shutdown()
    if r is None:
        sys.exit("\u274c Historique indisponible.")
    df = pd.DataFrame(r)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.iloc[:-1].reset_index(drop=True)


# ---------------------------------------------------------------- moteur
def jouer_trade(df, atr, i, sens, dist_sl, a):
    """Meme mecanique que le backtest : limite -> remplissage -> gestion.

    L'entree limite est placee a `dist_sl` de distance du close (ordre de repli),
    ce qui reproduit la logique 'attendre un pullback' du moteur DREVM.
    """
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    entry = c[i] - sens * dist_sl * 0.5     # limite placee en retrait
    sl = entry - sens * dist_sl
    R = abs(entry - sl)
    if R <= 0:
        return np.nan
    tp = entry + sens * a.tp_rr * R

    fill = -1
    for j in range(i + 1, min(i + 1 + a.expiry, n)):
        if (l[j] <= entry) if sens > 0 else (h[j] >= entry):
            fill = j
            break
    if fill < 0:
        return np.nan

    pnl, reste, sl_cur, part_faite = 0.0, 1.0, sl, False
    cible = entry + sens * a.partial_at_r * R
    for j in range(fill, min(fill + a.horizon, n)):
        hit_sl = (l[j] <= sl_cur) if sens > 0 else (h[j] >= sl_cur)
        hit_tp = (h[j] >= tp) if sens > 0 else (l[j] <= tp)
        if hit_sl:
            pnl += reste * (sl_cur - entry) * sens / R
            reste = 0.0
            break
        if hit_tp:
            pnl += reste * a.tp_rr
            reste = 0.0
            break
        if a.gestion == "complete":
            atteint = (h[j] >= cible) if sens > 0 else (l[j] <= cible)
            if not part_faite and atteint:
                part = a.partial_pct / 100.0
                pnl += part * a.partial_at_r
                reste -= part
                part_faite = True
                sl_cur = entry
            if part_faite and np.isfinite(atr[j]):
                d = a.trail_atr_mult * atr[j]
                nv = (c[j] - d) if sens > 0 else (c[j] + d)
                sl_cur = max(sl_cur, nv) if sens > 0 else min(sl_cur, nv)
    if reste > 0:
        fin = c[min(fill + a.horizon, n - 1)]
        pnl += reste * (fin - entry) * sens / R
    return pnl


def stats(r):
    r = np.asarray(pd.Series(r).dropna(), float)
    if len(r) == 0:
        return None
    g, p = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), wr=float((r > 0).mean()), exp=float(r.mean()),
                pf=float(g / p) if p > 0 else np.inf)


# ---------------------------------------------------------------- main
def main():
    a = parse_args()
    rng = np.random.default_rng(a.seed)

    sig = pd.read_csv(a.signaux, parse_dates=["time"])
    reel = sig[sig["rempli"]] if "rempli" in sig.columns else sig
    s_reel = stats(reel["resultat_R"])
    if s_reel is None:
        sys.exit("\u274c Aucun trade rempli dans le CSV de signaux.")

    df = charger_ohlc(a)
    atr = atr_wilder(df).values
    n = len(df)

    # distributions a repliquer
    heures_pool = reel["heure"].values if "heure" in reel.columns else None
    dist_atr = (reel["risque"] / reel["atr"]).replace([np.inf, -np.inf], np.nan).dropna().values
    if len(dist_atr) == 0:
        dist_atr = np.array([1.0])
    part_buy = float((reel["sens"] > 0).mean())
    n_trades = len(reel)

    heures_df = df["time"].dt.hour.values
    marge = a.expiry + a.horizon + 20
    candidats = np.arange(20, n - marge)
    if heures_pool is not None:
        creneaux = set(np.unique(heures_pool).tolist())
        candidats = candidats[np.isin(heures_df[candidats], list(creneaux))]
    if len(candidats) < 100:
        sys.exit("\u274c Pas assez de bougies candidates.")

    print(f"\n\U0001f3b2 ENTREES ALEATOIRES vs SIGNAL DREVM — {a.symbol} {a.timeframe}")
    print(f"   {n_trades} trades reels | {a.n_sim} simulations | mode {a.mode} | "
          f"gestion {a.gestion}")
    print("=" * 78)

    exp_alea, pf_alea, wr_alea = [], [], []
    for _ in range(a.n_sim):
        idx = rng.choice(candidats, size=n_trades, replace=False)
        if a.mode == "apparie":
            sens = np.where(rng.random(n_trades) < part_buy, 1, -1)
        else:
            sens = rng.choice([1, -1], size=n_trades)
        d = rng.choice(dist_atr, size=n_trades)
        res = [jouer_trade(df, atr, int(i), int(s), float(dd) * atr[int(i)], a)
               for i, s, dd in zip(idx, sens, d)]
        st = stats(res)
        if st:
            exp_alea.append(st["exp"])
            pf_alea.append(st["pf"])
            wr_alea.append(st["wr"])

    exp_alea = np.array(exp_alea)
    pf_alea = np.array(pf_alea)

    # bras BETA : sens reel conserve, dates tirees au hasard
    exp_beta = []
    sens_reel = reel["sens"].values
    for _ in range(a.n_sim):
        idx = rng.choice(candidats, size=n_trades, replace=False)
        d = rng.choice(dist_atr, size=n_trades)
        res = [jouer_trade(df, atr, int(i), int(s), float(dd) * atr[int(i)], a)
               for i, s, dd in zip(idx, sens_reel, d)]
        st = stats(res)
        if st:
            exp_beta.append(st["exp"])
    exp_beta = np.array(exp_beta)

    print(f"  1. REEL (signal DREVM) : n={s_reel['n']:4d} WR={s_reel['wr']*100:5.1f}% "
          f"exp={s_reel['exp']:+.4f}R PF={s_reel['pf']:.3f}")
    print(f"  2. ALEATOIRE           : exp={exp_alea.mean():+.4f}R "
          f"[{np.percentile(exp_alea,5):+.4f} ; {np.percentile(exp_alea,95):+.4f}] "
          f"PF={pf_alea.mean():.3f}")
    print(f"  3. BETA (sens conserve): exp={exp_beta.mean():+.4f}R "
          f"[{np.percentile(exp_beta,5):+.4f} ; {np.percentile(exp_beta,95):+.4f}]")

    p_alea = float((exp_alea >= s_reel["exp"]).mean())
    p_beta = float((exp_beta >= s_reel["exp"]).mean())
    print(f"\n  p(aleatoire \u2265 reel) = {p_alea:.3f}   "
          f"p(beta \u2265 reel) = {p_beta:.3f}")

    print("\n  \U0001f4d6 VERDICT :")
    if p_alea < 0.05 and p_beta < 0.05:
        print("     \u2705 Le signal bat le hasard ET le beta -> il apporte une information.")
    elif p_alea < 0.05:
        print("     \u26a0\ufe0f  Le signal bat le hasard mais pas le beta directionnel :")
        print("        l'edge vient du BIAIS DE SENS, pas de la selection des entrees.")
    else:
        print("     \u274c Le signal ne bat pas des entrees aleatoires :")
        print("        tout l'edge mesure provient de la GESTION DE POSITION.")
        print("        -> investir dans la gestion du risque, pas dans le scoring.")

    ecart = s_reel["exp"] - exp_alea.mean()
    print(f"\n  Valeur ajoutee du signal = {ecart:+.4f}R par trade")
    if abs(ecart) < 0.02:
        print("  (sous le seuil des couts de transaction : non exploitable)")


if __name__ == "__main__":
    main()
