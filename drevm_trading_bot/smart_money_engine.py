import pandas as pd
from ta.momentum import RSIIndicator

# =========================
# ICHIMOKU
# =========================
def ichimoku(df):

    high = df["high"]
    low = df["low"]

    df["tenkan"] = (high.rolling(9).max() + low.rolling(9).min()) / 2
    df["kijun"] = (high.rolling(26).max() + low.rolling(26).min()) / 2

    df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    df["senkou_b"] = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    return df


# =========================
# RSI DIVERGENCE
# =========================
def divergence(df):

    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()

    price = df["close"].values
    rsi = df["rsi"].values

    if len(price) < 20:
        return None

    # simple pivot logic
    p1, p2 = price[-10], price[-1]
    r1, r2 = rsi[-10], rsi[-1]

    if p2 < p1 and r2 > r1:
        return "BULLISH"

    if p2 > p1 and r2 < r1:
        return "BEARISH"

    return None


# =========================
# SUPPLY / DEMAND
# =========================
def supply_demand(df):

    recent = df.tail(50)

    supply = recent["high"].max()
    demand = recent["low"].min()

    return supply, demand


# =========================
# BREAKOUT VALIDATION
# =========================
def breakout(df):

    high = df["high"].rolling(20).max().iloc[-1]
    low = df["low"].rolling(20).min().iloc[-1]

    price = df["close"].iloc[-1]
    prev = df["close"].iloc[-2]

    # vrai breakout = clôture + continuation
    if price > high and prev > high:
        return "BULLISH"

    if price < low and prev < low:
        return "BEARISH"

    return None


# =========================
# MAIN ENGINE
# =========================
def smart_signal(df):

    df = ichimoku(df)

    div = divergence(df)
    brk = breakout(df)
    supply, demand = supply_demand(df)

    price = df["close"].iloc[-1]

    tenkan = df["tenkan"].iloc[-1]
    kijun = df["kijun"].iloc[-1]

    signal = None
    entry = None
    sl = None
    tp = None

    # =====================
    # BUY SETUP
    # =====================
    if div == "BULLISH" and price > tenkan and price > kijun:

        entry = price
        sl = demand
        tp = price + (price - sl) * 2

        signal = "BUY"

    # =====================
    # SELL SETUP
    # =====================
    elif div == "BEARISH" and price < tenkan and price < kijun:

        entry = price
        sl = supply
        tp = price - (sl - price) * 2

        signal = "SELL"

    # =====================
    # BREAKOUT PLAY
    # =====================
    elif brk == "BULLISH":

        entry = price
        sl = kijun
        tp = price + (price - sl) * 2

        signal = "BREAKOUT BUY"

    elif brk == "BEARISH":

        entry = price
        sl = kijun
        tp = price - (sl - price) * 2

        signal = "BREAKOUT SELL"

    if signal:
        return {
            "signal": signal,
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "divergence": div,
            "breakout": brk
        }

    return None