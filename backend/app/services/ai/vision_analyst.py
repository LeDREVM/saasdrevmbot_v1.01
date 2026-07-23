"""
Vision Analyst DREVM — analyse intégrale de captures de charts via Claude API.

Reçoit 1..N captures (URLs signées Supabase) d'un même symbole sur plusieurs
timeframes, les télécharge, et demande à Claude une analyse structurée complète
(Wyckoff, ICT/SMC, Fibonacci sniper, confluence, grade A+..D, plan de trade).

Des vetos déterministes DREVM sont appliqués côté Python APRÈS la réponse IA
(la note ne dépend jamais uniquement du modèle) :
  - R/R < 2                          → grade D (rejet dur)
  - Grade A+/A sans MSS/BOS confirmé → rétrogradé B
  - Contre-tendance sans MSS         → grade D
"""

import base64
import logging
from typing import Any, Dict, List, Optional

import anthropic
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_IMAGES = 6
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # aligné sur le bucket trade-screenshots

TF_ORDER = ["W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1"]

# ─── Tool de sortie structurée ────────────────────────────────────────────────

ANALYSIS_TOOL: Dict[str, Any] = {
    "name": "render_drevm_analysis",
    "description": (
        "Rend l'analyse DREVM finale structurée. À appeler UNE SEULE fois, "
        "après avoir examiné toutes les captures fournies."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "bias": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["long", "short", "neutral"]},
                    "score": {"type": "number", "description": "Conviction 0-10"},
                    "summary": {"type": "string", "description": "1-2 phrases max"},
                },
                "required": ["direction", "score", "summary"],
            },
            "wyckoff": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string", "description": "Ex: Accumulation phase B, Redistribution, Markup..."},
                    "events": {"type": "array", "items": {"type": "string"},
                               "description": "Ex: Spring, AR, SOS, UTAD, LPSY"},
                    "aligned_with_bias": {"type": "boolean"},
                },
                "required": ["phase", "aligned_with_bias"],
            },
            "structure": {
                "type": "object",
                "properties": {
                    "trend": {"type": "string", "description": "HH/HL, LL/LH, range..."},
                    "mss_confirmed": {"type": "boolean",
                                      "description": "MSS/BOS confirmé en CLÔTURE de bougie sur le TF d'exécution"},
                    "counter_trend": {"type": "boolean",
                                      "description": "Le setup va-t-il contre la tendance HTF ?"},
                    "key_levels": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["trend", "mss_confirmed", "counter_trend"],
            },
            "ict_smc": {
                "type": "object",
                "properties": {
                    "fvg": {"type": "string", "description": "FVG pertinents + prix EST dedans ou non"},
                    "order_blocks": {"type": "string"},
                    "liquidity": {"type": "string", "description": "Sweeps réalisés / pools visés"},
                    "price_in_zone": {"type": "boolean",
                                      "description": "Le prix est-il CONFIRMÉ dans une zone d'intérêt ?"},
                },
                "required": ["price_in_zone"],
            },
            "fibonacci": {
                "type": "object",
                "properties": {
                    "swing": {"type": "string", "description": "Leg utilisé (low → high, prix)"},
                    "sniper_zone": {"type": "string",
                                    "description": "Zone 61.8/71/81/88.6/95 pertinente + prix"},
                    "in_sniper_zone": {"type": "boolean"},
                },
                "required": ["in_sniper_zone"],
            },
            "per_timeframe": {
                "type": "array",
                "description": "Lecture concise de CHAQUE capture fournie",
                "items": {
                    "type": "object",
                    "properties": {
                        "timeframe": {"type": "string"},
                        "read": {"type": "string", "description": "2 phrases max"},
                    },
                    "required": ["timeframe", "read"],
                },
            },
            "confluences": {"type": "array", "items": {"type": "string"},
                            "description": "Confluences validées (zones avec prix DEDANS uniquement)"},
            "grade": {"type": "string", "enum": ["A+", "A", "B", "C", "D"]},
            "action": {"type": "string", "enum": ["LONG", "SHORT", "WAIT", "SKIP"]},
            "trade_plan": {
                "type": "object",
                "properties": {
                    "entry": {"type": "number"},
                    "sl": {"type": "number"},
                    "tp1": {"type": "number"},
                    "tp2": {"type": "number"},
                    "rr1": {"type": "number"},
                    "rr2": {"type": "number"},
                    "trigger": {"type": "string",
                                "description": "Condition d'entrée exacte (ex: sweep + reclaim M5 close > X)"},
                },
            },
            "invalidation": {"type": "string", "description": "Niveau + condition qui invalide le scénario"},
            "news_risk": {"type": "string", "description": "Risque news visible ou 'aucun visible'"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["bias", "wyckoff", "structure", "ict_smc", "fibonacci",
                     "per_timeframe", "confluences", "grade", "action", "invalidation"],
    },
}

SYSTEM_PROMPT = """Tu es l'analyste technique DREVM : méthodologie hybride \
Wyckoff + ICT/SMC + Fibonacci sniper (61.8/71/81/88.6/95%) + confluence \
multi-timeframe, sessions New York, instruments XAUUSD/US30/USDJPY/CADJPY/USDCAD.

Protocole d'analyse : top-down (du TF le plus haut vers le plus bas). \
Chaque capture fournie doit être lue individuellement puis synthétisée.

Règles de notation DREVM (STRICTES) :
- Grade A+/A : réservé aux setups avec MSS/BOS confirmé en CLÔTURE de bougie \
sur le TF d'exécution (no-repaint). Jamais sur une anticipation.
- Une zone (FVG/OB/Fibo) ne compte comme confluence QUE si le prix est \
CONFIRMÉ dedans, pas si elle existe simplement sur le chart.
- R/R < 2 = rejet dur → grade D, action SKIP ou WAIT.
- Contre-tendance HTF sans MSS confirmé → grade D.
- Grade B minimum pour envisager une position ; C = surveiller ; D = no trade.
- Entrées limit passives sans sweep + confirmation = à déconseiller \
explicitement dans warnings.
- Si les captures sont insuffisantes pour conclure (TF manquants, illisible), \
le dire dans warnings et rester conservateur (grade C max).

Sois factuel, chiffré (lis les prix sur les charts), concis. \
Termine TOUJOURS par un appel unique à render_drevm_analysis."""


def _guess_media_type(url: str, content_type: Optional[str]) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type.split(";")[0]
    lowered = url.lower().split("?")[0]
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


async def _download_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prépare les blocs image pour l'API Anthropic.
    Chaque item accepte SOIT `url` (URL signée à télécharger),
    SOIT `data` (base64 déjà prêt, ex: pipeline n8n) + `media_type` optionnel.
    """
    blocks: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for img in images[:MAX_IMAGES]:
            if img.get("data"):
                raw_len = len(img["data"]) * 3 // 4  # taille approx. décodée
                if raw_len > MAX_IMAGE_BYTES:
                    raise ValueError(f"Image trop lourde ({img.get('timeframe', '?')})")
                blocks.append({
                    "timeframe": img.get("timeframe") or "?",
                    "block": {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img.get("media_type") or "image/png",
                            "data": img["data"],
                        },
                    },
                })
                continue
            resp = await client.get(img["url"])
            resp.raise_for_status()
            if len(resp.content) > MAX_IMAGE_BYTES:
                raise ValueError(f"Image trop lourde ({img.get('timeframe', '?')})")
            blocks.append({
                "timeframe": img.get("timeframe") or "?",
                "block": {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _guess_media_type(img["url"], resp.headers.get("content-type")),
                        "data": base64.standard_b64encode(resp.content).decode(),
                    },
                },
            })
    return blocks


def format_telegram(result: Dict[str, Any]) -> str:
    """Formate une analyse en message Telegram (HTML) style DREVM, ADHD-friendly."""
    meta = result.get("_meta") or {}
    bias = result.get("bias") or {}
    plan = result.get("trade_plan") or {}
    grade = result.get("grade", "?")
    action = result.get("action", "?")

    g_emoji = {"A+": "💎", "A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(grade, "⚪")
    a_emoji = {"LONG": "🟢", "SHORT": "🔴", "WAIT": "⏳", "SKIP": "⛔"}.get(action, "")

    lines = [
        f"🗽 <b>DREVM Pre-Open NY — {meta.get('symbol', '?')}</b>",
        f"TF : {' → '.join(meta.get('timeframes', []))}",
        "",
        f"{g_emoji} <b>Grade {grade}</b> · {a_emoji} <b>{action}</b> · "
        f"Biais {bias.get('direction', '?')} {bias.get('score', '?')}/10",
        f"<i>{bias.get('summary', '')}</i>",
        "",
        f"🔵 Wyckoff : {(result.get('wyckoff') or {}).get('phase', '—')}",
        f"🔴 Structure : {(result.get('structure') or {}).get('trend', '—')} · "
        f"MSS {'✅' if (result.get('structure') or {}).get('mss_confirmed') else '❌'}",
        f"🎯 Fibo : {(result.get('fibonacci') or {}).get('sniper_zone', '—')}",
    ]
    if plan.get("entry"):
        lines += [
            "",
            f"📋 Entry <b>{plan['entry']}</b> · SL <b>{plan.get('sl', '?')}</b> · "
            f"TP1 <b>{plan.get('tp1', '?')}</b> ({plan.get('rr1', '?')}R)"
            + (f" · TP2 <b>{plan['tp2']}</b> ({plan.get('rr2', '?')}R)" if plan.get("tp2") else ""),
        ]
        if plan.get("trigger"):
            lines.append(f"🎬 {plan['trigger']}")
    lines += ["", f"⚠️ Invalidation : {result.get('invalidation', '—')}"]
    if result.get("news_risk"):
        lines.append(f"📅 {result['news_risk']}")
    for w in (result.get("warnings") or [])[:3]:
        lines.append(f"🚨 {w}")
    return "\n".join(lines)


def _apply_drevm_vetoes(result: Dict[str, Any]) -> Dict[str, Any]:
    """Vetos déterministes : la note finale ne dépend jamais que du modèle."""
    warnings = list(result.get("warnings") or [])
    grade = result.get("grade", "C")
    structure = result.get("structure") or {}
    plan = result.get("trade_plan") or {}

    rr1 = plan.get("rr1")
    if rr1 is not None and rr1 < 2:
        if grade != "D":
            warnings.append(f"VETO DREVM : R/R {rr1} < 2 → grade forcé D")
        grade = "D"
        if result.get("action") in ("LONG", "SHORT"):
            result["action"] = "SKIP"

    if grade in ("A+", "A") and not structure.get("mss_confirmed"):
        warnings.append("VETO DREVM : grade A sans MSS confirmé en clôture → rétrogradé B")
        grade = "B"

    if structure.get("counter_trend") and not structure.get("mss_confirmed"):
        if grade != "D":
            warnings.append("VETO DREVM : contre-tendance sans MSS confirmé → grade D")
        grade = "D"
        if result.get("action") in ("LONG", "SHORT"):
            result["action"] = "WAIT"

    result["grade"] = grade
    result["warnings"] = warnings
    return result


async def analyze_charts(
    symbol: str,
    images: List[Dict[str, Any]],
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyse intégrale DREVM.

    Args:
        symbol:  instrument (ex: XAUUSD)
        images:  [{url: <URL signée>, timeframe: "M5"}, ...] (max 6)
        context: contexte optionnel fourni par l'utilisateur (news, position...)

    Returns:
        dict structuré (schéma render_drevm_analysis) + clés meta.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY manquant dans la configuration")
    if not images:
        raise ValueError("Aucune image fournie")

    # Tri top-down (W1 → M1) pour respecter le protocole
    def tf_rank(img: Dict[str, Any]) -> int:
        tf = (img.get("timeframe") or "").upper()
        return TF_ORDER.index(tf) if tf in TF_ORDER else len(TF_ORDER)

    images = sorted(images, key=tf_rank)
    downloaded = await _download_images(images)

    content: List[Dict[str, Any]] = []
    tf_list = ", ".join(d["timeframe"] for d in downloaded)
    intro = (
        f"Analyse intégrale DREVM demandée.\n"
        f"Symbole : {symbol}\n"
        f"Captures fournies (ordre top-down) : {tf_list}\n"
    )
    if context:
        intro += f"Contexte utilisateur : {context}\n"
    content.append({"type": "text", "text": intro})

    for d in downloaded:
        content.append({"type": "text", "text": f"— Capture {d['timeframe']} :"})
        content.append(d["block"])

    content.append({
        "type": "text",
        "text": "Procède à l'analyse top-down complète puis appelle render_drevm_analysis.",
    })

    model = getattr(settings, "AI_VISION_MODEL", None) or "claude-sonnet-4-6"
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    resp = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "render_drevm_analysis"},
        messages=[{"role": "user", "content": content}],
    )

    result: Optional[Dict[str, Any]] = None
    for block in resp.content:
        if block.type == "tool_use" and block.name == "render_drevm_analysis":
            result = dict(block.input)
            break
    if result is None:
        raise RuntimeError("Le modèle n'a pas produit d'analyse structurée")

    result = _apply_drevm_vetoes(result)
    result["_meta"] = {
        "symbol": symbol,
        "timeframes": [d["timeframe"] for d in downloaded],
        "model": model,
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        },
    }
    logger.info("🤖 Analyse vision %s [%s] → grade %s / %s",
                symbol, tf_list, result["grade"], result.get("action"))
    return result
