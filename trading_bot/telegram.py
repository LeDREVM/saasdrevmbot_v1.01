# telegram.py
import requests

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"



if div_signal:

    message = f"""
⚡ RSI DIVERGENCE DETECTED

Pair: {pair}

Type: {div_signal}

🎯 Context:
- Wyckoff trap possible
- Liquidity sweep incoming

⚠️ Wait M5 confirmation before entry
"""

    send(message)

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})














if div_signals:

    msg = f"""
⚡ DIVERGENCE ENGINE

Pair: {pair}

Signals: {", ".join(div_signals)}

🎯 Interpretation:
- Reversal or continuation setup
- Wyckoff trap possible

⚠️ Wait M5 break structure before entry
"""

    send(msg)    


 last_rsi = df["rsi"].iloc[-1]

filtered = []

for sig in div_signals:

    if sig == "BULLISH_DIVERGENCE" and last_rsi < 40:
        filtered.append(sig)

    elif sig == "BEARISH_DIVERGENCE" and last_rsi > 60:
        filtered.append(sig)

    elif "HIDDEN" in sig:
        filtered.append(sig)   

signal = smart_signal(df)

if signal:

    msg = f"""
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
"""

    send(msg)        