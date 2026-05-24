#!/usr/bin/env python3
"""
scenarios_ev.py — Calcul d'espérance pondérée pour scenarios bull/base/bear

Usage:
  python scenarios_ev.py --bear-pct -30 --bear-prob 25 --base-pct 50 --base-prob 50 --bull-pct 200 --bull-prob 25 [--horizon 5]
"""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bear-pct", type=float, required=True, help="Impact scenario bear (%)")
    parser.add_argument("--bear-prob", type=float, required=True, help="Probabilité bear (%)")
    parser.add_argument("--base-pct", type=float, required=True)
    parser.add_argument("--base-prob", type=float, required=True)
    parser.add_argument("--bull-pct", type=float, required=True)
    parser.add_argument("--bull-prob", type=float, required=True)
    parser.add_argument("--horizon", type=int, default=5, help="Horizon en années")
    args = parser.parse_args()

    # Vérifier somme probabilités
    total = args.bear_prob + args.base_prob + args.bull_prob
    if abs(total - 100) > 0.5:
        print(f"⚠ Warning: somme probabilités = {total}% (doit être 100%)")

    bear = args.bear_prob / 100 * args.bear_pct / 100
    base = args.base_prob / 100 * args.base_pct / 100
    bull = args.bull_prob / 100 * args.bull_pct / 100
    ev = bear + base + bull
    annualized = ((1 + ev) ** (1/args.horizon) - 1) * 100 if args.horizon > 0 else ev * 100

    print("=" * 60)
    print("ESPÉRANCE PONDÉRÉE — SCENARIOS BULL/BASE/BEAR")
    print("=" * 60)
    print(f"\n{'Scenario':<10} {'Probabilité':>12} {'Impact':>10} {'Contribution':>15}")
    print("-" * 60)
    print(f"{'Bear':<10} {args.bear_prob:>11.0f}% {args.bear_pct:>9.0f}% {bear*100:>14.2f}%")
    print(f"{'Base':<10} {args.base_prob:>11.0f}% {args.base_pct:>9.0f}% {base*100:>14.2f}%")
    print(f"{'Bull':<10} {args.bull_prob:>11.0f}% {args.bull_pct:>9.0f}% {bull*100:>14.2f}%")
    print("-" * 60)
    print(f"{'TOTAL':<10} {total:>11.0f}% {' ':>10} {ev*100:>14.2f}%")

    print(f"\nEspérance pondérée totale : {ev*100:+.1f}%")
    print(f"Horizon                   : {args.horizon} ans")
    print(f"Rendement annualisé       : {annualized:+.2f}%/an")

    if annualized > 12:
        verdict = "🟢 EV exceptionnelle — position importante justifiée"
    elif annualized > 8:
        verdict = "🟢 EV positive solide — position normale"
    elif annualized > 5:
        verdict = "🟡 EV modeste — comparer aux alternatives"
    elif annualized > 0:
        verdict = "🟡 EV faible — peu d'edge vs S&P 500"
    else:
        verdict = "🔴 EV négative — refuser"

    print(f"\n{verdict}")


if __name__ == "__main__":
    main()
