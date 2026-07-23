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

import glob
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
NEWS_WINDOW_HOURS = int(os.environ.get("NEWS_WINDOW_HOURS", "2"))
_TTL_SECONDS = 120  # cache : évite de frapper la source à chaque /api/signal
# Source du calendrier : "backend" (défaut, ForexFactory/Investing via FastAPI),
# "mt5" (JSON exporté par mql/CalendarExporter.mq5), ou "file" (fichiers JSON
# ForexFactory hebdomadaires déposés dans CALENDAR_DIR).
NEWS_SOURCE = os.environ.get("NEWS_SOURCE", "backend").lower()
MT5_CALENDAR_FILE = os.environ.get("MT5_CALENDAR_FILE", "")
# Dossier des exports FF hebdomadaires (défaut : <repo>/data/calendar).
CALENDAR_DIR = os.environ.get(
    "CALENDAR_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "calendar"),
)
_FF_IMPACT = {"high": "high", "medium": "medium", "low": "low"}  # "holiday" ignoré

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


def _normalize_ff(raw: list) -> list:
    """ForexFactory {title, country, date(ISO), impact} → format interne."""
    out = []
    for e in raw:
        imp = _FF_IMPACT.get(str(e.get("impact", "")).lower())
        if imp is None:
            continue  # Holiday / inconnu
        out.append({
            "event": e.get("title"),
            "currency": e.get("country"),   # FF met la devise dans "country"
            "impact": imp,
            "datetime": e.get("date"),      # ISO avec fuseau, ex. ...-04:00
        })
    return out


def _load_file_calendar() -> tuple[list, str | None]:
    """Charge tous les JSON FF hebdo de CALENDAR_DIR (NEWS_SOURCE=file)."""
    if not os.path.isdir(CALENDAR_DIR):
        return [], f"dossier absent ({CALENDAR_DIR})"
    files = sorted(glob.glob(os.path.join(CALENDAR_DIR, "*.json")))
    if not files:
        return [], f"aucun fichier .json dans {CALENDAR_DIR}"
    events, errors = [], []
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                events.extend(_normalize_ff(json.load(fh)))
        except (OSError, ValueError) as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")
    return events, ("; ".join(errors) or None)


def upcoming_events(force: bool = False) -> tuple[list, str | None]:
    """Événements à venir (cache TTL). Source selon NEWS_SOURCE."""
    now = time.time()
    if not force and (now - _CACHE["ts"]) < _TTL_SECONDS:
        return _CACHE["events"], _CACHE["error"]
    if NEWS_SOURCE == "mt5":
        events, err = _load_mt5_calendar()
    elif NEWS_SOURCE == "file":
        events, err = _load_file_calendar()
    else:
        events, err = _fetch_upcoming(NEWS_WINDOW_HOURS)
    _CACHE.update(ts=now, events=events, error=err)
    return events, err


def _minutes_until(ev: dict) -> float | None:
    """Minutes jusqu'à l'événement. Gère l'ISO avec fuseau ("datetime") ou
    date+time naïfs (backend/mt5)."""
    dt = None
    iso = ev.get("datetime")
    if iso:
        try:
            dt = datetime.fromisoformat(str(iso))
        except (ValueError, TypeError):
            dt = None
    if dt is None:
        try:
            dt = datetime.strptime(f"{ev.get('date')} {ev.get('time')}", "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return None
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return (dt - now).total_seconds() / 60.0


def news_context(symbol: str) -> dict:
    """
    Renvoie {news_score, event_context, source, error} pour un symbole.
    Barème : annonce high-impact pertinente à ≤30 min → 15 ; ≤60 min → 40 ;
    ≤ fenêtre → 70 ; minutes inconnues → 45 (conservateur) ; sinon 100.
    """
    currencies = SYMBOL_CURRENCIES.get(symbol, {"USD"})
    window_min = NEWS_WINDOW_HOURS * 60
    events, err = upcoming_events()
    # High-impact, devise du symbole, ET à VENIR dans la fenêtre (0..window).
    scored = []
    for e in events:
        if str(e.get("impact", "")).lower() != "high" or e.get("currency") not in currencies:
            continue
        mins = _minutes_until(e)
        if mins is None or mins < 0 or mins > window_min:
            continue
        scored.append((mins, e))
    if not scored:
        return {"news_score": 100.0, "event_context": None,
                "source": "unavailable" if err else NEWS_SOURCE, "error": err}

    scored.sort(key=lambda x: x[0])
    mins, ev = scored[0]
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
