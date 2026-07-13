"""
trade_journal.py — Auto-journalisation Supabase.

Quand un trade est exécuté via /api/execute, insère une ligne dans la table
`journal_trades` de Supabase (REST, clé service_role). Dégradation propre :
si SUPABASE_URL / SUPABASE_SERVICE_KEY / JOURNAL_USER_ID ne sont pas configurés,
la journalisation est simplement ignorée (le trade s'exécute quand même).

Env :
  SUPABASE_URL          https://<ref>.supabase.co
  SUPABASE_SERVICE_KEY  clé service_role (⚠️ secret — jamais côté client)
  JOURNAL_USER_ID       auth.users.id du propriétaire du journal (uuid)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
JOURNAL_USER_ID = os.environ.get("JOURNAL_USER_ID", "")


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY and JOURNAL_USER_ID)


def record_trade(symbol: str, direction: str, entry=None, sl=None, tp=None,
                 notes: str = "") -> dict:
    """
    Insère un trade 'running' dans journal_trades. `direction` = "up"/"down".
    Renvoie {ok, id?/reason}.
    """
    if not enabled():
        return {"ok": False, "reason": "journal Supabase non configuré"}

    row = {
        "user_id": JOURNAL_USER_ID,
        "symbol": symbol,
        "direction": "buy" if direction == "up" else "sell",
        "entry": entry, "sl": sl, "tp": tp,
        "result": "running",
        "notes": notes,
    }
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/journal_trades",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Prefer": "return=representation",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        rid = data[0].get("id") if isinstance(data, list) and data else None
        return {"ok": True, "id": rid}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"ok": False, "reason": str(exc)}
