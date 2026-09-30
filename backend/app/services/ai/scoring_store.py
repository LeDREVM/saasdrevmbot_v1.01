"""Bounded JSON history with process locking and atomic replacement."""
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.ai.scoring_contract import validate_result

_STORE_PATH = Path(os.getenv("SCORING_STORE_PATH", "data/scoring_history.json"))
_MAX_ENTRIES = 500


@contextmanager
def _locked():
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(str(_STORE_PATH) + ".lock", "a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read():
    if not _STORE_PATH.exists():
        return []
    data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(s, dict) for s in data):
        raise ValueError("Historique scoring invalide")
    return data


def save_score(result):
    """Return the persisted entry; failures propagate rather than claiming success."""
    validate_result(result)
    entry = {**result}
    entry.setdefault("id", str(uuid4()))
    entry.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    with _locked():
        history = [entry] + _read()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=_STORE_PATH.parent,
                                             delete=False) as handle:
                temp_path = Path(handle.name)
                json.dump(history[:_MAX_ENTRIES], handle, ensure_ascii=False, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, _STORE_PATH)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
    return entry


def load_scores(limit=100):
    with _locked():
        data = _read()
    return data[:limit] if limit else data


def get_stats():
    scores = load_scores(limit=0)
    valid = []
    for score in scores:
        try:
            validate_result(score)
            valid.append(score)
        except RuntimeError:
            pass
    by_rec = {"TRADE": 0, "WAIT": 0, "SKIP": 0}
    by_grade = {}
    for score in valid:
        by_rec[score["recommendation"]] += 1
        by_grade.setdefault(score.get("setup_grade", "?"), []).append(score["score"])
    return {"total": len(valid), "invalid_entries": len(scores) - len(valid),
            "avg_score": round(sum(s["score"] for s in valid) / len(valid), 1) if valid else 0,
            "by_recommendation": by_rec,
            "avg_score_by_grade": {g: round(sum(v) / len(v), 1) for g, v in by_grade.items()}}
