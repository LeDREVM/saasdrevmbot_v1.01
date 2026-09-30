"""Strict provider output contract and transparent manual-context baseline."""
import math
from datetime import datetime, timezone


class ScoringError(RuntimeError):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def validate_result(result):
    if not isinstance(result, dict):
        raise ScoringError("Réponse IA invalide : objet attendu.")
    score = result.get("score")
    if (isinstance(score, bool) or not isinstance(score, (int, float))
            or not math.isfinite(score) or not 0 <= score <= 100):
        raise ScoringError("Réponse IA invalide : score hors limites.")
    if result.get("recommendation") not in {"TRADE", "WAIT", "SKIP"}:
        raise ScoringError("Réponse IA invalide : recommandation inconnue.")
    reasoning = result.get("reasoning")
    risks = result.get("risk_factors", [])
    if not isinstance(reasoning, str) or not 1 <= len(reasoning.strip()) <= 2000:
        raise ScoringError("Réponse IA invalide : justification manquante ou trop longue.")
    if (not isinstance(risks, list) or len(risks) > 12
            or any(not isinstance(r, str) or not 1 <= len(r) <= 300 for r in risks)):
        raise ScoringError("Réponse IA invalide : facteurs de risque incorrects.")
    return {"score": round(score, 1), "recommendation": result["recommendation"],
            "reasoning": reasoning.strip(), "risk_factors": risks}


def technical_baseline(context):
    """Baseline /55 from user-declared fields; never a win probability."""
    grade = {"A+": 25, "A": 20, "B": 12, "C": 5}.get(context.get("setup_grade"), 0)
    aligned = (context.get("htf_phase"), context.get("direction")) in {
        ("markup", "BUY"), ("markdown", "SELL")}
    criteria = [
        {"label": "Grade déclaré", "points": grade, "max": 25},
        {"label": "Phase H4 / direction", "points": 15 if aligned else 0, "max": 15},
        {"label": "Session déclarée active", "points": 10 if context.get("session_active") else 0, "max": 10},
        {"label": "Spread déclaré acceptable", "points": 5 if context.get("spread_ok") else 0, "max": 5},
    ]
    return {"points": sum(c["points"] for c in criteria), "max": 55,
            "source": "Contexte saisi manuellement", "criteria": criteria}


def score_local(context):
    """Score declared confluences locally; no provider, market or account calls."""
    baseline = technical_baseline(context)
    conf = context.get("confluence") or {}
    direction = context.get("direction")
    wyckoff = conf.get("wyckoff")
    aligned = (direction, wyckoff) in {("BUY", "SPRING"), ("SELL", "UTAD")}
    confirmed = conf.get("confirmed") is True
    kijun = conf.get("price_above_kijun")
    criteria = baseline["criteria"] + [
        {"label": "Spring/UTAD confirmé et aligné", "points": 15 if aligned and confirmed else 0, "max": 15},
        {"label": "Divergence RSI alignée déclarée", "points": 10 if conf.get("rsi_aligned") is True else 0, "max": 10},
        {"label": "Prix / Kijun aligné", "points": 10 if (direction == "BUY" and kijun is True) or (direction == "SELL" and kijun is False) else 0, "max": 10},
        {"label": "Zone M15 et trigger M5 déclarés", "points": 10 if conf.get("m15_zone_touched") is True and conf.get("m5_confirmed") is True else 0, "max": 10},
    ]
    score = sum(c["points"] for c in criteria)
    missing = ["Données saisies manuellement ; prix et volumes non vérifiés"]
    if not aligned or not confirmed:
        missing.append("Sweep et confirmation Wyckoff non validés")
    if not conf.get("m5_confirmed"):
        missing.append("Confirmation M5 absente")
    event = context.get("event_context") or {}
    minutes = event.get("minutes_until")
    news_checked = context.get("news_checked") is True
    imminent = isinstance(minutes, (int, float)) and not isinstance(minutes, bool) and 0 <= minutes < 30
    if not news_checked:
        missing.append("Calendrier non vérifié")
    if imminent:
        missing.append("Annonce dans moins de 30 minutes")
    rec = "SKIP" if score < 55 else "WAIT"
    if (score >= 75 and aligned and confirmed and conf.get("m5_confirmed") is True
            and context.get("session_active") is True and context.get("spread_ok") is True
            and news_checked and not imminent):
        rec = "TRADE"
    return {"score": score, "recommendation": rec,
            "reasoning": f"Barème local : {score}/100 sur les observations renseignées. Aucun appel IA ni validation de marché automatique.",
            "risk_factors": missing, "technical_baseline": {"points": score, "max": 100,
                "source": "Observations manuelles", "criteria": criteria},
            "symbol": context.get("symbol"), "direction": direction,
            "setup_grade": context.get("setup_grade"), "event_context": context.get("event_context"),
            "provider": "local", "model": None, "context_source": "manual",
            "generated_at": datetime.now(timezone.utc).isoformat()}
