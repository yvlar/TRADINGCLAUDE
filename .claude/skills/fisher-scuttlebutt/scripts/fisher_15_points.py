#!/usr/bin/env python3
"""
fisher_15_points.py — Évaluation des 15 points Fisher

Présente les 15 points de Fisher pour scoring qualitatif et flagge
les éléments éliminatoires.

Usage:
  python fisher_15_points.py inputs.json

Format JSON:
{
  "ticker": "CSU.TO",
  "scores": {
    "1_growth_potential": 4,
    "2_new_products_intent": 5,
    ...
    "14_management_franchise_problems": 5,
    "15_management_integrity": 5
  }
}
Chaque score: 1-5 (1=très mauvais, 5=excellent). Mettre null si pas évalué.
"""

import json
import sys


POINTS = [
    (1, "Potentiel de croissance du marché", False),
    (2, "Volonté de développer nouveaux produits", False),
    (3, "Efficacité de la R&D", False),
    (4, "Organisation commerciale", False),
    (5, "Marges bénéficiaires", False),
    (6, "Effort pour maintenir/améliorer les marges", False),
    (7, "Relations direction-personnel", False),
    (8, "Profondeur de l'équipe exécutive", False),
    (9, "Profondeur du middle management", False),
    (10, "Contrôle des coûts et comptable", False),
    (11, "Facteurs spécifiques à l'industrie", False),
    (12, "Vision long-terme vs court-terme", False),
    (13, "Besoin de capital nouveau (dilution)", False),
    (14, "Communication franche en cas de problème", True),  # ÉLIMINATOIRE
    (15, "Intégrité de la direction", True),  # ÉLIMINATOIRE
]


def evaluate(data: dict) -> dict:
    """Évalue les 15 points et retourne verdict global."""
    scores = data.get("scores", {})
    results = []
    eliminatoire_failed = False

    for num, label, is_critical in POINTS:
        key = next((k for k in scores if k.startswith(f"{num}_")), None)
        score = scores.get(key) if key else None
        is_passed = score is not None and score >= 3
        if is_critical and (score is None or score < 4):
            eliminatoire_failed = True

        results.append({
            "num": num,
            "label": label,
            "score": score,
            "is_critical": is_critical,
            "is_passed": is_passed,
        })

    valid_scores = [r["score"] for r in results if r["score"] is not None]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    passed_count = sum(1 for r in results if r["is_passed"])

    if eliminatoire_failed:
        verdict = "❌ REFUS — Échec sur point éliminatoire (14 ou 15)"
    elif avg_score >= 4 and passed_count >= 12:
        verdict = "✅ EXCELLENT — qualité Fisher"
    elif avg_score >= 3.5 and passed_count >= 10:
        verdict = "🟡 ACCEPTABLE — investiguer davantage"
    else:
        verdict = "❌ INSUFFISANT pour profil Fisher"

    return {
        "ticker": data.get("ticker", "?"),
        "results": results,
        "avg_score": round(avg_score, 2),
        "passed_count": passed_count,
        "evaluated_count": len(valid_scores),
        "verdict": verdict,
        "eliminatoire_failed": eliminatoire_failed,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    r = evaluate(data)

    print("=" * 78)
    print(f"15 POINTS FISHER — {r['ticker']}")
    print("=" * 78)

    for res in r["results"]:
        marker = "🔴" if res["is_critical"] else "  "
        score_str = f"{res['score']}/5" if res["score"] is not None else "N/A"
        passed = "✓" if res["is_passed"] else "✗"
        print(f"{marker} {res['num']:2d}. {res['label']:<45s} {score_str:>5s}  {passed}")

    print(f"\n{'─' * 78}")
    print(f"Score moyen      : {r['avg_score']}/5")
    print(f"Points passés     : {r['passed_count']}/{r['evaluated_count']}")
    print(f"\n{r['verdict']}")

    if r["eliminatoire_failed"]:
        print("\n⚠ Les points 14 (communication franche) et 15 (intégrité) sont")
        print("   ÉLIMINATOIRES selon Fisher. Refuser indépendamment du reste.")


if __name__ == "__main__":
    main()
