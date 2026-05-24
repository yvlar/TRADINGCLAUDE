#!/usr/bin/env python3
"""
peg_ratio.py — Calcul du ratio PEG de Lynch

PEG = P/E forward / Taux de croissance bénéfice (en %)

Usage:
  python peg_ratio.py --pe 18 --growth 22
"""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pe", type=float, required=True, help="P/E forward")
    parser.add_argument("--growth", type=float, required=True, help="Taux de croissance bénéfices (%)")
    args = parser.parse_args()

    if args.growth <= 0:
        print("⚠ Croissance non positive — PEG non applicable")
        return

    peg = args.pe / args.growth

    print("=" * 50)
    print(f"PEG = {args.pe} / {args.growth} = {peg:.2f}")
    print("=" * 50)

    if peg < 0.5:
        verdict = "🟢 TRÈS ATTRACTIF — Lynch buy candidate"
    elif peg < 1.0:
        verdict = "🟢 ATTRACTIF — niveau Lynch buy"
    elif peg < 1.5:
        verdict = "🟡 ÉQUITABLEMENT VALORISÉ"
    elif peg < 2.0:
        verdict = "🟡 LÉGÈREMENT CHER"
    else:
        verdict = "🔴 SUREVALUÉ — Lynch sell candidate"

    print(f"\nVerdict : {verdict}")
    print("\nRappel des seuils Lynch:")
    print("  PEG < 0.5  : très attractif")
    print("  PEG 0.5-1.0: attractif")
    print("  PEG 1.0-2.0: équitable")
    print("  PEG > 2.0  : surévalué")


if __name__ == "__main__":
    main()
