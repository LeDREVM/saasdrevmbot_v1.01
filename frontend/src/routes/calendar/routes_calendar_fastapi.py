"""
routes_calendar_fastapi.py
----------------------------
Router FastAPI équivalent au blueprint Flask, si saasdrevmbot tourne sur FastAPI.

Intégration dans main.py :

    from routes_calendar_fastapi import router as calendar_router
    app.include_router(calendar_router)

Endpoints exposés (mêmes routes que la version Flask) :
    POST /api/calendar/upload
    GET  /api/calendar/upcoming
    GET  /api/calendar/pair/{pair}
    GET  /api/calendar/alerts
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional
from economic_calendar import EconomicCalendar

router = APIRouter(prefix="/api/calendar", tags=["economic_calendar"])

# Adapte le chemin de la DB à la structure de ton repo
cal = EconomicCalendar(db_path="data/economic_calendar.db")


@router.post("/upload")
async def upload_calendar(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Format non supporté, envoie un .csv")

    raw = await file.read()
    try:
        count = cal.load_csv(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de parsing : {e}")

    return {"status": "ok", "evenements_charges": count}


@router.get("/upcoming")
def upcoming(
    hours: int = Query(24, ge=1),
    impact_min: str = Query("Low"),
    currency: Optional[str] = Query(None),
):
    currencies = {currency.upper()} if currency else None
    events = cal.get_upcoming_events(hours=hours, impact_min=impact_min, currencies=currencies)
    return [e.to_dict() for e in events]


@router.get("/pair/{pair}")
def events_for_pair(pair: str, hours: int = Query(24, ge=1), impact_min: str = Query("Medium")):
    try:
        events = cal.get_events_for_pair(pair, hours=hours, impact_min=impact_min)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [e.to_dict() for e in events]


@router.get("/alerts")
def alerts(hours: int = Query(24, ge=1), impact_min: str = Query("Medium")):
    return cal.get_all_pairs_alerts(hours=hours, impact_min=impact_min)
