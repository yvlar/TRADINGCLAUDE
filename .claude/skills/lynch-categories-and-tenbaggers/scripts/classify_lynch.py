#!/usr/bin/env python3
"""
classify_lynch.py — Classification d'une action selon les 6 catégories Lynch

Usage:
  python classify_lynch.py inputs.json

Format JSON:
{
  "ticker": "CSU.TO",
  "revenue_growth_5y": 0.18,
  "earnings_growth_5y": 0.22,
  "revenue_volatility": 0.05,
  "operating_margin_trend": "stable",
  "is_in_distress": false,
  "price_to_book": 12.0,
  "asset_value_estimate_vs_market_cap": 0.0
}
"""

import json
import sys


def classify(d: dict) -> dict:
    """Détermine la catégorie Lynch principale."""
    rg = d.get("revenue_growth_5y", 0)
    eg = d.get("earnings_growth_5y", 0)
    rv = d.get("revenue_volatility", 0)
    margin = d.get("operating_margin_trend", "stable")
    distress = d.get("is_in_distress", False)
    pb = d.get("price_to_book", 1)
    asset_ratio = d.get("asset_value_estimate_vs_market_cap", 1.0)

    candidates = []
    rationale = []

    # Asset play (priorité haute si vraie)
    if asset_ratio > 1.5:
        candidates.append(("Asset Play", "high"))
        rationale.append(f"Valeur des actifs > 150% cap. boursière (ratio {asset_ratio:.2f})")

    # Turnaround
    if distress:
        candidates.append(("Turnaround", "high"))
        rationale.append("Détresse récente — turnaround si plan de redressement crédible")

    # Cyclical (volatilité élevée des revenus)
    if rv > 0.20:
        candidates.append(("Cyclical", "high"))
        rationale.append(f"Volatilité revenus élevée ({rv*100:.1f}%) — profil cyclique")

    # Fast Grower (croissance bénéfices > 20% est suffisant, ou revenus > 15%)
    if (eg > 0.20 or rg > 0.15) and not distress and rv < 0.15:
        candidates.append(("Fast Grower", "high"))
        rationale.append(f"Croissance revenus {rg*100:.0f}%/an, bénéfices {eg*100:.0f}%/an — fast grower")

    # Stalwart
    if 0.05 <= rg <= 0.12 and 0.05 <= eg <= 0.15 and not distress and rv < 0.15:
        candidates.append(("Stalwart", "high"))
        rationale.append(f"Croissance stable 5-12%/an, faible volatilité — stalwart")

    # Slow Grower
    if rg < 0.05 and rg >= 0 and not distress:
        candidates.append(("Slow Grower", "high"))
        rationale.append(f"Croissance modeste ({rg*100:.1f}%/an) — slow grower")

    if not candidates:
        candidates.append(("Indéterminé", "low"))
        rationale.append("Profil ambigu — ne correspond clairement à aucune catégorie Lynch")

    return {
        "primary_category": candidates[0][0],
        "confidence": candidates[0][1],
        "all_candidates": candidates,
        "rationale": rationale,
        "metrics_observed": {
            "revenue_growth_5y": f"{rg*100:.1f}%",
            "earnings_growth_5y": f"{eg*100:.1f}%",
            "revenue_volatility": f"{rv*100:.1f}%",
            "operating_margin_trend": margin,
            "in_distress": distress,
        },
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    r = classify(d)

    print("=" * 70)
    print(f"CLASSIFICATION LYNCH — {d.get('ticker', '?')}")
    print("=" * 70)
    print(f"\nCatégorie principale : {r['primary_category']}")
    print(f"Confiance            : {r['confidence']}")

    if len(r["all_candidates"]) > 1:
        print("\nAutres catégories possibles:")
        for cat, conf in r["all_candidates"][1:]:
            print(f"  - {cat} (confiance {conf})")

    print("\nMétriques observées:")
    for k, v in r["metrics_observed"].items():
        print(f"  {k:30s} = {v}")

    print("\nRationale:")
    for line in r["rationale"]:
        print(f"  • {line}")

    print(f"\n→ Voir references/lynch-{r['primary_category'].lower().replace(' ', '-')}s.md")


if __name__ == "__main__":
    main()
