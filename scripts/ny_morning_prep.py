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

# Filtrage Telegram : n'alerte que les setups de grade >= NY_MIN_GRADE.
# Ordre croissant D < C < B < A < A+. "ALL" = tout envoyer.
# ⚠️ Le filtre ne concerne QUE Telegram : les 6 rapports sont TOUJOURS sauvegardés en local.
GRADE_ORDER = ["D", "C", "B", "A", "A+"]
MIN_GRADE = os.environ.get("NY_MIN_GRADE", "A").strip().upper()
if MIN_GRADE != "ALL" and MIN_GRADE not in GRADE_ORDER:
    print(f"⚠️  NY_MIN_GRADE='{MIN_GRADE}' invalide → 'A' par défaut (valeurs : A+, A, B, C, D, ALL)")
    MIN_GRADE = "A"

# Blackout news : détecte les news du jour à fort impact sur les devises du symbole
# (via le calendrier économique du backend). NY_NEWS_BLACKOUT=0 pour désactiver.
NEWS_BLACKOUT = os.environ.get("NY_NEWS_BLACKOUT", "1") != "0"
# Niveaux d'impact considérés comme blackout (défaut High ; ex : "High,Medium").
NEWS_IMPACT = [s.strip().capitalize() for s in os.environ.get("NY_NEWS_IMPACT", "High").split(",") if s.strip()]
# Mute : ne PAS envoyer sur Telegram un symbole en blackout (défaut 0 = juste annoter).
BLACKOUT_MUTE = os.environ.get("NY_BLACKOUT_MUTE", "0") != "0"

# Récapitulatif global : un message/rapport unique synthétisant les N symboles en
# fin de passe (trié par grade). NON soumis au filtre grade. NY_RECAP=0 pour désactiver.
RECAP = os.environ.get("NY_RECAP", "1") != "0"

# Devises concernées par symbole ; métaux/pétrole/indices → USD (pilotés par l'USD).
SYMBOL_CURRENCIES = {
    "XAUUSD": ["USD"], "XAGUSD": ["USD"], "XBRUSD": ["USD"],
    "XTIUSD": ["USD"], "US30": ["USD"], "BTCUSD": ["USD"],
}

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


def _get_json(url: str, headers: dict | None = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
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


BASE_CONTEXT = ("Prep automatique session NY 3h Guadeloupe (orchestrateur local). "
                "Vérifier le blackout news du jour avant toute exécution.")


def analyze_raw(symbol: str, images: list[dict], context: str | None = None) -> dict:
    """POST /api/vision/analyze-raw → analyse structurée + telegram_text."""
    return _post_json(
        f"{BACKEND_URL}/api/vision/analyze-raw",
        {"symbol": symbol, "images": images, "context": context or BASE_CONTEXT},
        headers=_secret_header(),
        timeout=ANALYZE_TIMEOUT,
    )


# ── Blackout news (calendrier économique) ────────────────────────────────────

def symbol_currencies(symbol: str) -> list[str]:
    """Devises dont les news impactent le symbole (FX = 2 devises, sinon override)."""
    s = symbol.upper()
    if s in SYMBOL_CURRENCIES:
        return SYMBOL_CURRENCIES[s]
    if len(s) == 6 and s.isalpha():
        return [s[:3], s[3:]]
    return [s]


def fetch_calendar() -> list[dict] | None:
    """Récupère les news du jour (impact NEWS_IMPACT). None si désactivé/indisponible."""
    if not NEWS_BLACKOUT:
        return None
    url = f"{BACKEND_URL}/api/n8n/calendar/today?impact={','.join(NEWS_IMPACT)}"
    try:
        res = _get_json(url, headers=_secret_header(), timeout=30)
        return res.get("events") or []
    except RuntimeError as e:
        print(f"⚠️  Calendrier indisponible ({e}) → blackout ignoré cette passe.")
        return None


def blackout_events_for(symbol: str, events: list[dict] | None) -> list[dict]:
    """Sous-ensemble des news dont la devise concerne le symbole."""
    if not events:
        return []
    curs = {c.upper() for c in symbol_currencies(symbol)}
    return [e for e in events if str(e.get("currency", "")).upper() in curs]


def _format_news(events: list[dict]) -> str:
    return "; ".join(
        f"{e.get('time', '?')} {e.get('currency', '?')} {e.get('event', '?')} [{e.get('impact', '?')}]"
        for e in events
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


def _summary_fields(result: dict) -> tuple[str, str, str]:
    """Extrait (grade, action, biais lisible) du contrat réel analyze-raw.

    Contrat : grade ∈ {A+,A,B,C,D} (top-level), action ∈ {LONG,SHORT,WAIT,SKIP},
    bias = objet {direction, score, summary}. Tolère aussi une forme aplatie.
    """
    grade = str(result.get("grade") or "?").upper()
    action = str(result.get("action") or "?").upper()
    bias = result.get("bias")
    if isinstance(bias, dict):
        bias_str = f"{bias.get('direction', '?')} {bias.get('score', '')}".strip()
    else:
        bias_str = str(bias or result.get("direction") or "?")
    return grade, action, bias_str


def passes_grade_filter(grade: str) -> bool:
    """True si le grade atteint le seuil NY_MIN_GRADE (Telegram).

    Fail-open : un grade non reconnu passe le filtre (on préfère notifier à tort
    plutôt que rater un vrai setup à cause d'un aléa de parsing).
    """
    if MIN_GRADE == "ALL":
        return True
    if grade not in GRADE_ORDER:
        return True
    return GRADE_ORDER.index(grade) >= GRADE_ORDER.index(MIN_GRADE)


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


# ── Récapitulatif global ─────────────────────────────────────────────────────

_GRADE_EMOJI = {"A+": "🟢", "A": "🟢", "B": "🟡", "C": "🔴", "D": "🔴"}


def _recap_sort_key(row: dict) -> int:
    """Tri : meilleurs grades d'abord, échecs en dernier."""
    if not row.get("ok"):
        return -1
    g = row.get("grade", "?")
    return GRADE_ORDER.index(g) if g in GRADE_ORDER else 0


def build_recap(rows: list[dict], date: str) -> str:
    """Construit le message récap HTML (un coup d'œil sur les N symboles)."""
    ok_rows = [r for r in rows if r.get("ok")]
    n_bo = sum(1 for r in ok_rows if r.get("blackout"))
    lines = [
        f"📋 <b>Récap prep NY — {date}</b>",
        f"{len(rows)} symbole(s) · {len(ok_rows)} analysé(s) · {n_bo} blackout",
        "",
    ]
    for r in sorted(rows, key=_recap_sort_key, reverse=True):
        if not r.get("ok"):
            lines.append(f"❌ <b>{r['symbol']}</b> — échec ({r.get('error', 'inconnu')})")
            continue
        emoji = _GRADE_EMOJI.get(r["grade"], "⚪")
        bo = " 🚫" if r.get("blackout") else ""
        lines.append(f"{emoji} <b>{r['grade']:2}</b> {r['symbol']:7} {r['action']:5} ({r['bias']}){bo}")
    return "\n".join(lines)


def save_recap(text: str, date: str) -> Path:
    out_dir = REPORTS_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "_RECAP.md"
    path.write_text(text, encoding="utf-8")
    return path


# ── Passe complète ───────────────────────────────────────────────────────────

def run_once(symbols: list[str], send_telegram: bool = True) -> int:
    """Exécute la chaîne pour chaque symbole. Retourne le nombre d'échecs."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n═══ Prep session NY — {stamp} ═══")
    print(f"    Symboles : {', '.join(symbols)}")
    print(f"    TF       : {', '.join(TIMEFRAMES)}")
    tg_mode = "OFF" if not send_telegram else ("ALL" if MIN_GRADE == "ALL" else f"grade ≥ {MIN_GRADE}")
    print(f"    Telegram : {tg_mode}   (les rapports locaux ne sont jamais filtrés)")

    # Calendrier récupéré UNE fois pour toute la passe.
    events = fetch_calendar()
    if NEWS_BLACKOUT:
        n = len(events) if events is not None else 0
        mode = "mute" if BLACKOUT_MUTE else "annotation"
        print(f"    Blackout : {', '.join(NEWS_IMPACT)} — {n} news aujourd'hui, mode {mode}")

    failures = sent = filtered = blackout = 0
    recap_rows: list[dict] = []

    for symbol in symbols:
        print(f"\n▶ {symbol}")
        try:
            print("  📸 capture multi-TF…")
            images = capture_set(symbol)
            print(f"     {len(images)} capture(s) OK")

            bo = blackout_events_for(symbol, events)
            context = BASE_CONTEXT
            if bo:
                blackout += 1
                news = _format_news(bo)
                curs = ", ".join(sorted({e.get("currency", "?") for e in bo}))
                context = (f"{BASE_CONTEXT}\n⚠️ BLACKOUT NEWS AUJOURD'HUI ({curs}) : {news}. "
                           "Intègre ce risque : si l'entrée tombe autour de ces horaires, "
                           "privilégier WAIT et abaisser le grade.")

            print("  🤖 analyse vision…")
            result = analyze_raw(symbol, images, context=context)

            # Bannière blackout en tête du rapport ET du message Telegram.
            if bo and result.get("telegram_text"):
                result["telegram_text"] = f"🚫 <b>BLACKOUT NEWS</b> — {_format_news(bo)}\n\n{result['telegram_text']}"

            path = save_report(symbol, result)
            grade, action, bias = _summary_fields(result)
            recap_rows.append({"symbol": symbol, "ok": True, "grade": grade,
                               "action": action, "bias": bias, "blackout": bool(bo)})
            tag = "  · 🚫 BLACKOUT" if bo else ""
            print(f"     grade={grade} · action={action} · biais={bias} "
                  f"· rapport → {path.relative_to(REPO_ROOT)}{tag}")

            if not (send_telegram and result.get("telegram_text")):
                pass
            elif bo and BLACKOUT_MUTE:
                print(f"  🔕 Telegram ignoré (blackout news, mode mute) — {_format_news(bo)}")
                filtered += 1
            elif passes_grade_filter(grade):
                if notify_telegram(result["telegram_text"]):
                    print(f"  📣 Telegram envoyé (grade {grade}{', 🚫 blackout' if bo else ''})")
                    sent += 1
            else:
                print(f"  🔕 Telegram ignoré (grade {grade} < seuil {MIN_GRADE})")
                filtered += 1
        except RuntimeError as e:
            failures += 1
            recap_rows.append({"symbol": symbol, "ok": False, "error": str(e)[:60]})
            print(f"  ❌ {symbol} : {e}")

    # ── Récapitulatif global (1 message/rapport, non filtré par grade) ──────────
    if RECAP and len(symbols) > 1 and recap_rows:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        recap = build_recap(recap_rows, day)
        rpath = save_recap(recap, day)
        print(f"\n📋 Récap → {rpath.relative_to(REPO_ROOT)}")
        if send_telegram and notify_telegram(recap):
            print("  📣 Récap envoyé sur Telegram")

    ok = len(symbols) - failures
    tg = "OFF" if not send_telegram else f"{sent} envoyé(s), {filtered} filtré(s) (seuil {MIN_GRADE})"
    bo_txt = f" · blackout {blackout}" if NEWS_BLACKOUT else ""
    print(f"\n═══ Terminé : {ok}/{len(symbols)} analysés, {failures} échec(s) "
          f"· rapports {ok}/{len(symbols)} · Telegram {tg}{bo_txt} ═══")
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
    print(f"   Filtre Telegram : {'ALL' if MIN_GRADE == 'ALL' else f'grade ≥ {MIN_GRADE}'} "
          f"(rapports locaux non filtrés).")
    if NEWS_BLACKOUT:
        print(f"   Blackout news : impact {', '.join(NEWS_IMPACT)}, "
              f"mode {'mute' if BLACKOUT_MUTE else 'annotation'}.")
    else:
        print("   Blackout news : désactivé.")
    print(f"   Récap global : {'activé' if RECAP else 'désactivé'}.")
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
