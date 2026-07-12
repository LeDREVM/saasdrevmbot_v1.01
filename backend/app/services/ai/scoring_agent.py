"""
Agent IA de scoring des setups de trading.

Reçoit un contexte (grade MQL, phase HTF, événement éco, corrélation historique)
et retourne un score /100 + recommandation TRADE / WAIT / SKIP via Claude tool use.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

# ─── Tool definitions ────────────────────────────────────────────────────────

TOOLS: List[Dict] = [
    {
        "name": "get_upcoming_events",
        "description": (
            "Retourne les événements économiques à fort impact prévus dans les N prochaines heures."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours_ahead": {
                    "type": "number",
                    "description": "Fenêtre de recherche en heures (défaut 2)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_correlation_stats",
        "description": (
            "Retourne les statistiques de corrélation historiques pour un symbole "
            "autour d'un type d'événement (mouvement moyen en pips, probabilité directionnelle)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ex: US30, USDJPY, XAUUSD"},
                "event_keyword": {
                    "type": "string",
                    "description": "Mot-clé de l'événement (ex: NFP, CPI, FOMC)",
                },
            },
            "required": ["symbol", "event_keyword"],
        },
    },
    {
        "name": "compute_score",
        "description": (
            "Calcule et retourne le score final /100 avec recommandation et raisonnement. "
            "Appeler EN DERNIER après avoir collecté toutes les informations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Score de 0 à 100",
                },
                "recommendation": {
                    "type": "string",
                    "enum": ["TRADE", "WAIT", "SKIP"],
                    "description": "TRADE=entrer, WAIT=attendre confirmation, SKIP=éviter",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Raisonnement concis (max 3 phrases)",
                },
                "risk_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des facteurs de risque identifiés",
                },
            },
            "required": ["score", "recommendation", "reasoning"],
        },
    },
]

SYSTEM_PROMPT = """Tu es un agent expert en trading Smart Money (ICT/Wyckoff) spécialisé sur la session New York.
Tu analyses des setups algorithmiques et tu scores leur qualité de 0 à 100 selon :

**Critères de scoring :**
- Grade setup MQL (A+=25pts, A=20pts, B=12pts, C=5pts)
- Phase HTF cohérente avec la direction (Markup→BUY +15pts, Markdown→SELL +15pts, sinon 0)
- Absence d'événement économique fort impact dans les 30 min (oui +15pts, annonce imminente -20pts)
- Corrélation historique favorable (mouvement moyen >15 pips +10pts, >8 pips +5pts)
- Session active NY/London (+10pts), hors session (-10pts)
- Probabilité directionnelle historique >65% (+10pts), >55% (+5pts)
- Spread acceptable (+5pts si dans les limites de l'EA)
- Bonus liquidité/structure confluente (+10pts) — quand un bloc « Confluence technique »
  est fourni, appuie ce bonus sur les piliers réels : FVG frais en mitigation, Wyckoff
  (Spring/UTAD), divergence RSI alignée et prix du bon côté de la Kijun. Un score de
  confluence élevé (≥8/11) renforce la conviction ; un FVG comblé ou non testé l'affaiblit.

**Recommandations :**
- TRADE : score ≥ 75 et pas d'annonce imminente
- WAIT  : score 55–74 ou annonce dans <30 min
- SKIP  : score < 55 ou risque extrême

Utilise les outils disponibles pour collecter les données avant de scorer.
Réponds toujours en français dans le raisonnement."""


class ScoringAgent:
    """Agent IA de scoring — orchestre les appels Claude + outils."""

    def __init__(
        self,
        calendar_fn=None,
        correlation_fn=None,
        api_key: Optional[str] = None,
    ):
        """
        Args:
            calendar_fn : callable(hours_ahead) → List[dict] événements à venir
            correlation_fn : callable(symbol, keyword) → dict stats corrélation
            api_key : clé Anthropic (sinon ANTHROPIC_API_KEY env)
        """
        self._calendar_fn = calendar_fn or _default_calendar
        self._correlation_fn = correlation_fn or _default_correlation
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    # ─── public ──────────────────────────────────────────────────────────────

    def score_setup(self, context: Dict) -> Dict:
        """
        Analyse un setup et retourne le score.

        Args:
            context: {
                symbol: str,
                setup_grade: str,          # A+/A/B/C
                htf_phase: str,            # markup/markdown/accumulation/distribution
                direction: str,            # BUY/SELL
                session_active: bool,
                spread_ok: bool,
                event_context: dict|None,  # annonce imminente si connue
            }

        Returns:
            {score, recommendation, reasoning, risk_factors, symbol, setup_grade,
             event_context, generated_at}
        """
        user_msg = self._build_user_message(context)
        messages = [{"role": "user", "content": user_msg}]

        final_result: Dict = {}

        for _ in range(6):  # max 6 tours
            resp = self._client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                break

            if resp.stop_reason == "tool_use":
                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    result = self._dispatch_tool(block.name, block.input, context)
                    # compute_score → capture le résultat final
                    if block.name == "compute_score":
                        final_result = dict(block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        if not final_result:
            final_result = {"score": 50, "recommendation": "WAIT", "reasoning": "Données insuffisantes."}

        return {
            **final_result,
            "symbol": context.get("symbol", "?"),
            "setup_grade": context.get("setup_grade", "?"),
            "event_context": context.get("event_context"),
            "generated_at": datetime.now().isoformat(),
        }

    # ─── tool dispatch ────────────────────────────────────────────────────────

    def _dispatch_tool(self, name: str, inputs: Dict, context: Dict) -> Any:
        try:
            if name == "get_upcoming_events":
                hours = float(inputs.get("hours_ahead", 2))
                return self._calendar_fn(hours)
            if name == "get_correlation_stats":
                return self._correlation_fn(inputs["symbol"], inputs["event_keyword"])
            if name == "compute_score":
                return {"status": "ok", "score": inputs.get("score")}
        except Exception as exc:
            logger.error(f"Tool {name} error: {exc}")
            return {"error": str(exc)}
        return {"error": f"unknown tool {name}"}

    # ─── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _build_user_message(ctx: Dict) -> str:
        grade = ctx.get("setup_grade", "?")
        phase = ctx.get("htf_phase", "?")
        direction = ctx.get("direction", "?")
        symbol = ctx.get("symbol", "?")
        session = "active" if ctx.get("session_active") else "inactive"
        spread = "OK" if ctx.get("spread_ok") else "large"
        event = ctx.get("event_context")

        msg = (
            f"Analyse ce setup et score-le :\n"
            f"- Symbole : {symbol}\n"
            f"- Grade setup MQL : {grade}\n"
            f"- Phase HTF : {phase}\n"
            f"- Direction : {direction}\n"
            f"- Session : {session}\n"
            f"- Spread : {spread}\n"
        )
        if event:
            msg += (
                f"- Annonce imminente : {event.get('event','?')} "
                f"({event.get('currency','?')}) dans {event.get('minutes_until','?')} min\n"
            )

        conf = ctx.get("confluence")
        if conf:
            msg += "\nConfluence technique (moteur Wyckoff + FVG + Ichimoku) :\n"
            pts, mx = conf.get("points"), conf.get("max")
            if pts is not None:
                msg += f"- Score confluence : {pts}/{mx}\n"
            pillars = conf.get("pillars") or {}
            if pillars:
                yes = [k for k, v in pillars.items() if v]
                no = [k for k, v in pillars.items() if not v]
                msg += f"- Piliers présents : {', '.join(yes) or 'aucun'}\n"
                msg += f"- Piliers absents : {', '.join(no) or 'aucun'}\n"
            if conf.get("wyckoff"):
                msg += f"- Wyckoff : {conf['wyckoff']}\n"
            fvg = conf.get("fvg") or {}
            if fvg.get("direction"):
                mit = "en mitigation (prix dans le gap)" if fvg.get("price_in_gap") else "non testé"
                fresh = "frais" if fvg.get("fresh") else "comblé"
                msg += f"- FVG : {fvg['direction']}, {fresh}, {mit}\n"
            if conf.get("rsi_divergence"):
                msg += f"- Divergence RSI : {conf['rsi_divergence']}\n"
            if conf.get("price_above_kijun") is not None:
                msg += f"- Ichimoku : prix {'au-dessus' if conf['price_above_kijun'] else 'en dessous'} de la Kijun\n"
            if conf.get("m15_zone_touched") is not None:
                msg += f"- Zone M15 touchée : {'oui' if conf['m15_zone_touched'] else 'non'}\n"
            if conf.get("m5_trigger"):
                msg += f"- Trigger M5 : {conf['m5_trigger']}\n"

        msg += "\nUtilise les outils disponibles pour compléter l'analyse puis appelle compute_score."
        return msg


# ─── default stubs (remplacés en prod par les vrais services) ─────────────────

def _default_calendar(hours_ahead: float = 2) -> List[Dict]:
    """Stub — retourne liste vide si aucun service calendar injecté."""
    return []


def _default_correlation(symbol: str, event_keyword: str) -> Dict:
    """Stub — retourne stats neutres si aucun service correlation injecté."""
    return {
        "symbol": symbol,
        "event_keyword": event_keyword,
        "samples": 0,
        "avg_movement_pips": 0,
        "direction_probability": {"up": 50, "down": 50, "neutral": 0},
        "note": "Pas de données historiques disponibles",
    }
