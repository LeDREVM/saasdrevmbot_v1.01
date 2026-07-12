# strategy_engine.py
from ta.momentum import RSIIndicator

def analyze(df):
    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()

    price = df["close"].iloc[-1]
    rsi = df["rsi"].iloc[-1]

    high = df["close"].rolling(20).max().iloc[-1]
    low = df["close"].rolling(20).min().iloc[-1]

    signal = "NONE"
    setup = "NONE"

    # WYCKOFF SIMPLIFIED MODEL
    if rsi < 30 and price <= low:
        signal = "BUY"
        setup = "SPRING (accumulation)"

    elif rsi > 70 and price >= high:
        signal = "SELL"
        setup = "UTAD (distribution)"

    return {
        "price": price,
        "rsi": rsi,
        "signal": signal,
        "setup": setup
    }