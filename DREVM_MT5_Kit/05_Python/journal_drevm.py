#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
journal_drevm.py — saasDrevmBot / DREVM_MT5_Kit
================================================
Journal des decisions DISCRETIONNAIRES sur les alertes de l'EA.

OBJECTIF (etabli lors de l'audit quantitatif de juillet 2026) :
  Le moteur automatique n'a pas d'edge mesurable. La question ouverte est :
  TON tri manuel des alertes en a-t-il un ?
  Ce journal capture chaque decision pour pouvoir rejouer, a ~40-50 trades,
  exactement les memes tests que sur l'EA :
    - expectancy des alertes PRISES vs REFUSEES
    - discrimination de TES grades (A+ humain bat-il B humain ?)
    - comparaison contre la baseline alertes brutes

REGLES DE SAISIE (sinon l'analyse future sera fausse) :
  1. Saisir CHAQUE alerte, y compris celles refusees.
  2. Donner ton grade AVANT de connaitre le resultat.
  3. Renseigner le resultat des alertes REFUSEES aussi (ce qu'aurait donne
     le trade) : c'est la seule facon de mesurer la valeur de ton filtre.
  4. Resultat toujours en R (multiple du risque initial), pas en dollars.

Stdlib uniquement (Python 3.8+) — tourne sur VPS Windows et Termux.
Fichier de donnees : journal_trades.csv (cree a cote du script, ou --fichier).

USAGE
  python journal_drevm.py add                    # saisie interactive (defaut)
  python journal_drevm.py add --rapide XAUUSD BUY A 61.8   # saisie eclair
  python journal_drevm.py close 12 --r 2.5      # cloturer le trade n.12
  python journal_drevm.py close 13 --r -1 --refuse   # resultat hypothetique d'un refus
  python journal_drevm.py list                   # trades ouverts + recents
  python journal_drevm.py stats                  # LE verdict : ton edge existe-t-il ?
  python journal_drevm.py export                 # CSV pret pour les scripts d'analyse
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone, timedelta

# Guadeloupe UTC-4, pas de DST
TZ_GP = timezone(timedelta(hours=-4))

CHAMPS = [
    "id", "horodatage", "symbole", "timeframe", "sens",
    "grade_ea", "score_ea",          # ce que l'EA a annonce
    "decision",                       # prise | refusee
    "grade_humain",                   # TON grade, donne AVANT le resultat
    "confluences",                    # texte libre court: "sweep+OB H1, kijun M15"
    "raison_refus",                   # si refusee : pourquoi
    "entry", "sl", "tp",
    "statut",                         # ouvert | clos
    "resultat_R",                     # en R ; pour une refusee = hypothetique
    "notes",
]

GRADES = ["A+", "A", "B", "C", "D"]
SYMBOLES = ["XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"]
SEUIL_VERDICT = 40   # nombre de trades clos avant verdict


# ---------------------------------------------------------------- fichier
def chemin_defaut():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "journal_trades.csv")


def charger(fichier):
    if not os.path.exists(fichier):
        return []
    with open(fichier, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sauver(fichier, lignes):
    tmp = fichier + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for l in lignes:
            w.writerow({k: l.get(k, "") for k in CHAMPS})
    os.replace(tmp, fichier)          # ecriture atomique


# ---------------------------------------------------------------- saisie
def demander(question, choix=None, defaut=None, vide_ok=False):
    suffixe = f" [{'/'.join(choix)}]" if choix else ""
    if defaut is not None:
        suffixe += f" (defaut {defaut})"
    while True:
        rep = input(f"  {question}{suffixe}: ").strip()
        if not rep:
            if defaut is not None:
                return defaut
            if vide_ok:
                return ""
            continue
        if choix and rep.upper() not in [c.upper() for c in choix]:
            print(f"    -> valeur attendue: {', '.join(choix)}")
            continue
        if choix:
            for c in choix:
                if c.upper() == rep.upper():
                    return c
        return rep


def cmd_add(args, fichier):
    lignes = charger(fichier)
    nid = 1 + max((int(l["id"]) for l in lignes), default=0)

    if args.rapide:
        sym, sens, grade_h, entry = (args.rapide + [None] * 4)[:4]
        ligne = dict(
            id=str(nid),
            horodatage=datetime.now(TZ_GP).strftime("%Y-%m-%d %H:%M"),
            symbole=(sym or "").upper(), timeframe=args.tf or "M5",
            sens=(sens or "").upper(),
            grade_ea=args.grade_ea or "", score_ea=args.score_ea or "",
            decision="prise", grade_humain=(grade_h or "").upper(),
            confluences=args.confluences or "", raison_refus="",
            entry=entry or "", sl=args.sl or "", tp=args.tp or "",
            statut="ouvert", resultat_R="", notes=args.notes or "",
        )
    else:
        print("\n\U0001f4dd Nouvelle alerte — reponses courtes, Entree = defaut")
        sym = demander("Symbole", SYMBOLES)
        sens = demander("Sens", ["BUY", "SELL"])
        tf = demander("Timeframe", ["M5", "M15", "H1", "H4"], defaut="M5")
        gea = demander("Grade annonce par l'EA", GRADES + [""], vide_ok=True)
        dec = demander("Decision", ["prise", "refusee"])
        ligne = dict(
            id=str(nid),
            horodatage=datetime.now(TZ_GP).strftime("%Y-%m-%d %H:%M"),
            symbole=sym, timeframe=tf, sens=sens,
            grade_ea=gea, score_ea=demander("Score EA (x/5)", vide_ok=True),
            decision=dec,
            grade_humain=demander("TON grade (avant resultat !)", GRADES),
            confluences=demander("Confluences vues (court)", vide_ok=True),
            raison_refus=(demander("Raison du refus", vide_ok=True)
                          if dec == "refusee" else ""),
            entry=demander("Entry", vide_ok=True),
            sl=demander("SL", vide_ok=True),
            tp=demander("TP", vide_ok=True),
            statut="ouvert", resultat_R="",
            notes=demander("Notes", vide_ok=True),
        )

    lignes.append(ligne)
    sauver(fichier, lignes)
    tag = "\U0001f7e2 PRISE" if ligne["decision"] == "prise" else "\U0001f534 REFUSEE"
    print(f"\n\u2705 #{nid} {ligne['symbole']} {ligne['sens']} "
          f"[{ligne['grade_humain']}] {tag} — enregistree.")
    if ligne["decision"] == "refusee":
        print("   \u26a0\ufe0f  Pense a cloturer ce refus avec son resultat hypothetique :")
        print(f"      python journal_drevm.py close {nid} --r <R> --refuse")


def cmd_close(args, fichier):
    lignes = charger(fichier)
    for l in lignes:
        if l["id"] == str(args.id):
            if l["statut"] == "clos" and not args.force:
                sys.exit(f"\u274c #{args.id} deja clos (resultat {l['resultat_R']}R). "
                         "--force pour ecraser.")
            if args.refuse and l["decision"] != "refusee":
                print("  \u2139\ufe0f  --refuse ignore : ce trade etait pris.")
            l["resultat_R"] = f"{args.r:+.2f}"
            l["statut"] = "clos"
            if args.note:
                l["notes"] = (l["notes"] + " | " if l["notes"] else "") + args.note
            sauver(fichier, lignes)
            hypo = " (hypothetique)" if l["decision"] == "refusee" else ""
            print(f"\u2705 #{args.id} clos a {args.r:+.2f}R{hypo}.")
            return
    sys.exit(f"\u274c id {args.id} introuvable.")


# ---------------------------------------------------------------- affichage
def cmd_list(args, fichier):
    lignes = charger(fichier)
    if not lignes:
        print("Journal vide. Commence avec: python journal_drevm.py add")
        return
    ouverts = [l for l in lignes if l["statut"] == "ouvert"]
    recents = [l for l in lignes if l["statut"] == "clos"][-args.n:]
    if ouverts:
        print(f"\n\U0001f7e1 OUVERTS ({len(ouverts)}) — a cloturer :")
        for l in ouverts:
            tag = "PRISE " if l["decision"] == "prise" else "REFUS "
            print(f"  #{l['id']:>3} {l['horodatage']} {l['symbole']:<7} "
                  f"{l['sens']:<4} [{l['grade_humain']}] {tag} {l['confluences'][:38]}")
    if recents:
        print(f"\n\U0001f4d8 DERNIERS CLOS :")
        for l in recents:
            r = float(l["resultat_R"] or 0)
            ico = "\u2705" if r > 0 else "\u274c"
            hypo = "*" if l["decision"] == "refusee" else " "
            print(f"  #{l['id']:>3} {l['symbole']:<7} {l['sens']:<4} "
                  f"[{l['grade_humain']}]{hypo} {r:+.2f}R {ico}")
    if any(l["decision"] == "refusee" for l in recents):
        print("  (* = resultat hypothetique d'une alerte refusee)")


# ---------------------------------------------------------------- stats
def _bloc(rs):
    if not rs:
        return None
    n = len(rs)
    exp = sum(rs) / n
    wr = sum(1 for r in rs if r > 0) / n
    g = sum(r for r in rs if r > 0)
    p = -sum(r for r in rs if r < 0)
    pf = (g / p) if p > 0 else float("inf")
    return n, wr, exp, pf


def _ligne(label, b):
    if b is None:
        return f"    {label:<14} —"
    n, wr, exp, pf = b
    return (f"    {label:<14} n={n:<4d} WR={wr*100:5.1f}%  "
            f"exp={exp:+.3f}R  PF={pf:.2f}")


def cmd_stats(args, fichier):
    lignes = charger(fichier)
    clos = [l for l in lignes if l["statut"] == "clos" and l["resultat_R"]]
    if not clos:
        print("Aucun trade clos — pas encore de stats.")
        return
    R = lambda ls: [float(l["resultat_R"]) for l in ls]
    prises = [l for l in clos if l["decision"] == "prise"]
    refus = [l for l in clos if l["decision"] == "refusee"]
    toutes = clos

    print(f"\n\U0001f4ca JOURNAL DREVM — {len(clos)} decisions cloturees "
          f"({len(prises)} prises / {len(refus)} refusees)")
    print("=" * 64)
    print("  1) TON FILTRE A-T-IL DE LA VALEUR ?")
    print(_ligne("prises", _bloc(R(prises))))
    print(_ligne("refusees*", _bloc(R(refus))))
    print(_ligne("alertes brutes", _bloc(R(toutes))))
    bp, br = _bloc(R(prises)), _bloc(R(refus))
    if bp and br:
        d = bp[2] - br[2]
        print(f"    \u0394 prises - refusees = {d:+.3f}R  "
              f"{'\u2705 ton tri ajoute de la valeur' if d > 0.05 else ('\u274c ton tri detruit de la valeur' if d < -0.05 else '\u2696\ufe0f indecis')}")
    elif not refus:
        print("    \u26a0\ufe0f  Aucune refusee cloturee : impossible de mesurer ton filtre.")
        print("       Renseigne le resultat hypothetique des refus (close --refuse).")

    print("\n  2) TES GRADES DISCRIMINENT-ILS ? (prises uniquement)")
    for g in GRADES:
        print(_ligne(f"grade {g}", _bloc(R([l for l in prises
                                            if l["grade_humain"] == g]))))
    exps = [(_bloc(R([l for l in prises if l["grade_humain"] == g])) or (0, 0, None, 0))[2]
            for g in GRADES]
    exps = [e for e in exps if e is not None]
    if len(exps) >= 2:
        mono = all(exps[i] >= exps[i + 1] for i in range(len(exps) - 1))
        print(f"    monotonie A+ \u2265 ... \u2265 D : {'\u2705' if mono else '\u274c'}")

    print("\n  3) PAR INSTRUMENT (prises)")
    for s in SYMBOLES:
        b = _bloc(R([l for l in prises if l["symbole"] == s]))
        if b:
            print(_ligne(s, b))

    n_tot = len(clos)
    print("\n" + "=" * 64)
    if n_tot < SEUIL_VERDICT:
        print(f"  \u23f3 {n_tot}/{SEUIL_VERDICT} decisions — verdict statistique a "
              f"{SEUIL_VERDICT}. Continue la collecte, ne change rien en route.")
    else:
        print(f"  \U0001f3af {n_tot} decisions : echantillon suffisant pour l'analyse "
              "complete (permutation, controle horaire). Exporte et envoie a Claude :")
        print("     python journal_drevm.py export")


def cmd_export(args, fichier):
    lignes = charger(fichier)
    clos = [l for l in lignes if l["statut"] == "clos" and l["resultat_R"]]
    if not clos:
        sys.exit("Rien a exporter.")
    out = args.sortie or fichier.replace(".csv", "_export.csv")
    # format aligne sur les colonnes des scripts d'analyse (resultat_R, grade...)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "symbole", "timeframe", "sens", "decision",
                    "grade", "grade_ea", "resultat_R", "confluences"])
        for l in clos:
            w.writerow([l["horodatage"], l["symbole"], l["timeframe"],
                        l["sens"], l["decision"], l["grade_humain"],
                        l["grade_ea"], l["resultat_R"], l["confluences"]])
    print(f"\u2705 {len(clos)} decisions exportees -> {out}")


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Journal discretionnaire DREVM")
    p.add_argument("--fichier", default=None, help="CSV du journal (defaut: a cote du script)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add", help="enregistrer une alerte/decision")
    pa.add_argument("--rapide", nargs="*", metavar="X",
                    help="saisie eclair: SYMBOLE SENS GRADE [ENTRY]")
    pa.add_argument("--tf", default=None)
    pa.add_argument("--grade-ea", default=None)
    pa.add_argument("--score-ea", default=None)
    pa.add_argument("--confluences", default=None)
    pa.add_argument("--sl", default=None)
    pa.add_argument("--tp", default=None)
    pa.add_argument("--notes", default=None)

    pc = sub.add_parser("close", help="cloturer avec le resultat en R")
    pc.add_argument("id", type=int)
    pc.add_argument("--r", type=float, required=True,
                    help="resultat en R (ex: 2.5, -1, 0.4)")
    pc.add_argument("--refuse", action="store_true",
                    help="marque un resultat HYPOTHETIQUE d'alerte refusee")
    pc.add_argument("--note", default=None)
    pc.add_argument("--force", action="store_true")

    pl = sub.add_parser("list", help="trades ouverts + recents")
    pl.add_argument("-n", type=int, default=10)

    sub.add_parser("stats", help="le verdict : ton edge existe-t-il ?")

    pe = sub.add_parser("export", help="CSV pour les scripts d'analyse")
    pe.add_argument("--sortie", default=None)

    args = p.parse_args()
    fichier = args.fichier or chemin_defaut()
    {"add": cmd_add, "close": cmd_close, "list": cmd_list,
     "stats": cmd_stats, "export": cmd_export}[args.cmd](args, fichier)


if __name__ == "__main__":
    main()
