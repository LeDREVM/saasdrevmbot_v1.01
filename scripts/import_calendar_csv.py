#!/usr/bin/env python3
"""
DREVM · Import CSV du calendrier économique (ForexFactory : daily / week / month).

Parse un ou plusieurs CSV et injecte les événements dans les DEUX cibles du projet :
  1. la DB backend (SQLite `backend/drevmbot.db`, table economic_events) —
     consommée par /api/calendar/*, /api/n8n/calendar, l'historique ;
  2. `data/events_log.json` — l'historique du moteur de corrélation Node
     (dashboard /correlations).

Dédup automatique : DB par (date, time, currency, event) ; Node par id.

Exemples :
  python scripts/import_calendar_csv.py ff_thisweek.csv
  python scripts/import_calendar_csv.py daily.csv week.csv month.csv --range mix
  python scripts/import_calendar_csv.py cal.csv --tz America/New_York
  python scripts/import_calendar_csv.py cal.csv --utc-offset -4   # Windows sans tzdata
  python scripts/import_calendar_csv.py cal.csv --no-node          # DB uniquement
  python scripts/import_calendar_csv.py cal.csv --dry-run          # parse seulement

⚠️ Si le serveur Node (src/server.js) tourne, arrête-le avant l'import (ou
   redémarre-le après) : il garde events_log.json en mémoire et réécrirait le
   fichier au prochain flush, écrasant l'import.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
NODE_LOG = REPO_ROOT / "data" / "events_log.json"
NODE_RETENTION_MS = 90 * 24 * 60 * 60 * 1000

# Cible la vraie DB backend quel que soit le cwd (avant tout import de la config).
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'drevmbot.db').as_posix()}")
sys.path.insert(0, str(BACKEND_DIR))

from app.services.economic_calendar.csv_importer import parse_calendar_csv  # noqa: E402


def resolve_tzinfo(tz_name: str, utc_offset):
    """tzinfo depuis --tz (IANA) ou --utc-offset (heures). Repli ET si tzdata absent."""
    if utc_offset is not None:
        return timezone(timedelta(hours=utc_offset)), f"UTC{utc_offset:+g}"
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name), tz_name
    except Exception:
        print(f"⚠️  Fuseau '{tz_name}' indisponible (tzdata absent ?) → repli UTC-4 (ET été). "
              f"Utilise --utc-offset pour fixer précisément.")
        return timezone(timedelta(hours=-4)), "UTC-4 (repli)"


def import_to_db(events) -> tuple[int, int]:
    from app.core.database import engine, SessionLocal
    from app.models.database import EconomicEventDB

    # NB : models/database.py a son propre declarative_base → créer la table via
    # la metadata du modèle (pas celle de core.database, qui est distincte).
    EconomicEventDB.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = skipped = 0
    try:
        for ev in events:
            e = ev.to_economic_event()
            exists = db.query(EconomicEventDB).filter_by(
                date=e.date, time=e.time, currency=e.currency, event=e.event
            ).first()
            if exists:
                skipped += 1
                continue
            db.add(EconomicEventDB(**e.to_dict()))
            added += 1
        db.commit()
    finally:
        db.close()
    return added, skipped


def import_to_node(events) -> tuple[int, int]:
    arr = []
    if NODE_LOG.exists():
        try:
            arr = json.loads(NODE_LOG.read_text(encoding="utf-8")) or []
        except json.JSONDecodeError:
            print(f"⚠️  {NODE_LOG} illisible → recréé.")
            arr = []
    by_id = {e["id"]: e for e in arr if isinstance(e, dict) and e.get("id")}

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff = now_ms - NODE_RETENTION_MS
    added = updated = 0
    for ev in events:
        entry = ev.to_node_entry()
        if entry["_loggedAt"] < cutoff:
            continue  # > 90 j : le moteur le purgerait de toute façon
        cur = by_id.get(entry["id"])
        if cur:
            changed = False
            for k in ("actual", "forecast", "previous"):
                if entry[k] and entry[k] != cur.get(k):
                    cur[k] = entry[k]
                    changed = True
            if changed:
                updated += 1
        else:
            by_id[entry["id"]] = entry
            added += 1

    NODE_LOG.parent.mkdir(parents=True, exist_ok=True)
    NODE_LOG.write_text(json.dumps(list(by_id.values())), encoding="utf-8")
    return added, updated


def main() -> int:
    p = argparse.ArgumentParser(description="Import CSV calendrier (ForexFactory) → DB backend + moteur Node.")
    p.add_argument("files", nargs="+", help="Fichiers CSV (daily / week / month).")
    p.add_argument("--tz", default="America/New_York", help="Fuseau des heures du CSV (défaut ForexFactory = US/Eastern).")
    p.add_argument("--utc-offset", type=float, default=None, help="Décalage UTC fixe en heures (ex -4). Prioritaire sur --tz.")
    p.add_argument("--range", default=None, help="Étiquette libre (daily/week/month) pour le log.")
    p.add_argument("--no-db", action="store_true", help="Ne pas écrire dans la DB backend.")
    p.add_argument("--no-node", action="store_true", help="Ne pas écrire dans events_log.json.")
    p.add_argument("--dry-run", action="store_true", help="Parser et afficher, sans rien écrire.")
    args = p.parse_args()

    tzinfo_obj, tz_label = resolve_tzinfo(args.tz, args.utc_offset)
    label = f" [{args.range}]" if args.range else ""
    print(f"═══ Import CSV calendrier{label} · fuseau {tz_label} ═══")

    all_events = []
    total_skipped = 0
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"  ❌ introuvable : {f}")
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")  # -sig : gère le BOM
        events, skipped = parse_calendar_csv(text, tzinfo_obj)
        print(f"  📄 {path.name} : {len(events)} événement(s), {len(skipped)} ignoré(s)")
        for s in skipped[:5]:
            print(f"       ⤷ {s}")
        if len(skipped) > 5:
            print(f"       ⤷ … +{len(skipped) - 5} autres")
        all_events.extend(events)
        total_skipped += len(skipped)

    if not all_events:
        print("Aucun événement exploitable. Rien à importer.")
        return 1

    print(f"\n  Total : {len(all_events)} événement(s) parsé(s), {total_skipped} ignoré(s).")

    if args.dry_run:
        for ev in all_events[:8]:
            print(f"    · {ev.date_iso} {ev.time_24} {ev.currency:4} [{ev.impact_level}] {ev.event}")
        if len(all_events) > 8:
            print(f"    … +{len(all_events) - 8} autres")
        print("(dry-run : rien écrit)")
        return 0

    if not args.no_db:
        added, skipped = import_to_db(all_events)
        print(f"  🗄️  DB backend : +{added} ajouté(s), {skipped} déjà présent(s)")

    if not args.no_node:
        added, updated = import_to_node(all_events)
        print(f"  🔗 events_log.json (Node) : +{added} ajouté(s), {updated} mis à jour")

    print("═══ Import terminé ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
