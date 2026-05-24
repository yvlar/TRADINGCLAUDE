#!/usr/bin/env python3
"""
check_coherence.py — Vérifie la cohérence dynamique d'un modèle de valorisation

Test la relation fondamentale: Croissance = ROIC × Taux de réinvestissement

Usage:
  python check_coherence.py --growth 25 --reinv 40 --industry-roic-leader 25
"""

import argparse


def check(growth_pct: float, reinv_pct: float, industry_roic: float) -> dict:
    """Vérifie cohérence."""
    if reinv_pct <= 0:
        return {"verdict": "Erreur: réinvestissement nul ou négatif"}

    g = growth_pct / 100
    r = reinv_pct / 100
    roic_implied = g / r if r > 0 else float('inf')

    flags = []

    if roic_implied * 100 > industry_roic + 10:
        flags.append(f"❌ ROIC implicite {roic_implied*100:.1f}% > leader sectoriel ({industry_roic}%) + 10pts")
    elif roic_implied * 100 > industry_roic:
        flags.append(f"⚠ ROIC implicite {roic_implied*100:.1f}% > leader sectoriel ({industry_roic}%)")
    else:
        flags.append(f"✓ ROIC implicite {roic_implied*100:.1f}% ≤ leader sectoriel ({industry_roic}%)")

    if roic_implied > 0.50:
        flags.append("❌ ROIC > 50% est rarement atteint et jamais maintenu durablement")
    elif roic_implied > 0.30:
        flags.append("⚠ ROIC > 30% — durée maximale typique 5-7 ans")

    return {
        "growth": growth_pct,
        "reinvestment": reinv_pct,
        "roic_implied": round(roic_implied * 100, 2),
        "industry_roic": industry_roic,
        "flags": flags,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--growth", type=float, required=True, help="Croissance projetée (%)")
    parser.add_argument("--reinv", type=float, required=True, help="Taux de réinvestissement (%)")
    parser.add_argument("--industry-roic-leader", type=float, default=20,
                        help="ROIC du leader sectoriel pour comparaison (%)")
    args = parser.parse_args()

    r = check(args.growth, args.reinv, args.industry_roic_leader)

    print("=" * 65)
    print("TEST DE COHÉRENCE DYNAMIQUE")
    print("=" * 65)
    print(f"\nCroissance projetée   : {r['growth']}%")
    print(f"Taux de réinvestissement: {r['reinvestment']}%")
    print(f"\n→ ROIC implicite: {r['roic_implied']}%")
    print(f"→ Leader sectoriel: {r['industry_roic']}%")
    print(f"\nÉvaluation:")
    for f in r["flags"]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
