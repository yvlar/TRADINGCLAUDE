#!/usr/bin/env python3
"""
build_thesis.py — Génère un document de thèse d'investissement structuré

Usage:
  python build_thesis.py inputs.json

Format JSON:
{
  "ticker": "CSU.TO",
  "company_name": "Constellation Software Inc.",
  "thesis_type": "compounder",
  "current_price": 4200,
  "currency": "CAD",
  "market_cap_b": 90,
  "summary": "Constellation Software est un compounder...",
  "business_description": "...",
  "moat_description": "...",
  "moat_type": "switching costs + scale",
  "key_metrics": {
    "roic_avg": 0.28,
    "revenue_growth_5y": 0.18,
    "gross_margin": 0.42,
    "fcf_margin": 0.22,
    "net_debt_ebitda": 0.5
  },
  "management": "Mark Leonard, CEO. Track record 25 ans...",
  "valuation": {
    "method": "DCF + comparables",
    "intrinsic_value": 5500,
    "margin_of_safety_pct": 0.24
  },
  "scenarios": {
    "bear": {"prob": 0.20, "impact_pct": -0.30, "conditions": "..."},
    "base": {"prob": 0.55, "impact_pct": 0.80, "conditions": "..."},
    "bull": {"prob": 0.25, "impact_pct": 2.50, "conditions": "..."}
  },
  "kill_criteria": [
    "ROIC < 18% pendant 2 ans consécutifs",
    "Mark Leonard quitte sans plan succession",
    "Croissance organique < 3% pendant 2 ans"
  ],
  "devils_advocate": [
    "Multiples acquisitions en hausse",
    "Loi des grands nombres",
    "Concurrence accrue (Vista, Roper)"
  ],
  "position_size_pct": 0.07,
  "horizon_years": 7,
  "review_date": "2027-Q4"
}
"""

import json
import sys
from datetime import datetime


def calculate_ev(scenarios: dict) -> float:
    """Calcule l'espérance pondérée."""
    return sum(s["prob"] * s["impact_pct"] for s in scenarios.values())


def build_thesis_doc(d: dict) -> str:
    """Génère le markdown de la thèse."""
    lines = []
    lines.append(f"# Thèse d'Investissement — {d['company_name']} ({d['ticker']})")
    lines.append(f"\n*Date : {datetime.now().strftime('%Y-%m-%d')}*")
    lines.append(f"*Type : {d['thesis_type']}*")
    lines.append(f"*Prix actuel : {d['current_price']} {d['currency']}*")
    lines.append(f"*Cap. boursière : {d['market_cap_b']} G {d['currency']}*\n")

    # 1. Résumé
    lines.append("## 1. Résumé exécutif\n")
    lines.append(d["summary"])

    # 2. Description
    lines.append("\n## 2. Description de l'entreprise\n")
    lines.append(d["business_description"])

    # 3. Avantage concurrentiel
    lines.append("\n## 3. Avantage concurrentiel\n")
    lines.append(f"**Type de moat** : {d['moat_type']}\n")
    lines.append(d["moat_description"])

    # 4. Économie
    lines.append("\n## 4. Économie de l'entreprise\n")
    lines.append("**Métriques clés** :")
    metrics = d.get("key_metrics", {})
    for k, v in metrics.items():
        if isinstance(v, float) and abs(v) < 5:
            lines.append(f"- {k} : {v*100:.1f}%" if k != "net_debt_ebitda" else f"- {k} : {v:.2f}×")
        else:
            lines.append(f"- {k} : {v}")

    # 5. Direction
    lines.append("\n## 5. Direction et gouvernance\n")
    lines.append(d.get("management", "(à compléter)"))

    # 6. Valorisation
    lines.append("\n## 6. Valorisation et marge de sécurité\n")
    val = d.get("valuation", {})
    lines.append(f"**Méthode** : {val.get('method', '')}")
    lines.append(f"**Valeur intrinsèque estimée** : {val.get('intrinsic_value')} {d['currency']}")
    lines.append(f"**Marge de sécurité** : {val.get('margin_of_safety_pct', 0)*100:.1f}%\n")

    # 7. Scenarios
    lines.append("\n## 7. Scenarios pondérés\n")
    scenarios = d.get("scenarios", {})
    lines.append("| Scenario | Probabilité | Impact | Conditions |")
    lines.append("|----------|-------------|--------|------------|")
    for name in ["bear", "base", "bull"]:
        s = scenarios.get(name, {})
        prob = s.get("prob", 0)
        impact = s.get("impact_pct", 0)
        cond = s.get("conditions", "")
        lines.append(f"| {name.title()} | {prob*100:.0f}% | {impact*100:+.0f}% | {cond} |")

    ev = calculate_ev(scenarios)
    horizon = d.get("horizon_years", 5)
    annualized = ((1 + ev) ** (1/horizon) - 1) * 100 if horizon > 0 else ev * 100
    lines.append(f"\n**EV pondérée** : {ev*100:+.1f}% sur {horizon} ans = ~{annualized:.1f}%/an")

    # 8. Risques et kill criteria
    lines.append("\n## 8. Risques principaux et kill criteria\n")
    lines.append("### Kill criteria (sortie automatique si déclenché) :")
    for kc in d.get("kill_criteria", []):
        lines.append(f"- {kc}")

    lines.append("\n### Devil's advocate (5 arguments contre) :")
    for da in d.get("devils_advocate", []):
        lines.append(f"- {da}")

    # 9. Décision
    lines.append("\n## 9. Décision et exécution\n")
    pos_size = d.get("position_size_pct", 0)
    lines.append(f"- **Position size** : {pos_size*100:.1f}% du portfolio")
    lines.append(f"- **Prix d'achat cible** : {d['current_price']} {d['currency']}")
    lines.append(f"- **Horizon** : {horizon}+ ans")
    lines.append(f"- **Date de révision** : {d.get('review_date', 'annuelle')}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    doc = build_thesis_doc(d)
    print(doc)


if __name__ == "__main__":
    main()
