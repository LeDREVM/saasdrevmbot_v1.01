def get_bias_h4(df_h4):
    if df_h4["close"].iloc[-1] > df_h4["close"].iloc[-20]:
        return "BULLISH"
    return "BEARISH"


def get_zone_m15(df_m15):
    high = df_m15["high"].rolling(30).max().iloc[-1]
    low = df_m15["low"].rolling(30).min().iloc[-1]
    return high, low


def entry_m5(df_m5):
    last = df_m5["close"].iloc[-1]
    prev = df_m5["close"].iloc[-2]

    if last > prev:
        return "BUY_TRIGGER"
    elif last < prev:
        return "SELL_TRIGGER"