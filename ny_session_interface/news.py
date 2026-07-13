"""
news.py — Contexte news pour l'AI Setup Validator.

Interroge le calendrier économique du backend (`GET /api/calendar/upcoming`,
alimenté par les scrapers ForexFactory/Investing — même source que le scraper
goldyxrogers) et en dérive, par symbole :
  • news_score (0..100)  — pénalise la proximité d'une annonce à fort impact ;
  • event_context        — la prochaine annonce imminente pertinente (ou None).

Le `news_score` nourrit le hard-filter News du validator (< 60 → bloque EXECUTE).
Dégradation propre : si le backend est injoignable, news_score = 100 (pas de
pénalité) et source = "unavailable".
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
NEWS_WINDOW_HOURS = int(os.environ.get("NEWS_WINDOW_HOURS", "2"))
_TTL_SECONDS = 120  # cache : évite de frapper la source à chaque /api/signal
# Source du calendrier : "backend" (défaut, ForexFactory/Investing via FastAPI)
# ou "mt5" (fichier JSON exporté par mql/CalendarExporter.mq5).
NEWS_SOURCE = os.environ.get("NEWS_SOURCE", "backend").lower()
MT5_CALENDAR_FILE = os.environ.get("MT5_CALENDAR_FILE", "")

# Devises pertinentes par symbole (pour filtrer les annonces).
SYMBOL_CURRENCIES = {
    "US30": {"USD"},
    "USDJPY": {"USD", "JPY"},
    "XBRUSD": {"USD"},   # Brent coté USD
    "XAUUSD": {"USD"},
    "WTI": {"USD"},
    "EURUSD": {"USD", "EUR"},
    "GBPUSD": {"USD", "GBP"},
}

_CACHE: dict = {"ts": 0.0, "events": [], "error": None}


def _fetch_upcoming(hours: int) -> tuple[list, str | None]:
    url = f"{BACKEND_URL}/api/calendar/upcoming?hours={hours}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("events", []), None
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
        return [], str(exc)


def _load_mt5_calendar() -> tuple[list, str | None]:
    """Lit le JSON exporté par mql/CalendarExporter.mq5 (NEWS_SOURCE=mt5)."""
    if not MT5_CALENDAR_FILE:
        return [], "MT5_CALENDAR_FILE non défini"
    if not os.path.exists(MT5_CALENDAR_FILE):
        return [], f"fichier absent ({MT5_CALENDAR_FILE})"
    try:
        with open(MT5_CALENDAR_FILE, encoding="utf-8") as fh:
            events = json.load(fh)
        return (events if isinstance(events, list) else []), None
    except (OSError, ValueError) as exc:
        return [], str(exc)


def upcoming_events(force: bool = False) -> tuple[list, str | None]:
    """Événements à venir (cache TTL). Source selon NEWS_SOURCE."""
    now = time.time()
    if not force and (now - _CACHE["ts"]) < _TTL_SECONDS:
        return _CACHE["events"], _CACHE["error"]
    if NEWS_SOURCE == "mt5":
        events, err = _load_mt5_calendar()
    else:
        events, err = _fetch_upcoming(NEWS_WINDOW_HOURS)
    _CACHE.update(ts=now, events=events, error=err)
    return events, err


def _minutes_until(ev: dict) -> float | None:
    try:
        dt = datetime.strptime(f"{ev.get('date')} {ev.get('time')}", "%Y-%m-%d %H:%M")
        return (dt - datetime.now()).total_seconds() / 60.0
    except (ValueError, TypeError):
        return None


def news_context(symbol: str) -> dict:
    """
    Renvoie {news_score, event_context, source, error} pour un symbole.
    Barème : annonce high-impact pertinente à ≤30 min → 15 ; ≤60 min → 40 ;
    ≤ fenêtre → 70 ; minutes inconnues → 45 (conservateur) ; sinon 100.
    """
    currencies = SYMBOL_CURRENCIES.get(symbol, {"USD"})
    events, err = upcoming_events()
    matches = [
        e for e in events
        if str(e.get("impact", "")).lower() == "high" and e.get("currency") in currencies
    ]
    if not matches:
        return {"news_score": 100.0, "event_context": None,
                "source": "unavailable" if err else NEWS_SOURCE, "error": err}

    matches.sort(key=lambda e: (_minutes_until(e) if _minutes_until(e) is not None else 1e9))
    ev = matches[0]
    mins = _minutes_until(ev)
    if mins is None:
        score = 45.0
    elif mins <= 30:
        score = 15.0
    elif mins <= 60:
        score = 40.0
    else:
        score = 70.0

    return {
        "news_score": score,
        "event_context": {
            "event": ev.get("event"), "currency": ev.get("currency"),
            "impact": ev.get("impact"),
            "minutes_until": round(mins) if mins is not None else None,
        },
        "source": NEWS_SOURCE, "error": None,
    }
