#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest_clusters_jaunes.py — DREVM / GoldXrodgers
===================================================
Backtest de la these de l'article MQL5 #16555 ("clusters jaunes") :
un pic anormal de VOLATILITE DE VOLUME precede-t-il les retournements ?

Regles DREVM respectees :
  - NO-REPAINT : le z-score est calcule uniquement sur bougies CLOTUREES,
    avec des fenetres glissantes strictement causales (aucun lookahead).
  - Les retournements (swings) sont labellises a posteriori : c'est normal,
    on evalue un PREDICTEUR contre une verite terrain.

Metriques honnetes (ce que l'article ne fait pas) :
  - Precision  = P(retournement a +/- tol barres | barre jaune)
  - Rappel     = P(barre jaune a +/- tol barres | retournement)
  - Baseline   = P(barre quelconque a +/- tol d'un retournement)
  - Lift       = Precision / Baseline  (<= 1.0 => signal inutile)
  - p-value    = test de permutation (positions du signal melangees)
  - Avance     = distance mediane signal->retournement (negatif = predictif)

Prerequis : Windows + terminal MT5 Fusion Markets ouvert et connecte.
  pip install MetaTrader5 pandas numpy

Exemples :
  python backtest_clusters_jaunes.py
  python backtest_clusters_jaunes.py --timeframe M15 --bars 40000 --z 2.5
  python backtest_clusters_jaunes.py --symbols XAUUSD US30 --session 15:30-23:00
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- constantes
SYMBOLES_DREVM = ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]

VERDICTS = {
    "OK":     "\u2705 EXPLOITABLE",   # lift >= 1.5, avance <= 0, p < 0.05
    "MOYEN":  "\u26a0\ufe0f  MARGINAL",
    "NUL":    "\u274c INUTILE",
}


# ---------------------------------------------------------------- arguments
def parse_args():
    p = argparse.ArgumentParser(
        description="Backtest clusters jaunes (volatilite de volume) vs retournements")
    p.add_argument("--symbols", nargs="+", default=SYMBOLES_DREVM,
                   help="Symboles Fusion Markets (defaut: les 5 DREVM)")
    p.add_argument("--timeframe", default="M5",
                   choices=["M5", "M15", "M30", "H1", "H4"],
                   help="Timeframe d'evaluation (defaut: M5, regle no-repaint)")
    p.add_argument("--bars", type=int, default=60000,
                   help="Nombre de bougies a charger (defaut: 60000)")
    p.add_argument("--z", type=float, default=2.0,
                   help="Seuil z-score volatilite de volume => barre jaune (defaut: 2.0)")
    p.add_argument("--vol-window", type=int, default=10,
                   help="Fenetre std du volume = 'volatilite de volume' (defaut: 10)")
    p.add_argument("--z-window", type=int, default=288,
                   help="Fenetre du z-score causal (defaut: 288 = 1 jour en M5)")
    p.add_argument("--swing", type=int, default=5,
                   help="k bougies de chaque cote pour un swing/fractal (defaut: 5)")
    p.add_argument("--atr-mult", type=float, default=1.0,
                   help="Filtre: distance min entre swings en multiples d'ATR14 (defaut: 1.0)")
    p.add_argument("--tol", type=int, default=3,
                   help="Tolerance +/- N barres autour du retournement (defaut: 3, comme l'article)")
    p.add_argument("--session", default=None, metavar="HH:MM-HH:MM",
                   help="Filtre horaire SERVEUR (GMT+3 ete Fusion). Ex NY: 15:30-23:00")
    p.add_argument("--n-perm", type=int, default=200,
                   help="Iterations du test de permutation (defaut: 200)")
    p.add_argument("--out", default="resultats",
                   help="Dossier de sortie CSV (defaut: ./resultats)")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# ---------------------------------------------------------------- MT5
def init_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("\u274c Package MetaTrader5 introuvable. Windows uniquement : "
                 "pip install MetaTrader5 (a lancer sur le VPS Hostinger).")
    if not mt5.initialize():
        sys.exit(f"\u274c Echec initialisation MT5 : {mt5.last_error()} "
                 "(terminal Fusion Markets ouvert et connecte ?)")
    return mt5


def charger_bougies(mt5, symbole, tf_name, n_bars):
    tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
              "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
              "H4": mt5.TIMEFRAME_H4}
    if not mt5.symbol_select(symbole, True):
        print(f"  \u26a0\ufe0f  {symbole} indisponible chez le broker (suffixe ?) — ignore.")
        return None
    rates = mt5.copy_rates_from_pos(symbole, tf_map[tf_name], 0, n_bars)
    if rates is None or len(rates) < 2000:
        print(f"  \u26a0\ufe0f  {symbole}: donnees insuffisantes "
              f"({0 if rates is None else len(rates)} bougies) — ignore.")
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    # On exclut la derniere bougie (potentiellement en cours) : no-repaint.
    return df.iloc[:-1].reset_index(drop=True)


# ---------------------------------------------------------------- signal jaune
def signal_jaune(df, vol_window, z_window, seuil_z):
    """Z-score CAUSAL de la volatilite de volume, evalue au close uniquement.

    volatilite de volume = std glissante du tick_volume (fenetre vol_window)
    z-score = (valeur - moyenne des z_window barres PRECEDENTES) / std idem
    -> shift(1) sur les stats de reference pour exclure la barre courante.
    """
    vol_volat = df["tick_volume"].rolling(vol_window).std()
    ref_mean = vol_volat.rolling(z_window).mean().shift(1)
    ref_std = vol_volat.rolling(z_window).std().shift(1)
    z = (vol_volat - ref_mean) / ref_std.replace(0, np.nan)
    df["z_vol"] = z
    df["jaune"] = (z >= seuil_z).fillna(False)
    return df


# ---------------------------------------------------------------- retournements
def atr14(df):
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(14).mean()


def detecter_retournements(df, k, atr_mult):
    """Swings fractals (k bougies de chaque cote) filtres par distance ATR.

    Labellisation a posteriori (verite terrain). Un swing high suivi d'un
    swing low (et vice-versa) n'est retenu que si l'ecart de prix entre les
    deux >= atr_mult * ATR14 au moment du swing => elimine le bruit.
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    bruts = []  # (index, type, prix)
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and (h[i] > h[i - k:i]).all():
            bruts.append((i, "H", h[i]))
        elif l[i] == l[i - k:i + k + 1].min() and (l[i] < l[i - k:i]).all():
            bruts.append((i, "L", l[i]))

    # Alternance H/L : on garde l'extreme le plus extreme entre deux alternances
    alternes = []
    for idx, typ, px in bruts:
        if alternes and alternes[-1][1] == typ:
            if (typ == "H" and px > alternes[-1][2]) or \
               (typ == "L" and px < alternes[-1][2]):
                alternes[-1] = (idx, typ, px)
        else:
            alternes.append((idx, typ, px))

    # Filtre amplitude ATR
    atr = atr14(df).values
    retenus = []
    for j in range(1, len(alternes)):
        i0, _, p0 = alternes[j - 1]
        i1, _, p1 = alternes[j]
        seuil = atr[i1] if np.isfinite(atr[i1]) else np.nanmedian(atr)
        if abs(p1 - p0) >= atr_mult * seuil:
            retenus.append(i1)
            if not retenus or (len(retenus) >= 2 and retenus[-2] != i0):
                pass
            if i0 not in retenus:
                retenus.append(i0)
    retenus = sorted(set(retenus))
    return np.array(retenus, dtype=int)


# ---------------------------------------------------------------- metriques
def proche_de(indices_cibles, n, tol):
    """Masque booleen: bougies situees a +/- tol d'un indice cible."""
    m = np.zeros(n, dtype=bool)
    for i in indices_cibles:
        m[max(0, i - tol):min(n, i + tol + 1)] = True
    return m


def evaluer(df, revs, tol, n_perm, rng, masque_session=None):
    n = len(df)
    jaunes = np.flatnonzero(df["jaune"].values)
    valide = df["z_vol"].notna().values  # zone chauffee des fenetres
    if masque_session is not None:
        valide &= masque_session
        jaunes = jaunes[masque_session[jaunes]]
        revs = revs[masque_session[revs]]

    zone_rev = proche_de(revs, n, tol)
    zone_jaune = proche_de(jaunes, n, tol)

    n_valide = int(valide.sum())
    if len(jaunes) == 0 or len(revs) == 0 or n_valide == 0:
        return None

    precision = zone_rev[jaunes].mean()
    rappel = zone_jaune[revs].mean()
    baseline = zone_rev[valide].mean()
    lift = precision / baseline if baseline > 0 else np.nan

    # Avance/retard : pour chaque jaune "touchant", distance au retournement
    # le plus proche (negatif = le jaune PRECEDE le retournement -> predictif)
    dists = []
    for j in jaunes:
        d = revs - j
        dd = d[np.abs(d) <= tol]
        if len(dd):
            dists.append(dd[np.argmin(np.abs(dd))])
    avance_med = float(np.median(dists)) if dists else np.nan
    # convention : jaune a l'indice j, retournement a r ; d = r - j
    # d > 0 => le jaune arrive AVANT le retournement (predictif)

    # Test de permutation : on tire len(jaunes) positions au hasard dans la
    # zone valide et on mesure la precision obtenue par chance.
    pool = np.flatnonzero(valide)
    hits = 0
    for _ in range(n_perm):
        tirage = rng.choice(pool, size=len(jaunes), replace=False)
        if zone_rev[tirage].mean() >= precision:
            hits += 1
    p_value = (hits + 1) / (n_perm + 1)

    return {
        "bougies": n_valide,
        "jaunes": len(jaunes),
        "retournements": len(revs),
        "precision": precision,
        "rappel": rappel,
        "baseline": baseline,
        "lift": lift,
        "avance_mediane": avance_med,
        "p_value": p_value,
    }


def verdict(m):
    if m is None:
        return VERDICTS["NUL"]
    if m["lift"] >= 1.5 and m["p_value"] < 0.05 and (np.isnan(m["avance_mediane"]) or m["avance_mediane"] >= 0):
        return VERDICTS["OK"]
    if m["lift"] >= 1.15 and m["p_value"] < 0.10:
        return VERDICTS["MOYEN"]
    return VERDICTS["NUL"]


# ---------------------------------------------------------------- session
def masque_horaire(df, plage):
    """Filtre HH:MM-HH:MM en heure SERVEUR (Fusion = GMT+3 en ete)."""
    debut, fin = plage.split("-")
    h0, m0 = map(int, debut.split(":"))
    h1, m1 = map(int, fin.split(":"))
    minutes = df["time"].dt.hour * 60 + df["time"].dt.minute
    a, b = h0 * 60 + m0, h1 * 60 + m1
    return ((minutes >= a) & (minutes <= b)).values if a <= b \
        else ((minutes >= a) | (minutes <= b)).values


# ---------------------------------------------------------------- main
def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    mt5 = init_mt5()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n\U0001f7e1 BACKTEST CLUSTERS JAUNES — {args.timeframe} | "
          f"z>={args.z} | tol=+/-{args.tol} | swing k={args.swing} | "
          f"ATR filtre x{args.atr_mult}")
    if args.session:
        print(f"\u23f0 Session serveur : {args.session} (GMT+3 ete Fusion)")
    print("=" * 78)

    lignes = []
    try:
        for sym in args.symbols:
            df = charger_bougies(mt5, sym, args.timeframe, args.bars)
            if df is None:
                continue
            df = signal_jaune(df, args.vol_window, args.z_window, args.z)
            revs = detecter_retournements(df, args.swing, args.atr_mult)
            masque = masque_horaire(df, args.session) if args.session else None
            m = evaluer(df, revs, args.tol, args.n_perm, rng, masque)

            if m is None:
                print(f"{sym:<8} \u274c pas assez de signaux/retournements")
                continue

            v = verdict(m)
            print(f"{sym:<8} {v:<18} "
                  f"prec {m['precision']*100:5.1f}%  "
                  f"base {m['baseline']*100:5.1f}%  "
                  f"lift {m['lift']:.2f}  "
                  f"rappel {m['rappel']*100:4.1f}%  "
                  f"avance {m['avance_mediane']:+.1f}b  "
                  f"p={m['p_value']:.3f}  "
                  f"({m['jaunes']} jaunes / {m['retournements']} revs)")

            m.update(symbole=sym, timeframe=args.timeframe, verdict=v,
                     seuil_z=args.z, tol=args.tol,
                     date_test=datetime.now().strftime("%Y-%m-%d %H:%M"))
            lignes.append(m)

            # Export detail par bougie (audit / re-analyse Claude vision etc.)
            detail = df[["time", "close", "tick_volume", "z_vol", "jaune"]].copy()
            detail["retournement"] = False
            detail.loc[detail.index.isin(revs), "retournement"] = True
            detail.to_csv(out_dir / f"{sym}_{args.timeframe}_detail.csv", index=False)
    finally:
        mt5.shutdown()

    if lignes:
        synthese = pd.DataFrame(lignes)
        fichier = out_dir / f"synthese_{args.timeframe}_z{args.z}.csv"
        synthese.to_csv(fichier, index=False)
        print("=" * 78)
        print(f"\U0001f4be Synthese : {fichier}")
        print(f"\U0001f4c1 Details par bougie : {out_dir}/<SYMBOLE>_{args.timeframe}_detail.csv")
        print("\n\U0001f4d6 Lecture rapide :")
        print("  lift >= 1.5 ET p < 0.05 ET avance >= 0  => facteur de confluence candidat")
        print("  lift ~ 1.0                              => le '97%' de l'article = baseline triviale")
        print("  avance negative                          => le jaune ARRIVE APRES le retournement (inutile)")
    else:
        print("\u274c Aucun resultat. Verifie les noms de symboles Fusion Markets.")


if __name__ == "__main__":
    main()
