#!/usr/bin/env python3
"""
compute_fscore.py — Piotroski F-Score (2000, 9 critères binaires)

Distingue les vraies opportunités value des value traps.
À utiliser sur l'univers des actions à faible P/B (bottom 20%).

Usage:
  python compute_fscore.py
  python compute_fscore.py data.json

Format JSON:
{
  "current": {
    "net_income": 1200,
    "cfo": 1300,
    "total_assets": 50000,
    "long_term_debt": 8000,
    "current_assets": 12000,
    "current_liabilities": 6000,
    "shares_outstanding": 1000,
    "sales": 80000,
    "cogs": 50000
  },
  "previous": {
    ... mêmes champs pour T-1 ...
  }
}

Référence: references/piotroski-f-score.md
"""

import json
import sys
from pathlib import Path


def compute_fscore(curr: dict, prev: dict) -> dict:
    """Calcule le F-Score Piotroski (0-9)."""

    signals = {}

    # PROFITABILITÉ (4 points)
    # 1. ROA > 0
    roa_curr = curr["net_income"] / curr["total_assets"]
    roa_prev = prev["net_income"] / prev["total_assets"]
    signals["1. ROA > 0"] = 1 if roa_curr > 0 else 0

    # 2. CFO > 0
    signals["2. CFO > 0"] = 1 if curr["cfo"] > 0 else 0

    # 3. ROA en hausse
    signals["3. ROA en hausse"] = 1 if roa_curr > roa_prev else 0

    # 4. CFO > Net Income (qualité des accruals)
    signals["4. CFO > NI"] = 1 if curr["cfo"] > curr["net_income"] else 0

    # LEVIER, LIQUIDITÉ, FONDS (3 points)
    # 5. Diminution de la dette LT (ratio LTD/TA en baisse)
    ltd_ta_curr = curr["long_term_debt"] / curr["total_assets"]
    ltd_ta_prev = prev["long_term_debt"] / prev["total_assets"]
    signals["5. Désendettement LT"] = 1 if ltd_ta_curr < ltd_ta_prev else 0

    # 6. Augmentation du current ratio
    cr_curr = curr["current_assets"] / curr["current_liabilities"]
    cr_prev = prev["current_assets"] / prev["current_liabilities"]
    signals["6. Current ratio en hausse"] = 1 if cr_curr > cr_prev else 0

    # 7. Pas d'émission nette d'actions
    signals["7. Pas de dilution"] = 1 if curr["shares_outstanding"] <= prev["shares_outstanding"] else 0

    # EFFICACITÉ OPÉRATIONNELLE (2 points)
    # 8. Marge brute en hausse
    gm_curr = (curr["sales"] - curr["cogs"]) / curr["sales"]
    gm_prev = (prev["sales"] - prev["cogs"]) / prev["sales"]
    signals["8. Marge brute en hausse"] = 1 if gm_curr > gm_prev else 0

    # 9. Asset turnover en hausse
    at_curr = curr["sales"] / curr["total_assets"]
    at_prev = prev["sales"] / prev["total_assets"]
    signals["9. Asset turnover en hausse"] = 1 if at_curr > at_prev else 0

    f_score = sum(signals.values())

    # Verdict
    if f_score >= 8:
        verdict = "FORTE QUALITÉ — candidate value solide"
        flag = "vert"
    elif f_score == 7:
        verdict = "BON — acceptable"
        flag = "vert"
    elif f_score >= 4:
        verdict = "MOYEN — investiguer"
        flag = "jaune"
    else:
        verdict = "QUALITÉ DÉGRADÉE — probable value trap"
        flag = "rouge"

    return {
        "f_score": f_score,
        "max_score": 9,
        "verdict": verdict,
        "flag": flag,
        "signals": signals,
        "details": {
            "ROA_t": round(roa_curr, 4),
            "ROA_t-1": round(roa_prev, 4),
            "Marge brute_t": round(gm_curr, 4),
            "Marge brute_t-1": round(gm_prev, 4),
        },
    }


def interactive_input() -> dict:
    fields = [
        "net_income", "cfo", "total_assets", "long_term_debt",
        "current_assets", "current_liabilities", "shares_outstanding",
        "sales", "cogs"
    ]
    print("=" * 60)
    print("Piotroski F-Score — saisie interactive")
    print("=" * 60)
    print("\nValeurs pour T (exercice courant):\n")
    curr = {f: float(input(f"  {f}: ")) for f in fields}
    print("\nValeurs pour T-1:\n")
    prev = {f: float(input(f"  {f}: ")) for f in fields}
    return {"current": curr, "previous": prev}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"Erreur: fichier introuvable: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            data = json.load(f)
    else:
        data = interactive_input()

    result = compute_fscore(data["current"], data["previous"])

    print("\n" + "=" * 60)
    print(f"F-SCORE = {result['f_score']}/{result['max_score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flag: {result['flag'].upper()}")
    print("=" * 60)
    print("\nSignaux:")
    for k, v in result["signals"].items():
        symbol = "✓" if v == 1 else "✗"
        print(f"  {symbol} {k}")


if __name__ == "__main__":
    main()
