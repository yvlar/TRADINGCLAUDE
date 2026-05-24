#!/usr/bin/env python3
"""
compute_multiples.py — Valorisation par multiples comparables

Calcule la valeur d'une entreprise en appliquant la médiane des multiples des pairs.

Usage:
  python compute_multiples.py inputs.json

Format JSON:
{
  "company": "Target Corp",
  "metrics": {
    "ebitda_forward": 5000,
    "earnings_forward": 3000,
    "fcf": 2800,
    "revenue": 25000,
    "book_value_tangible": 18000
  },
  "shares_diluted": 1000,
  "net_debt": 8000,
  "peers": [
    {"name": "Pair 1", "ev_ebitda": 11.2, "pe_forward": 18.5, "p_fcf": 22.0, "ev_revenue": 2.3, "p_b_tangible": 2.1},
    {"name": "Pair 2", "ev_ebitda": 9.8, "pe_forward": 16.2, "p_fcf": 20.5, "ev_revenue": 2.0, "p_b_tangible": 1.9},
    {"name": "Pair 3", "ev_ebitda": 12.5, "pe_forward": 21.0, "p_fcf": 25.0, "ev_revenue": 2.5, "p_b_tangible": 2.4},
    {"name": "Pair 4", "ev_ebitda": 10.5, "pe_forward": 17.8, "p_fcf": 21.2, "ev_revenue": 2.1, "p_b_tangible": 2.0}
  ]
}

Référence: references/comparables.md
"""

import json
import statistics
import sys
from pathlib import Path


def compute_multiples(d):
    """Applique la médiane des multiples sectoriels aux métriques de la cible."""
    metrics = d["metrics"]
    peers = d["peers"]
    shares = d["shares_diluted"]
    net_debt = d["net_debt"]

    multiples_to_check = [
        ("ev_ebitda", "ebitda_forward", True),    # True = needs net_debt subtraction
        ("pe_forward", "earnings_forward", False),
        ("p_fcf", "fcf", False),
        ("ev_revenue", "revenue", True),
        ("p_b_tangible", "book_value_tangible", False),
    ]

    results = []
    for mult_name, metric_name, is_ev_based in multiples_to_check:
        peer_multiples = [p.get(mult_name) for p in peers if p.get(mult_name) is not None]
        if not peer_multiples or metrics.get(metric_name) is None:
            continue

        median_mult = statistics.median(peer_multiples)
        mean_mult = statistics.mean(peer_multiples)

        if is_ev_based:
            implied_ev = median_mult * metrics[metric_name]
            implied_equity = implied_ev - net_debt
        else:
            implied_equity = median_mult * metrics[metric_name]

        price = implied_equity / shares

        results.append({
            "multiple": mult_name,
            "median_mult": round(median_mult, 2),
            "mean_mult": round(mean_mult, 2),
            "min_peer": round(min(peer_multiples), 2),
            "max_peer": round(max(peer_multiples), 2),
            "implied_price": round(price, 2),
            "n_peers": len(peer_multiples),
        })

    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    if sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    with open(sys.argv[1]) as f:
        d = json.load(f)

    results = compute_multiples(d)

    print("=" * 78)
    print(f"VALORISATION PAR MULTIPLES — {d.get('company', 'Cible')}")
    print(f"Pairs utilisés: {len(d['peers'])}")
    print("=" * 78)

    print(f"\n{'Multiple':<18} {'Min':>7} {'Médiane':>9} {'Moyenne':>9} {'Max':>7} {'Prix impliqué':>15}")
    print("-" * 78)
    for r in results:
        print(f"{r['multiple']:<18} {r['min_peer']:>7.2f} {r['median_mult']:>9.2f} {r['mean_mult']:>9.2f} {r['max_peer']:>7.2f} {r['implied_price']:>15.2f}")

    if results:
        prices = [r["implied_price"] for r in results]
        print("\n" + "-" * 78)
        print(f"Fourchette des prix impliqués : {min(prices):.2f} – {max(prices):.2f}")
        print(f"Médiane des prix impliqués    : {statistics.median(prices):.2f}")
        print(f"Moyenne                       : {statistics.mean(prices):.2f}")
        print("\nNote: utiliser la médiane plutôt que la moyenne des multiples sectoriels.")
        print("      Pondérer les multiples selon leur pertinence sectorielle (voir comparables.md).")


if __name__ == "__main__":
    main()
