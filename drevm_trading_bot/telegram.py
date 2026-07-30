# telegram.py — Notifications Telegram du bot
import os

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")


def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})


# ---------------------------------------------------------------------------
# Messages pré-formatés (anciens blocs orphelins, remis en fonctions propres)
# ---------------------------------------------------------------------------

def notify_divergence(pair, div_signal):
    """Alerte divergence RSI simple."""
    if not div_signal:
        return
    send(f"""
⚡ RSI DIVERGENCE DETECTED

Pair: {pair}

Type: {div_signal}

🎯 Context:
- Wyckoff trap possible
- Liquidity sweep incoming

⚠️ Wait M5 confirmation before entry
""")


def notify_divergences(pair, div_signals):
    """Alerte multi-divergences (divergence engine)."""
    if not div_signals:
        return
    send(f"""
⚡ DIVERGENCE ENGINE

Pair: {pair}

Signals: {", ".join(div_signals)}

🎯 Interpretation:
- Reversal or continuation setup
- Wyckoff trap possible

⚠️ Wait M5 break structure before entry
""")


def filter_divergences(df, div_signals):
    """Filtre les divergences selon le RSI courant (contexte extrême)."""
    last_rsi = df["rsi"].iloc[-1]
    filtered = []
    for sig in div_signals:
        if sig == "BULLISH_DIVERGENCE" and last_rsi < 40:
            filtered.append(sig)
        elif sig == "BEARISH_DIVERGENCE" and last_rsi > 60:
            filtered.append(sig)
        elif "HIDDEN" in sig:
            filtered.append(sig)
    return filtered


def notify_smart_money(pair, signal):
    """Alerte signal smart money complet (entry / SL / TP / confluence)."""
    if not signal:
        return
    send(f"""
🔥 SMART MONEY SIGNAL

Pair: {pair}

Type: {signal['signal']}

📍 Entry: {signal['entry']}
🛑 SL: {signal['sl']}
🎯 TP: {signal['tp']}

🧠 Confluence:
- Divergence: {signal['divergence']}
- Breakout: {signal['breakout']}

⚠️ Confirm M5 structure before execution
""")
