#!/usr/bin/env python3
"""
compute_mscore.py — Beneish M-Score (1999, 8 variables)

Détecte la probabilité de manipulation des bénéfices.

Usage:
  python compute_mscore.py                         # mode interactif (stdin)
  python compute_mscore.py data.json               # mode batch (fichier JSON)
  python compute_mscore.py --help                  # aide

Format JSON attendu (toutes les valeurs en devise et unités cohérentes):
{
  "current": {
    "receivables": 1500,
    "sales": 10000,
    "cogs": 6000,
    "current_assets": 3500,
    "ppe_net": 5000,
    "securities": 200,
    "total_assets": 12000,
    "depreciation": 800,
    "sga": 2000,
    "net_income": 1200,
    "cfo": 1100,
    "current_liabilities": 1800,
    "long_term_debt": 3000
  },
  "previous": {
    ... mêmes champs pour T-1 ...
  }
}

Référence: references/beneish-m-score.md
"""

import json
import sys
from pathlib import Path


def compute_mscore(curr: dict, prev: dict) -> dict:
    """Calcule le M-Score de Beneish à partir des données T et T-1."""

    # 1. DSRI — Days Sales in Receivables Index
    dsri = (curr["receivables"] / curr["sales"]) / (prev["receivables"] / prev["sales"])

    # 2. GMI — Gross Margin Index
    gm_curr = (curr["sales"] - curr["cogs"]) / curr["sales"]
    gm_prev = (prev["sales"] - prev["cogs"]) / prev["sales"]
    gmi = gm_prev / gm_curr

    # 3. AQI — Asset Quality Index
    aq_curr = 1 - (curr["current_assets"] + curr["ppe_net"] + curr["securities"]) / curr["total_assets"]
    aq_prev = 1 - (prev["current_assets"] + prev["ppe_net"] + prev["securities"]) / prev["total_assets"]
    aqi = aq_curr / aq_prev

    # 4. SGI — Sales Growth Index
    sgi = curr["sales"] / prev["sales"]

    # 5. DEPI — Depreciation Index
    dep_rate_curr = curr["depreciation"] / (curr["depreciation"] + curr["ppe_net"])
    dep_rate_prev = prev["depreciation"] / (prev["depreciation"] + prev["ppe_net"])
    depi = dep_rate_prev / dep_rate_curr

    # 6. SGAI — SG&A Index
    sgai = (curr["sga"] / curr["sales"]) / (prev["sga"] / prev["sales"])

    # 7. TATA — Total Accruals to Total Assets
    tata = (curr["net_income"] - curr["cfo"]) / curr["total_assets"]

    # 8. LVGI — Leverage Index
    lvg_curr = (curr["current_liabilities"] + curr["long_term_debt"]) / curr["total_assets"]
    lvg_prev = (prev["current_liabilities"] + prev["long_term_debt"]) / prev["total_assets"]
    lvgi = lvg_curr / lvg_prev

    # M-Score (8 variables)
    m_score = (
        -4.84
        + 0.92 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    # Interprétation
    if m_score <= -2.22:
        verdict = "FAIBLE probabilité de manipulation"
        flag = "vert"
    elif m_score <= -1.78:
        verdict = "ZONE GRISE — investiguer"
        flag = "jaune"
    else:
        verdict = "PROBABILITÉ ÉLEVÉE de manipulation"
        flag = "rouge"

    return {
        "m_score": round(m_score, 3),
        "verdict": verdict,
        "flag": flag,
        "components": {
            "DSRI": round(dsri, 3),
            "GMI": round(gmi, 3),
            "AQI": round(aqi, 3),
            "SGI": round(sgi, 3),
            "DEPI": round(depi, 3),
            "SGAI": round(sgai, 3),
            "TATA": round(tata, 4),
            "LVGI": round(lvgi, 3),
        },
        "thresholds": {
            "low_risk": "M ≤ -2.22",
            "grey_zone": "-2.22 < M ≤ -1.78",
            "high_risk": "M > -1.78",
        },
    }


def interactive_input() -> dict:
    """Mode interactif: demande les valeurs une par une."""
    fields = [
        "receivables", "sales", "cogs", "current_assets", "ppe_net",
        "securities", "total_assets", "depreciation", "sga", "net_income",
        "cfo", "current_liabilities", "long_term_debt"
    ]
    print("=" * 60)
    print("Beneish M-Score — saisie interactive")
    print("=" * 60)
    print("\nEntrer les valeurs pour l'exercice T (le plus récent):\n")
    curr = {}
    for f in fields:
        curr[f] = float(input(f"  {f}: "))
    print("\nEntrer les valeurs pour l'exercice T-1:\n")
    prev = {}
    for f in fields:
        prev[f] = float(input(f"  {f}: "))
    return {"current": curr, "previous": prev}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        # Mode fichier JSON
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"Erreur: fichier introuvable: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            data = json.load(f)
    else:
        # Mode interactif
        data = interactive_input()

    if "current" not in data or "previous" not in data:
        print("Erreur: le JSON doit contenir 'current' et 'previous'", file=sys.stderr)
        sys.exit(1)

    result = compute_mscore(data["current"], data["previous"])

    print("\n" + "=" * 60)
    print(f"M-SCORE = {result['m_score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flag: {result['flag'].upper()}")
    print("=" * 60)
    print("\nComposantes:")
    for k, v in result["components"].items():
        print(f"  {k:6s} = {v}")
    print("\nSeuils:")
    for k, v in result["thresholds"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
