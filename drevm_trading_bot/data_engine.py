"""Validated Twelve Data candles for the trading engine."""
import logging
import os

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
PAIRS = ["EUR/USD", "GBP/JPY", "XAU/USD", "USD/CAD"]
TIMEFRAMES = {"H4": "4h", "M15": "15min", "M5": "5min"}
SUPPORTED_INTERVALS = {
    "1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h",
    "8h", "1day", "1week", "1month",
}
LOGGER = logging.getLogger(__name__)


class DataEngineError(RuntimeError):
    """The provider did not return usable candles (never contains credentials)."""


def get_data(symbol, interval="5min"):
    """Return chronological numeric OHLCV candles with a fresh RangeIndex.

    Accepts H4/M15/M5 aliases and existing Twelve Data interval names.
    Intraday datetime values are UTC; daily/weekly/monthly dates retain the
    provider's exchange calendar semantics. Missing/invalid volume stays NaN,
    never fabricated as zero. Invalid OHLC rows are dropped with a warning;
    no usable rows, configuration or provider failures raise DataEngineError.
    The last bar can still be forming, as in the original API.
    """
    if not isinstance(symbol, str) or not symbol.strip() or "," in symbol:
        raise ValueError("symbol must be a single non-empty instrument")
    if not isinstance(interval, str):
        raise ValueError("interval must be a string")
    interval = interval.strip()
    interval = TIMEFRAMES.get(interval.upper(), interval.lower())
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError("Unsupported interval; use H4, M15, M5 or a Twelve Data interval")
    api_key = os.getenv("TWELVEDATA_API_KEY", API_KEY).strip()
    if not api_key or api_key == "YOUR_TWELVEDATA_KEY":
        raise DataEngineError("TWELVEDATA_API_KEY is not configured")

    try:
        response = requests.get(
            "https://api.twelvedata.com/time_series",
            params={"symbol": symbol.strip(), "interval": interval,
                    "apikey": api_key, "outputsize": 200, "timezone": "UTC"},
            timeout=(5, 15),
        )
        response.raise_for_status()
    except requests.Timeout:
        raise DataEngineError("Twelve Data request timed out") from None
    except requests.RequestException:
        # Requests exceptions can include the complete URL and API key.
        raise DataEngineError("Twelve Data HTTP/network request failed") from None
    try:
        payload = response.json()
    except ValueError:
        raise DataEngineError("Twelve Data returned invalid JSON") from None
    if not isinstance(payload, dict):
        raise DataEngineError("Twelve Data returned an invalid response object")
    if payload.get("status") not in (None, "ok") or "code" in payload:
        # Do not echo arbitrary provider messages that may contain credentials.
        raise DataEngineError("Twelve Data reported an API error")
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise DataEngineError("Twelve Data returned no candle list")
    if not all(isinstance(row, dict) for row in values):
        raise DataEngineError("Twelve Data returned malformed candle records")

    df = pd.DataFrame(values)
    required = ["datetime", "open", "high", "low", "close"]
    if not set(required).issubset(df.columns):
        raise DataEngineError("Twelve Data candles lack datetime or OHLC columns")
    df = df.reindex(columns=required + ["volume"]).copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
        df[column] = df[column].replace([float("inf"), -float("inf")], float("nan"))
    df.loc[df["volume"] < 0, "volume"] = float("nan")
    original_count = len(df)
    df = df.dropna(subset=required)
    df = df.loc[
        (df[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (df["low"] <= df[["open", "close"]].min(axis=1))
        & (df["high"] >= df[["open", "close"]].max(axis=1))
    ]
    dropped = original_count - len(df)
    if dropped:
        LOGGER.warning("Dropped %d invalid Twelve Data candles", dropped)
    # The first valid occurrence in provider order wins deterministically.
    df = df.drop_duplicates("datetime", keep="first")
    df = df.sort_values("datetime").reset_index(drop=True)
    if df.empty:
        raise DataEngineError("Twelve Data returned no valid OHLC candles")
    return df
