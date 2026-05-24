#!/usr/bin/env python3
"""
biais_audit.py — Audit des 25 biais cognitifs Munger pour une décision

Présente les 25 biais en groupes thématiques pour audit systématique avant
une décision d'investissement majeure.

Usage:
  python biais_audit.py --decision "achat-tesla-200usd"
  python biais_audit.py --json inputs.json
"""

import argparse
import json


BIAIS = [
    {"id": 1, "nom": "Reward and punishment superresponse", "groupe": "Incitatifs",
     "question": "Quels incitatifs animent les acteurs (direction, analystes, vendeurs) ?"},
    {"id": 2, "nom": "Liking / Loving tendency", "groupe": "Émotions",
     "question": "Suis-je biaisé positivement par charisme du CEO ou popularité de la marque ?"},
    {"id": 3, "nom": "Disliking / Hating tendency", "groupe": "Émotions",
     "question": "Est-ce que je rejette automatiquement des sources contradictoires ?"},
    {"id": 4, "nom": "Doubt-avoidance", "groupe": "Décision",
     "question": "Suis-je en train de me précipiter pour résoudre l'incertitude ?"},
    {"id": 5, "nom": "Inconsistency-avoidance / Commitment", "groupe": "Décision",
     "question": "Suis-je ancré dans une position publique qui me bloque ?"},
    {"id": 6, "nom": "Curiosity", "groupe": "Positifs",
     "question": "Ai-je investigué suffisamment ? Quelles questions reste-t-il sans réponse ?"},
    {"id": 7, "nom": "Kantian fairness", "groupe": "Réglementaire",
     "question": "Cette entreprise est-elle perçue comme injuste — risque réglementaire futur ?"},
    {"id": 8, "nom": "Envy / Jealousy", "groupe": "Émotions",
     "question": "Est-ce que je veux acheter parce que d'autres ont fait fortune sur ce titre ?"},
    {"id": 9, "nom": "Reciprocation", "groupe": "Sources",
     "question": "Mes sources sont-elles biaisées par relations commerciales ?"},
    {"id": 10, "nom": "Influence-from-mere-association", "groupe": "Émotions",
     "question": "Suis-je biaisé par expérience passée (gain/perte) sur ce titre ou ce secteur ?"},
    {"id": 11, "nom": "Pain-avoiding denial", "groupe": "Décision",
     "question": "Y a-t-il des évidences que je refuse de voir ?"},
    {"id": 12, "nom": "Excessive self-regard", "groupe": "Décision",
     "question": "Suis-je trop confiant dans ma compétence d'analyse ?"},
    {"id": 13, "nom": "Over-optimism", "groupe": "Projection",
     "question": "Mes projections sont-elles toutes optimistes ? Cas pessimiste fait ?"},
    {"id": 14, "nom": "Deprival-superreaction (loss aversion)", "groupe": "Émotions",
     "question": "Suis-je ancré sur prix d'achat passé plutôt que valeur actuelle ?"},
    {"id": 15, "nom": "Social-proof", "groupe": "Foule",
     "question": "Suis-je en train d'acheter parce que tout le monde achète ?"},
    {"id": 16, "nom": "Contrast-misreaction", "groupe": "Comparaisons",
     "question": "Mon ancrage de comparaison est-il pertinent (historique long-terme) ?"},
    {"id": 17, "nom": "Stress-influence", "groupe": "Décision",
     "question": "Suis-je sous pression émotionnelle (panique, euphorie, urgence) ?"},
    {"id": 18, "nom": "Availability-misweighing", "groupe": "Mémoire",
     "question": "Suis-je trop influencé par événements récents ou vivides ?"},
    {"id": 19, "nom": "Use-it-or-lose-it", "groupe": "Compétences",
     "question": "Mes outils analytiques sont-ils à jour ?"},
    {"id": 20, "nom": "Drug/dopamine influence", "groupe": "Comportement",
     "question": "Cette transaction me procure-t-elle excitation au-delà du raisonnable ?"},
    {"id": 21, "nom": "Senescence-misinfluence", "groupe": "Cognition",
     "question": "Mon jugement est-il aussi acéré qu'auparavant ?"},
    {"id": 22, "nom": "Authority-misinfluence", "groupe": "Sources",
     "question": "Suis-je en train de suivre une autorité (Buffett, Klarman, etc.) sans analyse propre ?"},
    {"id": 23, "nom": "Twaddle", "groupe": "Communication",
     "question": "La présentation contient-elle bavardage qui masque l'absence de substance ?"},
    {"id": 24, "nom": "Reason-respecting", "groupe": "Logique",
     "question": "Les 'raisons' données tiennent-elles quantitativement ?"},
    {"id": 25, "nom": "Lollapalooza", "groupe": "Combinaison",
     "question": "Combien de biais ci-dessus s'alignent ? (3+ = lollapalooza probable)"},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=str, default=None,
                        help="Description courte de la décision à auditer")
    parser.add_argument("--json", type=str, default=None,
                        help="Fichier JSON avec analyse pré-remplie")
    args = parser.parse_args()

    decision = args.decision or "(décision non spécifiée)"

    print("=" * 78)
    print(f"AUDIT DES 25 BIAIS COGNITIFS — {decision}")
    print("=" * 78)
    print("\nPour chaque biais, se demander si applicable. Coch ✓ ou ✗.")
    print()

    # Grouper
    groupes = {}
    for b in BIAIS:
        groupes.setdefault(b["groupe"], []).append(b)

    for groupe, biais_list in groupes.items():
        print(f"\n━━━ {groupe.upper()} ━━━")
        for b in biais_list:
            print(f"\n  {b['id']:2d}. {b['nom']}")
            print(f"      → {b['question']}")

    print("\n" + "=" * 78)
    print("ÉTAPES SUIVANTES:")
    print("=" * 78)
    print("\n1. Identifier les biais qui s'appliquent à TOI dans cette décision")
    print("2. Identifier les biais qui s'appliquent au MARCHÉ (créant l'opportunité)")
    print("3. Compter les biais alignés — si 3+ alignés vers la même conclusion,")
    print("   suspecter un lollapalooza et inverser la position")
    print("4. Effectuer l'inversion: 'Comment cette position pourrait-elle échouer ?'")
    print("5. Si 5+ scenarios d'échec sont plausibles, refuser ou réduire le sizing")


if __name__ == "__main__":
    main()
