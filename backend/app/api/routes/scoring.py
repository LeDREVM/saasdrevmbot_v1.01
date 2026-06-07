"""
Router scoring IA — historique + déclenchement manuel depuis le dashboard.

  GET  /api/scoring/history    → liste des scores récents
  GET  /api/scoring/stats      → statistiques agrégées
  POST /api/scoring/analyze    → lance l'agent IA et persiste le résultat
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ai import scoring_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scoring", tags=["AI Scoring"])


class AnalyzeRequest(BaseModel):
    symbol: str
    setup_grade: str
    htf_phase: str
    direction: str
    session_active: bool = True
    spread_ok: bool = True
    event_context: Optional[dict] = None
    notify: bool = False


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=500)):
    """Historique des scores (plus récents en premier)."""
    return JSONResponse({"count": limit, "scores": scoring_store.load_scores(limit)})


@router.get("/stats")
async def get_stats():
    """Statistiques agrégées sur l'historique de scoring."""
    return JSONResponse(scoring_store.get_stats())


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Lance l'agent IA de scoring, persiste et retourne le résultat."""
    try:
        from app.services.ai.scoring_agent import ScoringAgent

        agent = ScoringAgent()
        result = agent.score_setup(req.dict(exclude={"notify"}))
        scoring_store.save_score(result)

        if req.notify:
            try:
                from app.services.notifications.telegram_notifier import TelegramNotifier
                TelegramNotifier().send_scoring_result(result)
            except Exception as exc:
                logger.warning(f"Notification scoring échouée: {exc}")

        return JSONResponse(result)
    except Exception as exc:
        logger.error(f"Erreur analyse scoring: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
