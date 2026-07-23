import pandas as pd
from ta.momentum import RSIIndicator

def detect_divergence(df):

    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()

    # On prend les 20 dernières bougies
    recent = df.tail(20)

    price = recent["close"].values
    rsi = recent["rsi"].values

    signal = None

    # DETECTION HIGHS / LOWS
    max_price_1 = max(price[:-5])
    max_price_2 = max(price[-5:])

    min_price_1 = min(price[:-5])
    min_price_2 = min(price[-5:])

    max_rsi_1 = max(rsi[:-5])
    max_rsi_2 = max(rsi[-5:])

    min_rsi_1 = min(rsi[:-5])
    min_rsi_2 = min(rsi[-5:])

    # 🔴 BEARISH DIVERGENCE
    if max_price_2 > max_price_1 and max_rsi_2 < max_rsi_1:
        signal = "BEARISH_DIVERGENCE"

    # 🟢 BULLISH DIVERGENCE
    elif min_price_2 < min_price_1 and min_rsi_2 > min_rsi_1:
        signal = "BULLISH_DIVERGENCE"


# DETECT PIVOTS
def find_pivots(series, window=3):
    pivots_high = []
    pivots_low = []

    for i in range(window, len(series) - window):
        if series[i] == max(series[i-window:i+window]):
            pivots_high.append(i)
        if series[i] == min(series[i-window:i+window]):
            pivots_low.append(i)

    return pivots_high, pivots_low


def detect_divergences(df):

    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()

    price = df["close"].values
    rsi = df["rsi"].values

    highs, lows = find_pivots(price)

    signals = []

    # 🔴 BEARISH DIVERGENCE (REVERSAL)
    if len(highs) >= 2:
        h1, h2 = highs[-2], highs[-1]

        if price[h2] > price[h1] and rsi[h2] < rsi[h1]:
            signals.append("BEARISH_DIVERGENCE")

    # 🟢 BULLISH DIVERGENCE (REVERSAL)
    if len(lows) >= 2:
        l1, l2 = lows[-2], lows[-1]

        if price[l2] < price[l1] and rsi[l2] > rsi[l1]:
            signals.append("BULLISH_DIVERGENCE")

    # 🔵 HIDDEN BULLISH (CONTINUATION)
    if len(lows) >= 2:
        l1, l2 = lows[-2], lows[-1]

        if price[l2] > price[l1] and rsi[l2] < rsi[l1]:
            signals.append("HIDDEN_BULLISH")

    # 🟣 HIDDEN BEARISH (CONTINUATION)
    if len(highs) >= 2:
        h1, h2 = highs[-2], highs[-1]

        if price[h2] < price[h1] and rsi[h2] > rsi[h1]:
            signals.append("HIDDEN_BEARISH")

    return signals