"""Local, on-demand scoring; no external model or notifications."""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, confloat

from app.services.ai import scoring_store
from app.services.ai.scoring_contract import score_local

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scoring", tags=["Scoring"])


class Confluence(BaseModel):
    wyckoff: Optional[Literal["SPRING", "UTAD"]] = None
    confirmed: bool = False
    rsi_aligned: bool = False
    price_above_kijun: Optional[bool] = None
    m15_zone_touched: bool = False
    m5_confirmed: bool = False


class EventContext(BaseModel):
    event: str = Field(default="Annonce", max_length=200)
    currency: Optional[str] = Field(default=None, max_length=10)
    minutes_until: confloat(allow_inf_nan=False, ge=0, le=10080)


class AnalyzeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9/._-]+$")
    setup_grade: Literal["A+", "A", "B", "C"]
    htf_phase: Literal["markup", "markdown", "accumulation", "distribution"]
    direction: Literal["BUY", "SELL"]
    session_active: bool = False
    spread_ok: bool = False
    news_checked: bool = False
    event_context: Optional[EventContext] = None
    confluence: Optional[Confluence] = None
    notify: bool = False  # compatibility; this route never sends messages


@router.get("/status")
def get_status():
    return {"provider": "local", "model": None, "configured": True,
            "mode": "on_demand", "external_calls": False,
            "message": "Scoring local prêt · aucun envoi externe"}


@router.get("/history")
def get_history(limit: int = Query(50, ge=1, le=500)):
    try:
        scores = scoring_store.load_scores(limit)
        return {"count": len(scores), "scores": scores}
    except (OSError, ValueError):
        raise HTTPException(503, "Historique indisponible ; fichier conservé pour récupération.") from None


@router.get("/stats")
def get_stats():
    try:
        return scoring_store.get_stats()
    except (OSError, ValueError):
        raise HTTPException(503, "Statistiques indisponibles.") from None


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    if req.notify:
        raise HTTPException(422, "Les notifications ne sont pas activées pour le scoring local.")
    context = req.model_dump(exclude={"notify"})
    context["symbol"] = context["symbol"].upper()
    result = score_local(context)
    try:
        return scoring_store.save_score(result)
    except (OSError, ValueError):
        logger.error("Scoring history persistence failed")
        raise HTTPException(503, "Le score a été calculé mais sa sauvegarde a échoué. Réessaie.") from None
