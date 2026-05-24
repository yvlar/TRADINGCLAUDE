#!/usr/bin/env python3
"""
compute_accruals.py — Ratio d'accruals (Sloan, 1996)

Mesure la qualité des bénéfices (proportion cash vs accruals).
Plus le ratio est élevé, plus les bénéfices sont "fragiles".

Usage:
  python compute_accruals.py
  python compute_accruals.py data.json
  python compute_accruals.py --version operating data.json    # version Sloan originale

Format JSON:
{
  "method": "simple",    # ou "operating" pour la version Sloan complète
  "current": {
    "net_income": 1200,
    "cfo": 900,
    "total_assets": 50000,
    # Pour la version "operating", ajouter:
    "current_assets": 12000,
    "cash": 2000,
    "current_liabilities": 6000,
    "short_term_debt": 1500,
    "taxes_payable": 300,
    "depreciation": 800
  },
  "previous": {
    ... champs T-1 ...
  }
}

Référence: references/sloan-accruals.md
"""

import json
import sys
from pathlib import Path


def compute_accruals_simple(curr: dict, prev: dict) -> dict:
    """Version simple: (NI - CFO) / Total Assets moyens."""
    avg_ta = (curr["total_assets"] + prev["total_assets"]) / 2
    accruals = curr["net_income"] - curr["cfo"]
    ratio = accruals / avg_ta

    return {
        "method": "simple",
        "accruals_ratio": round(ratio, 4),
        "accruals_pct": f"{round(ratio * 100, 2)}%",
        "components": {
            "Net Income": curr["net_income"],
            "CFO": curr["cfo"],
            "Accruals (NI - CFO)": accruals,
            "Total Assets moyens": avg_ta,
        },
    }


def compute_accruals_operating(curr: dict, prev: dict) -> dict:
    """Version Sloan originale: accruals d'exploitation."""
    delta_ca = curr["current_assets"] - prev["current_assets"]
    delta_cash = curr["cash"] - prev["cash"]
    delta_cl = curr["current_liabilities"] - prev["current_liabilities"]
    delta_std = curr.get("short_term_debt", 0) - prev.get("short_term_debt", 0)
    delta_tax = curr.get("taxes_payable", 0) - prev.get("taxes_payable", 0)
    depreciation = curr["depreciation"]

    operating_accruals = (delta_ca - delta_cash) - (delta_cl - delta_std - delta_tax) - depreciation

    avg_ta = (curr["total_assets"] + prev["total_assets"]) / 2
    ratio = operating_accruals / avg_ta

    return {
        "method": "operating (Sloan original)",
        "accruals_ratio": round(ratio, 4),
        "accruals_pct": f"{round(ratio * 100, 2)}%",
        "components": {
            "ΔCA": delta_ca,
            "ΔCash": delta_cash,
            "ΔCL": delta_cl,
            "ΔSTD": delta_std,
            "ΔTaxes_payable": delta_tax,
            "Depreciation": depreciation,
            "Operating Accruals": operating_accruals,
            "Total Assets moyens": avg_ta,
        },
    }


def interpret(ratio: float) -> tuple[str, str]:
    """Interprétation grossière (sans données sectorielles)."""
    if ratio > 0.10:
        return "ÉLEVÉ — bénéfices de qualité fragile", "rouge"
    elif ratio > 0.05:
        return "MODÉRÉ — surveiller", "jaune"
    elif ratio > -0.05:
        return "NORMAL — bénéfices équilibrés", "vert"
    else:
        return "TRÈS NÉGATIF — investiguer (peut signaler dégradation des accruals ou one-off)", "jaune"


def interactive_input() -> dict:
    print("=" * 60)
    print("Sloan Accruals Ratio — saisie interactive")
    print("=" * 60)
    print("\nMéthode:")
    print("  1. Simple: (NI - CFO) / TA moyens (recommandé)")
    print("  2. Operating: version Sloan originale (plus de données requises)")
    method_choice = input("\nChoix [1]: ").strip() or "1"
    method = "simple" if method_choice == "1" else "operating"

    if method == "simple":
        fields = ["net_income", "cfo", "total_assets"]
    else:
        fields = ["net_income", "cfo", "total_assets", "current_assets", "cash",
                  "current_liabilities", "short_term_debt", "taxes_payable", "depreciation"]

    print("\nValeurs T:\n")
    curr = {f: float(input(f"  {f}: ")) for f in fields}
    print("\nValeurs T-1:\n")
    prev = {f: float(input(f"  {f}: ")) for f in fields}
    return {"method": method, "current": curr, "previous": prev}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    method = "simple"
    json_file = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--version":
            method = args[i + 1]
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
        method = data.get("method", method)
    else:
        data = interactive_input()
        method = data["method"]

    if method == "simple":
        result = compute_accruals_simple(data["current"], data["previous"])
    else:
        result = compute_accruals_operating(data["current"], data["previous"])

    verdict, flag = interpret(result["accruals_ratio"])

    print("\n" + "=" * 60)
    print(f"ACCRUALS RATIO = {result['accruals_pct']}")
    print(f"Méthode: {result['method']}")
    print(f"Verdict: {verdict}")
    print(f"Flag: {flag.upper()}")
    print("=" * 60)
    print("\nComposantes:")
    for k, v in result["components"].items():
        print(f"  {k:25s} = {v}")
    print("\nNote: l'interprétation rigoureuse exige une comparaison décile par décile")
    print("au sein du secteur. Les seuils ci-dessus sont des heuristiques grossières.")


if __name__ == "__main__":
    main()
