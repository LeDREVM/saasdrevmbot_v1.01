"""
Persistance simple des résultats de scoring IA dans un fichier JSON.
(Léger, sans dépendance DB — suffisant pour l'historique du dashboard.)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

_STORE_PATH = Path(os.getenv("SCORING_STORE_PATH", "data/scoring_history.json"))
_MAX_ENTRIES = 500


def _ensure_store() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text("[]", encoding="utf-8")


def save_score(result: Dict) -> None:
    """Ajoute un résultat de scoring en tête de l'historique (FIFO borné)."""
    try:
        _ensure_store()
        history = load_scores()
        entry = {**result}
        entry.setdefault("generated_at", datetime.now().isoformat())
        history.insert(0, entry)
        history = history[:_MAX_ENTRIES]
        _STORE_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"💾 Score sauvegardé ({len(history)} entrées)")
    except Exception as exc:
        logger.error(f"Erreur sauvegarde score: {exc}")


def load_scores(limit: int = 100) -> List[Dict]:
    """Retourne l'historique des scores (plus récents en premier)."""
    try:
        _ensure_store()
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return data[:limit] if limit else data
    except Exception as exc:
        logger.error(f"Erreur lecture scores: {exc}")
        return []


def get_stats() -> Dict:
    """Statistiques agrégées sur l'historique des scores."""
    scores = load_scores(limit=0)
    if not scores:
        return {
            "total": 0,
            "avg_score": 0,
            "by_recommendation": {"TRADE": 0, "WAIT": 0, "SKIP": 0},
            "avg_score_by_grade": {},
        }

    total = len(scores)
    avg = round(sum(s.get("score", 0) for s in scores) / total, 1)

    by_rec = {"TRADE": 0, "WAIT": 0, "SKIP": 0}
    for s in scores:
        rec = s.get("recommendation", "WAIT")
        by_rec[rec] = by_rec.get(rec, 0) + 1

    by_grade: Dict[str, List[int]] = {}
    for s in scores:
        g = s.get("setup_grade", "?")
        by_grade.setdefault(g, []).append(s.get("score", 0))
    avg_by_grade = {g: round(sum(v) / len(v), 1) for g, v in by_grade.items()}

    return {
        "total": total,
        "avg_score": avg,
        "by_recommendation": by_rec,
        "avg_score_by_grade": avg_by_grade,
    }
