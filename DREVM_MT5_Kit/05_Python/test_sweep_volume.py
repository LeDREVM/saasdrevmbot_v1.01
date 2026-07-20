#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_sweep_volume.py — DREVM / GoldXrodgers
============================================
Le delta de volume au moment d'un SWEEP DE LIQUIDITE ameliore-t-il
le taux de reussite du setup ?

DIFFERENCE CLE vs le test precedent (clusters jaunes) :
  On ne compare plus "bougies avec signal" vs "toutes les bougies"
  -> ce design avait produit un artefact d'heure d'ouverture.
  On compare ici SWEEPS A FORT VOLUME vs SWEEPS A FAIBLE VOLUME.
  La population de base est deja conditionnee a un evenement structurel,
  donc l'heure, la session et la volatilite de fond sont largement
  neutralisees par construction. Un controle horaire en strates est
  applique en plus (test 4).

DEFINITION DU SWEEP (SMC/ICT, no-repaint)
  1. Swing de reference = fractal k barres, CONFIRME (donc connu seulement
     k barres apres sa formation -> aucun lookahead).
  2. Sweep haussier (=> biais SELL) : une bougie fait high > swing_high
     mais CLOTURE sous swing_high. La liquidite au-dessus a ete prise
     puis rejetee.
  3. Sweep baissier (=> biais BUY) : low < swing_low et close > swing_low.
  4. Le sweep n'est valide qu'a la CLOTURE de la bougie (regle DREVM M5).

DELTA DE VOLUME
  vol_ratio = tick_volume(bougie de sweep) / mediane(tick_volume des 20 precedentes)
  Mesure purement locale => insensible au niveau de volume de la session.

EVALUATION ECONOMIQUE (le vrai juge)
  Entree  : close de la bougie de sweep
  SL      : extreme du sweep +/- buffer ATR
  Cible   : 2R
  Sortie  : premier des deux touche dans les N barres suivantes, sinon flat.
  Metriques : winrate, expectancy en R, profit factor.
  Le tout ventile par quintile de vol_ratio.

Prerequis : Windows + terminal MT5 Fusion Markets ouvert.
  pip install MetaTrader5 pandas numpy

Exemples :
  python test_sweep_volume.py
  python test_sweep_volume.py --symbols US30 XAUUSD --bars 100000
  python test_sweep_volume.py --rr 3 --horizon 60 --swing 8
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLES_DREVM = ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]


# ---------------------------------------------------------------- arguments
def parse_args():
    p = argparse.ArgumentParser(description="Delta de volume au sweep de liquidite")
    p.add_argument("--symbols", nargs="+", default=SYMBOLES_DREVM)
    p.add_argument("--timeframe", default="M5",
                   choices=["M5", "M15", "M30", "H1"])
    p.add_argument("--bars", type=int, default=100000)
    p.add_argument("--swing", type=int, default=5,
                   help="k barres de chaque cote pour un swing fractal (defaut 5)")
    p.add_argument("--lookback-swing", type=int, default=100,
                   help="Fenetre max de recherche du swing balaye (defaut 100)")
    p.add_argument("--vol-ref", type=int, default=20,
                   help="N bougies precedentes pour la mediane de volume (defaut 20)")
    p.add_argument("--rr", type=float, default=2.0,
                   help="Objectif en R (defaut 2.0)")
    p.add_argument("--sl-buffer", type=float, default=0.25,
                   help="Buffer SL au-dela de l'extreme, en multiples d'ATR14 (defaut 0.25)")
    p.add_argument("--horizon", type=int, default=48,
                   help="Barres max pour resoudre le trade (defaut 48 = 4h en M5)")
    p.add_argument("--min-r-dist", type=float, default=0.3,
                   help="Distance SL minimale en ATR, filtre les sweeps degeneres")
    p.add_argument("--out", default="resultats_sweep")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# ---------------------------------------------------------------- MT5
def init_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("\u274c Package MetaTrader5 introuvable (Windows uniquement) : "
                 "pip install MetaTrader5")
    if not mt5.initialize():
        sys.exit(f"\u274c Echec init MT5 : {mt5.last_error()}")
    return mt5


MIN_BOUGIES = 3000  # plancher absolu pour que les stats aient un sens


def charger(mt5, symbole, tf_name, n_bars):
    """Chargement robuste.

    MT5 renvoie None (et non une serie tronquee) quand on demande plus de
    bougies que l'historique present en cache. On amorce donc le telechargement
    puis on degresse la demande jusqu'a obtenir quelque chose d'exploitable.
    """
    tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
              "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1}
    tf = tf_map[tf_name]

    if not mt5.symbol_select(symbole, True):
        print(f"  \u26a0\ufe0f  {symbole} : symbole absent du Market Watch "
              f"(suffixe broker ? ex. {symbole}.a) — ignore.")
        return None

    # Amorce : force MT5 a rapatrier l'historique depuis le serveur.
    mt5.copy_rates_from_pos(symbole, tf, 0, 100)

    paliers = [n_bars, 60000, 30000, 15000, 5000, MIN_BOUGIES]
    paliers = sorted({p for p in paliers if p <= n_bars}, reverse=True)

    for p in paliers:
        r = mt5.copy_rates_from_pos(symbole, tf, 0, p)
        if r is not None and len(r) >= MIN_BOUGIES:
            if p < n_bars:
                print(f"  \u2139\ufe0f  {symbole} : {n_bars} bougies indisponibles, "
                      f"replie sur {len(r)}.")
            df = pd.DataFrame(r)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df.iloc[:-1].reset_index(drop=True)  # exclut la bougie en cours

    dispo = mt5.copy_rates_from_pos(symbole, tf, 0, MIN_BOUGIES)
    n_dispo = 0 if dispo is None else len(dispo)
    print(f"  \u26a0\ufe0f  {symbole} : seulement {n_dispo} bougies {tf_name} "
          f"accessibles (minimum {MIN_BOUGIES}).")
    print(f"      \u2192 dans MT5 : Outils > Options > Graphiques > "
          f"'Max. barres dans le graphique' = Illimite, puis ouvrir un chart "
          f"{symbole} {tf_name} et faire defiler vers la gauche.")
    return None


# ---------------------------------------------------------------- indicateurs
def atr14(df):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean()


def swings_confirmes(df, k):
    """Retourne deux tableaux : pour chaque indice i, le dernier swing high /
    swing low CONNU a la cloture de i (confirme k barres plus tot).
    Aucun lookahead : un swing en position p n'est disponible qu'a partir de p+k.
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    sh_px = np.full(n, np.nan)   # prix du dernier swing high connu
    sh_idx = np.full(n, -1)
    sl_px = np.full(n, np.nan)
    sl_idx = np.full(n, -1)

    est_sh = np.zeros(n, bool)
    est_sl = np.zeros(n, bool)
    for p in range(k, n - k):
        w_h = h[p - k:p + k + 1]
        w_l = l[p - k:p + k + 1]
        if h[p] == w_h.max() and (h[p] > h[p - k:p]).all():
            est_sh[p] = True
        if l[p] == w_l.min() and (l[p] < l[p - k:p]).all():
            est_sl[p] = True

    cur_h, cur_hi = np.nan, -1
    cur_l, cur_li = np.nan, -1
    for i in range(n):
        p = i - k                      # swing confirme seulement maintenant
        if p >= 0 and est_sh[p]:
            cur_h, cur_hi = h[p], p
        if p >= 0 and est_sl[p]:
            cur_l, cur_li = l[p], p
        sh_px[i], sh_idx[i] = cur_h, cur_hi
        sl_px[i], sl_idx[i] = cur_l, cur_li
    return sh_px, sh_idx, sl_px, sl_idx


# ---------------------------------------------------------------- sweeps
def detecter_sweeps(df, k, lookback, vol_ref, atr, min_r_dist):
    """Detecte les sweeps de liquidite valides a la cloture.

    Retourne un DataFrame : index, sens (-1 sell / +1 buy), entree, extreme,
    vol_ratio, heure, dist_atr.
    """
    h, l = df["high"].values, df["low"].values
    c = df["close"].values
    v = df["tick_volume"].values.astype(float)
    n = len(df)
    sh_px, sh_idx, sl_px, sl_idx = swings_confirmes(df, k)

    # mediane causale du volume sur les vol_ref bougies PRECEDENTES
    vol_med = pd.Series(v).rolling(vol_ref).median().shift(1).values

    lignes = []
    for i in range(k + vol_ref + 20, n):
        if not np.isfinite(atr[i]) or not np.isfinite(vol_med[i]) or vol_med[i] <= 0:
            continue

        # --- sweep haussier -> biais SELL
        if np.isfinite(sh_px[i]) and (i - sh_idx[i]) <= lookback:
            if h[i] > sh_px[i] and c[i] < sh_px[i]:
                dist = (h[i] - c[i]) / atr[i]
                if dist >= min_r_dist:
                    lignes.append((i, -1, c[i], h[i], v[i] / vol_med[i], dist))
                    continue

        # --- sweep baissier -> biais BUY
        if np.isfinite(sl_px[i]) and (i - sl_idx[i]) <= lookback:
            if l[i] < sl_px[i] and c[i] > sl_px[i]:
                dist = (c[i] - l[i]) / atr[i]
                if dist >= min_r_dist:
                    lignes.append((i, 1, c[i], l[i], v[i] / vol_med[i], dist))

    if not lignes:
        return pd.DataFrame()
    out = pd.DataFrame(lignes, columns=["i", "sens", "entree", "extreme",
                                        "vol_ratio", "dist_atr"])
    out["heure"] = df["time"].dt.hour.values[out["i"].values]
    out["time"] = df["time"].values[out["i"].values]
    return out


# ---------------------------------------------------------------- simulation
def simuler(df, sweeps, atr, rr, sl_buffer, horizon):
    """Trade a la cloture du sweep. SL au-dela de l'extreme + buffer ATR.
    Resolution barre par barre. Si SL et TP sont touches sur la meme barre,
    on compte le SL (hypothese conservatrice).
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    res = []
    for row in sweeps.itertuples():
        i, sens, entree, extreme = row.i, row.sens, row.entree, row.extreme
        buf = sl_buffer * atr[i]
        sl = extreme + buf if sens == -1 else extreme - buf
        risque = abs(entree - sl)
        if risque <= 0 or i + horizon >= n:
            continue
        tp = entree - rr * risque if sens == -1 else entree + rr * risque

        issue = 0.0
        for j in range(i + 1, min(i + 1 + horizon, n)):
            if sens == -1:
                if h[j] >= sl:
                    issue = -1.0
                    break
                if l[j] <= tp:
                    issue = rr
                    break
            else:
                if l[j] <= sl:
                    issue = -1.0
                    break
                if h[j] >= tp:
                    issue = rr
                    break
        else:
            # non resolu : sortie au marche a la fin de l'horizon
            fin = df["close"].values[min(i + horizon, n - 1)]
            issue = ((entree - fin) if sens == -1 else (fin - entree)) / risque
        res.append(issue)
    sweeps = sweeps.iloc[:len(res)].copy()
    sweeps["resultat_R"] = res
    return sweeps


# ---------------------------------------------------------------- stats
def stats_bloc(r):
    r = np.asarray(r, float)
    if len(r) == 0:
        return None
    gains, pertes = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), winrate=float((r > 0).mean()),
                expectancy=float(r.mean()),
                pf=float(gains / pertes) if pertes > 0 else np.inf)


def bootstrap_diff(a, b, n_boot, rng):
    """p-value : P(expectancy(a) <= expectancy(b)) par bootstrap."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    na = len(a)
    cnt = 0
    for _ in range(n_boot):
        p = rng.permutation(pool)
        if (p[:na].mean() - p[na:].mean()) >= obs:
            cnt += 1
    return (cnt + 1) / (n_boot + 1), obs


# ---------------------------------------------------------------- main
def main():
    a = parse_args()
    rng = np.random.default_rng(a.seed)
    mt5 = init_mt5()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n\U0001f4a7 DELTA DE VOLUME AU SWEEP — {a.timeframe} | "
          f"swing k={a.swing} | cible {a.rr}R | horizon {a.horizon}b | "
          f"ref volume {a.vol_ref}b")
    print("=" * 84)

    synth = []
    try:
        for sym in a.symbols:
            df = charger(mt5, sym, a.timeframe, a.bars)
            if df is None:
                continue
            atr = atr14(df).values
            sw = detecter_sweeps(df, a.swing, a.lookback_swing, a.vol_ref,
                                 atr, a.min_r_dist)
            if sw.empty or len(sw) < 60:
                print(f"{sym}: trop peu de sweeps ({len(sw)}) — ignore.")
                continue
            sw = simuler(df, sw, atr, a.rr, a.sl_buffer, a.horizon)

            base = stats_bloc(sw["resultat_R"])
            print(f"\n\u2500\u2500\u2500 {sym} \u2500\u2500\u2500  "
                  f"{df.time.min().date()} \u2192 {df.time.max().date()}")
            print(f"  BASELINE tous sweeps : n={base['n']} "
                  f"WR={base['winrate']*100:.1f}% "
                  f"exp={base['expectancy']:+.3f}R PF={base['pf']:.2f}")

            # --- 1) quintiles de vol_ratio
            sw["quintile"] = pd.qcut(sw["vol_ratio"], 5, labels=False,
                                     duplicates="drop")
            print("  \u2500 Par quintile de delta de volume :")
            for q in sorted(sw["quintile"].dropna().unique()):
                b = sw[sw["quintile"] == q]
                s = stats_bloc(b["resultat_R"])
                print(f"    Q{int(q)+1} (vol x{b['vol_ratio'].min():.2f}"
                      f"\u2013{b['vol_ratio'].max():.2f}) : n={s['n']:4d} "
                      f"WR={s['winrate']*100:5.1f}% exp={s['expectancy']:+.3f}R "
                      f"PF={s['pf']:.2f}")

            # --- 2) haut vs bas quintile, test de permutation
            qmax = sw["quintile"].max()
            haut = sw[sw["quintile"] == qmax]["resultat_R"].values
            bas = sw[sw["quintile"] == 0]["resultat_R"].values
            p, diff = bootstrap_diff(haut, bas, 2000, rng)
            print(f"  \u2500 Q5 vs Q1 : \u0394exp={diff:+.3f}R  p={p:.4f} "
                  f"{'\u2705' if p < 0.05 else '\u274c'}")

            # --- 3) split out-of-sample chronologique 70/30
            cut = int(len(sw) * 0.7)
            for lab, part in [("in-sample ", sw.iloc[:cut]),
                              ("out-sample", sw.iloc[cut:])]:
                hi = part[part["vol_ratio"] >= part["vol_ratio"].quantile(0.8)]
                lo = part[part["vol_ratio"] <= part["vol_ratio"].quantile(0.2)]
                sh, sl_ = stats_bloc(hi["resultat_R"]), stats_bloc(lo["resultat_R"])
                if sh and sl_:
                    print(f"  \u2500 {lab} : fort vol exp={sh['expectancy']:+.3f}R "
                          f"(n={sh['n']}) | faible vol exp={sl_['expectancy']:+.3f}R "
                          f"(n={sl_['n']})")

            # --- 4) CONTROLE HORAIRE (la lecon du test precedent)
            print("  \u2500 Controle par heure serveur (fort vs faible vol, meme heure) :")
            seuil_hi = sw["vol_ratio"].quantile(0.8)
            seuil_lo = sw["vol_ratio"].quantile(0.2)
            num = den = 0.0
            for hh, g in sw.groupby("heure"):
                hi = g[g["vol_ratio"] >= seuil_hi]["resultat_R"]
                lo = g[g["vol_ratio"] <= seuil_lo]["resultat_R"]
                if len(hi) >= 15 and len(lo) >= 15:
                    print(f"    {int(hh):02d}h : fort={hi.mean():+.3f}R (n={len(hi)}) "
                          f"faible={lo.mean():+.3f}R (n={len(lo)}) "
                          f"\u0394={hi.mean()-lo.mean():+.3f}R")
                    num += (hi.mean() - lo.mean()) * len(hi)
                    den += len(hi)
            if den > 0:
                dd = num / den
                brut = (sw[sw["vol_ratio"] >= seuil_hi]["resultat_R"].mean()
                        - sw[sw["vol_ratio"] <= seuil_lo]["resultat_R"].mean())
                if dd > 0.05:
                    diag = "\u2705 survit au controle horaire"
                elif abs(dd) <= 0.05:
                    diag = "\u274c aucun effet (volume non informatif)"
                elif brut > 0.05:
                    diag = "\u274c artefact horaire (effet brut annule par le controle)"
                else:
                    diag = "\u274c effet inverse (fort volume degrade le setup)"
                print(f"    >> \u0394 AJUSTE PAR HEURE = {dd:+.3f}R "
                      f"(brut {brut:+.3f}R) \u2192 {diag}")
            else:
                print("    (pas assez de sweeps par heure pour stratifier)")

            # --- 5) concentration horaire (diagnostic d'artefact)
            top = sw[sw["vol_ratio"] >= seuil_hi]["heure"].value_counts(normalize=True)
            print(f"    concentration heure dominante (fort vol) : "
                  f"{top.iloc[0]*100:.0f}% a {int(top.index[0]):02d}h")

            sw.to_csv(out_dir / f"{sym}_{a.timeframe}_sweeps.csv", index=False)
            synth.append(dict(symbole=sym, n=base["n"],
                              exp_global=base["expectancy"],
                              wr_global=base["winrate"],
                              delta_q5_q1=diff, p_value=p,
                              delta_ajuste_heure=num / den if den else np.nan,
                              date=datetime.now().strftime("%Y-%m-%d %H:%M")))
    finally:
        mt5.shutdown()

    if synth:
        f = out_dir / f"synthese_sweep_{a.timeframe}.csv"
        pd.DataFrame(synth).to_csv(f, index=False)
        print("\n" + "=" * 84)
        print(f"\U0001f4be Synthese : {f}")
        print(f"\U0001f4c1 Detail par sweep : {out_dir}/<SYMBOLE>_{a.timeframe}_sweeps.csv")
        print("\n\U0001f4d6 Lecture :")
        print("  Le seul chiffre qui compte = \u0394 AJUSTE PAR HEURE.")
        print("  > +0.10R et p<0.05  -> facteur de confluence credible")
        print("  ~ 0R                 -> le delta de volume n'apporte rien au sweep")
        print("  \u0394 brut fort mais ajuste nul -> artefact de session (cf. clusters jaunes)")


if __name__ == "__main__":
    main()
