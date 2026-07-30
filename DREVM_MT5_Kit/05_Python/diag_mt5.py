#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_mt5.py — DREVM : que renvoie reellement le terminal Fusion Markets ?"""
import MetaTrader5 as mt5

if not mt5.initialize():
    raise SystemExit(f"Echec init MT5 : {mt5.last_error()}")

info = mt5.terminal_info()
print(f"Terminal : {info.name} | connecte={info.connected} | "
      f"trade_allowed={info.trade_allowed}")
print(f"Compte   : {mt5.account_info().login} / {mt5.account_info().server}\n")

tfs = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}

print("Symboles visibles contenant US30 / XAU :")
for s in mt5.symbols_get():
    if "US30" in s.name.upper() or "XAU" in s.name.upper():
        print(f"  {s.name:<16} visible={s.visible}")

print("\nHistorique reellement disponible :")
for sym in ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]:
    if not mt5.symbol_select(sym, True):
        print(f"  {sym:<10} absent du Market Watch")
        continue
    mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 100)  # amorce
    ligne = f"  {sym:<10}"
    for nom, tf in tfs.items():
        best = 0
        for p in (200000, 100000, 60000, 30000, 15000, 5000, 1000):
            r = mt5.copy_rates_from_pos(sym, tf, 0, p)
            if r is not None and len(r) > best:
                best = len(r)
                break
        ligne += f" {nom}={best:>7}"
    r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, best or 1000)
    if r is not None and len(r):
        import pandas as pd
        d = pd.to_datetime(r["time"], unit="s")
        ligne += f"  depuis {d.min().date()}"
    print(ligne)

mt5.shutdown()
