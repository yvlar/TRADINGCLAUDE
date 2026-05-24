#!/usr/bin/env python3
"""
dhandho_checklist.py — Checklist des 9 principes Dhandho de Pabrai

Usage:
  python dhandho_checklist.py inputs.json

Format JSON:
{
  "ticker": "EXAMPLE",
  "is_existing_business_5y_plus": true,
  "is_simple_business": true,
  "is_in_distress_or_unloved": true,
  "has_durable_moat": true,
  "moat_score": "wide",
  "tailwind_sectoriel": false,
  "estimated_downside_pct": -0.30,
  "estimated_upside_pct": 2.50,
  "probability_upside": 0.65,
  "n_positions_in_portfolio": 12,
  "is_clone_of_super_investor": true,
  "super_investor_name": "Klarman"
}
"""

import json
import sys


def evaluate_dhandho(d: dict) -> dict:
    """Évalue les 9 principes."""
    checks = []

    # P1 - Existing business
    p1 = d.get("is_existing_business_5y_plus", False)
    checks.append(("P1. Entreprise existante (5+ ans)", p1))

    # P2 - Simple business
    p2 = d.get("is_simple_business", False)
    checks.append(("P2. Business simple à comprendre", p2))

    # P3 - Distressed
    p3 = d.get("is_in_distress_or_unloved", False)
    checks.append(("P3. En distress ou peu aimé du marché", p3))

    # P4 - Moat
    moat = d.get("has_durable_moat", False) and d.get("moat_score", "none") in ("narrow", "wide")
    checks.append(("P4. Moat durable identifiable", moat))

    # P5 - Few bets (N ≤ 15)
    n_pos = d.get("n_positions_in_portfolio", 99)
    p5 = n_pos <= 15
    checks.append((f"P5. Concentration ({n_pos} positions ≤ 15)", p5))

    # P6 - Arbitrage / asymétrie
    downside = abs(d.get("estimated_downside_pct", 0))
    upside = d.get("estimated_upside_pct", 0)
    asymmetry = upside / downside if downside > 0 else 0
    p6 = asymmetry >= 2.5
    checks.append((f"P6. Asymétrie ≥ 2.5:1 (actuelle {asymmetry:.2f})", p6))

    # P7 - Tailwind
    p7 = d.get("tailwind_sectoriel", False)
    checks.append(("P7. Tailwind sectoriel structurel", p7))

    # P8 - Low risk, high uncertainty
    # Heuristique: bilan tenable (downside < 50%) et incertitude élevée (upside > 200%)
    p8 = downside <= 0.50 and upside >= 1.5
    checks.append(("P8. Low risk (< 50% downside) / High uncertainty", p8))

    # P9 - Cloning
    p9 = d.get("is_clone_of_super_investor", False)
    name = d.get("super_investor_name", "")
    label = f"P9. Clone d'un super-investor ({name})" if p9 else "P9. Clone d'un super-investor"
    checks.append((label, p9))

    # Score global
    score = sum(1 for _, ok in checks if ok)

    # Calcul EV
    ev = (d.get("probability_upside", 0.5) * upside) - ((1 - d.get("probability_upside", 0.5)) * downside)

    if score >= 7:
        verdict = "✅ DHANDHO FORTE — opportunité asymétrique de qualité"
        flag = "vert"
    elif score >= 5:
        verdict = "🟡 DHANDHO PARTIELLE — investiguer davantage"
        flag = "jaune"
    else:
        verdict = "❌ PAS UNE DHANDHO — chercher meilleure opportunité"
        flag = "rouge"

    return {
        "checks": checks,
        "score": score,
        "max_score": 9,
        "asymmetry_ratio": round(asymmetry, 2),
        "expected_value_pct": f"{ev*100:.1f}%",
        "verdict": verdict,
        "flag": flag,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    r = evaluate_dhandho(d)

    print("=" * 70)
    print(f"DHANDHO CHECKLIST — {d.get('ticker', '?')}")
    print("=" * 70)

    print(f"\nScore: {r['score']}/{r['max_score']}")
    print(f"{r['verdict']}")
    print(f"Asymétrie: {r['asymmetry_ratio']}:1")
    print(f"EV attendue: {r['expected_value_pct']}")

    print("\nDétail des 9 principes:")
    for label, ok in r["checks"]:
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {label}")


if __name__ == "__main__":
    main()
