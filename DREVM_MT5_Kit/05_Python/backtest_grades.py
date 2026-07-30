#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest_grades.py — DREVM / GoldXrodgers
==========================================
Rejoue FIDELEMENT le moteur de confluence de GoldXrodgers_5ers_5K_EA.mq5
sur l'historique Fusion Markets et mesure expectancy / winrate / profit factor
PAR GRADE (A+ / A / B / C).

Question : les grades se differencient-ils vraiment ?
Benchmark etabli precedemment : sweep naif = 0.00R d'expectancy.

REPLICATION DU SCORING (gMaxScore = 7)
  1. Wyckoff MARKUP/MARKDOWN      (+1 des qu'une direction existe)
  2. Fibo dans [InpFibZoneMin, InpFibZoneMax]
  3. Position vs Kijun
  4. RSI directionnel + pente (rsi[1] vs rsi[3])
  5. FVG dans le sens
  6. Order Block dans le sens
  7. R/R >= InpMinRR
  Grade : ratio = score/7 -> >=0.85 A+ | >=0.70 A | >=0.55 B | sinon C

MECANIQUE D'EXECUTION (fidele a FireSignal / MODE_PENDING)
  L'EA place un ORDRE LIMITE a gEntry = swing -/+ range*InpFibEntry.
  Le backtest simule donc : ordre pose a la cloture de la barre de signal,
  rempli seulement si le prix revient le toucher avant expiration,
  sinon annule (ces signaux sont comptes separement comme "non remplis").

GESTION DE POSITION (fidele a ManagePositions)
  Mode --gestion complete : partiel 50% a 1R, SL au breakeven apres le partiel,
  puis trailing ATR x1.5 sur le runner. Mode --gestion simple : SL/TP secs.

CONTROLES ANTI-ARTEFACT (lecons des tests precedents)
  - Evaluation sur bougie CLOTUREE uniquement (aucun lookahead).
  - Stratification horaire systematique.
  - Split out-of-sample chronologique 70/30.
  - Test de permutation sur l'ecart A+/A vs C.

Prerequis : Windows + terminal MT5 Fusion Markets ouvert.
  pip install MetaTrader5 pandas numpy

Exemples :
  python backtest_grades.py
  python backtest_grades.py --symbols US30 XAUUSD --gestion complete
  python backtest_grades.py --no-session --expiry 48
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLES_DREVM = ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]
MIN_BOUGIES = 3000
MAX_SCORE = 7


# ---------------------------------------------------------------- arguments
def parse_args():
    p = argparse.ArgumentParser(description="Backtest du scoring DREVM par grade")
    p.add_argument("--symbols", nargs="+", default=SYMBOLES_DREVM)
    p.add_argument("--timeframe", default="M5", choices=["M5", "M15", "M30", "H1"])
    p.add_argument("--bars", type=int, default=60000)
    # --- parametres miroir des inputs de l'EA ---
    p.add_argument("--ema-fast", type=int, default=50)
    p.add_argument("--ema-slow", type=int, default=100)
    p.add_argument("--kijun", type=int, default=26)
    p.add_argument("--tenkan", type=int, default=9)
    p.add_argument("--senkou", type=int, default=52)
    p.add_argument("--rsi-period", type=int, default=14)
    p.add_argument("--rsi-bull-min", type=float, default=45.0)
    p.add_argument("--rsi-bear-max", type=float, default=55.0)
    p.add_argument("--swing-lookback", type=int, default=60)
    p.add_argument("--imb-lookback", type=int, default=20)
    p.add_argument("--min-fvg-atr", type=float, default=0.30)
    p.add_argument("--fib-zone-min", type=float, default=0.50)
    p.add_argument("--fib-zone-max", type=float, default=0.886)
    p.add_argument("--fib-entry", type=float, default=0.618)
    p.add_argument("--fib-stop-buf-atr", type=float, default=0.5)
    p.add_argument("--min-rr", type=float, default=2.0)
    p.add_argument("--tp-rr", type=float, default=2.5)
    p.add_argument("--range-max-atr", type=float, default=2.5)
    # --- sessions ---
    p.add_argument("--no-session", action="store_true",
                   help="Desactive le filtre de session (InpUseSession=false)")
    p.add_argument("--london", default="8-12")
    p.add_argument("--ny", default="13-21")
    # --- simulation ---
    p.add_argument("--expiry", type=int, default=24,
                   help="Barres avant annulation de l'ordre limite (defaut 24)")
    p.add_argument("--horizon", type=int, default=96,
                   help="Barres max pour resoudre le trade une fois rempli")
    p.add_argument("--gestion", default="complete", choices=["simple", "complete"],
                   help="simple = SL/TP secs | complete = partiel 1R + BE + trailing")
    p.add_argument("--partial-at-r", type=float, default=1.0)
    p.add_argument("--partial-pct", type=float, default=50.0)
    p.add_argument("--trail-atr-mult", type=float, default=1.5)
    p.add_argument("--cooldown", type=int, default=12,
                   help="Barres min entre deux signaux (evite le sur-comptage)")
    p.add_argument("--version", default="v3", choices=["v2", "v3"],
                   help="v2 = scoring d'origine (7 pts) | v3 = corrige (5 pts)")
    p.add_argument("--fib-mode", default="engage", choices=["zone", "engage"],
                   help="zone = retracement dans [min,max] | engage = repli demarre")
    p.add_argument("--fib-progress-min", type=float, default=0.236)
    p.add_argument("--zone-tol-atr", type=float, default=0.15)
    p.add_argument("--min-limit-gap-atr", type=float, default=0.10)
    p.add_argument("--out", default="resultats_grades")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# ---------------------------------------------------------------- MT5
def init_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("\u274c Package MetaTrader5 introuvable (Windows) : pip install MetaTrader5")
    if not mt5.initialize():
        sys.exit(f"\u274c Echec init MT5 : {mt5.last_error()}")
    return mt5


def charger(mt5, symbole, tf_name, n_bars):
    tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
              "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1}
    tf = tf_map[tf_name]
    if not mt5.symbol_select(symbole, True):
        print(f"  \u26a0\ufe0f  {symbole} absent du Market Watch — ignore.")
        return None
    mt5.copy_rates_from_pos(symbole, tf, 0, 100)  # amorce l'historique
    for p in sorted({n_bars, 60000, 30000, 15000, 5000, MIN_BOUGIES}, reverse=True):
        if p > n_bars:
            continue
        r = mt5.copy_rates_from_pos(symbole, tf, 0, p)
        if r is not None and len(r) >= MIN_BOUGIES:
            if p < n_bars:
                print(f"  \u2139\ufe0f  {symbole} : replie sur {len(r)} bougies.")
            df = pd.DataFrame(r)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df.iloc[:-1].reset_index(drop=True)
    print(f"  \u26a0\ufe0f  {symbole} : historique insuffisant — ignore.")
    return None


# ---------------------------------------------------------------- indicateurs
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi_wilder(close, n):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr_wilder(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def ichimoku(df, tenkan, kijun, senkou):
    hh = lambda n: df["high"].rolling(n).max()
    ll = lambda n: df["low"].rolling(n).min()
    tk = (hh(tenkan) + ll(tenkan)) / 2
    kj = (hh(kijun) + ll(kijun)) / 2
    # SpanA/SpanB tels que LUS par CopyBuffer a la barre i : projetes en avant
    # de `kijun` barres, donc la valeur visible en i vient de i - kijun.
    span_a = ((tk + kj) / 2).shift(kijun)
    span_b = ((hh(senkou) + ll(senkou)) / 2).shift(kijun)
    return kj, span_a, span_b


# ---------------------------------------------------------------- FVG / OB
def detecter_fvg_ob(h, l, o, c, atr, i, lookback, min_fvg_atr, sens):
    """Reproduit BullishFVG/BearishFVG et BullishOB/BearishOB.

    Attention a l'indexation : dans l'EA, iHigh(_Symbol,_Period,k) designe la
    k-ieme barre EN ARRIERE depuis la barre courante. Ici la barre de signal
    est `i` (deja cloturee), donc l'indice EA k correspond a i - k + 1.
    """
    fvg = ob = False
    base = i + 1  # barre 0 de l'EA = barre non cloturee suivante

    for k in range(1, lookback + 1):
        a, b = base - k, base - k - 2
        if b < 0:
            break
        if sens > 0:
            if l[a] > h[b] and (l[a] - h[b]) >= atr * min_fvg_atr:
                fvg = True
                break
        else:
            if l[b] > h[a] and (l[b] - h[a]) >= atr * min_fvg_atr:
                fvg = True
                break

    for k in range(2, lookback + 1):
        a, prev = base - k, base - k + 1
        if a < 0 or prev >= len(c):
            break
        if sens > 0:
            if c[a] < o[a] and c[prev] > h[a]:
                ob = True
                break
        else:
            if c[a] > o[a] and c[prev] < l[a]:
                ob = True
                break
    return fvg, ob


def detecter_fvg_ob_zone(h, l, o, c, atr, i, lookback, min_fvg_atr, sens,
                         entry, zone_tol_atr):
    """v3 : le point n'est accorde que si `entry` tombe DANS la zone detectee."""
    tol = atr * zone_tol_atr
    dedans = lambda lo, hi: (lo - tol) <= entry <= (hi + tol)
    fvg = ob = False
    base = i + 1
    for k in range(1, lookback + 1):
        x, y = base - k, base - k - 2
        if y < 0:
            break
        if sens > 0:
            if l[x] > h[y] and (l[x] - h[y]) >= atr * min_fvg_atr:
                fvg = dedans(h[y], l[x])
                break
        else:
            if l[y] > h[x] and (l[y] - h[x]) >= atr * min_fvg_atr:
                fvg = dedans(h[x], l[y])
                break
    for k in range(2, lookback + 1):
        x, prev = base - k, base - k + 1
        if x < 0 or prev >= len(c):
            break
        if sens > 0:
            if c[x] < o[x] and c[prev] > h[x]:
                ob = dedans(l[x], h[x])
                break
        else:
            if c[x] > o[x] and c[prev] < l[x]:
                ob = dedans(l[x], h[x])
                break
    return fvg, ob


# ---------------------------------------------------------------- scoring
def analyser(df, a):
    """Rejoue Analyze() sur chaque barre cloturee. Retourne un DataFrame de signaux."""
    h, l, o, c = (df[x].values for x in ("high", "low", "open", "close"))
    n = len(df)

    emaF = ema(df["close"], a.ema_fast).values
    emaS = ema(df["close"], a.ema_slow).values
    kj, spA, spB = ichimoku(df, a.tenkan, a.kijun, a.senkou)
    kj, spA, spB = kj.values, spA.values, spB.values
    rsi = rsi_wilder(df["close"], a.rsi_period).values
    atr = atr_wilder(df).values

    sw_h = df["high"].rolling(a.swing_lookback).max().values
    sw_l = df["low"].rolling(a.swing_lookback).min().values

    heures = df["time"].dt.hour.values
    lo_s, hi_s = (int(x) for x in a.london.split("-"))
    lo_n, hi_n = (int(x) for x in a.ny.split("-"))

    depart = max(a.ema_slow, a.senkou + a.kijun, a.swing_lookback, a.imb_lookback + 3) + 5
    lignes = []
    dernier = -10 ** 9

    for i in range(depart, n - 1):
        if i - dernier < a.cooldown:
            continue
        if not a.no_session:
            hh = heures[i]
            if not ((lo_s <= hh < hi_s) or (lo_n <= hh < hi_n)):
                continue
        A = atr[i]
        if not np.isfinite(A) or A <= 0:
            continue
        if not (np.isfinite(spA[i]) and np.isfinite(spB[i]) and np.isfinite(kj[i])):
            continue

        swH, swL = sw_h[i], sw_l[i]
        rng = swH - swL
        if not np.isfinite(rng) or rng <= 0:
            continue

        c1 = c[i]
        kumo_top, kumo_bot = max(spA[i], spB[i]), min(spA[i], spB[i])
        trend_up = (emaF[i] > emaS[i]) and (c1 > kumo_top)
        trend_dn = (emaF[i] < emaS[i]) and (c1 < kumo_bot)
        tight = rng < A * a.range_max_atr

        if trend_up:
            phase = "MARKUP"
        elif trend_dn:
            phase = "MARKDOWN"
        elif tight and c1 <= swL + rng * 0.4:
            phase = "ACCUMULATION"
        elif tight and c1 >= swH - rng * 0.4:
            phase = "DISTRIBUTION"
        else:
            phase = "RANGE"

        if not (trend_up or trend_dn):
            continue

        sens = 1 if trend_up else -1

        if a.version == "v3":
            # --- jambe d'impulsion (et non le range brut de N barres)
            w_h = h[i - a.swing_lookback + 1:i + 1]
            w_l = l[i - a.swing_lookback + 1:i + 1]
            if sens > 0:
                k = int(np.argmax(w_h))          # position du sommet
                leg_h = w_h[k]
                leg_l = w_l[:k + 1].min()        # plus bas AVANT le sommet
            else:
                k = int(np.argmin(w_l))
                leg_l = w_l[k]
                leg_h = w_h[:k + 1].max()
            leg_rng = leg_h - leg_l
            if leg_rng <= 0:
                continue
            swH, swL, rng = leg_h, leg_l, leg_rng
            score = 0                            # Wyckoff n'est plus un point
        else:
            score = 1                            # (1) Wyckoff (v2)

        fib_pos = (swH - c1) / rng if sens > 0 else (c1 - swL) / rng
        if a.version == "v3" and a.fib_mode == "engage":
            f_fib = (a.fib_progress_min <= fib_pos < a.fib_entry)
        else:
            f_fib = (min(a.fib_zone_min, a.fib_zone_max) <= fib_pos
                     <= max(a.fib_zone_min, a.fib_zone_max))
        score += f_fib                               # (2) Fibonacci
        f_kij = (c1 > kj[i]) if sens > 0 else (c1 < kj[i])
        score += f_kij                               # (3) Kijun
        f_rsi = ((rsi[i] >= a.rsi_bull_min and rsi[i] > rsi[i - 2]) if sens > 0
                 else (rsi[i] <= a.rsi_bear_max and rsi[i] < rsi[i - 2]))
        score += f_rsi                               # (4) RSI
        if sens > 0:
            entry = swH - rng * a.fib_entry
            sl = swL - A * a.fib_stop_buf_atr
            risque = entry - sl
            tp = entry + risque * a.tp_rr
            f_rr = risque > 0 and (tp - entry) / risque >= a.min_rr
        else:
            entry = swL + rng * a.fib_entry
            sl = swH + A * a.fib_stop_buf_atr
            risque = sl - entry
            tp = entry - risque * a.tp_rr
            f_rr = risque > 0 and (entry - tp) / risque >= a.min_rr
        if risque <= 0:
            continue

        if a.version == "v3":
            # R/R = filtre de rejet, plus un point
            if not f_rr:
                continue
            # coherence de l'ordre limite (BuyLimit sous le marche)
            if sens > 0 and entry >= c1 - A * a.min_limit_gap_atr:
                continue
            if sens < 0 and entry <= c1 + A * a.min_limit_gap_atr:
                continue
            # FVG/OB : le point exige que l'ENTREE soit dans la zone
            f_fvg, f_ob = detecter_fvg_ob_zone(h, l, o, c, A, i, a.imb_lookback,
                                               a.min_fvg_atr, sens, entry,
                                               a.zone_tol_atr)
            score += f_fvg + f_ob
            max_score = 5
        else:
            f_fvg, f_ob = detecter_fvg_ob(h, l, o, c, A, i, a.imb_lookback,
                                          a.min_fvg_atr, sens)
            score += f_fvg + f_ob + f_rr
            max_score = 7

        ratio = score / max_score
        grade = "A+" if ratio >= 0.85 else "A" if ratio >= 0.70 else "B" if ratio >= 0.55 else "C"

        lignes.append(dict(i=i, time=df["time"].values[i], heure=heures[i],
                           sens=sens, phase=phase, score=score, grade=grade,
                           entry=entry, sl=sl, tp=tp, risque=risque, atr=A,
                           f_fib=int(f_fib), f_kijun=int(f_kij), f_rsi=int(f_rsi),
                           f_fvg=int(f_fvg), f_ob=int(f_ob), f_rr=int(f_rr)))
        dernier = i

    return pd.DataFrame(lignes)


# ---------------------------------------------------------------- simulation
def simuler(df, sig, a):
    """Ordre limite -> remplissage -> gestion. Retourne le resultat en R."""
    h, l, c = (df[x].values for x in ("high", "low", "close"))
    atr = atr_wilder(df).values
    n = len(df)
    res, rempli, bar_fill = [], [], []

    for s in sig.itertuples():
        i, sens, entry, sl, tp, R = s.i, s.sens, s.entry, s.sl, s.tp, s.risque

        # --- 1. attente de remplissage de l'ordre limite
        fill = -1
        for j in range(i + 1, min(i + 1 + a.expiry, n)):
            touche = (l[j] <= entry) if sens > 0 else (h[j] >= entry)
            if touche:
                fill = j
                break
        if fill < 0:
            res.append(np.nan)
            rempli.append(False)
            bar_fill.append(-1)
            continue
        rempli.append(True)
        bar_fill.append(fill)

        # --- 2. gestion du trade
        pnl = 0.0
        part_faite = False
        reste = 1.0
        sl_cur = sl
        cible_part = entry + sens * a.partial_at_r * R

        for j in range(fill, min(fill + a.horizon, n)):
            hit_sl = (l[j] <= sl_cur) if sens > 0 else (h[j] >= sl_cur)
            hit_tp = (h[j] >= tp) if sens > 0 else (l[j] <= tp)

            if hit_sl:  # hypothese conservatrice : SL prioritaire
                pnl += reste * (sl_cur - entry) * sens / R
                reste = 0.0
                break
            if hit_tp:
                pnl += reste * a.tp_rr
                reste = 0.0
                break

            if a.gestion == "complete":
                atteint = (h[j] >= cible_part) if sens > 0 else (l[j] <= cible_part)
                if not part_faite and atteint:
                    part = a.partial_pct / 100.0
                    pnl += part * a.partial_at_r
                    reste -= part
                    part_faite = True
                    sl_cur = entry  # breakeven
                if part_faite and np.isfinite(atr[j]):
                    d = a.trail_atr_mult * atr[j]
                    nouveau = (c[j] - d) if sens > 0 else (c[j] + d)
                    sl_cur = max(sl_cur, nouveau) if sens > 0 else min(sl_cur, nouveau)

        if reste > 0:  # non resolu : sortie au marche
            fin = c[min(fill + a.horizon, n - 1)]
            pnl += reste * (fin - entry) * sens / R
        res.append(pnl)

    sig = sig.copy()
    sig["rempli"] = rempli
    sig["bar_fill"] = bar_fill
    sig["resultat_R"] = res
    return sig


# ---------------------------------------------------------------- stats
def bloc(r):
    r = np.asarray(pd.Series(r).dropna(), float)
    if len(r) == 0:
        return None
    g, p = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), wr=float((r > 0).mean()), exp=float(r.mean()),
                pf=float(g / p) if p > 0 else np.inf)


def permut(a_, b_, n_perm, rng):
    a_, b_ = np.asarray(a_, float), np.asarray(b_, float)
    if len(a_) < 5 or len(b_) < 5:
        return np.nan, np.nan
    obs = a_.mean() - b_.mean()
    pool = np.concatenate([a_, b_])
    na = len(a_)
    cnt = sum(1 for _ in range(n_perm)
              if (lambda p: p[:na].mean() - p[na:].mean())(rng.permutation(pool)) >= obs)
    return (cnt + 1) / (n_perm + 1), obs


ORDRE = ["A+", "A", "B", "C"]


# ---------------------------------------------------------------- main
def main():
    a = parse_args()
    rng = np.random.default_rng(a.seed)
    mt5 = init_mt5()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n\U0001f3af BACKTEST SCORING DREVM PAR GRADE — {a.timeframe} | "
          f"gestion={a.gestion} | expiry={a.expiry}b | horizon={a.horizon}b")
    print(f"   Benchmark de reference : sweep naif = 0.00R")
    print("=" * 86)

    synth = []
    try:
        for sym in a.symbols:
            df = charger(mt5, sym, a.timeframe, a.bars)
            if df is None:
                continue
            sig = analyser(df, a)
            if sig.empty:
                print(f"{sym} : aucun signal genere.")
                continue
            sig = simuler(df, sig, a)
            pris = sig[sig["rempli"]]

            print(f"\n\u2500\u2500\u2500 {sym} \u2500\u2500\u2500 "
                  f"{df.time.min().date()} \u2192 {df.time.max().date()}")
            print(f"  signaux={len(sig)}  remplis={len(pris)} "
                  f"({len(pris)/len(sig)*100:.0f}%)  non remplis={len(sig)-len(pris)}")

            g = bloc(pris["resultat_R"])
            if g is None:
                continue
            print(f"  GLOBAL : n={g['n']} WR={g['wr']*100:.1f}% "
                  f"exp={g['exp']:+.3f}R PF={g['pf']:.2f}")

            # --- par grade
            print("  \u2500 Par grade :")
            stats_grade = {}
            for gr in ORDRE:
                b = pris[pris["grade"] == gr]
                s = bloc(b["resultat_R"])
                if s is None:
                    print(f"    {gr:<2} : aucun trade")
                    continue
                stats_grade[gr] = s
                print(f"    {gr:<2} : n={s['n']:4d} WR={s['wr']*100:5.1f}% "
                      f"exp={s['exp']:+.3f}R PF={s['pf']:.2f}")

            # --- monotonie
            dispo = [gr for gr in ORDRE if gr in stats_grade]
            exps = [stats_grade[gr]["exp"] for gr in dispo]
            mono = all(exps[k] >= exps[k + 1] for k in range(len(exps) - 1))
            print(f"    monotonie A+ \u2265 A \u2265 B \u2265 C : "
                  f"{'\u2705 OUI' if mono else '\u274c NON'}")

            # --- haut (A+/A) vs bas (C)
            haut = pris[pris["grade"].isin(["A+", "A"])]["resultat_R"].dropna().values
            bas = pris[pris["grade"] == "C"]["resultat_R"].dropna().values
            p, d = permut(haut, bas, 3000, rng)
            if np.isfinite(p):
                print(f"  \u2500 (A+/A) vs C : \u0394exp={d:+.3f}R p={p:.4f} "
                      f"{'\u2705' if p < 0.05 else '\u274c'}")

            # --- out-of-sample chronologique
            cut = int(len(pris) * 0.7)
            for lab, part in [("in-sample ", pris.iloc[:cut]), ("out-sample", pris.iloc[cut:])]:
                sh = bloc(part[part["grade"].isin(["A+", "A"])]["resultat_R"])
                sc = bloc(part[part["grade"] == "C"]["resultat_R"])
                if sh and sc:
                    print(f"  \u2500 {lab} : A+/A exp={sh['exp']:+.3f}R (n={sh['n']}) | "
                          f"C exp={sc['exp']:+.3f}R (n={sc['n']})")

            # --- controle horaire
            print("  \u2500 Controle par heure (A+/A vs C, meme heure) :")
            num = den = 0.0
            for hh, grp in pris.groupby("heure"):
                x = grp[grp["grade"].isin(["A+", "A"])]["resultat_R"].dropna()
                y = grp[grp["grade"] == "C"]["resultat_R"].dropna()
                if len(x) >= 10 and len(y) >= 10:
                    print(f"    {int(hh):02d}h : A+/A={x.mean():+.3f}R (n={len(x)}) "
                          f"C={y.mean():+.3f}R (n={len(y)}) \u0394={x.mean()-y.mean():+.3f}R")
                    num += (x.mean() - y.mean()) * len(x)
                    den += len(x)
            d_aj = num / den if den else np.nan
            if den:
                print(f"    >> \u0394 AJUSTE PAR HEURE = {d_aj:+.3f}R "
                      f"{'\u2705 le scoring discrimine' if d_aj > 0.05 else '\u274c pas de discrimination'}")

            # --- valeur marginale de chaque facteur
            print("  \u2500 Valeur marginale de chaque facteur (present vs absent) :")
            for f in ["f_fib", "f_kijun", "f_rsi", "f_fvg", "f_ob", "f_rr"]:
                on = pris[pris[f] == 1]["resultat_R"].dropna()
                off = pris[pris[f] == 0]["resultat_R"].dropna()
                if len(on) >= 30 and len(off) >= 30:
                    print(f"    {f:<8}: present {on.mean():+.3f}R (n={len(on):4d}) | "
                          f"absent {off.mean():+.3f}R (n={len(off):4d}) | "
                          f"\u0394={on.mean()-off.mean():+.3f}R")
                else:
                    taux = pris[f].mean() * 100
                    print(f"    {f:<8}: non discriminant (present dans {taux:.0f}% des trades)")

            sig.to_csv(out / f"{sym}_{a.version}_{a.timeframe}_signaux.csv", index=False)
            ligne = dict(symbole=sym, signaux=len(sig), remplis=len(pris),
                         exp_global=g["exp"], wr_global=g["wr"], pf_global=g["pf"],
                         monotone=mono, delta_haut_bas=d, p_value=p,
                         delta_ajuste_heure=d_aj,
                         date=datetime.now().strftime("%Y-%m-%d %H:%M"))
            for gr in ORDRE:
                if gr in stats_grade:
                    ligne[f"exp_{gr}"] = stats_grade[gr]["exp"]
                    ligne[f"n_{gr}"] = stats_grade[gr]["n"]
            synth.append(ligne)
    finally:
        mt5.shutdown()

    if synth:
        f = out / f"synthese_grades_{a.version}_{a.timeframe}_{a.gestion}.csv"
        pd.DataFrame(synth).to_csv(f, index=False)
        print("\n" + "=" * 86)
        print(f"\U0001f4be Synthese : {f}")
        print(f"\U0001f4c1 Detail : {out}/<SYMBOLE>_{a.timeframe}_signaux.csv")
        print("\n\U0001f4d6 Lecture :")
        print("  Le scoring est VALIDE si : monotonie OUI + \u0394 ajuste heure > +0.05R")
        print("  + l'ecart tient en out-of-sample. Sinon les grades sont cosmetiques.")
        print("  Les \u0394 par facteur disent lesquels meritent leur point.")


if __name__ == "__main__":
    main()
