"""
twelvedata.py — Source de prix Twelve Data (bougies OHLC) pour le validator.

Utilisé comme source alternative à MT5 dans /api/signal (PRICE_SOURCE=twelvedata).
Renvoie un DataFrame open/high/low/close(/volume) chronologique, compatible avec
les détecteurs (setup_validator). Dégradation propre : clé absente / erreur → None.

Env : TWELVEDATA_API_KEY
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
BASE_URL = "https://api.twelvedata.com"

# Symboles internes → tickers Twelve Data (ajuster selon ton plan).
SYMBOL_MAP = {
    "US30": "DJI",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD",
    "XBRUSD": "BRENT",
    "WTI": "WTI/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
}


def enabled() -> bool:
    return bool(TWELVEDATA_API_KEY)


def get_candles(symbol: str, interval: str = "5min", outputsize: int = 250):
    """Bougies OHLC (chronologique) via /time_series. None si indisponible."""
    if not TWELVEDATA_API_KEY:
        return None
    td_symbol = SYMBOL_MAP.get(symbol, symbol)
    query = urllib.parse.urlencode({
        "symbol": td_symbol, "interval": interval, "outputsize": outputsize,
        "apikey": TWELVEDATA_API_KEY, "format": "JSON", "order": "ASC",
    })
    try:
        with urllib.request.urlopen(f"{BASE_URL}/time_series?{query}", timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return None

    if data.get("status") != "ok" or not data.get("values"):
        return None
    df = pd.DataFrame(data["values"])
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            return None
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df if len(df) >= 60 else None
