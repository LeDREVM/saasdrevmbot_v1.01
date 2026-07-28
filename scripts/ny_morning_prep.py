#!/usr/bin/env python3
"""
DREVM · Prep session NY — orchestrateur LOCAL (remplace n8n / WF6).

Chaîne, en local et sans n8n :
    screenshot-service (:3001)  POST /capture-set        (Puppeteer → TradingView)
        └─▶ backend (:8000)     POST /api/vision/analyze-raw   (→ Claude Vision)
             └─▶ backend        POST /api/n8n/notify/telegram  (best-effort)
             └─▶ rapport sauvegardé dans data/ny_reports/<date>/<symbole>.md

Déclenchement : tous les jours ouvrés à **3h00 heure Guadeloupe** (= 07:00 UTC ;
la Guadeloupe est en UTC-4 toute l'année, sans changement d'heure été/hiver).

Deux modes :
    --daemon   (défaut) : le script se planifie lui-même et tourne en continu.
    --once              : exécute une passe immédiate et sort (pour cron / Task Scheduler).
    --symbol SYM        : exécute une passe sur UN seul symbole (test manuel).

Zéro dépendance : stdlib uniquement (urllib, json, datetime). Se lance depuis
n'importe où, mais lit backend/.env pour récupérer N8N_WEBHOOK_SECRET si absent
de l'environnement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Config (surchargée par variables d'environnement) ────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent

SCREENSHOT_URL = os.environ.get("SCREENSHOT_URL", "http://localhost:3001").rstrip("/")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")

# 6 symboles session NY (modifiable via NY_SYMBOLS="XAUUSD,EURUSD,...")
SYMBOLS = [s.strip().upper() for s in os.environ.get(
    "NY_SYMBOLS", "USDJPY,CADJPY,XAUUSD,XBRUSD,GBPJPY,EURUSD"
).split(",") if s.strip()]

# TF nécessaires session NY, top-down SMC/ICT (modifiable via NY_TIMEFRAMES)
TIMEFRAMES = [t.strip().upper() for t in os.environ.get(
    "NY_TIMEFRAMES", "D1,H4,M15,M5"
).split(",") if t.strip()]

# 07:00 UTC = 3h00 Guadeloupe (UTC-4 fixe). Surcharge : NY_RUN_HOUR_UTC.
RUN_HOUR_UTC = int(os.environ.get("NY_RUN_HOUR_UTC", "7"))
RUN_MINUTE_UTC = int(os.environ.get("NY_RUN_MINUTE_UTC", "0"))
# Jours ouvrés uniquement (marché fermé le week-end). NY_WEEKDAYS_ONLY=0 → 7/7.
WEEKDAYS_ONLY = os.environ.get("NY_WEEKDAYS_ONLY", "1") != "0"

REPORTS_DIR = REPO_ROOT / "data" / "ny_reports"

CAPTURE_TIMEOUT = 150      # s (Puppeteer, multi-TF)
ANALYZE_TIMEOUT = 210      # s (Claude Vision)
NOTIFY_TIMEOUT = 30        # s


# ── Secret partagé (env, sinon backend/.env) ─────────────────────────────────

def _load_secret() -> str:
    secret = os.environ.get("N8N_WEBHOOK_SECRET")
    if secret:
        return secret
    env_file = REPO_ROOT / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("N8N_WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


N8N_SECRET = _load_secret()


# ── HTTP (stdlib) ────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} sur {url} : {detail[:300]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connexion échouée sur {url} : {e.reason} "
                           f"(le service est-il lancé ?)") from None


def _secret_header() -> dict:
    if not N8N_SECRET:
        raise RuntimeError(
            "N8N_WEBHOOK_SECRET manquant : renseigne-le dans l'environnement ou "
            "dans backend/.env (même valeur que celle attendue par le backend)."
        )
    return {"X-N8N-Secret": N8N_SECRET}


# ── Étapes du pipeline ───────────────────────────────────────────────────────

def capture_set(symbol: str) -> list[dict]:
    """POST /capture-set → [{timeframe, media_type, data(base64)}]."""
    res = _post_json(
        f"{SCREENSHOT_URL}/capture-set",
        {"symbol": symbol, "timeframes": TIMEFRAMES},
        timeout=CAPTURE_TIMEOUT,
    )
    images = res.get("images") or []
    if res.get("errors"):
        for err in res["errors"]:
            print(f"    ⚠️  capture {symbol} {err.get('timeframe')}: {err.get('error')}")
    if not images:
        raise RuntimeError(f"aucune capture réussie pour {symbol}")
    return images


def analyze_raw(symbol: str, images: list[dict]) -> dict:
    """POST /api/vision/analyze-raw → analyse structurée + telegram_text."""
    return _post_json(
        f"{BACKEND_URL}/api/vision/analyze-raw",
        {
            "symbol": symbol,
            "images": images,
            "context": ("Prep automatique session NY 3h Guadeloupe (orchestrateur local). "
                        "Vérifier le blackout news du jour avant toute exécution."),
        },
        headers=_secret_header(),
        timeout=ANALYZE_TIMEOUT,
    )


def notify_telegram(text: str) -> bool:
    """POST /api/n8n/notify/telegram — best-effort (n'interrompt pas la passe)."""
    try:
        _post_json(
            f"{BACKEND_URL}/api/n8n/notify/telegram",
            {"text": text},
            headers=_secret_header(),
            timeout=NOTIFY_TIMEOUT,
        )
        return True
    except RuntimeError as e:
        print(f"    ⚠️  Telegram non envoyé : {e}")
        return False


def save_report(symbol: str, result: dict) -> Path:
    """Sauvegarde le rapport (Markdown + JSON brut) sous data/ny_reports/<date>/."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = REPORTS_DIR / day
    out_dir.mkdir(parents=True, exist_ok=True)
    text = result.get("telegram_text") or json.dumps(result, ensure_ascii=False, indent=2)
    md_path = out_dir / f"{symbol}.md"
    md_path.write_text(text, encoding="utf-8")
    (out_dir / f"{symbol}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path


# ── Passe complète ───────────────────────────────────────────────────────────

def run_once(symbols: list[str], send_telegram: bool = True) -> int:
    """Exécute la chaîne pour chaque symbole. Retourne le nombre d'échecs."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n═══ Prep session NY — {stamp} ═══")
    print(f"    Symboles : {', '.join(symbols)}")
    print(f"    TF       : {', '.join(TIMEFRAMES)}")
    failures = 0

    for symbol in symbols:
        print(f"\n▶ {symbol}")
        try:
            print("  📸 capture multi-TF…")
            images = capture_set(symbol)
            print(f"     {len(images)} capture(s) OK")

            print("  🤖 analyse vision…")
            result = analyze_raw(symbol, images)

            path = save_report(symbol, result)
            grade = result.get("grade") or result.get("action", {}).get("grade") or "?"
            bias = result.get("bias") or result.get("direction") or "?"
            print(f"     grade={grade} · biais={bias} · rapport → {path.relative_to(REPO_ROOT)}")

            if send_telegram and result.get("telegram_text"):
                if notify_telegram(result["telegram_text"]):
                    print("  📣 Telegram envoyé")
        except RuntimeError as e:
            failures += 1
            print(f"  ❌ {symbol} : {e}")

    ok = len(symbols) - failures
    print(f"\n═══ Terminé : {ok}/{len(symbols)} OK, {failures} échec(s) ═══")
    return failures


# ── Planificateur (mode daemon) ──────────────────────────────────────────────

def _seconds_until_next_run() -> tuple[float, datetime]:
    now = datetime.now(timezone.utc)
    target = now.replace(hour=RUN_HOUR_UTC, minute=RUN_MINUTE_UTC, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    while WEEKDAYS_ONLY and target.weekday() >= 5:  # 5=samedi, 6=dimanche
        target += timedelta(days=1)
    return (target - now).total_seconds(), target


def run_daemon() -> None:
    print("🟢 Orchestrateur prep NY (local) démarré.")
    print(f"   Déclenchement : {RUN_HOUR_UTC:02d}:{RUN_MINUTE_UTC:02d} UTC "
          f"= 3h Guadeloupe, {'jours ouvrés' if WEEKDAYS_ONLY else '7/7'}.")
    print(f"   Screenshot : {SCREENSHOT_URL}   Backend : {BACKEND_URL}")
    print("   Ctrl+C pour arrêter.\n")
    while True:
        delay, target = _seconds_until_next_run()
        print(f"⏳ Prochaine passe : {target.strftime('%Y-%m-%d %H:%M UTC')} "
              f"(dans {delay / 3600:.1f} h)")
        remaining = delay
        try:
            while remaining > 0:
                chunk = min(remaining, 3600)
                time.sleep(chunk)
                remaining -= chunk
        except KeyboardInterrupt:
            print("\n🛑 Arrêt demandé.")
            return
        try:
            run_once(SYMBOLS)
        except KeyboardInterrupt:
            print("\n🛑 Arrêt demandé.")
            return
        except Exception as e:  # ne jamais tuer le daemon sur une passe ratée
            print(f"❌ Passe échouée : {e}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Orchestrateur local prep session NY (sans n8n).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--daemon", action="store_true", help="Tourne en continu (défaut).")
    group.add_argument("--once", action="store_true", help="Une passe immédiate puis sort.")
    parser.add_argument("--symbol", help="Ne traite qu'un symbole (test manuel).")
    parser.add_argument("--no-telegram", action="store_true", help="N'envoie pas sur Telegram.")
    args = parser.parse_args()

    if args.symbol:
        return 1 if run_once([args.symbol.upper()], send_telegram=not args.no_telegram) else 0
    if args.once:
        return 1 if run_once(SYMBOLS, send_telegram=not args.no_telegram) else 0
    run_daemon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
