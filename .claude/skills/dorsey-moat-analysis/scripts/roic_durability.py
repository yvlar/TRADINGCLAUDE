#!/usr/bin/env python3
"""
roic_durability.py — Test de durabilité du ROIC pour identifier un moat probable

Calcule la moyenne, l'écart-type et la tendance du ROIC sur 10 ans
pour confirmer/infirmer la présence d'un moat économique.

Usage:
  python roic_durability.py inputs.json

Format JSON:
{
  "ticker": "CSU.TO",
  "roic_history": [0.28, 0.29, 0.27, 0.30, 0.31, 0.28, 0.29, 0.31, 0.30, 0.32],
  "wacc": 0.085
}

Référence: SKILL.md
"""

import json
import sys
import statistics


def analyze_roic(history: list, wacc: float) -> dict:
    """Analyse moyenne, dispersion, tendance, spread vs WACC."""
    n = len(history)
    mean = statistics.mean(history)
    stdev = statistics.stdev(history) if n > 1 else 0
    cv = stdev / mean if mean > 0 else float('inf')  # coefficient de variation

    # Tendance: régression linéaire simple (pente)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = mean
    num = sum((xs[i] - x_mean) * (history[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0

    # Spread vs WACC
    spread = mean - wacc

    # Verdict
    if mean >= 0.15 and cv < 0.20 and spread > 0.05:
        verdict = "✅ MOAT PROBABLE — ROIC élevé, stable, durablement > WACC"
        flag = "vert"
    elif mean >= 0.10 and cv < 0.30 and spread > 0.02:
        verdict = "⚠ MOAT POSSIBLE — chiffres acceptables, à investiguer"
        flag = "jaune"
    else:
        verdict = "❌ PAS DE MOAT IDENTIFIABLE — ROIC trop faible, volatile, ou proche du WACC"
        flag = "rouge"

    # Détecter érosion
    if slope < -0.005:
        erosion_warning = "⚠ Tendance à la baisse détectée — moat possiblement en érosion"
    elif slope > 0.005:
        erosion_warning = "📈 Tendance haussière — moat possiblement en renforcement"
    else:
        erosion_warning = ""

    return {
        "n_years": n,
        "mean": round(mean, 4),
        "mean_pct": f"{mean*100:.1f}%",
        "stdev": round(stdev, 4),
        "cv": round(cv, 3),
        "slope_per_year": round(slope, 5),
        "spread_vs_wacc": round(spread, 4),
        "spread_pct": f"{spread*100:.1f} pts",
        "verdict": verdict,
        "flag": flag,
        "erosion_warning": erosion_warning,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    result = analyze_roic(d["roic_history"], d["wacc"])

    print("=" * 70)
    print(f"TEST DE DURABILITÉ DU ROIC — {d.get('ticker', '?')}")
    print(f"Historique sur {result['n_years']} ans")
    print("=" * 70)

    print(f"\nROIC moyen        : {result['mean_pct']}")
    print(f"Écart-type        : {result['stdev']*100:.2f}%")
    print(f"Coef. de variation: {result['cv']:.3f} (< 0.20 = stable)")
    print(f"Tendance/an       : {result['slope_per_year']*100:+.2f} pts")
    print(f"Spread vs WACC    : {result['spread_pct']}")
    print(f"\n{result['verdict']}")
    if result['erosion_warning']:
        print(f"{result['erosion_warning']}")

    print("\nHistorique:")
    for i, r in enumerate(d["roic_history"]):
        bar = "█" * int(r * 100)
        print(f"  Année T-{result['n_years']-i-1}: {r*100:5.2f}% {bar}")


if __name__ == "__main__":
    main()
