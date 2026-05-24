#!/usr/bin/env python3
"""
calc_pbr.py — Calcul du PBR moyen pondéré après plusieurs transactions

Suit le PBR (ACB) selon la méthode canadienne obligatoire (moyenne pondérée).
Gère achats, ventes, DRIP, retours de capital, splits.

Usage:
  python calc_pbr.py transactions.json
  python calc_pbr.py    # mode interactif

Format JSON:
{
  "ticker": "XYZ",
  "transactions": [
    {"date": "2024-01-15", "type": "buy", "shares": 100, "price": 50.00, "fees": 10.00},
    {"date": "2024-06-20", "type": "buy", "shares": 100, "price": 60.00, "fees": 10.00},
    {"date": "2024-09-10", "type": "drip", "shares": 2, "price": 55.00},
    {"date": "2024-11-15", "type": "roc", "amount": 200},
    {"date": "2024-12-15", "type": "sell", "shares": 50, "price": 70.00, "fees": 10.00}
  ]
}

Référence: references/pbr-acb.md
"""

import json
import sys
from pathlib import Path


def process_transactions(transactions: list) -> list:
    """Traite chaque transaction et garde l'historique du PBR."""
    shares = 0
    total_cost = 0.0
    history = []

    for tx in transactions:
        date = tx.get("date", "?")
        ttype = tx["type"].lower()

        if ttype == "buy":
            cost = tx["shares"] * tx["price"] + tx.get("fees", 0)
            shares += tx["shares"]
            total_cost += cost
            event = f"Achat {tx['shares']} @ {tx['price']:.2f} + frais {tx.get('fees', 0):.2f}"

        elif ttype == "drip":
            # DRIP: dividende réinvesti, ajoute au coût total
            cost = tx["shares"] * tx["price"]
            shares += tx["shares"]
            total_cost += cost
            event = f"DRIP {tx['shares']} @ {tx['price']:.2f}"

        elif ttype == "roc":
            # Retour de capital: diminue le PBR
            total_cost -= tx["amount"]
            event = f"Retour de capital -{tx['amount']:.2f}"
            if total_cost < 0:
                event += " ⚠ PBR à zéro, surplus = gain en capital"
                gain = -total_cost
                total_cost = 0
                event += f" ({gain:.2f}$)"

        elif ttype == "sell":
            if tx["shares"] > shares:
                event = f"Vente {tx['shares']} ⚠ ERREUR: dépasse position {shares}"
            else:
                pbr_per_share = total_cost / shares if shares > 0 else 0
                cost_attributed = pbr_per_share * tx["shares"]
                proceeds = tx["shares"] * tx["price"] - tx.get("fees", 0)
                gain = proceeds - cost_attributed
                shares -= tx["shares"]
                total_cost -= cost_attributed
                event = (f"Vente {tx['shares']} @ {tx['price']:.2f} | "
                        f"Produit: {proceeds:.2f} | "
                        f"PBR attribué: {cost_attributed:.2f} | "
                        f"Gain/perte: {gain:+.2f}")

        elif ttype == "split":
            # Split N:1 (ratio dans tx["ratio"])
            ratio = tx["ratio"]
            shares = int(shares * ratio)
            event = f"Split {ratio}:1 → {shares} actions, PBR/action / {ratio}"

        else:
            event = f"⚠ Type inconnu: {ttype}"

        pbr_per_share = total_cost / shares if shares > 0 else 0
        history.append({
            "date": date,
            "event": event,
            "shares": shares,
            "total_cost": round(total_cost, 2),
            "pbr_per_share": round(pbr_per_share, 4),
        })

    return history


def interactive():
    print("=" * 60)
    print("Calculateur de PBR — saisie interactive")
    print("=" * 60)
    ticker = input("Ticker: ").strip()
    transactions = []
    print("\nEntrer les transactions (ligne vide pour terminer)")
    print("Format: type;shares;price;fees    (ex: buy;100;50.00;10.00)")
    print("Types: buy, sell, drip, roc, split")
    while True:
        line = input("> ").strip()
        if not line:
            break
        parts = line.split(";")
        ttype = parts[0]
        if ttype in ("buy", "sell", "drip"):
            transactions.append({
                "type": ttype,
                "shares": float(parts[1]),
                "price": float(parts[2]),
                "fees": float(parts[3]) if len(parts) > 3 else 0,
            })
        elif ttype == "roc":
            transactions.append({"type": "roc", "amount": float(parts[1])})
        elif ttype == "split":
            transactions.append({"type": "split", "ratio": float(parts[1])})

    return {"ticker": ticker, "transactions": transactions}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = interactive()

    print(f"\n{'='*78}")
    print(f"HISTORIQUE PBR — {data.get('ticker', '?')}")
    print(f"{'='*78}")

    history = process_transactions(data["transactions"])
    for h in history:
        print(f"\n{h['date']}: {h['event']}")
        print(f"  → Actions: {h['shares']} | Coût total: {h['total_cost']:.2f} | PBR/action: {h['pbr_per_share']:.4f}")

    if history:
        last = history[-1]
        print(f"\n{'='*78}")
        print(f"POSITION FINALE")
        print(f"  Actions:        {last['shares']}")
        print(f"  Coût total:     {last['total_cost']:.2f}")
        print(f"  PBR/action:     {last['pbr_per_share']:.4f}")
        print(f"{'='*78}")


if __name__ == "__main__":
    main()
