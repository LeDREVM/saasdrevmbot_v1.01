#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drevm_ai_advisor.py — Pont IA DREVM
====================================
Lit les positions ouvertes MT5 (Fusion Markets) + contexte marché,
envoie le tout à Claude API avec le protocole DREVM,
renvoie l'analyse sur Telegram.

Prérequis (VPS Windows, MT5 lancé et connecté) :
    pip install MetaTrader5 requests

Config : variables d'environnement ou fichier .env à côté du script
    ANTHROPIC_API_KEY=sk-ant-...
    TELEGRAM_BOT_TOKEN=123456:ABC...
    TELEGRAM_CHAT_ID=123456789

Usage :
    python drevm_ai_advisor.py              # analyse unique de toutes les positions
    python drevm_ai_advisor.py --loop 15    # boucle toutes les 15 min
    python drevm_ai_advisor.py --symbol XAUUSD   # un seul symbole

Déploiement NSSM (service Windows) :
    nssm install DrevmAiAdvisor "C:\\Python311\\python.exe" ^
        "C:\\drevm\\drevm_ai_advisor.py --loop 15"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERREUR: pip install MetaTrader5 (Windows uniquement)")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERREUR: pip install requests")
    sys.exit(1)

# ────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────

def load_env():
    """Charge un .env simple (KEY=VALUE) à côté du script si présent."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

CLAUDE_MODEL   = "claude-sonnet-4-6"   # bon rapport qualité/coût pour l'analyse
CLAUDE_URL     = "https://api.anthropic.com/v1/messages"
MAX_TOKENS     = 1200

# Instruments DREVM
SYMBOLS_DREVM  = ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]

SYSTEM_PROMPT = """Tu es l'analyste technique DREVM de Négus Dja (méthodologie SMC/ICT, sessions New York).
Tu reçois les positions ouvertes MT5 (Fusion Markets) avec leur contexte marché.

Ton rôle : diagnostiquer chaque position et recommander une action claire.

Protocole DREVM :
- Top-down : biais EMA50/200 H1 + structure H4 avant tout
- Une position CONTRE le biais HTF est un contre-trend → sécuriser rapidement
- Zones Fibonacci sniper : 61.8/71/81/88.6/95%
- Guardrails : jamais de martingale contre-tendance, jamais déplacer un SL dans le mauvais sens
- Position en profit sur contre-trend → recommander SL breakeven immédiat + sortie partielle
- Position en perte proche du SL sans confirmation → envisager clôture manuelle

Format de réponse (STRICT, concis, français, emojis) :
Pour chaque position :
📌 [SYMBOLE] [BUY/SELL] [lots] @ [entrée] | P&L: [x]
🧭 Contexte: [biais EMA + position vs Fibo en 1 ligne]
⚖️ Diagnostic: [ALIGNÉ tendance / CONTRE-TREND] + risque en 1 ligne
🎯 ACTION: [TENIR / SL BREAKEVEN / SORTIE PARTIELLE / CLÔTURER] + niveau précis
---
Termine par une ligne de synthèse compte : exposition totale, cohérence globale.
Maximum 150 mots par position. Pas de disclaimers."""

# ────────────────────────────────────────────────────────────────────
# MT5 — collecte des données
# ────────────────────────────────────────────────────────────────────

def mt5_connect() -> bool:
    if not mt5.initialize():
        print(f"ERREUR MT5 initialize: {mt5.last_error()}")
        return False
    info = mt5.account_info()
    if info is None:
        print("ERREUR: pas de compte connecté dans MT5")
        return False
    print(f"MT5 connecté: {info.login} | Equity {info.equity:.2f} {info.currency}")
    return True


def ema(values, period):
    """EMA simple sur une liste de closes."""
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def market_context(symbol: str) -> dict:
    """Contexte marché : EMA H1, swing H1, position Fibo, dernières bougies H4."""
    ctx = {"symbol": symbol}

    # EMA 50/200 sur H1
    rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 260)
    if rates_h1 is not None and len(rates_h1) >= 210:
        closes = [r["close"] for r in rates_h1]
        e50  = ema(closes, 50)
        e200 = ema(closes, 200)
        ctx["ema50_h1"]  = round(e50, 5) if e50 else None
        ctx["ema200_h1"] = round(e200, 5) if e200 else None
        if e50 and e200:
            ctx["biais_ema"] = "BULLISH" if e50 > e200 else "BEARISH"

        # Swing high/low sur les 120 dernières H1
        window = rates_h1[-120:]
        hi = max(window, key=lambda r: r["high"])
        lo = min(window, key=lambda r: r["low"])
        swing_high, swing_low = float(hi["high"]), float(lo["low"])
        ctx["swing_high_h1"] = swing_high
        ctx["swing_low_h1"]  = swing_low

        tick = mt5.symbol_info_tick(symbol)
        if tick and swing_high > swing_low:
            px = tick.bid
            ctx["prix"] = px
            rng = swing_high - swing_low
            # % de retracement selon la jambe (high plus récent = jambe up)
            if hi["time"] > lo["time"]:
                ctx["trend_jambe"] = "HAUSSIERE"
                ctx["fib_retracement_pct"] = round((swing_high - px) / rng * 100, 1)
            else:
                ctx["trend_jambe"] = "BAISSIERE"
                ctx["fib_retracement_pct"] = round((px - swing_low) / rng * 100, 1)

    # 5 dernières bougies H4 (OHLC compact)
    rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 5)
    if rates_h4 is not None:
        ctx["h4_recent"] = [
            {"o": round(float(r["open"]), 5), "h": round(float(r["high"]), 5),
             "l": round(float(r["low"]), 5),  "c": round(float(r["close"]), 5)}
            for r in rates_h4
        ]
    return ctx


def collect_positions(symbol_filter: str = None) -> dict:
    """Positions ouvertes + contexte compte + contexte marché par symbole."""
    acct = mt5.account_info()
    payload = {
        "horodatage": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "compte": {
            "equity":  round(acct.equity, 2),
            "balance": round(acct.balance, 2),
            "devise":  acct.currency,
            "marge_libre": round(acct.margin_free, 2),
        },
        "positions": [],
        "contextes_marche": {},
    }

    positions = mt5.positions_get()
    if positions is None:
        positions = []

    symbols_seen = set()
    for p in positions:
        if symbol_filter and p.symbol != symbol_filter:
            continue
        payload["positions"].append({
            "symbole":  p.symbol,
            "type":     "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
            "lots":     p.volume,
            "entree":   p.price_open,
            "prix":     p.price_current,
            "sl":       p.sl,
            "tp":       p.tp,
            "pnl":      round(p.profit, 2),
            "magic":    p.magic,
            "ouverture": datetime.fromtimestamp(p.time).strftime("%Y-%m-%d %H:%M"),
        })
        symbols_seen.add(p.symbol)

    for s in symbols_seen:
        payload["contextes_marche"][s] = market_context(s)

    return payload

# ────────────────────────────────────────────────────────────────────
# Claude API
# ────────────────────────────────────────────────────────────────────

def ask_claude(payload: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return "ERREUR: ANTHROPIC_API_KEY manquant (.env)"

    user_msg = (
        "Voici mes positions ouvertes et leur contexte marché. "
        "Analyse chaque position selon le protocole DREVM et donne l'action.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
    )

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }

    try:
        r = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            return f"ERREUR Claude API HTTP {r.status_code}: {r.text[:300]}"
        data = r.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts).strip() or "Réponse vide."
    except requests.RequestException as e:
        return f"ERREUR réseau Claude API: {e}"

# ────────────────────────────────────────────────────────────────────
# Telegram
# ────────────────────────────────────────────────────────────────────

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("(Telegram non configuré — affichage console uniquement)")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram limite à 4096 caractères par message
    for chunk_start in range(0, len(text), 3900):
        chunk = text[chunk_start:chunk_start + 3900]
        try:
            r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": chunk}, timeout=15)
            if r.status_code != 200:
                print(f"Telegram HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            print(f"ERREUR Telegram: {e}")

# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

def run_once(symbol_filter: str = None):
    payload = collect_positions(symbol_filter)

    if not payload["positions"]:
        msg = f"🤖 DREVM AI Advisor — {payload['horodatage']}\nAucune position ouverte."
        print(msg)
        send_telegram(msg)
        return

    n = len(payload["positions"])
    print(f"Analyse de {n} position(s) via Claude...")
    analysis = ask_claude(payload)

    header = (f"🤖 DREVM AI Advisor — {payload['horodatage']}\n"
              f"💰 Equity {payload['compte']['equity']} {payload['compte']['devise']} "
              f"| {n} position(s)\n"
              f"{'─' * 25}\n")
    full = header + analysis
    print(full)
    send_telegram(full)


def main():
    ap = argparse.ArgumentParser(description="DREVM AI Advisor — positions MT5 -> Claude -> Telegram")
    ap.add_argument("--loop", type=int, metavar="MIN",
                    help="Boucle : analyse toutes les X minutes")
    ap.add_argument("--symbol", type=str, help="Limiter à un symbole (ex: XAUUSD)")
    args = ap.parse_args()

    if not mt5_connect():
        sys.exit(1)

    try:
        if args.loop:
            print(f"Mode boucle: analyse toutes les {args.loop} min. Ctrl+C pour arrêter.")
            while True:
                run_once(args.symbol)
                time.sleep(args.loop * 60)
        else:
            run_once(args.symbol)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
