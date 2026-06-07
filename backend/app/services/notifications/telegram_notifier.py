"""
Telegram notifier — envoie les annonces économiques et scores IA via Bot API.
"""

import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
SCORE_EMOJI = {range(80, 101): "🟢", range(60, 80): "🟡", range(0, 60): "🔴"}


def _score_emoji(score: int) -> str:
    for r, emoji in SCORE_EMOJI.items():
        if score in r:
            return emoji
    return "⚪"


class TelegramNotifier:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        if not self.token or not self.chat_id:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID non configuré")

    # ─── public API ──────────────────────────────────────────────────────────

    def send_daily_calendar(self, events: List[Dict]) -> bool:
        """Envoie le résumé calendrier du jour en Markdown Telegram."""
        if not events:
            return True
        today = datetime.now().strftime("%d/%m/%Y")
        high = [e for e in events if e.get("impact") in ("High", "high")]
        medium = [e for e in events if e.get("impact") in ("Medium", "medium")]

        lines = [
            f"📊 *Calendrier Économique — {today}*",
            f"_{len(events)} événements • {len(high)} 🔴 Fort • {len(medium)} 🟡 Moyen_",
            "",
        ]

        if high:
            lines.append("*🔴 Fort impact*")
            for e in high[:8]:
                forecast = e.get("forecast") or "—"
                previous = e.get("previous") or "—"
                lines.append(
                    f"`{e.get('time','??:??')}` {e.get('currency','?')} — {e.get('event','?')}"
                    f"\n  ↳ Prév: `{forecast}` | Préc: `{previous}`"
                )
            if len(high) > 8:
                lines.append(f"_…et {len(high)-8} autres_")

        if medium:
            lines.append("")
            lines.append("*🟡 Impact moyen*")
            for e in medium[:5]:
                lines.append(
                    f"`{e.get('time','??:??')}` {e.get('currency','?')} — {e.get('event','?')}"
                )
            if len(medium) > 5:
                lines.append(f"_…et {len(medium)-5} autres_")

        return self._send_message("\n".join(lines))

    def send_pre_event_alert(self, events: List[Dict], minutes: int = 30) -> bool:
        """Rappel X minutes avant un événement à fort impact."""
        if not events:
            return True
        lines = [f"⏰ *Annonce dans {minutes} min*", ""]
        for e in events[:5]:
            emoji = IMPACT_EMOJI.get(e.get("impact", "Low"), "⚪")
            forecast = e.get("forecast") or "—"
            previous = e.get("previous") or "—"
            lines.append(
                f"{emoji} `{e.get('time','??:??')}` *{e.get('currency','?')}* — {e.get('event','?')}"
                f"\n  Prév: `{forecast}` | Préc: `{previous}`"
            )
        return self._send_message("\n".join(lines))

    def send_scoring_result(self, result: Dict) -> bool:
        """Envoie le résultat de l'agent IA de scoring."""
        score = result.get("score", 0)
        rec = result.get("recommendation", "WAIT")
        reasoning = result.get("reasoning", "")
        symbol = result.get("symbol", "?")
        grade = result.get("setup_grade", "?")
        event_name = result.get("event_context", {}).get("event", "")

        emoji = _score_emoji(score)
        rec_emoji = {"TRADE": "✅", "SKIP": "❌", "WAIT": "⏳"}.get(rec, "❓")

        lines = [
            f"🤖 *Score IA — {symbol}*",
            f"{emoji} Score : *{score}/100*  {rec_emoji} `{rec}`",
            f"Grade setup : `{grade}`",
        ]
        if event_name:
            lines.append(f"Contexte : _{event_name}_")
        if reasoning:
            lines.append("")
            lines.append(f"_{reasoning[:280]}_")

        return self._send_message("\n".join(lines))

    def test_connection(self) -> bool:
        msg = "✅ *saasDrevmBot connecté* — Telegram OK"
        return self._send_message(msg)

    # ─── internal ────────────────────────────────────────────────────────────

    def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.token or not self.chat_id:
            logger.error("❌ Telegram non configuré")
            return False
        url = TELEGRAM_API.format(token=self.token, method="sendMessage")
        try:
            resp = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                timeout=10,
            )
            if resp.ok:
                logger.info("✅ Message Telegram envoyé")
                return True
            logger.error(f"❌ Telegram {resp.status_code}: {resp.text[:200]}")
            return False
        except Exception as exc:
            logger.error(f"❌ Telegram exception: {exc}")
            return False
