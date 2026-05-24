#!/usr/bin/env python3
"""
graham_screen.py — Application des critères Graham (défensif ou entreprenant)

Usage:
  python graham_screen.py inputs.json
  python graham_screen.py --profil entreprenant inputs.json

Format JSON:
{
  "ticker": "RY.TO",
  "profil": "defensif",   # defensif ou entreprenant
  "currency": "CAD",
  "price": 130.0,
  "revenu_annuel": 50000,         # millions
  "current_assets": 1500000,
  "current_liabilities": 700000,
  "long_term_debt": 800000,
  "working_capital": 800000,
  "deficits_10ans": 0,            # nombre d'années avec déficit
  "deficits_5ans": 0,
  "dividendes_continus_annees": 25,
  "verse_dividende": true,
  "bpa_actuel": 12.0,
  "bpa_il_y_a_10ans": 8.0,
  "bpa_5ans_passe_positif": true,
  "book_value_per_share": 75.0,
  "tangible_book_value_per_share": 70.0
}

Référence: references/graham-defensif.md, references/graham-entreprenant.md
"""

import json
import sys
import argparse


def screen_defensif(d: dict) -> dict:
    """Applique les 8 critères défensifs."""
    pe = d["price"] / d["bpa_actuel"]
    pb = d["price"] / d["book_value_per_share"]
    current_ratio = d["current_assets"] / d["current_liabilities"]
    croissance_eps = (d["bpa_actuel"] / d["bpa_il_y_a_10ans"] - 1) * 100

    criteria = {
        "1. Taille (revenus > 700M)": d["revenu_annuel"] >= 700,
        "2a. Current ratio ≥ 2.0": current_ratio >= 2.0,
        "2b. LTD ≤ Working Capital": d["long_term_debt"] <= d["working_capital"],
        "3. Aucun déficit sur 10 ans": d["deficits_10ans"] == 0,
        "4. Dividende continu ≥ 20 ans": d["dividendes_continus_annees"] >= 20,
        "5. Croissance BPA ≥ 33% sur 10 ans": croissance_eps >= 33,
        "6. P/E ≤ 15": pe <= 15,
        "7. P/B ≤ 1.5": pb <= 1.5,
        "8. P/E × P/B ≤ 22.5": pe * pb <= 22.5,
    }

    score = sum(1 for v in criteria.values() if v)
    max_score = 9  # 8 critères + 2a/2b séparés

    return {
        "profil": "défensif",
        "score": score,
        "max_score": max_score,
        "criteria": criteria,
        "metrics": {
            "P/E": round(pe, 2),
            "P/B": round(pb, 2),
            "P/E × P/B": round(pe * pb, 2),
            "Current ratio": round(current_ratio, 2),
            "Croissance BPA 10 ans (%)": round(croissance_eps, 1),
        },
    }


def screen_entreprenant(d: dict) -> dict:
    """Applique les 5 critères entreprenants."""
    pb_tangible = d["price"] / d["tangible_book_value_per_share"]
    current_ratio = d["current_assets"] / d["current_liabilities"]
    debt_vs_wc = d["long_term_debt"] / d["working_capital"] if d["working_capital"] > 0 else 999

    criteria = {
        "1a. Current ratio ≥ 1.5": current_ratio >= 1.5,
        "1b. Dette ≤ 110% Working Capital": debt_vs_wc <= 1.10,
        "2. Aucun déficit sur 5 ans": d["deficits_5ans"] == 0,
        "3. Verse un dividende": d["verse_dividende"],
        "4. Croissance BPA positive 5 ans": d["bpa_5ans_passe_positif"],
        "5. Prix ≤ 120% NAV tangible": pb_tangible <= 1.2,
    }

    score = sum(1 for v in criteria.values() if v)
    max_score = 6

    return {
        "profil": "entreprenant",
        "score": score,
        "max_score": max_score,
        "criteria": criteria,
        "metrics": {
            "P/B tangible": round(pb_tangible, 2),
            "Current ratio": round(current_ratio, 2),
            "Dette/WC": round(debt_vs_wc, 2),
        },
    }


def verdict_text(score: int, max_score: int, profil: str) -> str:
    pct = score / max_score
    if pct >= 0.85:
        return "✅ PASSE — procéder à l'analyse fondamentale approfondie"
    elif pct >= 0.65:
        return "⚠ LIMITE — watchlist avec prix d'achat cible"
    else:
        return "❌ ÉCHEC — rejeter pour ce profil"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Fichier JSON d'inputs")
    parser.add_argument("--profil", choices=["defensif", "entreprenant"], default=None)
    args = parser.parse_args()

    with open(args.input_file) as f:
        d = json.load(f)

    profil = args.profil or d.get("profil", "defensif")

    if profil == "defensif":
        r = screen_defensif(d)
    else:
        r = screen_entreprenant(d)

    print("=" * 70)
    print(f"SCREENING GRAHAM — {d.get('ticker', '?')} — Profil {profil.upper()}")
    print(f"Prix: {d['price']} {d.get('currency', '?')}")
    print("=" * 70)

    print(f"\nSCORE: {r['score']}/{r['max_score']}")
    print(verdict_text(r['score'], r['max_score'], profil))

    print("\nCritères:")
    for k, passed in r["criteria"].items():
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {k}")

    print("\nMétriques:")
    for k, v in r["metrics"].items():
        print(f"  {k:30s} = {v}")


if __name__ == "__main__":
    main()
