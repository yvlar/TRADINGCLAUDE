#!/usr/bin/env python3
"""
triangulate.py — Triangulation des trois méthodes en fourchette finale

Combine les résultats de DCF, multiples comparables et méthode sectorielle
en une fourchette pondérée basse / centrale / haute.

Usage:
  python triangulate.py inputs.json

Format JSON:
{
  "company": "Example Corp",
  "current_price": 75.50,
  "currency": "CAD",
  "methods": {
    "dcf": {
      "low": 80.0,
      "central": 95.0,
      "high": 110.0,
      "weight": 0.50
    },
    "comparables": {
      "low": 70.0,
      "central": 85.0,
      "high": 100.0,
      "weight": 0.30
    },
    "sectorial": {
      "low": 75.0,
      "central": 90.0,
      "high": 105.0,
      "weight": 0.20
    }
  }
}

Référence: SKILL.md, étape 5
"""

import json
import sys
from pathlib import Path


def triangulate(methods: dict):
    """Pondère les trois méthodes."""
    total_weight = sum(m["weight"] for m in methods.values())
    if abs(total_weight - 1.0) > 0.01:
        return {"error": f"La somme des poids doit être 1.0, est {total_weight}"}

    low = sum(m["low"] * m["weight"] for m in methods.values())
    central = sum(m["central"] * m["weight"] for m in methods.values())
    high = sum(m["high"] * m["weight"] for m in methods.values())

    # Détecter les divergences
    centrals = [m["central"] for m in methods.values()]
    max_div = (max(centrals) / min(centrals) - 1) * 100

    return {
        "low": round(low, 2),
        "central": round(central, 2),
        "high": round(high, 2),
        "max_divergence_pct": round(max_div, 1),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    if sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    with open(sys.argv[1]) as f:
        d = json.load(f)

    result = triangulate(d["methods"])
    if "error" in result:
        print(f"Erreur: {result['error']}", file=sys.stderr)
        sys.exit(1)

    company = d.get("company", "Cible")
    currency = d.get("currency", "USD")
    current = d.get("current_price")

    print("=" * 70)
    print(f"TRIANGULATION — {company}")
    print("=" * 70)

    print(f"\n{'Méthode':<15} {'Bas':>10} {'Centrale':>12} {'Haut':>10} {'Poids':>8}")
    print("-" * 70)
    for name, m in d["methods"].items():
        print(f"{name:<15} {m['low']:>10.2f} {m['central']:>12.2f} {m['high']:>10.2f} {m['weight']:>7.0%}")

    print("-" * 70)
    print(f"{'PONDÉRÉ':<15} {result['low']:>10.2f} {result['central']:>12.2f} {result['high']:>10.2f}")
    print(f"\nFourchette finale : {result['low']:.2f} – {result['high']:.2f} {currency}")
    print(f"Centrale          : {result['central']:.2f} {currency}")

    if current:
        margin = (result['central'] - current) / result['central'] * 100
        print(f"\nPrix actuel       : {current:.2f} {currency}")
        print(f"Marge de sécurité : {margin:+.1f}% (vs centrale)")

    print(f"\nDivergence max entre méthodes : {result['max_divergence_pct']}%")
    if result['max_divergence_pct'] > 30:
        print("⚠  Divergence > 30% — investiguer plutôt que pondérer aveuglément.")
        print("   Quelle méthode capture-t-elle mieux la réalité économique ?")


if __name__ == "__main__":
    main()
