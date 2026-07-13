"""
economic_calendar.py
---------------------
Module autonome pour charger, parser et exploiter les exports CSV du
calendrier économique ForexFactory (format "ff_calendar_thisweek.csv").

Colonnes attendues du CSV :
    Title, Country, Date, Time, Impact, Forecast, Previous, URL

Conçu pour s'intégrer dans saasdrevmbot (Python / Flask ou FastAPI).
Aucune dépendance externe autre que la stdlib -> pas de conflit avec
requirements.txt existant.

Usage rapide :
    from economic_calendar import EconomicCalendar

    cal = EconomicCalendar(db_path="data/economic_calendar.db")
    nb_events = cal.load_csv("ff_calendar_thisweek.csv")
    upcoming = cal.get_upcoming_events(hours=24)
    high_impact_gold = cal.get_events_for_pair("XAUUSD", impact_min="Medium")
"""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union, BinaryIO


# ---------------------------------------------------------------------------
# Mapping devise -> paires GoldXrodgers (à adapter si tu ajoutes des paires)
# ---------------------------------------------------------------------------
PAIR_CURRENCY_MAP: dict[str, set[str]] = {
    "XAUUSD": {"USD", "EUR"},  # EUR ajouté : corrélation DXY inverse (CPI/ECB EUR bouge le dollar)
    "USDJPY": {"USD", "JPY"},
    "CADJPY": {"CAD", "JPY"},
    "EURUSD": {"EUR", "USD"},
    "XBRUSD": {"USD"},  # Brent, sensible principalement au USD (+ EIA/OPEC, pas de code FF dédié)
}

IMPACT_ORDER = {"Holiday": 0, "Low": 1, "Medium": 2, "High": 3}


@dataclass
class EconomicEvent:
    title: str
    country: str  # code devise FF: USD, EUR, JPY, GBP, AUD, CAD, CHF, NZD, CNY...
    event_dt: datetime  # date + heure combinées (naive, timezone du flux FF)
    impact: str  # Low / Medium / High / Holiday
    forecast: str
    previous: str
    url: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_dt"] = self.event_dt.isoformat()
        return d


class EconomicCalendar:
    """Charge des CSV ForexFactory et les rend interrogeables (SQLite)."""

    def __init__(self, db_path: Union[str, Path] = "economic_calendar.db"):
        self.db_path = str(db_path)
        self._init_db()

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #
    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS economic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    country TEXT NOT NULL,
                    event_dt TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    forecast TEXT,
                    previous TEXT,
                    url TEXT,
                    UNIQUE(title, country, event_dt)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_dt ON economic_events(event_dt)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_country ON economic_events(country)"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
        """Convertit 'MM-DD-YYYY' + 'h:mmam/pm' (ou vide/'All Day') en datetime."""
        date_str = (date_str or "").strip()
        time_str = (time_str or "").strip()
        if not date_str:
            return None
        try:
            base = datetime.strptime(date_str, "%m-%d-%Y")
        except ValueError:
            return None

        if not time_str or time_str.lower() in ("all day", "tentative"):
            return base

        for fmt in ("%I:%M%p", "%I:%M %p", "%I%p"):
            try:
                t = datetime.strptime(time_str.lower().replace(" ", ""), fmt.replace(" ", ""))
                return base.replace(hour=t.hour, minute=t.minute)
            except ValueError:
                continue
        return base  # fallback : on garde au moins la date

    def _parse_csv_rows(self, file_obj) -> list[EconomicEvent]:
        reader = csv.DictReader(file_obj)
        events: list[EconomicEvent] = []
        for row in reader:
            dt = self._parse_datetime(row.get("Date", ""), row.get("Time", ""))
            if dt is None:
                continue
            events.append(
                EconomicEvent(
                    title=(row.get("Title") or "").strip(),
                    country=(row.get("Country") or "").strip().upper(),
                    event_dt=dt,
                    impact=(row.get("Impact") or "Low").strip(),
                    forecast=(row.get("Forecast") or "").strip(),
                    previous=(row.get("Previous") or "").strip(),
                    url=(row.get("URL") or "").strip(),
                )
            )
        return events

    # ------------------------------------------------------------------ #
    # Chargement (endpoint upload -> ici)
    # ------------------------------------------------------------------ #
    def load_csv(self, source: Union[str, Path, BinaryIO, bytes, str]) -> int:
        """
        Charge un CSV depuis :
          - un chemin de fichier (str/Path)
          - un objet fichier binaire (ex: werkzeug FileStorage.stream, UploadFile.file)
          - des bytes bruts (ex: contenu déjà lu en mémoire)
        Retourne le nombre d'évènements insérés/mis à jour.
        """
        if isinstance(source, (str, Path)) and Path(str(source)).exists():
            with open(source, "r", encoding="utf-8-sig", newline="") as f:
                events = self._parse_csv_rows(f)
        elif isinstance(source, bytes):
            text = source.decode("utf-8-sig")
            events = self._parse_csv_rows(io.StringIO(text))
        else:
            # objet fichier (upload) : on lit puis on décode
            raw = source.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8-sig")
            events = self._parse_csv_rows(io.StringIO(raw))

        if not events:
            return 0

        with self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO economic_events
                    (title, country, event_dt, impact, forecast, previous, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title, country, event_dt) DO UPDATE SET
                    impact=excluded.impact,
                    forecast=excluded.forecast,
                    previous=excluded.previous,
                    url=excluded.url
                """,
                [
                    (e.title, e.country, e.event_dt.isoformat(), e.impact, e.forecast, e.previous, e.url)
                    for e in events
                ],
            )
        return len(events)

    # ------------------------------------------------------------------ #
    # Requêtes utiles pour le bot
    # ------------------------------------------------------------------ #
    def _rows_to_events(self, rows) -> list[EconomicEvent]:
        return [
            EconomicEvent(
                title=r[0],
                country=r[1],
                event_dt=datetime.fromisoformat(r[2]),
                impact=r[3],
                forecast=r[4],
                previous=r[5],
                url=r[6],
            )
            for r in rows
        ]

    def get_upcoming_events(
        self, hours: int = 24, impact_min: str = "Low", currencies: Optional[set[str]] = None
    ) -> list[EconomicEvent]:
        """Évènements entre maintenant et +N heures, filtrés par impact/devises."""
        now = datetime.utcnow()
        until = now + timedelta(hours=hours)
        min_rank = IMPACT_ORDER.get(impact_min, 1)

        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT title, country, event_dt, impact, forecast, previous, url
                FROM economic_events
                WHERE event_dt BETWEEN ? AND ?
                ORDER BY event_dt ASC
                """,
                (now.isoformat(), until.isoformat()),
            ).fetchall()

        events = self._rows_to_events(rows)
        events = [e for e in events if IMPACT_ORDER.get(e.impact, 1) >= min_rank]
        if currencies:
            events = [e for e in events if e.country in currencies]
        return events

    def get_events_for_pair(
        self, pair: str, hours: int = 24, impact_min: str = "Medium"
    ) -> list[EconomicEvent]:
        """Raccourci : évènements pertinents pour une paire GoldXrodgers (ex: 'XAUUSD')."""
        currencies = PAIR_CURRENCY_MAP.get(pair.upper())
        if not currencies:
            raise ValueError(f"Paire inconnue : {pair}. Ajoute-la dans PAIR_CURRENCY_MAP.")
        return self.get_upcoming_events(hours=hours, impact_min=impact_min, currencies=currencies)

    def get_all_pairs_alerts(self, hours: int = 24, impact_min: str = "Medium") -> dict[str, list[dict]]:
        """Renvoie, pour chaque paire suivie par FiboAlgoBot, les évènements à risque à venir."""
        return {
            pair: [e.to_dict() for e in self.get_events_for_pair(pair, hours=hours, impact_min=impact_min)]
            for pair in PAIR_CURRENCY_MAP
        }

    def clear_past_events(self) -> int:
        """Nettoyage optionnel : supprime les évènements passés depuis plus de 7 jours."""
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM economic_events WHERE event_dt < ?", (cutoff,))
            return cur.rowcount
