#!/usr/bin/env python3
"""
graham_value.py — Calcul de la valeur intrinsèque selon Graham

Deux formules :
  V = BPA × (8.5 + 2g)              # simple
  V = BPA × (8.5 + 2g) × 4.4 / Y    # ajustée du taux AAA

Usage:
  python graham_value.py --bpa 12 --g 6 --y 5 --prix 130
  python graham_value.py    # mode interactif
"""

import argparse


def graham_simple(bpa: float, g: float) -> float:
    """V = BPA × (8.5 + 2g)"""
    return bpa * (8.5 + 2 * g)


def graham_ajuste(bpa: float, g: float, y: float) -> float:
    """V = BPA × (8.5 + 2g) × 4.4 / Y"""
    return bpa * (8.5 + 2 * g) * 4.4 / y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpa", type=float, default=None, help="Bénéfice par action")
    parser.add_argument("--g", type=float, default=None, help="Croissance attendue (%)")
    parser.add_argument("--y", type=float, default=None, help="Rendement obligations AAA (%)")
    parser.add_argument("--prix", type=float, default=None, help="Prix actuel pour calcul marge")
    args = parser.parse_args()

    if args.bpa is None:
        args.bpa = float(input("BPA (bénéfice par action): "))
    if args.g is None:
        args.g = float(input("Croissance attendue sur 7-10 ans (%): "))
    if args.y is None:
        args.y = float(input("Rendement obligations AAA actuel (%): "))
    if args.prix is None:
        try:
            args.prix = float(input("Prix actuel (vide pour skip): ") or 0)
        except ValueError:
            args.prix = 0

    if args.g > 15:
        print("\n⚠ Croissance > 15 % — Graham conseillait de plafonner à 15 %")
        print("  Le résultat sera utilisé tel quel mais avec extrême prudence.\n")

    v_simple = graham_simple(args.bpa, args.g)
    v_ajuste = graham_ajuste(args.bpa, args.g, args.y)

    print("\n" + "=" * 60)
    print("VALEUR INTRINSÈQUE GRAHAM")
    print("=" * 60)
    print(f"\nFormule simple    : V = {args.bpa} × (8.5 + 2 × {args.g})")
    print(f"                    = {v_simple:.2f}")
    print(f"\nFormule ajustée   : V = {args.bpa} × (8.5 + 2 × {args.g}) × 4.4 / {args.y}")
    print(f"                    = {v_ajuste:.2f}")

    if args.prix > 0:
        marge_simple = (v_simple - args.prix) / v_simple * 100
        marge_ajuste = (v_ajuste - args.prix) / v_ajuste * 100
        print(f"\n{'─' * 60}")
        print(f"Prix actuel       : {args.prix:.2f}")
        print(f"Marge sécurité (simple)  : {marge_simple:+.1f}%")
        print(f"Marge sécurité (ajustée) : {marge_ajuste:+.1f}%")

        marge_moyenne = (marge_simple + marge_ajuste) / 2
        if marge_moyenne >= 30:
            print(f"\n✅ Marge ≥ 30% (Graham): opportunité ACHAT")
        elif marge_moyenne >= 15:
            print(f"\n⚠ Marge entre 15-30%: WATCHLIST")
        else:
            print(f"\n❌ Marge < 15%: insuffisant pour Graham")


if __name__ == "__main__":
    main()
