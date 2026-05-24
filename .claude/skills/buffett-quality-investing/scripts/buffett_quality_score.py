#!/usr/bin/env python3
"""
buffett_quality_score.py — Score de qualité Buffett

Évalue les métriques quantitatives qui constituent le filtre 2 ("favorable
long-term economics") de Buffett.

Usage:
  python buffett_quality_score.py inputs.json

Format JSON:
{
  "ticker": "EXAMPLE",
  "roic_history_10y": [0.20, 0.22, 0.25, 0.23, 0.24, 0.26, 0.25, 0.24, 0.27, 0.28],
  "wacc": 0.085,
  "gross_margin_history_5y": [0.40, 0.41, 0.42, 0.41, 0.42],
  "fcf_to_revenue_5y": [0.20, 0.22, 0.21, 0.23, 0.22],
  "capex_to_da_ratio_5y": [1.1, 1.2, 1.0, 1.1, 1.2],
  "stock_based_comp_pct_revenue": 0.04
}
"""

import json
import sys
import statistics


def evaluate(d: dict) -> dict:
    """Calcule les métriques de qualité Buffett."""
    roic_hist = d.get("roic_history_10y", [])
    wacc = d.get("wacc", 0.085)
    gm_hist = d.get("gross_margin_history_5y", [])
    fcf_rev = d.get("fcf_to_revenue_5y", [])
    capex_da = d.get("capex_to_da_ratio_5y", [])
    sbc = d.get("stock_based_comp_pct_revenue", 0)

    flags = []

    # 1. ROIC
    roic_mean = statistics.mean(roic_hist) if roic_hist else 0
    roic_min = min(roic_hist) if roic_hist else 0
    roic_pass = roic_mean >= 0.15 and roic_min >= wacc
    spread_vs_wacc = roic_mean - wacc

    if roic_pass:
        flags.append(f"✓ ROIC moyen {roic_mean*100:.1f}% > 15%, min {roic_min*100:.1f}% > WACC")
    else:
        flags.append(f"✗ ROIC moyen {roic_mean*100:.1f}% (cible 15%+, min > WACC {wacc*100:.1f}%)")

    # 2. ROIC stabilité
    roic_cv = statistics.stdev(roic_hist) / roic_mean if roic_mean > 0 and len(roic_hist) > 1 else float('inf')
    stable = roic_cv < 0.20
    if stable:
        flags.append(f"✓ ROIC stable (CV {roic_cv:.2f} < 0.20)")
    else:
        flags.append(f"✗ ROIC volatil (CV {roic_cv:.2f}, cible < 0.20)")

    # 3. Marges brutes stables ou en amélioration
    gm_mean = statistics.mean(gm_hist) if gm_hist else 0
    gm_trend = (gm_hist[-1] - gm_hist[0]) if len(gm_hist) >= 2 else 0
    gm_stable = abs(gm_trend) < 0.03 or gm_trend > 0
    if gm_stable:
        flags.append(f"✓ Marges brutes stables ou en amélioration ({gm_mean*100:.1f}% en moyenne)")
    else:
        flags.append(f"✗ Marges brutes en compression ({gm_trend*100:+.1f} pts sur 5 ans)")

    # 4. FCF / Revenue
    fcf_rev_mean = statistics.mean(fcf_rev) if fcf_rev else 0
    fcf_pass = fcf_rev_mean >= 0.15
    if fcf_pass:
        flags.append(f"✓ FCF/Revenue {fcf_rev_mean*100:.1f}% ≥ 15%")
    else:
        flags.append(f"✗ FCF/Revenue {fcf_rev_mean*100:.1f}% (cible ≥ 15%)")

    # 5. Capex/D&A (proxy pour capital intensity)
    capex_da_mean = statistics.mean(capex_da) if capex_da else 0
    capital_light = capex_da_mean < 1.5
    if capital_light:
        flags.append(f"✓ Capex/D&A {capex_da_mean:.2f}× < 1.5× (capital light)")
    else:
        flags.append(f"⚠ Capex/D&A {capex_da_mean:.2f}× ≥ 1.5× (capital intensive)")

    # 6. SBC pas excessive
    sbc_ok = sbc < 0.05
    if sbc_ok:
        flags.append(f"✓ SBC {sbc*100:.1f}% < 5% du revenu")
    else:
        flags.append(f"✗ SBC {sbc*100:.1f}% ≥ 5% (dilution excessive)")

    # Score global
    passed = sum(1 for f in flags if f.startswith("✓"))
    total = len(flags)

    if passed == total:
        verdict = "✅ BUFFETT QUALITY — wonderful business candidate"
        flag = "vert"
    elif passed >= total - 1:
        verdict = "🟡 PROCHE QUALITY — un seul critère manqué, à investiguer"
        flag = "jaune"
    else:
        verdict = "❌ PAS WONDERFUL BUSINESS — multiples critères non atteints"
        flag = "rouge"

    return {
        "ticker": d.get("ticker", "?"),
        "roic_mean_pct": round(roic_mean * 100, 1),
        "roic_min_pct": round(roic_min * 100, 1),
        "roic_cv": round(roic_cv, 3) if roic_cv != float('inf') else None,
        "spread_vs_wacc_pts": round(spread_vs_wacc * 100, 1),
        "gm_mean_pct": round(gm_mean * 100, 1),
        "gm_trend_pts": round(gm_trend * 100, 2),
        "fcf_rev_pct": round(fcf_rev_mean * 100, 1),
        "capex_da_ratio": round(capex_da_mean, 2),
        "sbc_pct": round(sbc * 100, 2),
        "flags": flags,
        "score": f"{passed}/{total}",
        "verdict": verdict,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        d = json.load(f)

    r = evaluate(d)

    print("=" * 75)
    print(f"BUFFETT QUALITY SCORE — {r['ticker']}")
    print("=" * 75)

    print(f"\nMétriques:")
    print(f"  ROIC moyen 10 ans  : {r['roic_mean_pct']}%")
    print(f"  ROIC minimum       : {r['roic_min_pct']}%")
    print(f"  Spread vs WACC     : {r['spread_vs_wacc_pts']:+.1f} pts")
    print(f"  ROIC CV (stabilité): {r['roic_cv']}")
    print(f"  Marge brute moy.   : {r['gm_mean_pct']}%")
    print(f"  Marge brute trend  : {r['gm_trend_pts']:+.1f} pts sur 5 ans")
    print(f"  FCF/Revenue        : {r['fcf_rev_pct']}%")
    print(f"  Capex/D&A          : {r['capex_da_ratio']}×")
    print(f"  SBC % revenu       : {r['sbc_pct']}%")

    print(f"\nÉvaluation:")
    for f in r["flags"]:
        print(f"  {f}")

    print(f"\nScore: {r['score']}")
    print(f"\n{r['verdict']}")


if __name__ == "__main__":
    main()
