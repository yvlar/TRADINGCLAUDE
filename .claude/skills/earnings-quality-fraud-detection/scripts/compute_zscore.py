#!/usr/bin/env python3
"""
compute_zscore.py — Altman Z-Score (1968, 1983, 1995)

Prédit la probabilité de faillite à 2 ans.
Trois variantes selon le profil d'entreprise.

Usage:
  python compute_zscore.py                            # mode interactif
  python compute_zscore.py data.json                  # mode batch
  python compute_zscore.py --variant z'' data.json    # forcer variante

Variantes:
  z   : entreprises industrielles cotées (par défaut)
  z'  : entreprises industrielles privées
  z'' : services, retail, tech, marchés émergents

Format JSON:
{
  "variant": "z",  # optionnel: z, z', z''
  "working_capital": 5000,
  "total_assets": 50000,
  "retained_earnings": 12000,
  "ebit": 8000,
  "market_value_equity": 60000,    # pour z; book value pour z'
  "total_liabilities": 25000,
  "sales": 80000
}

Référence: references/altman-z-score.md
"""

import json
import sys
from pathlib import Path


def compute_zscore(data: dict, variant: str = "z") -> dict:
    """Calcule le Z-Score Altman selon la variante."""

    x1 = data["working_capital"] / data["total_assets"]
    x2 = data["retained_earnings"] / data["total_assets"]
    x3 = data["ebit"] / data["total_assets"]
    x4 = data["market_value_equity"] / data["total_liabilities"]
    x5 = data["sales"] / data["total_assets"]

    if variant == "z":
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        thresholds = {"safe": 2.99, "distress": 1.81}
        formula = "1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5"
    elif variant == "z'":
        z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
        thresholds = {"safe": 2.90, "distress": 1.23}
        formula = "0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5"
    elif variant == "z''":
        # X5 (sales/TA) exclu pour Z''
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        thresholds = {"safe": 2.60, "distress": 1.10}
        formula = "6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×X4"
    else:
        raise ValueError(f"Variante inconnue: {variant}. Utiliser z, z' ou z''.")

    if z > thresholds["safe"]:
        verdict = "ZONE SÛRE — faible probabilité de faillite"
        flag = "vert"
    elif z > thresholds["distress"]:
        verdict = "ZONE GRISE — incertain"
        flag = "jaune"
    else:
        verdict = "ZONE DE DÉTRESSE — risque de faillite à 2 ans"
        flag = "rouge"

    return {
        "z_score": round(z, 3),
        "variant": variant,
        "formula": formula,
        "verdict": verdict,
        "flag": flag,
        "components": {
            "X1 (WC/TA)": round(x1, 3),
            "X2 (RE/TA)": round(x2, 3),
            "X3 (EBIT/TA)": round(x3, 3),
            "X4 (MVE/TL)": round(x4, 3),
            "X5 (Sales/TA)": round(x5, 3),
        },
        "thresholds": thresholds,
    }


def interactive_input() -> tuple[dict, str]:
    """Mode interactif."""
    print("=" * 60)
    print("Altman Z-Score — saisie interactive")
    print("=" * 60)
    print("\nVariantes:")
    print("  z   : industriel coté (par défaut)")
    print("  z'  : industriel privé")
    print("  z'' : service, retail, tech, marché émergent")
    variant = input("\nVariante [z]: ").strip() or "z"

    fields = [
        ("working_capital", "Working Capital (Actif circulant - Passif circulant)"),
        ("total_assets", "Total Assets"),
        ("retained_earnings", "Retained Earnings (Réserves accumulées)"),
        ("ebit", "EBIT"),
        ("market_value_equity", "Market Value of Equity (ou Book Value pour z')"),
        ("total_liabilities", "Total Liabilities"),
        ("sales", "Sales (Revenus)"),
    ]
    data = {}
    for key, label in fields:
        data[key] = float(input(f"  {label}: "))
    return data, variant


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    variant = "z"
    json_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--variant":
            variant = args[i + 1]
            i += 2
        else:
            json_file = args[i]
            i += 1

    if json_file:
        path = Path(json_file)
        if not path.exists():
            print(f"Erreur: fichier introuvable: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            data = json.load(f)
        if "variant" in data:
            variant = data.pop("variant")
    else:
        data, variant = interactive_input()

    result = compute_zscore(data, variant)

    print("\n" + "=" * 60)
    print(f"Z-SCORE ({result['variant']}) = {result['z_score']}")
    print(f"Formule: {result['formula']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flag: {result['flag'].upper()}")
    print("=" * 60)
    print("\nComposantes:")
    for k, v in result["components"].items():
        print(f"  {k:18s} = {v}")
    print(f"\nSeuils:")
    print(f"  Sûr:      Z > {result['thresholds']['safe']}")
    print(f"  Détresse: Z < {result['thresholds']['distress']}")


if __name__ == "__main__":
    main()
