# wyckoff_engine.py

def detect_wyckoff(df):

    high = df["high"].rolling(20).max().iloc[-2]
    low = df["low"].rolling(20).min().iloc[-2]

    last = df["close"].iloc[-1]

    # SPRING
    if last < low and df["close"].iloc[-1] > low:
        return "SPRING"

    # UTAD
    if last > high and df["close"].iloc[-1] < high:
        return "UTAD"

    return None