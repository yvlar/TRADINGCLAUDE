#!/usr/bin/env python3
"""
compute_cscore.py — Montier C-Score (6 signaux binaires de "cooking the books")

Drapeaux qualitatifs de manipulation comptable, complémentaires au M-Score.

Usage:
  python compute_cscore.py
  python compute_cscore.py data.json

Format JSON:
{
  "current": {
    "net_income": 1200,
    "cfo": 900,
    "receivables": 1500,
    "sales": 10000,
    "inventory": 2000,
    "cogs": 6000,
    "other_current_assets": 500,
    "depreciation": 800,
    "ppe_gross": 8000,
    "total_assets": 50000
  },
  "previous": {
    ... mêmes champs T-1 ...
  },
  "older": {  # OPTIONNEL: T-2, T-3, T-4 pour analyser la divergence NI/CFO sur 4 ans
    "t-2": {"net_income": ..., "cfo": ...},
    "t-3": {"net_income": ..., "cfo": ...},
    "t-4": {"net_income": ..., "cfo": ...}
  }
}

Référence: references/montier-c-score.md
"""

import json
import sys
from pathlib import Path


def compute_cscore(curr: dict, prev: dict, older: dict = None) -> dict:
    """Calcule le C-Score (0-6, plus c'est haut, plus c'est suspect)."""

    signals = {}

    # 1. Divergence croissante NI vs CFO (sur 4 ans si possible, sinon T vs T-1)
    # Note: le signal s'allume seulement si NI > CFO ET le gap se creuse.
    # Un CFO > NI (gap négatif) est au contraire un signal positif (Sloan).
    if older and all(k in older for k in ["t-2", "t-3", "t-4"]):
        gaps = [
            curr["net_income"] - curr["cfo"],
            prev["net_income"] - prev["cfo"],
            older["t-2"]["net_income"] - older["t-2"]["cfo"],
            older["t-3"]["net_income"] - older["t-3"]["cfo"],
            older["t-4"]["net_income"] - older["t-4"]["cfo"],
        ]
        first_half_avg = sum(gaps[3:]) / 2
        second_half_avg = sum(gaps[:2]) / 2
        # Signal seulement si gap positif et croissant
        signals["1. Gap NI/CFO en hausse (NI > CFO)"] = (
            1 if second_half_avg > 0 and second_half_avg > first_half_avg * 1.2 else 0
        )
    else:
        gap_curr = curr["net_income"] - curr["cfo"]
        gap_prev = prev["net_income"] - prev["cfo"]
        # Signal seulement si gap positif (NI > CFO) et croissant
        signals["1. Gap NI/CFO en hausse (NI > CFO)"] = (
            1 if gap_curr > 0 and gap_curr > gap_prev else 0
        )

    # 2. DSO en hausse > 10%
    dso_curr = curr["receivables"] / curr["sales"] * 365
    dso_prev = prev["receivables"] / prev["sales"] * 365
    signals["2. DSO en hausse > 10%"] = 1 if dso_curr / dso_prev > 1.10 else 0

    # 3. DIO en hausse > 10%
    dio_curr = curr["inventory"] / curr["cogs"] * 365
    dio_prev = prev["inventory"] / prev["cogs"] * 365
    signals["3. DIO en hausse > 10%"] = 1 if dio_curr / dio_prev > 1.10 else 0

    # 4. Other Current Assets / Sales en hausse > 10%
    oca_ratio_curr = curr["other_current_assets"] / curr["sales"]
    oca_ratio_prev = prev["other_current_assets"] / prev["sales"]
    signals["4. OCA/Sales en hausse > 10%"] = (
        1 if oca_ratio_curr / oca_ratio_prev > 1.10 else 0
    )

    # 5. Dépréciation/PP&E gross en baisse > 5%
    dep_rate_curr = curr["depreciation"] / curr["ppe_gross"]
    dep_rate_prev = prev["depreciation"] / prev["ppe_gross"]
    signals["5. Taux dépréciation en baisse > 5%"] = (
        1 if (1 - dep_rate_curr / dep_rate_prev) > 0.05 else 0
    )

    # 6. Croissance des actifs > 10%
    growth_rate = curr["total_assets"] / prev["total_assets"] - 1
    signals["6. Croissance actifs > 10%"] = 1 if growth_rate > 0.10 else 0

    c_score = sum(signals.values())

    if c_score <= 1:
        verdict = "OK — pas de drapeaux qualitatifs"
        flag = "vert"
    elif c_score <= 3:
        verdict = "DRAPEAUX JAUNES — surveiller, contexte requis"
        flag = "jaune"
    else:
        verdict = "MANIPULATION COMPTABLE PROBABLE — investigation forensique requise"
        flag = "rouge"

    return {
        "c_score": c_score,
        "max_score": 6,
        "verdict": verdict,
        "flag": flag,
        "signals": signals,
        "details": {
            "DSO_t": round(dso_curr, 1),
            "DSO_t-1": round(dso_prev, 1),
            "DIO_t": round(dio_curr, 1),
            "DIO_t-1": round(dio_prev, 1),
            "Croissance actifs": f"{round(growth_rate * 100, 1)}%",
        },
    }


def interactive_input() -> dict:
    fields = [
        "net_income", "cfo", "receivables", "sales", "inventory", "cogs",
        "other_current_assets", "depreciation", "ppe_gross", "total_assets"
    ]
    print("=" * 60)
    print("Montier C-Score — saisie interactive")
    print("=" * 60)
    print("\nValeurs pour T (exercice courant):\n")
    curr = {f: float(input(f"  {f}: ")) for f in fields}
    print("\nValeurs pour T-1:\n")
    prev = {f: float(input(f"  {f}: ")) for f in fields}
    return {"current": curr, "previous": prev}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"Erreur: fichier introuvable: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            data = json.load(f)
    else:
        data = interactive_input()

    older = data.get("older")
    result = compute_cscore(data["current"], data["previous"], older)

    print("\n" + "=" * 60)
    print(f"C-SCORE = {result['c_score']}/{result['max_score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flag: {result['flag'].upper()}")
    print("=" * 60)
    print("\nSignaux (⚠ = drapeau levé):")
    for k, v in result["signals"].items():
        symbol = "⚠" if v == 1 else "✓"
        print(f"  {symbol} {k}")
    print("\nDétails:")
    for k, v in result["details"].items():
        print(f"  {k:25s} = {v}")


if __name__ == "__main__":
    main()
