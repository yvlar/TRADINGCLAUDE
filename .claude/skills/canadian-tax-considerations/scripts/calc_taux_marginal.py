#!/usr/bin/env python3
"""
calc_taux_marginal.py — Calcul du taux marginal effectif Québec selon revenu et type

Calcule le taux d'imposition marginal pour un revenu de placement donné,
en tenant compte des tranches Québec + fédéral et du type de revenu.

⚠️ Tranches 2026. Vérifier valeurs courantes via web_search avant utilisation.

Usage:
  python calc_taux_marginal.py
  python calc_taux_marginal.py --revenu 150000 --type div_eligibles --montant 1000
"""

import argparse
import sys

# Tranches 2026 fédérales et Québec (haut taux ~53.31% combiné)
# Valeurs simplifiées — pour calculs précis, utiliser logiciel d'impôt
TRANCHES_FED_2026 = [
    (0, 57375, 0.15),
    (57375, 114750, 0.205),
    (114750, 177882, 0.26),
    (177882, 253414, 0.29),
    (253414, float('inf'), 0.33),
]

TRANCHES_QC_2026 = [
    (0, 53255, 0.14),
    (53255, 106495, 0.19),
    (106495, 129590, 0.24),
    (129590, float('inf'), 0.2575),
]


def taux_marginal_combine(revenu_total: float) -> float:
    """Retourne le taux marginal combiné fédéral + Québec."""
    fed = next(t[2] for t in TRANCHES_FED_2026 if t[0] <= revenu_total < t[1])
    qc = next(t[2] for t in TRANCHES_QC_2026 if t[0] <= revenu_total < t[1])
    # Abattement du Québec (16.5% du fédéral pour résidents Québec)
    fed_apres_abattement = fed * (1 - 0.165)
    return fed_apres_abattement + qc


def impot_dividende_eligible(montant: float, taux_marginal: float) -> dict:
    """Calcule l'impôt sur dividende éligible avec gross-up et crédits."""
    majore = montant * 1.38
    impot_brut = majore * taux_marginal
    credit_fed = majore * 0.150198
    credit_qc = majore * 0.117
    impot_net = impot_brut - credit_fed - credit_qc
    return {
        "type": "dividende éligible",
        "montant_recu": montant,
        "majore": majore,
        "impot_brut": impot_brut,
        "credit_federal": credit_fed,
        "credit_provincial": credit_qc,
        "impot_net": max(0, impot_net),
        "taux_effectif": max(0, impot_net) / montant if montant > 0 else 0,
    }


def impot_gain_capital(montant: float, taux_marginal: float) -> dict:
    """Gain en capital: 50% inclus."""
    inclusion = montant * 0.50
    impot = inclusion * taux_marginal
    return {
        "type": "gain en capital",
        "montant_recu": montant,
        "inclusion": inclusion,
        "impot_net": impot,
        "taux_effectif": impot / montant if montant > 0 else 0,
    }


def impot_interet(montant: float, taux_marginal: float) -> dict:
    """Intérêts: 100% inclus."""
    impot = montant * taux_marginal
    return {
        "type": "intérêts",
        "montant_recu": montant,
        "impot_net": impot,
        "taux_effectif": taux_marginal,
    }


def impot_dividende_us(montant: float, taux_marginal: float, compte: str = "non_enregistre") -> dict:
    """Dividende US selon le compte."""
    if compte == "non_enregistre":
        retenue = montant * 0.15
        impot_canadien = montant * taux_marginal
        # Crédit pour impôt étranger limité à l'impôt canadien
        credit = min(retenue, impot_canadien)
        impot_net = retenue + max(0, impot_canadien - credit)
        return {
            "type": "dividende US (non-enregistré)",
            "montant_recu": montant,
            "retenue_us": retenue,
            "impot_canadien_brut": impot_canadien,
            "credit_etranger": credit,
            "impot_net_total": impot_net,
            "taux_effectif": impot_net / montant if montant > 0 else 0,
        }
    elif compte == "celi":
        retenue = montant * 0.15
        return {
            "type": "dividende US (CELI - retenue NON récupérable)",
            "montant_recu": montant,
            "retenue_us": retenue,
            "impot_net_total": retenue,
            "taux_effectif": 0.15,
        }
    elif compte == "reer":
        return {
            "type": "dividende US (REER - exempté par convention)",
            "montant_recu": montant,
            "retenue_us": 0,
            "impot_net_total": 0,
            "taux_effectif": 0.0,
            "note": "Valable pour titres directs ou ETF coté aux US, pas pour ETF canadien d'actions US",
        }


def main():
    parser = argparse.ArgumentParser(description="Calcul du taux marginal Québec")
    parser.add_argument("--revenu", type=float, default=None, help="Revenu imposable annuel total")
    parser.add_argument("--type", choices=["div_eligibles", "div_us", "gain_capital", "interet"],
                        default=None, help="Type de revenu de placement")
    parser.add_argument("--montant", type=float, default=None, help="Montant du revenu de placement")
    parser.add_argument("--compte", choices=["non_enregistre", "celi", "reer"],
                        default="non_enregistre", help="Compte (pour dividendes US)")
    args = parser.parse_args()

    if args.revenu is None:
        args.revenu = float(input("Revenu imposable annuel ($): "))
    if args.type is None:
        print("\nTypes de revenu:")
        print("  1. Dividendes éligibles canadiens")
        print("  2. Dividendes US")
        print("  3. Gain en capital")
        print("  4. Intérêts")
        choix = input("Choix [1-4]: ").strip()
        args.type = ["div_eligibles", "div_us", "gain_capital", "interet"][int(choix) - 1]
    if args.montant is None:
        args.montant = float(input("Montant du revenu de placement ($): "))

    taux = taux_marginal_combine(args.revenu)

    print(f"\n{'='*60}")
    print(f"Taux marginal combiné (Québec) à {args.revenu:,.0f}$ : {taux*100:.2f}%")
    print(f"{'='*60}\n")

    if args.type == "div_eligibles":
        r = impot_dividende_eligible(args.montant, taux)
    elif args.type == "div_us":
        r = impot_dividende_us(args.montant, taux, args.compte)
    elif args.type == "gain_capital":
        r = impot_gain_capital(args.montant, taux)
    elif args.type == "interet":
        r = impot_interet(args.montant, taux)

    print(f"Type: {r['type']}")
    print(f"Montant reçu: {r['montant_recu']:,.2f}$")
    print(f"Impôt net: {r.get('impot_net', r.get('impot_net_total', 0)):,.2f}$")
    print(f"Taux effectif: {r['taux_effectif']*100:.2f}%")

    if "note" in r:
        print(f"\nℹ️  {r['note']}")


if __name__ == "__main__":
    main()
