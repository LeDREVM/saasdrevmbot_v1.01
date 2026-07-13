"""
alphavantage.py — Source de prix Alpha Vantage (bougies OHLC) pour le validator.

Source alternative dans /api/signal (PRICE_SOURCE=alphavantage). Gère le forex
(FX_INTRADAY) et les actions/indices (TIME_SERIES_INTRADAY). Renvoie un DataFrame
open/high/low/close(/volume) chronologique, compatible setup_validator.
Dégradation propre : clé absente, symbole non mappé, rate-limit ou erreur → None.

⚠️ Alpha Vantage n'a PAS d'intraday pour le Brent (XBRUSD) — non mappé (fallback).
Free tier : 25 req/jour, 5/min → réponse "Note"/"Information" ⇒ None.

Env : ALPHAVANTAGE_API_KEY
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")
BASE_URL = "https://www.alphavantage.co/query"

# symbole interne → ("fx", from, to) | ("equity", ticker)
SYMBOL_MAP = {
    "USDJPY": ("fx", "USD", "JPY"),
    "EURUSD": ("fx", "EUR", "USD"),
    "GBPUSD": ("fx", "GBP", "USD"),
    "XAUUSD": ("fx", "XAU", "USD"),   # selon disponibilité AV
    "US30": ("equity", "DJI"),        # indices : support limité côté AV
}


def enabled() -> bool:
    return bool(ALPHAVANTAGE_API_KEY)


def _fetch(params: dict):
    url = f"{BASE_URL}?{urllib.parse.urlencode({**params, 'apikey': ALPHAVANTAGE_API_KEY})}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return None


def _parse(time_series: dict):
    rows = [{
        "datetime": dt,
        "open": v.get("1. open"), "high": v.get("2. high"),
        "low": v.get("3. low"), "close": v.get("4. close"),
        "volume": v.get("5. volume"),
    } for dt, v in time_series.items()]
    df = pd.DataFrame(rows)
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]) \
           .sort_values("datetime").reset_index(drop=True)
    return df


def get_candles(symbol: str, interval: str = "5min", outputsize: int = 250):
    """Bougies OHLC (chronologique) via Alpha Vantage. None si indisponible."""
    if not ALPHAVANTAGE_API_KEY:
        return None
    mapping = SYMBOL_MAP.get(symbol)
    if mapping is None:
        return None

    if mapping[0] == "fx":
        _, frm, to = mapping
        data = _fetch({"function": "FX_INTRADAY", "from_symbol": frm, "to_symbol": to,
                       "interval": interval, "outputsize": "full"})
        ts_key = f"Time Series FX ({interval})"
    else:
        _, ticker = mapping
        data = _fetch({"function": "TIME_SERIES_INTRADAY", "symbol": ticker,
                       "interval": interval, "outputsize": "full"})
        ts_key = f"Time Series ({interval})"

    # Rate-limit / erreur → la réponse contient "Note"/"Information" sans série.
    if not data or ts_key not in data:
        return None
    df = _parse(data[ts_key])
    if len(df) > outputsize:
        df = df.tail(outputsize).reset_index(drop=True)
    return df if len(df) >= 60 else None
