#!/usr/bin/env python3
"""
marge_securite.py — Calcul et validation de la marge de sécurité Klarman

Compare la marge de sécurité actuelle au seuil minimum exigé selon le type
d'opportunité (compounder, cyclique, special situation, distressed, etc.).

Usage:
  python marge_securite.py --intrinsic 100 --price 65 --type compounder
"""

import argparse


SEUILS_MARGE = {
    "compounder": (0.25, 0.30, "Compounder de qualité"),
    "cyclique": (0.40, 0.50, "Cyclique au creux"),
    "special_situation": (0.30, 0.40, "Special situation (spinoff, restructuration)"),
    "distressed": (0.50, 0.70, "Distressed debt"),
    "asset_play_distress": (0.55, 0.65, "Asset play en distress"),
}


def evaluate(intrinsic: float, price: float, opportunity_type: str) -> dict:
    """Calcule et valide la marge de sécurité."""
    if intrinsic <= 0:
        return {"error": "Valeur intrinsèque doit être positive"}

    marge_actuelle = (intrinsic - price) / intrinsic

    if opportunity_type not in SEUILS_MARGE:
        return {"error": f"Type inconnu: {opportunity_type}"}

    seuil_min, seuil_recommande, label = SEUILS_MARGE[opportunity_type]

    if marge_actuelle >= seuil_recommande:
        verdict = "✅ ACHAT — marge supérieure au seuil recommandé"
        flag = "vert"
    elif marge_actuelle >= seuil_min:
        verdict = "⚠ ACHAT POSSIBLE — marge entre seuil minimum et recommandé"
        flag = "jaune"
    else:
        verdict = f"❌ ATTENDRE — marge insuffisante (< {seuil_min*100:.0f}%)"
        flag = "rouge"

    # Calcul du prix d'achat cible pour atteindre le seuil minimum
    prix_cible_min = intrinsic * (1 - seuil_min)
    prix_cible_recommande = intrinsic * (1 - seuil_recommande)

    return {
        "type": label,
        "intrinsic_value": intrinsic,
        "current_price": price,
        "marge_actuelle": marge_actuelle,
        "marge_actuelle_pct": f"{marge_actuelle*100:.1f}%",
        "seuil_min_pct": f"{seuil_min*100:.0f}%",
        "seuil_recommande_pct": f"{seuil_recommande*100:.0f}%",
        "prix_cible_min": round(prix_cible_min, 2),
        "prix_cible_recommande": round(prix_cible_recommande, 2),
        "verdict": verdict,
        "flag": flag,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intrinsic", type=float, required=True, help="Valeur intrinsèque estimée")
    parser.add_argument("--price", type=float, required=True, help="Prix de marché actuel")
    parser.add_argument("--type", choices=list(SEUILS_MARGE.keys()), default="compounder",
                        help="Type d'opportunité")
    args = parser.parse_args()

    r = evaluate(args.intrinsic, args.price, args.type)

    print("=" * 65)
    print(f"MARGE DE SÉCURITÉ KLARMAN — {r['type']}")
    print("=" * 65)
    print(f"\nValeur intrinsèque   : {r['intrinsic_value']}")
    print(f"Prix actuel          : {r['current_price']}")
    print(f"\nMarge de sécurité    : {r['marge_actuelle_pct']}")
    print(f"Seuil minimum exigé  : {r['seuil_min_pct']}")
    print(f"Seuil recommandé     : {r['seuil_recommande_pct']}")
    print(f"\nPrix cible (min)         : {r['prix_cible_min']}")
    print(f"Prix cible (recommandé)  : {r['prix_cible_recommande']}")
    print(f"\n{r['verdict']}")


if __name__ == "__main__":
    main()
