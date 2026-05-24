#!/usr/bin/env python3
"""
compute_wacc.py — Calcul du WACC (CMPC)

WACC = (E/V) × Re + (D/V) × Rd × (1 − T)
Re via CAPM = Rf + β × (Rm − Rf)

Usage:
  python compute_wacc.py inputs.json
  python compute_wacc.py    # mode interactif

Format JSON:
{
  "rf": 0.035,                    # taux sans risque (10 ans Canada/US)
  "beta": 1.1,                    # bêta de l'action
  "erp": 0.0423,                  # equity risk premium (Damodaran 4.23% en 2026 mature market)
  "country_risk_premium": 0.0,    # 0 pour Canada/US, ajouter pour émergents
  "rd": 0.05,                     # coût marginal de la dette
  "tax_rate": 0.265,              # 26.5% pour Québec
  "market_value_equity": 50000,
  "market_value_debt": 20000
}

Référence: references/dcf.md, section "Calcul du WACC"
"""

import json
import sys
from pathlib import Path


def compute_wacc(rf, beta, erp, crp, rd, tax_rate, mve, mvd):
    re = rf + beta * (erp + crp)
    v = mve + mvd
    e_v = mve / v
    d_v = mvd / v
    wacc = e_v * re + d_v * rd * (1 - tax_rate)

    return {
        "re_capm": round(re, 4),
        "after_tax_rd": round(rd * (1 - tax_rate), 4),
        "weight_equity": round(e_v, 3),
        "weight_debt": round(d_v, 3),
        "wacc": round(wacc, 4),
        "wacc_pct": f"{round(wacc * 100, 2)}%",
    }


def interactive():
    print("=" * 60)
    print("Calcul du WACC")
    print("=" * 60)
    fields = [
        ("rf", "Taux sans risque (ex: 0.035 pour 3.5%)"),
        ("beta", "Bêta de l'action (ex: 1.1)"),
        ("erp", "Equity Risk Premium (Damodaran 2026 mature: 0.0423)"),
        ("country_risk_premium", "Country Risk Premium (0 pour Canada/US)"),
        ("rd", "Coût marginal de la dette (ex: 0.05 pour 5%)"),
        ("tax_rate", "Taux d'imposition effectif (Québec: 0.265)"),
        ("market_value_equity", "Capitalisation boursière"),
        ("market_value_debt", "Valeur de marché de la dette (≈ valeur comptable si pas de bons publics)"),
    ]
    return {k: float(input(f"  {label}: ")) for k, label in fields}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            d = json.load(f)
    else:
        d = interactive()

    r = compute_wacc(
        d["rf"], d["beta"], d["erp"], d.get("country_risk_premium", 0),
        d["rd"], d["tax_rate"], d["market_value_equity"], d["market_value_debt"]
    )

    print("\n" + "=" * 60)
    print(f"WACC = {r['wacc_pct']}")
    print("=" * 60)
    print(f"\nRe (coût des CP via CAPM) : {r['re_capm']*100:.2f}%")
    print(f"Rd × (1−T)                : {r['after_tax_rd']*100:.2f}%")
    print(f"Pondération CP            : {r['weight_equity']*100:.1f}%")
    print(f"Pondération Dette         : {r['weight_debt']*100:.1f}%")


if __name__ == "__main__":
    main()
