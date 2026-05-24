#!/usr/bin/env python3
"""
calc_norberts_gambit.py — Comparaison Norbert's Gambit vs conversion classique

Calcule l'économie réalisée en utilisant le Norbert's Gambit pour conversion CAD↔USD.

Usage:
  python calc_norberts_gambit.py --montant 50000 --taux_change 1.35 --spread_courtier 0.0175
"""

import argparse


def calc_conversion_classique(montant_cad: float, taux: float, spread: float) -> dict:
    """Conversion via le service standard du courtier."""
    taux_effectif = taux * (1 + spread)
    montant_usd = montant_cad / taux_effectif
    cout_total = montant_cad - (montant_usd * taux)
    return {
        "methode": "Conversion classique (spread courtier)",
        "taux_effectif": taux_effectif,
        "montant_usd_recu": montant_usd,
        "cout_total_cad": cout_total,
    }


def calc_norberts_gambit(montant_cad: float, taux: float,
                          commission_par_trade: float = 9.95,
                          spread_titre: float = 0.0015,
                          frais_journalisation: float = 0) -> dict:
    """Norbert's Gambit avec DLR.TO/DLR.U.TO."""
    # Achat en CAD: prix légèrement supérieur au mid (côté ask)
    achat_cout = montant_cad - commission_par_trade
    # Le NAV reflète le taux de change ; on perd le spread bid-ask au passage
    parts_cad = achat_cout / (taux * (1 + spread_titre / 2))
    # Journalisation (généralement gratuite mais variable)
    parts_usd = parts_cad
    # Vente en USD au bid
    vente_brut_usd = parts_usd * 1.0 * (1 - spread_titre / 2)  # DLR.U.TO ~= 1 USD
    vente_net_usd = vente_brut_usd - (commission_par_trade / taux)

    # Coût total en CAD équivalent
    montant_usd_obtenu = vente_net_usd
    cout_total_cad = montant_cad - (montant_usd_obtenu * taux) - frais_journalisation

    return {
        "methode": "Norbert's Gambit (DLR.TO ↔ DLR.U.TO)",
        "montant_usd_recu": montant_usd_obtenu,
        "cout_total_cad": cout_total_cad,
        "commissions": commission_par_trade * 2,
        "frais_journalisation": frais_journalisation,
    }


def main():
    parser = argparse.ArgumentParser(description="Norbert's Gambit calculator")
    parser.add_argument("--montant", type=float, default=None, help="Montant CAD à convertir")
    parser.add_argument("--taux_change", type=float, default=None, help="Taux mid CAD/USD (ex: 1.35)")
    parser.add_argument("--spread_courtier", type=float, default=0.0175, help="Spread courtier classique (def 1.75%)")
    parser.add_argument("--commission", type=float, default=9.95, help="Commission par trade")
    parser.add_argument("--frais_journalisation", type=float, default=0, help="Frais de journalisation")
    args = parser.parse_args()

    if args.montant is None:
        args.montant = float(input("Montant CAD à convertir: "))
    if args.taux_change is None:
        args.taux_change = float(input("Taux mid CAD/USD (ex: 1.35): "))

    classique = calc_conversion_classique(args.montant, args.taux_change, args.spread_courtier)
    gambit = calc_norberts_gambit(args.montant, args.taux_change, args.commission,
                                   frais_journalisation=args.frais_journalisation)

    print("\n" + "=" * 70)
    print(f"COMPARAISON CONVERSION CAD → USD")
    print(f"Montant: {args.montant:,.2f} CAD | Taux mid: {args.taux_change}")
    print("=" * 70)

    print(f"\n📕 {classique['methode']}")
    print(f"  Taux effectif:    {classique['taux_effectif']:.4f}")
    print(f"  USD reçus:        {classique['montant_usd_recu']:,.2f} USD")
    print(f"  Coût total:       {classique['cout_total_cad']:,.2f} CAD")
    print(f"  En % du montant:  {classique['cout_total_cad'] / args.montant * 100:.2f}%")

    print(f"\n📗 {gambit['methode']}")
    print(f"  USD reçus:        {gambit['montant_usd_recu']:,.2f} USD")
    print(f"  Coût total:       {gambit['cout_total_cad']:,.2f} CAD")
    print(f"  En % du montant:  {gambit['cout_total_cad'] / args.montant * 100:.2f}%")
    print(f"  Commissions:      {gambit['commissions']:.2f} CAD")
    print(f"  Frais journal.:   {gambit['frais_journalisation']:.2f} CAD")

    economie = classique['cout_total_cad'] - gambit['cout_total_cad']
    economie_pct = economie / args.montant * 100
    print(f"\n💰 ÉCONOMIE: {economie:,.2f} CAD ({economie_pct:.2f}% du montant)")

    if args.montant < 1000:
        print("\n⚠️  Pour < 1 000 CAD, le gambit est rarement rentable vs simplicité.")
    elif economie < gambit['commissions'] + gambit['frais_journalisation']:
        print("\n⚠️  L'économie ne couvre pas les frais. Conversion classique préférable.")


if __name__ == "__main__":
    main()
