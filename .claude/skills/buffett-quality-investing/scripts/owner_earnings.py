#!/usr/bin/env python3
"""
owner_earnings.py — Calcul des Owner Earnings (méthode Buffett 1986)

Usage:
  python owner_earnings.py inputs.json

Format JSON:
{
  "ticker": "AAPL",
  "fiscal_year": "2023",
  "net_income": 96995,
  "depreciation_amortization": 11519,
  "stock_based_comp": 10833,
  "treat_sbc_as_noncash": false,
  "other_noncash": 1000,
  "capex_total": 10959,
  "capex_maintenance_estimate": 9000,
  "wc_change_avg_5y": 500,
  "shares_outstanding": 15550,
  "market_cap": 3000000,
  "net_debt": 50000
}
"""

import json
import sys


def calculate_owner_earnings(d: dict) -> dict:
    """Calcule Owner Earnings avec décomposition."""
    ni = d.get("net_income", 0)
    da = d.get("depreciation_amortization", 0)
    sbc = d.get("stock_based_comp", 0)
    treat_sbc_as_noncash = d.get("treat_sbc_as_noncash", False)
    other = d.get("other_noncash", 0)
    capex_total = d.get("capex_total", 0)
    capex_maint = d.get("capex_maintenance_estimate", 0)
    wc = d.get("wc_change_avg_5y", 0)

    # Note: la pratique moderne est plutôt de ne PAS traiter SBC comme purely non-cash
    sbc_added = sbc if treat_sbc_as_noncash else 0
    sbc_subtracted_warning = sbc if not treat_sbc_as_noncash else 0

    owner_earnings = ni + da + sbc_added + other - capex_maint - wc

    # Comparaisons
    fcf_standard = ni + da + sbc + other - capex_total - wc
    fcf_strict = ni + da + other - capex_total - wc

    # Yields
    market_cap = d.get("market_cap", 0)
    net_debt = d.get("net_debt", 0)
    ev = market_cap + net_debt

    oe_yield = owner_earnings / ev if ev > 0 else 0
    fcf_yield = fcf_standard / ev if ev > 0 else 0

    # Per share
    shares = d.get("shares_outstanding", 0)
    oe_per_share = owner_earnings / shares if shares > 0 else 0

    return {
        "ticker": d.get("ticker", "?"),
        "fiscal_year": d.get("fiscal_year", "?"),
        "net_income": ni,
        "da": da,
        "sbc": sbc,
        "sbc_treatment": "non-cash (added back)" if treat_sbc_as_noncash else "cash cost (NOT added)",
        "capex_total": capex_total,
        "capex_maintenance": capex_maint,
        "capex_growth": capex_total - capex_maint,
        "owner_earnings": round(owner_earnings, 1),
        "fcf_standard": round(fcf_standard, 1),
        "fcf_strict": round(fcf_strict, 1),
        "owner_earnings_per_share": round(oe_per_share, 2),
        "owner_earnings_yield": f"{oe_yield*100:.2f}%",
        "fcf_yield_standard": f"{fcf_yield*100:.2f}%",
        "verdict": (
            "🟢 ATTRACTIF (yield >= 6%)" if oe_yield >= 0.06
            else "🟡 RAISONNABLE (yield 4-6%)" if oe_yield >= 0.04
            else "🔴 CHER (yield < 4%)"
        ),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    r = calculate_owner_earnings(d)

    print("=" * 75)
    print(f"OWNER EARNINGS — {r['ticker']} FY{r['fiscal_year']}")
    print("=" * 75)

    print(f"\nDécomposition (en M$):")
    print(f"  Net Income            : {r['net_income']:>12}")
    print(f"  + D&A (non-cash)      : {r['da']:>12}")
    print(f"  + SBC                 : {r['sbc']:>12}  ← traitement: {r['sbc_treatment']}")
    print(f"  − Capex maintenance   : {r['capex_maintenance']:>12}")
    print(f"  ─" * 35)
    print(f"  = OWNER EARNINGS      : {r['owner_earnings']:>12}")

    print(f"\nComparaisons:")
    print(f"  FCF standard (capex total)         : {r['fcf_standard']}")
    print(f"  FCF strict (capex total + SBC cash): {r['fcf_strict']}")
    print(f"  Capex de croissance estimé         : {r['capex_growth']}")

    print(f"\nYields:")
    print(f"  Owner Earnings yield  : {r['owner_earnings_yield']}")
    print(f"  FCF standard yield    : {r['fcf_yield_standard']}")

    print(f"\nOwner Earnings/action : {r['owner_earnings_per_share']}")

    print(f"\n{r['verdict']}")


if __name__ == "__main__":
    main()
