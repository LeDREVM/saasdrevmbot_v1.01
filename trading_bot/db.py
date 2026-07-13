# db.py — Persistance SQLite des signaux du bot
# Utilisé par main.py (écriture) et dashboard.py (lecture)

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "db.sqlite"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée la table signals si elle n'existe pas."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                pair      TEXT    NOT NULL,
                signal    TEXT    NOT NULL,          -- BUY / SELL
                setup     TEXT,
                score     INTEGER,
                grade     TEXT,                       -- A+ / A / B / C
                price     REAL,
                rsi       REAL
            )
        """)


def save_signal(pair, signal, setup=None, score=None, grade=None, price=None, rsi=None):
    """Enregistre un signal détecté (appelé depuis main.py)."""
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO signals (timestamp, pair, signal, setup, score, grade, price, rsi) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"),
             pair, signal, setup, score, grade, price, rsi),
        )


def get_signals(limit=20):
    """Derniers signaux, plus récents en premier."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats():
    """Statistiques agrégées : totaux, par grade, par paire, par sens."""
    init_db()
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
        by_grade = {
            r["grade"] or "?": r["c"]
            for r in conn.execute(
                "SELECT grade, COUNT(*) c FROM signals GROUP BY grade"
            ).fetchall()
        }
        by_pair = {
            r["pair"]: r["c"]
            for r in conn.execute(
                "SELECT pair, COUNT(*) c FROM signals GROUP BY pair ORDER BY c DESC"
            ).fetchall()
        }
        by_side = {
            r["signal"]: r["c"]
            for r in conn.execute(
                "SELECT signal, COUNT(*) c FROM signals GROUP BY signal"
            ).fetchall()
        }
        last = conn.execute(
            "SELECT timestamp FROM signals ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "total": total,
        "by_grade": by_grade,
        "by_pair": by_pair,
        "by_side": by_side,
        "last_signal_at": last["timestamp"] if last else None,
    }
