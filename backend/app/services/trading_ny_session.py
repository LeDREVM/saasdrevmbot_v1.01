from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Dict, Any


class HTFPhase(str, Enum):
    """Phase de marché H4 (Dow / Wyckoff simplifié)."""

    MARKUP = "markup"  # tendance haussière
    MARKDOWN = "markdown"  # tendance baissière
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


class SetupType(str, Enum):
    BUY_CONTINUATION = "buy_continuation"
    SELL_CONTINUATION = "sell_continuation"
    RANGE_BUY = "range_buy"
    RANGE_SELL = "range_sell"
    NONE = "none"


class SetupGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


class FibZone(str, Enum):
    """Zones Fibonacci pertinentes sur M15."""

    SHALLOW = "23.6_38.2"
    EQUILIBRIUM = "50_61.8"
    SNIPER = "71"
    DEEP = "81_88.6_95"


@dataclass
class MarketContext:
    """
    Représente la lecture multi-timeframe H4 → M15 → M5
    inspirée de la Trading Bible NY Session.
    """

    h4_phase: HTFPhase
    h4_trend: Literal["up", "down", "range"]
    m15_fib_zone: Optional[FibZone]
    m15_is_logical_zone: bool  # demande/offre, SR, Kijun, EMA, range, etc.
    swept_liquidity_side_m5: Optional[Literal["high", "low"]]  # sweep du high ou du low sur M5
    m5_bos_direction: Optional[Literal["up", "down"]]  # cassure de structure sur M5


@dataclass
class NySessionSetup:
    """Classification du setup NY Session + checklist d’exécution."""

    setup_type: SetupType
    grade: SetupGrade
    is_valid: bool

    # Checklist synthétique
    h4_ok: bool
    m15_zone_ok: bool
    fib_ok: bool
    liquidity_ok: bool
    trigger_ok: bool
    rr_ok: bool

    notes: str


def classify_setup(
    context: MarketContext,
    rr_ratio: float,
) -> NySessionSetup:
    """
    Applique la logique de la Trading Bible NY Session :

    - Biais H4 (phase + tendance)
    - Zone M15 cohérente (SR / demande-offre / range / Kijun / EMA / nuage Ichimoku)
    - Niveau Fibonacci 61.8 / 71 / 81 / 88.6 / 95 privilégié pour les continuations
    - Sweep de liquidité sur M5 puis cassure de structure (BOS) dans le sens du trade
    - R/R acceptable (min 2R conseillé)
    """

    h4_ok = context.h4_phase in (
        HTFPhase.MARKUP,
        HTFPhase.MARKDOWN,
        HTFPhase.ACCUMULATION,
        HTFPhase.DISTRIBUTION,
    )

    m15_zone_ok = context.m15_is_logical_zone
    fib_ok = context.m15_fib_zone in {
        FibZone.EQUILIBRIUM,
        FibZone.SNIPER,
        FibZone.DEEP,
    }

    liquidity_ok = context.swept_liquidity_side_m5 is not None
    trigger_ok = context.m5_bos_direction is not None
    rr_ok = rr_ratio >= 2.0

    setup_type = SetupType.NONE
    notes: list[str] = []

    # BUY continuation : H4 haussier, retour sur 61.8/71/81, sweep du low puis BOS haussier.
    if (
        context.h4_phase == HTFPhase.MARKUP
        and context.h4_trend == "up"
        and context.swept_liquidity_side_m5 == "low"
        and context.m5_bos_direction == "up"
    ):
        setup_type = SetupType.BUY_CONTINUATION
        notes.append("Biais H4 haussier + sweep des lows + BOS haussier (setup BUY continuation).")

    # SELL continuation : H4 baissier, retour sur 61.8/71/88.6, sweep du high puis BOS baissier.
    if (
        context.h4_phase == HTFPhase.MARKDOWN
        and context.h4_trend == "down"
        and context.swept_liquidity_side_m5 == "high"
        and context.m5_bos_direction == "down"
    ):
        setup_type = SetupType.SELL_CONTINUATION
        notes.append("Biais H4 baissier + sweep des highs + BOS baissier (setup SELL continuation).")

    # Range extrême BUY : accumulation, borne basse de range, spring + reprise haussière M5.
    if (
        context.h4_phase == HTFPhase.ACCUMULATION
        and context.h4_trend == "range"
        and context.swept_liquidity_side_m5 == "low"
        and context.m5_bos_direction == "up"
    ):
        setup_type = SetupType.RANGE_BUY
        notes.append("Phase d'accumulation + spring bas de range + reprise M5 (BUY de range).")

    # Range extrême SELL : distribution, borne haute de range, UTAD + cassure baissière M5.
    if (
        context.h4_phase == HTFPhase.DISTRIBUTION
        and context.h4_trend == "range"
        and context.swept_liquidity_side_m5 == "high"
        and context.m5_bos_direction == "down"
    ):
        setup_type = SetupType.RANGE_SELL
        notes.append("Phase de distribution + UTAD haut de range + cassure M5 (SELL de range).")

    # Détermination de la note A+/A/B/C en fonction de la confluence
    confluences = sum(
        [
            h4_ok,
            m15_zone_ok,
            fib_ok,
            liquidity_ok,
            trigger_ok,
            rr_ok,
        ]
    )

    if confluences >= 6:
        grade = SetupGrade.A_PLUS
    elif confluences >= 5:
        grade = SetupGrade.A
    elif confluences >= 4:
        grade = SetupGrade.B
    else:
        grade = SetupGrade.C

    is_valid = setup_type is not SetupType.NONE and grade in (
        SetupGrade.A_PLUS,
        SetupGrade.A,
        SetupGrade.B,
    )

    if not m15_zone_ok:
        notes.append("Zone M15 pas assez logique (SR / demande-offre / Kijun / EMA / range manquant).")
    if not fib_ok:
        notes.append("Niveau Fibonacci hors 61.8/71/81/88.6/95 (zone de probabilité plus faible).")
    if not liquidity_ok:
        notes.append("Pas de sweep de liquidité clair sur M5.")
    if not trigger_ok:
        notes.append("Pas de cassure de structure propre sur M5.")
    if not rr_ok:
        notes.append("R/R < 2R : risque/rendement peu intéressant.")

    if setup_type is SetupType.NONE:
        notes.append("Aucun setup NY Session propre détecté (attente recommandée).")

    return NySessionSetup(
        setup_type=setup_type,
        grade=grade,
        is_valid=is_valid,
        h4_ok=h4_ok,
        m15_zone_ok=m15_zone_ok,
        fib_ok=fib_ok,
        liquidity_ok=liquidity_ok,
        trigger_ok=trigger_ok,
        rr_ok=rr_ok,
        notes=" ".join(notes),
    )


def build_journal_entry(
    symbol: str,
    context: MarketContext,
    setup: NySessionSetup,
    risk_r_percent: float,
    result_r: Optional[float],
    discipline_score: Optional[int],
    screenshot_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construit une ligne de journal compatible avec un template type FTMO :

    - Contexte H4
    - Zone M15
    - Trigger M5
    - Type de setup (BUY/SELL continuation ou range)
    - R/R prévu et résultat en R
    - Qualité de setup (A+/A/B/C)
    """

    return {
        "Symbol": symbol,
        "H4_Phase": context.h4_phase.value,
        "H4_Trend": context.h4_trend,
        "M15_Fib_Zone": context.m15_fib_zone.value if context.m15_fib_zone else None,
        "M15_Logical_Zone": context.m15_is_logical_zone,
        "M5_Swept_Liquidity": context.swept_liquidity_side_m5,
        "M5_BOS_Direction": context.m5_bos_direction,
        "Setup_Type": setup.setup_type.value,
        "Setup_Grade": setup.grade.value,
        "NY_Setup_Valid": setup.is_valid,
        "Risk_Per_Trade_R": risk_r_percent,
        "Result_R": result_r,
        "Discipline_Score": discipline_score,
        "Notes": setup.notes,
        "Screenshot": screenshot_path,
    }

