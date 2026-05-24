#!/usr/bin/env python3
"""
cycle_position.py — Position sur le pendule du cycle (Marks)

Évalue la position du pendule du sentiment de marché en agrégeant ~10
indicateurs et calcule l'allocation cash/equity recommandée.

Usage:
  python cycle_position.py inputs.json

Format JSON:
{
  "date": "2026-04",
  "indicators": {
    "cape_shiller": 32,
    "buffett_indicator_pct_gdp": 165,
    "high_yield_spread_bps": 320,
    "vix": 16,
    "aaii_bull_pct": 45,
    "aaii_bear_pct": 28,
    "ipo_activity": "elevated",
    "spac_volume": "low",
    "margin_debt_growth_pct": 15,
    "media_sentiment": "optimistic"
  }
}
"""

import json
import sys


def score_indicator(name: str, value) -> int:
    """Retourne -2 (panique) à +2 (euphorie)."""
    if name == "cape_shiller":
        if value > 35: return 2
        elif value > 28: return 1
        elif value < 13: return -2
        elif value < 17: return -1
        return 0
    if name == "buffett_indicator_pct_gdp":
        if value > 180: return 2
        elif value > 130: return 1
        elif value < 60: return -2
        elif value < 90: return -1
        return 0
    if name == "high_yield_spread_bps":
        if value < 250: return 2  # spreads très bas = euphorie
        elif value < 400: return 1
        elif value > 1500: return -2  # spreads très hauts = panique
        elif value > 800: return -1
        return 0
    if name == "vix":
        if value < 12: return 2
        elif value < 16: return 1
        elif value > 40: return -2
        elif value > 28: return -1
        return 0
    if name == "aaii_bull_pct":
        if value > 50: return 2
        elif value > 40: return 1
        elif value < 20: return -2
        elif value < 30: return -1
        return 0
    if name == "aaii_bear_pct":
        if value < 20: return 1
        elif value > 55: return -2
        elif value > 40: return -1
        return 0
    if name in ("ipo_activity", "spac_volume", "media_sentiment"):
        mapping = {"frenzy": 2, "elevated": 1, "normal": 0, "low": -1, "minimal": -2}
        sentiment_map = {"euphoric": 2, "optimistic": 1, "neutral": 0, "skeptical": -1, "panicked": -2}
        if name == "media_sentiment":
            return sentiment_map.get(value, 0)
        return mapping.get(value, 0)
    if name == "margin_debt_growth_pct":
        if value > 25: return 2
        elif value > 10: return 1
        elif value < -15: return -2
        elif value < -5: return -1
        return 0
    return 0


def evaluate(data: dict) -> dict:
    """Agrège les indicateurs."""
    indicators = data["indicators"]
    scores = {}
    for name, value in indicators.items():
        scores[name] = (value, score_indicator(name, value))

    total_score = sum(s for _, s in scores.values())
    n = len(scores)
    # Normalise sur -10 à +10
    normalized = total_score / n * 5

    # Allocation
    if normalized >= 8:
        zone = "Euphorie extrême"
        cash, equity = "60-80%", "20-40%"
        action = "Liquider agressivement, accumuler cash. Refuser FOMO."
    elif normalized >= 3:
        zone = "Optimisme normal"
        cash, equity = "20-40%", "60-80%"
        action = "Sélectivité accrue, vendre les positions chères."
    elif normalized >= -2:
        zone = "Neutre"
        cash, equity = "10-20%", "80-90%"
        action = "Allocation standard. Pas d'ajustement majeur."
    elif normalized >= -7:
        zone = "Pessimisme normal"
        cash, equity = "0-10%", "90-100%"
        action = "Acheter graduellement les opportunités."
    else:
        zone = "Panique extrême"
        cash, equity = "0%", "100%+"
        action = "Déployer agressivement. Considérer levier modeste."

    return {
        "date": data.get("date", "?"),
        "scores": scores,
        "total_raw": total_score,
        "normalized_score": round(normalized, 1),
        "zone": zone,
        "allocation_cash": cash,
        "allocation_equity": equity,
        "action": action,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    r = evaluate(data)

    print("=" * 75)
    print(f"POSITION SUR LE PENDULE DU CYCLE — {r['date']}")
    print("=" * 75)

    print(f"\n{'Indicateur':<32} {'Valeur':<15} {'Score'}")
    print("-" * 75)
    for name, (value, score) in r["scores"].items():
        symbol = "📈" if score > 0 else "📉" if score < 0 else "➖"
        print(f"{name:<32} {str(value):<15} {symbol} {score:+d}")

    print(f"\n{'─' * 75}")
    print(f"Score normalisé (-10 à +10) : {r['normalized_score']:+.1f}")
    print(f"Zone du pendule              : {r['zone']}")
    print(f"\nAllocation recommandée:")
    print(f"  Cash    : {r['allocation_cash']}")
    print(f"  Equity  : {r['allocation_equity']}")
    print(f"\nAction : {r['action']}")

    # Visualisation pendule
    print("\n" + "─" * 75)
    pos = int((r['normalized_score'] + 10) / 2)
    bar = "─" * pos + "●" + "─" * (10 - pos)
    print("Panique ────────────── Neutre ────────────── Euphorie")
    print(f"        {bar}")


if __name__ == "__main__":
    main()
