#!/usr/bin/env python3
"""
dcf_story.py — DCF en deux phases pour story stocks (méthode Damodaran)

Modélise explicitement la transition de l'état initial (souvent non rentable)
vers l'état stable (croissance perpétuelle), avec marges et réinvestissement
qui évoluent année par année.

Usage:
  python dcf_story.py inputs.json

Format JSON:
{
  "ticker": "EXAMPLE",
  "revenue_initial": 5000,
  "revenue_growth_path": [0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.07, 0.05, 0.03],
  "operating_margin_path": [-0.15, -0.05, 0.02, 0.08, 0.12, 0.16, 0.18, 0.20, 0.20, 0.20],
  "reinvestment_rate_path": [0.80, 0.70, 0.60, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20],
  "tax_rate": 0.25,
  "wacc": 0.09,
  "terminal_growth": 0.025,
  "terminal_roic": 0.20,
  "shares_outstanding": 1000,
  "net_debt": -500,
  "probability_survival": 0.75,
  "value_if_failure_per_share": 5.0
}
"""

import json
import sys


def project_dcf(d: dict) -> dict:
    """Projette les flux et calcule la valeur intrinsèque."""
    rev = d["revenue_initial"]
    growth_path = d["revenue_growth_path"]
    margin_path = d["operating_margin_path"]
    reinv_path = d["reinvestment_rate_path"]
    tax = d["tax_rate"]
    wacc = d["wacc"]
    g_term = d["terminal_growth"]
    roic_term = d["terminal_roic"]
    shares = d["shares_outstanding"]
    net_debt = d["net_debt"]

    n = len(growth_path)
    if not (len(margin_path) == n == len(reinv_path)):
        raise ValueError("Tous les paths doivent avoir la même longueur")

    flows = []
    for t in range(n):
        rev *= (1 + growth_path[t])
        ebit = rev * margin_path[t]
        ebit_after_tax = ebit * (1 - tax) if ebit > 0 else ebit  # NOL si pertes
        reinvestment = ebit_after_tax * reinv_path[t] if ebit_after_tax > 0 else 0
        fcf = ebit_after_tax - reinvestment
        flows.append({
            "year": t + 1,
            "revenue": round(rev, 1),
            "growth": f"{growth_path[t]*100:.1f}%",
            "margin": f"{margin_path[t]*100:.1f}%",
            "ebit": round(ebit, 1),
            "ebit_aftertax": round(ebit_after_tax, 1),
            "reinvestment": round(reinvestment, 1),
            "fcf": round(fcf, 1),
        })

    # Terminal value
    last_ebit_aftertax = flows[-1]["ebit_aftertax"]
    terminal_reinv_rate = g_term / roic_term
    terminal_fcf = last_ebit_aftertax * (1 + g_term) * (1 - terminal_reinv_rate)
    terminal_value = terminal_fcf / (wacc - g_term)

    # PV des flows
    pv_flows = sum(f["fcf"] / (1 + wacc) ** f["year"] for f in flows)
    pv_terminal = terminal_value / (1 + wacc) ** n

    enterprise_value = pv_flows + pv_terminal
    equity_value = enterprise_value - net_debt
    value_per_share_success = equity_value / shares

    # Test cohérence dynamique sur la phase terminale
    coherence_ok = abs(g_term - roic_term * terminal_reinv_rate) < 0.001

    # Probabilité de survie
    p_survival = d.get("probability_survival", 1.0)
    failure_value = d.get("value_if_failure_per_share", 0)
    expected_value = p_survival * value_per_share_success + (1 - p_survival) * failure_value

    return {
        "flows": flows,
        "pv_flows": round(pv_flows, 1),
        "terminal_value": round(terminal_value, 1),
        "pv_terminal": round(pv_terminal, 1),
        "tv_pct_of_ev": round(pv_terminal / enterprise_value * 100, 1),
        "enterprise_value": round(enterprise_value, 1),
        "equity_value": round(equity_value, 1),
        "value_per_share_success": round(value_per_share_success, 2),
        "expected_value": round(expected_value, 2),
        "p_survival": p_survival,
        "coherence_terminal_ok": coherence_ok,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    r = project_dcf(d)

    print("=" * 78)
    print(f"DCF DEUX PHASES — {d.get('ticker', '?')}")
    print("=" * 78)

    print(f"\n{'Année':<6} {'Revenu':>10} {'Croiss.':>8} {'Marge':>8} {'EBIT':>10} {'FCF':>10}")
    print("-" * 78)
    for f in r["flows"]:
        print(f"{f['year']:<6} {f['revenue']:>10} {f['growth']:>8} {f['margin']:>8} "
              f"{f['ebit']:>10} {f['fcf']:>10}")

    print(f"\n{'─' * 78}")
    print(f"PV flows phase 1     : {r['pv_flows']:>12}")
    print(f"PV valeur terminale  : {r['pv_terminal']:>12} ({r['tv_pct_of_ev']:.1f}% EV)")
    print(f"Valeur d'entreprise  : {r['enterprise_value']:>12}")
    print(f"Valeur des fonds prop: {r['equity_value']:>12}")
    print(f"\n{'═' * 78}")
    print(f"Valeur/action si SUCCÈS    : {r['value_per_share_success']}")
    print(f"Probabilité de survie      : {r['p_survival']*100:.0f}%")
    print(f"Valeur/action ESPÉRÉE      : {r['expected_value']}")
    print(f"{'═' * 78}")

    if r["tv_pct_of_ev"] > 75:
        print("\n⚠ VT > 75% de l'EV — la valorisation dépend fortement du terminal.")
        print("  Sensibilité accrue aux paramètres terminaux.")

    if not r["coherence_terminal_ok"]:
        print("\n❌ INCOHÉRENCE TERMINALE — g_term ≠ ROIC × Reinvestment_rate")


if __name__ == "__main__":
    main()
