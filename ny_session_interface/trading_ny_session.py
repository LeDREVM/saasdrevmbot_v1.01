"""
==============================================================================
 trading_ny_session.py  —  ⚠️ PLACEHOLDER / STUB
==============================================================================

 Ce fichier n'est PAS ta vraie Trading Bible. C'est un substitut minimal qui
 définit les mêmes symboles (enums, dataclasses, classify_setup,
 build_journal_entry) afin que le bot + l'interface tournent de bout en bout
 SANS MetaTrader5 et SANS ta logique propriétaire (mode démo / DRY_RUN).

 👉 Remplace ce fichier par ton vrai module `trading_ny_session.py`
    (backend/app/services/) dès que tu déploies pour de bon. L'interface et le
    moteur ne dépendent que de l'API publique définie ci-dessous.
==============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────────

class HTFPhase(Enum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"


class FibZone(Enum):
    SHALLOW = "shallow"          # < 45 %
    EQUILIBRIUM = "equilibrium"  # 50 – 61.8 %
    SNIPER = "sniper"            # ~71 %
    DEEP = "deep"                # 79 – 88.6 %


class SetupGrade(Enum):
    C = "C"
    B = "B"
    A = "A"
    A_PLUS = "A+"


class SetupType(Enum):
    NONE = "none"
    SWEEP_BOS = "sweep+bos"
    CONTINUATION = "continuation"
    REVERSAL = "reversal"


# ── Données ──────────────────────────────────────────────────────────────────

@dataclass
class MarketContext:
    h4_phase: HTFPhase
    h4_trend: str                          # "up" | "down" | "range"
    m15_fib_zone: FibZone
    m15_is_logical_zone: bool
    swept_liquidity_side_m5: Optional[str] # "high" | "low" | None
    m5_bos_direction: Optional[str]        # "up" | "down" | None


@dataclass
class SetupResult:
    is_valid: bool
    grade: SetupGrade
    setup_type: SetupType
    reasons: list = field(default_factory=list)


# ── Logique de scoring (PLACEHOLDER — heuristique de démonstration) ───────────

def classify_setup(ctx: MarketContext, rr_ratio: float = 2.0) -> SetupResult:
    """
    ⚠️ Heuristique de démonstration UNIQUEMENT. À remplacer par ta vraie Bible.

    Idée de base : un setup valide = sweep de liquidité + BOS M5 cohérent avec
    le sens du sweep. La note monte avec l'alignement H4, la zone logique et la
    profondeur du retracement Fib.
    """
    reasons: list[str] = []
    swept = ctx.swept_liquidity_side_m5
    bos = ctx.m5_bos_direction

    if not swept or not bos:
        return SetupResult(False, SetupGrade.C, SetupType.NONE, ["pas de sweep+BOS"])

    # Sweep des highs → on cherche un retournement baissier (BOS down), et inverse.
    coherent = (swept == "high" and bos == "down") or (swept == "low" and bos == "up")
    if not coherent:
        return SetupResult(False, SetupGrade.C, SetupType.NONE, ["sweep/BOS incohérents"])

    score = 1
    reasons.append("sweep + BOS cohérents")

    if ctx.m15_is_logical_zone:
        score += 1
        reasons.append("zone logique M15")

    if ctx.m15_fib_zone in (FibZone.SNIPER, FibZone.DEEP):
        score += 1
        reasons.append(f"fib {ctx.m15_fib_zone.value}")

    trend_aligned = (bos == "up" and ctx.h4_trend == "up") or \
                    (bos == "down" and ctx.h4_trend == "down")
    if trend_aligned:
        score += 1
        reasons.append("aligné tendance H4")
        setup_type = SetupType.CONTINUATION
    else:
        setup_type = SetupType.REVERSAL

    grade = {1: SetupGrade.B, 2: SetupGrade.A, 3: SetupGrade.A, 4: SetupGrade.A_PLUS}.get(
        score, SetupGrade.B
    )
    return SetupResult(True, grade, setup_type, reasons)


def build_journal_entry(symbol: str, context: MarketContext, setup: SetupResult,
                        risk_r_percent: float, result_r=None,
                        discipline_score=None) -> dict:
    """Construit une entrée de journal (compatible avec l'interface)."""
    return {
        "symbol": symbol,
        "setup_type": setup.setup_type.value,
        "grade": setup.grade.value,
        "h4_phase": context.h4_phase.value,
        "h4_trend": context.h4_trend,
        "fib_zone": context.m15_fib_zone.value,
        "logical_zone": context.m15_is_logical_zone,
        "swept": context.swept_liquidity_side_m5,
        "bos": context.m5_bos_direction,
        "risk_pct": risk_r_percent,
        "result_r": result_r,
        "discipline_score": discipline_score,
        "reasons": setup.reasons,
    }
