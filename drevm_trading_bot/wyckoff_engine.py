"""Price-based Spring/UTAD detection without future candles."""
import pandas as pd


def detect_wyckoff(df):
    """Return SPRING, UTAD or None on the latest confirmation candle.

    Input must be chronological CLOSED candles. The preceding candle must
    sweep one boundary of the previous 20-bar range and close strictly inside
    that range. The latest candle confirms by closing above the sweep high
    (Spring) or below its low (UTAD), without touching the sweep extreme again.
    A two-sided sweep is ambiguous and rejected. Signals occur only on this
    immediate confirmation, not repeatedly on subsequent bars.

    This is a price pattern, not proof of a full Wyckoff accumulation or
    distribution phase. Volume is optional and not used as fabricated evidence.
    Insufficient or malformed data returns None. Input is never modified.
    """
    columns = ["high", "low", "close"]
    if not isinstance(df, pd.DataFrame) or not set(columns).issubset(df.columns):
        return None
    if len(df) < 22:
        return None
    bars = df.iloc[-22:][columns].apply(pd.to_numeric, errors="coerce")
    bars = bars.replace([float("inf"), -float("inf")], float("nan"))
    if bars.isna().any().any():
        return None
    valid = ((bars > 0).all(axis=1)
             & (bars["low"] <= bars["close"])
             & (bars["close"] <= bars["high"]))
    if not valid.all():
        return None
    history = bars.iloc[:-2]
    sweep, confirmation = bars.iloc[-2], bars.iloc[-1]
    support, resistance = history["low"].min(), history["high"].max()
    if support >= resistance:
        return None
    swept_low = sweep["low"] < support
    swept_high = sweep["high"] > resistance
    if swept_low == swept_high:
        return None
    if not support < sweep["close"] < resistance:
        return None
    if (swept_low and confirmation["close"] > sweep["high"]
            and confirmation["low"] > sweep["low"]):
        return "SPRING"
    if (swept_high and confirmation["close"] < sweep["low"]
            and confirmation["high"] < sweep["high"]):
        return "UTAD"
    return None
