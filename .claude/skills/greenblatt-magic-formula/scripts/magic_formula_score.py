#!/usr/bin/env python3
"""
magic_formula_score.py — Screening Magic Formula Greenblatt

Calcule ROC + Earnings Yield, applique le double classement et sort le top.

Usage:
  python magic_formula_score.py univers.json
  python magic_formula_score.py --top 30 univers.json

Format JSON:
{
  "universe": [
    {
      "ticker": "AAPL",
      "ebit": 114000,
      "current_assets": 143000,
      "excess_cash": 80000,
      "current_liabilities": 145000,
      "interest_bearing_debt_st": 15000,
      "ppe_net": 44000,
      "market_cap": 3000000,
      "total_debt": 110000,
      "cash_and_equivalents": 30000
    },
    ...
  ]
}

Référence: references/formules-magic-formula.md
"""

import json
import sys
import argparse


def compute_roc(ebit, ca, excess_cash, cl, st_debt, ppe):
    """ROC = EBIT / (NWC + PP&E)"""
    nwc = max(0, (ca - excess_cash) - (cl - st_debt))
    capital = nwc + ppe
    if capital <= 0:
        return None
    return ebit / capital


def compute_ey(ebit, market_cap, total_debt, cash):
    """EY = EBIT / EV"""
    ev = market_cap + total_debt - cash
    if ev <= 0:
        return None
    return ebit / ev


def rank_universe(universe: list) -> list:
    """Calcule ROC, EY, ranks et score combiné."""
    scored = []
    for stock in universe:
        roc = compute_roc(
            stock["ebit"], stock["current_assets"], stock.get("excess_cash", 0),
            stock["current_liabilities"], stock.get("interest_bearing_debt_st", 0),
            stock["ppe_net"]
        )
        ey = compute_ey(
            stock["ebit"], stock["market_cap"],
            stock["total_debt"], stock.get("cash_and_equivalents", 0)
        )
        if roc is None or ey is None:
            continue  # Exclure les actions avec données invalides
        scored.append({
            "ticker": stock["ticker"],
            "roc": roc,
            "ey": ey,
            "roc_pct": f"{roc*100:.1f}%",
            "ey_pct": f"{ey*100:.1f}%",
        })

    # Rang ROC (1 = meilleur, plus haut)
    scored_by_roc = sorted(scored, key=lambda x: -x["roc"])
    for i, s in enumerate(scored_by_roc, 1):
        s["rank_roc"] = i

    # Rang EY (1 = meilleur, plus haut)
    scored_by_ey = sorted(scored, key=lambda x: -x["ey"])
    for i, s in enumerate(scored_by_ey, 1):
        s["rank_ey"] = i

    # Score combiné
    for s in scored:
        s["combined_score"] = s["rank_roc"] + s["rank_ey"]

    return sorted(scored, key=lambda x: x["combined_score"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Fichier JSON de l'univers")
    parser.add_argument("--top", type=int, default=30, help="Nombre de positions top à afficher")
    args = parser.parse_args()

    with open(args.input_file) as f:
        d = json.load(f)

    ranked = rank_universe(d["universe"])

    print("=" * 80)
    print(f"MAGIC FORMULA — Top {args.top} sur {len(ranked)} actions de l'univers")
    print("=" * 80)
    print(f"\n{'Rang':<5} {'Ticker':<10} {'ROC':>8} {'EY':>8} {'#ROC':>6} {'#EY':>6} {'Score':>7}")
    print("-" * 80)

    for i, s in enumerate(ranked[:args.top], 1):
        print(f"{i:<5} {s['ticker']:<10} {s['roc_pct']:>8} {s['ey_pct']:>8} "
              f"{s['rank_roc']:>6} {s['rank_ey']:>6} {s['combined_score']:>7}")

    print("\n" + "─" * 80)
    print("Note: appliquer le filtre qualitatif minimal sur ces candidats avant achat.")
    print("Voir references/portefeuille-discipline.md pour la construction de portefeuille.")


if __name__ == "__main__":
    main()
