#!/usr/bin/env python3
"""
compute_dcf.py — DCF avec matrice de sensibilité 5×5

Calcule la valeur intrinsèque d'une entreprise et sa sensibilité au WACC et g.

Usage:
  python compute_dcf.py inputs.json
  python compute_dcf.py --help

Format JSON:
{
  "fcf_projections": [1500, 1650, 1815, 1996, 2196],   # 5 ans de FCF projetés
  "wacc": 0.085,                                         # 8.5%
  "perpetual_growth": 0.025,                             # 2.5%
  "net_debt": 5000,
  "cash_excedentaire": 1500,
  "shares_diluted": 1000,
  "currency": "CAD",
  "company": "Example Corp"
}

Référence: references/dcf.md
"""

import json
import sys
from pathlib import Path


def compute_dcf(fcf_list: list, wacc: float, g: float,
                net_debt: float, excess_cash: float, shares: float) -> dict:
    """Calcule la VE et la valeur des CP."""
    n = len(fcf_list)

    # Valeur actualisée des FCF projetés
    pv_fcf = sum(fcf / (1 + wacc) ** (t + 1) for t, fcf in enumerate(fcf_list))

    # Valeur terminale (Gordon)
    fcf_terminal = fcf_list[-1] * (1 + g)
    if wacc <= g:
        return {"error": "WACC doit être > g pour que Gordon converge"}
    vt = fcf_terminal / (wacc - g)
    pv_vt = vt / (1 + wacc) ** n

    # Valeur d'entreprise
    ev = pv_fcf + pv_vt

    # Valeur des capitaux propres
    equity = ev - net_debt + excess_cash

    # Prix par action
    price_per_share = equity / shares

    return {
        "pv_fcf": round(pv_fcf, 1),
        "pv_terminal_value": round(pv_vt, 1),
        "enterprise_value": round(ev, 1),
        "equity_value": round(equity, 1),
        "price_per_share": round(price_per_share, 2),
        "vt_share_of_ev": f"{round(pv_vt / ev * 100, 1)}%",
    }


def sensitivity_matrix(fcf_list, wacc_base, g_base, net_debt, excess_cash, shares):
    """Matrice 5×5 (WACC ± 1% × g ± 0.5%)."""
    wacc_steps = [wacc_base - 0.01, wacc_base - 0.005, wacc_base,
                  wacc_base + 0.005, wacc_base + 0.01]
    g_steps = [g_base - 0.01, g_base - 0.005, g_base,
               g_base + 0.005, g_base + 0.01]

    matrix = []
    for w in wacc_steps:
        row = []
        for g in g_steps:
            r = compute_dcf(fcf_list, w, g, net_debt, excess_cash, shares)
            if "error" in r:
                row.append(None)
            else:
                row.append(r["price_per_share"])
        matrix.append(row)

    return {
        "wacc_steps": [round(w * 100, 2) for w in wacc_steps],
        "g_steps": [round(g * 100, 2) for g in g_steps],
        "prices": matrix,
    }


def print_matrix(m: dict, currency: str):
    """Imprime la matrice de sensibilité."""
    print("\n" + "=" * 72)
    print("MATRICE DE SENSIBILITÉ — Prix par action en " + currency)
    print("=" * 72)

    # En-tête colonnes (g)
    header = "WACC \\ g  |"
    for g in m["g_steps"]:
        header += f"  g={g:5.2f}% |"
    print(header)
    print("-" * len(header))

    # Lignes (WACC)
    for i, w in enumerate(m["wacc_steps"]):
        row = f"WACC={w:5.2f}% |"
        for price in m["prices"][i]:
            if price is None:
                row += "    n/a    |"
            else:
                row += f" {price:9.2f} |"
        print(row)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Erreur: {path} introuvable", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        d = json.load(f)

    base = compute_dcf(
        d["fcf_projections"], d["wacc"], d["perpetual_growth"],
        d["net_debt"], d["cash_excedentaire"], d["shares_diluted"]
    )

    currency = d.get("currency", "USD")
    company = d.get("company", "Entreprise")

    print("=" * 72)
    print(f"DCF — {company}")
    print("=" * 72)
    print(f"WACC: {d['wacc']*100:.2f}%   |   g (perpétuel): {d['perpetual_growth']*100:.2f}%")
    print(f"Période de projection: {len(d['fcf_projections'])} ans")
    print()
    print(f"PV des FCF projetés       : {base['pv_fcf']:,.1f} {currency}")
    print(f"PV de la valeur terminale : {base['pv_terminal_value']:,.1f} {currency}")
    print(f"  → part de la VT dans VE : {base['vt_share_of_ev']}")
    print(f"Valeur d'entreprise       : {base['enterprise_value']:,.1f} {currency}")
    print(f"Valeur des capitaux propres: {base['equity_value']:,.1f} {currency}")
    print(f"PRIX PAR ACTION (centrale): {base['price_per_share']:,.2f} {currency}")

    if float(base['vt_share_of_ev'].rstrip('%')) > 75:
        print("\n⚠  La valeur terminale représente plus de 75% de la VE.")
        print("   Le résultat est très sensible aux hypothèses long-terme.")

    matrix = sensitivity_matrix(
        d["fcf_projections"], d["wacc"], d["perpetual_growth"],
        d["net_debt"], d["cash_excedentaire"], d["shares_diluted"]
    )
    print_matrix(matrix, currency)

    # Fourchette
    flat_prices = [p for row in matrix["prices"] for p in row if p is not None]
    print(f"\nFourchette de la matrice : {min(flat_prices):.2f} – {max(flat_prices):.2f} {currency}")
    print(f"Centrale (base case)     : {base['price_per_share']:.2f} {currency}")
    print(f"Dispersion               : {(max(flat_prices)/min(flat_prices) - 1)*100:.1f}%")


if __name__ == "__main__":
    main()
