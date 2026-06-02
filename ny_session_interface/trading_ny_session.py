"""
==============================================================================
 trading_ny_session.py  —  Smart Money Trading System (scoring & décision)
==============================================================================

 Implémente la logique de décision du "SMART MONEY TRADING SYSTEM" :
   Multi-Timeframe (H4 biais / M15 zones / M5 entrée) + Wyckoff (Spring/UTAD)
   + RSI divergence + Ichimoku (Kijun) + scoring A+/A/B/C.

 Répartition des responsabilités :
   • Le calcul des indicateurs (RSI, Ichimoku, Wyckoff, biais, zones, trigger)
     est fait dans ny_session_bot.py (détecteurs) et déposé dans MarketContext.
   • Ce module prend la décision : smart_signal + scoring de confluence.

 Référence : "Smart Money Trading System" (config fournie). Le SMART SIGNAL
 (section 6) déclenche l'entrée ; le grade reflète la "logique finale"
 (section 11) — plus la confluence H4/M15/M5 est complète, plus le grade monte
 (A+ = toutes les conditions alignées).
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
    SHALLOW = "shallow"
    EQUILIBRIUM = "equilibrium"
    SNIPER = "sniper"
    DEEP = "deep"


class SetupGrade(Enum):
    C = "C"
    B = "B"
    A = "A"
    A_PLUS = "A+"


class SetupType(Enum):
    NONE = "none"
    CONTINUATION = "continuation"   # signal aligné au biais H4
    REVERSAL = "reversal"           # signal contre le biais H4


# ── Contexte de marché (rempli par les détecteurs) ───────────────────────────

@dataclass
class MarketContext:
    # H4 — biais
    h4_phase: HTFPhase = HTFPhase.ACCUMULATION
    h4_trend: str = "range"                  # "up" | "down" | "range"
    h4_bias: str = "BULLISH"                 # "BULLISH" | "BEARISH" (get_bias_h4)
    # M15 — zones de liquidité
    m15_fib_zone: FibZone = FibZone.EQUILIBRIUM
    m15_is_logical_zone: bool = False
    m15_zone_touched: bool = False           # prix sur l'extrême du range M15(30)
    # M5 — déclenchement / structure
    m5_trigger: Optional[str] = None         # "BUY_TRIGGER" | "SELL_TRIGGER"
    m5_bos_direction: Optional[str] = None   # "up" | "down" (structure)
    swept_liquidity_side_m5: Optional[str] = None
    # Moteurs
    rsi_divergence: Optional[str] = None     # "BULLISH" | "BEARISH"
    wyckoff: Optional[str] = None            # "SPRING" | "UTAD"
    price_above_kijun: bool = False          # Ichimoku Kijun(26)


@dataclass
class SetupResult:
    is_valid: bool
    grade: SetupGrade
    setup_type: SetupType
    direction: Optional[str] = None          # "up" | "down"
    reasons: list = field(default_factory=list)
    score: int = 0


# ── Décision : SMART SIGNAL + scoring de confluence ──────────────────────────

def classify_setup(ctx: MarketContext, rr_ratio: float = 2.0) -> SetupResult:
    div = ctx.rsi_divergence
    wy = ctx.wyckoff

    # 1) SMART SIGNAL (section 6) : divergence + Wyckoff + filtre Kijun
    direction: Optional[str] = None
    if div == "BULLISH" and wy == "SPRING" and ctx.price_above_kijun:
        direction = "up"
    elif div == "BEARISH" and wy == "UTAD" and not ctx.price_above_kijun:
        direction = "down"

    if direction is None:
        return SetupResult(False, SetupGrade.C, SetupType.NONE, None,
                           ["pas de smart signal (divergence+Wyckoff+Kijun)"])

    # 2) LOGIQUE FINALE (section 11) : confluence H4 / M15 / M5
    bias_ok = (direction == "up" and ctx.h4_bias == "BULLISH") or \
              (direction == "down" and ctx.h4_bias == "BEARISH")
    trig_ok = (direction == "up" and ctx.m5_trigger == "BUY_TRIGGER") or \
              (direction == "down" and ctx.m5_trigger == "SELL_TRIGGER")
    zone_ok = ctx.m15_zone_touched

    reasons = ["smart signal " + ("BUY" if direction == "up" else "SELL"),
               f"divergence {div}", f"wyckoff {wy}",
               "prix " + ("> Kijun" if ctx.price_above_kijun else "< Kijun")]
    if bias_ok:
        reasons.append("H4 biais aligné")
    if zone_ok:
        reasons.append("M15 zone touchée")
    if trig_ok:
        reasons.append("M5 trigger")

    # 3) GRADE = nombre de confluences de la logique finale (0..3)
    extras = sum([bias_ok, zone_ok, trig_ok])
    grade = {3: SetupGrade.A_PLUS, 2: SetupGrade.A, 1: SetupGrade.B}.get(extras, SetupGrade.C)
    # Score façon PDF (divergence +3, wyckoff +3) enrichi de la confluence.
    score = 6 + extras

    setup_type = SetupType.CONTINUATION if bias_ok else SetupType.REVERSAL
    return SetupResult(True, grade, setup_type, direction, reasons, score)


def build_journal_entry(symbol: str, context: MarketContext, setup: SetupResult,
                        risk_r_percent: float, result_r=None,
                        discipline_score=None) -> dict:
    return {
        "symbol": symbol,
        "direction": setup.direction,
        "setup_type": setup.setup_type.value,
        "grade": setup.grade.value,
        "score": setup.score,
        "h4_bias": context.h4_bias,
        "h4_phase": context.h4_phase.value,
        "divergence": context.rsi_divergence,
        "wyckoff": context.wyckoff,
        "price_above_kijun": context.price_above_kijun,
        "m15_zone_touched": context.m15_zone_touched,
        "m15_fib_zone": context.m15_fib_zone.value,
        "m5_trigger": context.m5_trigger,
        "risk_pct": risk_r_percent,
        "result_r": result_r,
        "discipline_score": discipline_score,
        "reasons": setup.reasons,
    }
