"""
Route API — Analyse vision DREVM.

POST /api/vision/analyze
    Body : { symbol, images: [{url, timeframe}], context? }
    → analyse intégrale structurée (grade, plan, invalidation...).

Les URLs sont des URLs SIGNÉES Supabase générées côté front (bucket privé) :
le backend n'a pas besoin de la clé service_role.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app.services.ai.vision_analyst import MAX_IMAGES, analyze_charts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["Vision DREVM"])


class VisionImage(BaseModel):
    url: HttpUrl
    timeframe: Optional[str] = Field(None, examples=["M5", "H4", "D1"])


class VisionAnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["XAUUSD"])
    images: List[VisionImage] = Field(..., min_length=1, max_length=MAX_IMAGES)
    context: Optional[str] = Field(
        None, description="Contexte libre : news du jour, position ouverte, biais..."
    )


@router.post("/analyze")
async def analyze(req: VisionAnalyzeRequest):
    try:
        result = await analyze_charts(
            symbol=req.symbol.upper().strip(),
            images=[{"url": str(i.url), "timeframe": i.timeframe} for i in req.images],
            context=req.context,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:  # httpx / anthropic
        logger.exception("Erreur analyse vision")
        raise HTTPException(status_code=502, detail=f"Analyse échouée : {e}")
