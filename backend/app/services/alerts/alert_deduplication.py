from datetime import datetime, timedelta
from hashlib import sha256
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.database import AlertDeduplication


CLAIM_TTL = timedelta(minutes=15)


def build_alert_key(
    event: Dict,
    symbol: str,
    alert_type: str,
    channel: str,
) -> str:
    """Construit une clé stable pour un événement et un canal donnés."""
    parts = (
        event.get("date", ""),
        event.get("time", ""),
        event.get("currency", ""),
        event.get("event_name", event.get("event", "")),
        symbol,
        alert_type,
        channel,
    )
    normalized = "|".join(str(part).strip().lower() for part in parts)
    return sha256(normalized.encode("utf-8")).hexdigest()


def claim_alert(
    db: Session,
    event: Dict,
    symbol: str,
    alert_type: str,
    channel: str,
) -> Optional[str]:
    """Réserve une alerte; retourne sa clé ou None si elle est déjà réservée."""
    key = build_alert_key(event, symbol, alert_type, channel)
    now = datetime.utcnow()
    existing = (
        db.query(AlertDeduplication)
        .filter(AlertDeduplication.dedupe_key == key)
        .first()
    )

    if existing:
        if now - existing.claimed_at < CLAIM_TTL:
            return None
        db.delete(existing)
        db.flush()

    db.add(
        AlertDeduplication(
            dedupe_key=key,
            alert_type=alert_type,
            channel=channel,
            symbol=symbol,
            claimed_at=now,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    return key


def release_alert(db: Session, key: str) -> None:
    """Libère une réservation dont l'envoi a échoué."""
    (
        db.query(AlertDeduplication)
        .filter(AlertDeduplication.dedupe_key == key)
        .delete(synchronize_session=False)
    )
    db.commit()
