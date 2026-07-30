"""
Import CSV du calendrier économique (ForexFactory & exports compatibles).

Gère indifféremment les exports **daily / week / month** de ForexFactory : le
format est identique, seule la plage de dates change. Le parseur est tolérant
sur les en-têtes (insensible à la casse, alias multiples) et sur les formats de
date/heure/impact.

Un `NormalizedEvent` sait se convertir dans les DEUX cibles du projet :
  - `to_economic_event()` → `EconomicEvent` (calendrier backend / DB SQLite)
  - `to_node_entry()`     → dict compatible `data/events_log.json` (moteur de
    corrélation Node) : { id, event, currency, time, date, impactLevel,
    actual, forecast, previous, _parsedTime, _loggedAt }

Les heures du CSV sont interprétées dans le fuseau fourni (défaut ForexFactory =
US/Eastern) puis converties en UTC pour `_parsedTime`.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import List, Optional, Tuple

from .base_scraper import EconomicEvent, ImpactLevel

# Alias d'en-têtes acceptés (comparaison en minuscules, sans espaces).
_HEADER_ALIASES = {
    "event":    ["event", "title", "name"],
    "currency": ["currency", "country", "ccy", "cur"],
    "date":     ["date"],
    "time":     ["time"],
    "impact":   ["impact", "importance"],
    "forecast": ["forecast"],
    "previous": ["previous", "prev"],
    "actual":   ["actual"],
    "datetime": ["datetime", "date/time", "start", "datetime(utc)"],
}

_DATE_FORMATS = [
    "%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d",
    "%b %d, %Y", "%b %d %Y", "%B %d, %Y", "%d/%m/%Y", "%b %d",
]

_NON_TIMES = {"", "all day", "tentative", "holiday", "day 1", "day 2", "n/a", "-"}

_IMPACT_INT = {1: ImpactLevel.LOW, 2: ImpactLevel.MEDIUM, 3: ImpactLevel.HIGH}


@dataclass
class NormalizedEvent:
    date_iso: str        # YYYY-MM-DD (fuseau local du CSV)
    date_display: str    # "Mon DD" (format d'affichage FF, pour l'id/moteur Node)
    time_24: str         # HH:MM (24h, fuseau local)
    time_raw: str        # heure d'origine du CSV ("8:30am", "All Day"…)
    currency: str
    event: str
    impact_level: int    # 1 Low / 2 Medium / 3 High
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    parsed_time_iso: str  # instant UTC ISO ("2026-06-28T16:35:00.000Z")
    logged_at_ms: int     # epoch ms de l'instant de l'événement

    def to_economic_event(self, source: str = "forexfactory-csv") -> EconomicEvent:
        return EconomicEvent(
            source=source,
            date=self.date_iso,
            time=self.time_24,
            currency=self.currency,
            event=self.event,
            impact=_IMPACT_INT[self.impact_level],
            actual=self.actual,
            forecast=self.forecast,
            previous=self.previous,
        )

    def node_id(self) -> str:
        # Réplique le schéma d'id du scraper FF (espaces → underscores) pour que
        # les événements importés dédupliquent avec ceux scrapés en direct.
        raw = f"{self.date_display}_{self.time_raw}_{self.currency}_{self.event}"
        return "FF_" + re.sub(r"\s+", "_", raw.strip())

    def to_node_entry(self) -> dict:
        return {
            "id":          self.node_id(),
            "event":       self.event,
            "currency":    self.currency,
            "time":        self.time_raw,
            "date":        self.date_display,
            "impactLevel": self.impact_level,
            "actual":      self.actual,
            "forecast":    self.forecast,
            "previous":    self.previous,
            "_parsedTime": self.parsed_time_iso,
            "_loggedAt":   self.logged_at_ms,
        }


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _build_header_map(fieldnames: List[str]) -> dict:
    """Associe chaque champ logique à la colonne réelle du CSV."""
    lookup = { (fn or "").strip().lower(): fn for fn in fieldnames }
    mapping = {}
    for logical, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                mapping[logical] = lookup[alias]
                break
    return mapping


def _parse_impact(raw: str) -> int:
    r = raw.strip().lower()
    if "high" in r or r == "3":
        return 3
    if "med" in r or r == "2":
        return 2
    return 1  # Low, Holiday, Non-Economic, vide…


def _parse_time(raw: str) -> Tuple[int, int, bool]:
    """→ (heure, minute, is_timed). Non-horaire (All Day/Tentative…) → 00:00."""
    r = raw.strip().lower()
    if r in _NON_TIMES:
        return 0, 0, False
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)?", r)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        ap = m.group(3)
        if ap == "pm" and h != 12:
            h += 12
        elif ap == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return h, mn, True
    return 0, 0, False


def _parse_date(raw: str) -> Optional[datetime]:
    r = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            d = datetime.strptime(r, fmt)
            if fmt == "%b %d":  # sans année → année courante
                d = d.replace(year=datetime.now().year)
            return d
        except ValueError:
            continue
    return None


def parse_calendar_csv(text: str, tz: tzinfo) -> Tuple[List[NormalizedEvent], List[str]]:
    """Parse un CSV calendrier. Retourne (événements normalisés, lignes ignorées)."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["CSV vide ou sans en-tête"]

    hmap = _build_header_map(reader.fieldnames)
    if "event" not in hmap or "currency" not in hmap:
        return [], [f"Colonnes 'event'/'currency' introuvables (en-têtes: {reader.fieldnames})"]

    utc = timezone.utc
    events: List[NormalizedEvent] = []
    skipped: List[str] = []

    for i, row in enumerate(reader, start=2):  # ligne 1 = en-tête
        event = _norm(row.get(hmap["event"]))
        currency = _norm(row.get(hmap["currency"])).upper()
        if not event or not currency:
            skipped.append(f"L{i}: event/currency manquant")
            continue

        # ── Instant : soit un datetime ISO (avec offset), soit date + time ──
        dt_local = None
        iso_col = hmap.get("datetime")
        iso_raw = _norm(row.get(iso_col)) if iso_col else ""
        date_raw = _norm(row.get(hmap["date"])) if "date" in hmap else ""
        time_raw = _norm(row.get(hmap["time"])) if "time" in hmap else ""

        if iso_raw:
            try:
                parsed = datetime.fromisoformat(iso_raw.replace("Z", "+00:00"))
                dt_local = parsed.astimezone(tz) if parsed.tzinfo else parsed.replace(tzinfo=tz)
                if not time_raw:
                    time_raw = dt_local.strftime("%I:%M%p").lstrip("0").lower()
            except ValueError:
                dt_local = None

        if dt_local is None:
            d = _parse_date(date_raw)
            if d is None:
                skipped.append(f"L{i}: date illisible '{date_raw}' ({event})")
                continue
            h, mn, _timed = _parse_time(time_raw)
            dt_local = datetime(d.year, d.month, d.day, h, mn, tzinfo=tz)

        dt_utc = dt_local.astimezone(utc)

        events.append(NormalizedEvent(
            date_iso=dt_local.strftime("%Y-%m-%d"),
            date_display=f"{dt_local.strftime('%b')} {dt_local.day}",
            time_24=dt_local.strftime("%H:%M"),
            time_raw=time_raw or dt_local.strftime("%H:%M"),
            currency=currency,
            event=event,
            impact_level=_parse_impact(_norm(row.get(hmap.get("impact")))) if "impact" in hmap else 1,
            forecast=_norm(row.get(hmap.get("forecast"))) or None if "forecast" in hmap else None,
            previous=_norm(row.get(hmap.get("previous"))) or None if "previous" in hmap else None,
            actual=_norm(row.get(hmap.get("actual"))) or None if "actual" in hmap else None,
            parsed_time_iso=dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            logged_at_ms=int(dt_utc.timestamp() * 1000),
        ))

    return events, skipped
