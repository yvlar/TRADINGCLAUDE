---
name: graham-stock-screening
description: Applique les critères quantitatifs de Benjamin Graham (chapitres 14 et 15 de The Intelligent Investor) pour filtrer les actions selon l'approche value classique. À utiliser dès que l'utilisateur fournit un ticker et veut évaluer la qualité fondamentale, mentionne Graham, "Intelligent Investor", défensif, entreprenant, marge de sécurité quantitative, P/E ≤ 15, P/B ≤ 1.5, ou demande si une action est "value" au sens classique. Filtre éliminatoire avant analyse approfondie. Utilise toujours ce skill pour le premier filtrage quantitatif d'une action ou d'un univers d'actions.
---

# Graham Stock Screening

Applique les critères quantitatifs de *The Intelligent Investor* (Graham, 1949 / révisé 1973) pour évaluer si une action passe les filtres de qualité d'un investisseur value. C'est un **filtre éliminatoire** : l'objectif n'est pas de trouver la meilleure action, c'est d'éliminer rapidement les candidats qui ne méritent pas une analyse fondamentale approfondie.

## Deux profils d'investisseurs Graham

Graham distingue deux profils, chacun avec ses propres critères. Avant de lancer le screen, identifier le profil :

| Profil | Caractéristiques | Critères |
|--------|------------------|----------|
| **Défensif** (chapitre 14) | Veut posséder des actions sans y consacrer beaucoup de temps | Plus stricts, 8 critères |
| **Entreprenant** (chapitre 15) | Prêt à un travail substantiel pour battre le marché | Plus permissifs sur taille, plus stricts sur prix, 5 critères |

Voir `references/graham-defensif.md` et `references/graham-entreprenant.md` pour les détails.

## Workflow

### Étape 1 — Récupérer les données

Via web_search ou directement depuis le rapport annuel :
- Prix actuel, capitalisation, secteur, devise
- Bilan et compte de résultat sur 5-10 ans
- BPA historique, dividendes versés, actions en circulation
- Rendement actuel des obligations AAA (utile pour la formule ajustée)

### Étape 2 — Lancer le screen automatisé

```bash
python scripts/graham_screen.py inputs.json
```

Le script applique les 8 critères défensifs (ou 5 entreprenants selon profil), affiche le score, identifie les drapeaux rouges, et calcule la valeur Graham estimée + marge de sécurité.

### Étape 3 — Estimer la valeur intrinsèque (formule de Graham)

```bash
python scripts/graham_value.py
```

Calcule deux versions :
- **Formule simple** : V = BPA × (8.5 + 2g)
- **Formule ajustée du taux sans risque** : V = BPA × (8.5 + 2g) × 4.4 / Y

Voir `references/formule-graham.md` pour le détail.

### Étape 4 — Interpréter le verdict

| Critères passés | Lecture |
|-----------------|---------|
| 7-8 défensifs (ou 5/5 entreprenants) | Procéder à l'analyse approfondie |
| 5-6 défensifs | Watchlist avec prix d'achat cible |
| < 5 défensifs | Rejet |

Une action qui passe le filtre devient candidate pour une analyse plus profonde — typiquement enchaîner avec :
- `dorsey-moat-analysis` (qualité économique durable ?)
- `earnings-quality-fraud-detection` (qualité comptable ?)
- `stock-valuation-triangulation` (valorisation rigoureuse au-delà de Graham)

## Drapeaux rouges (à signaler quel que soit le score)

- Bénéfices volatils ou récemment négatifs sur 10 ans
- Dette en croissance rapide (> 10 %/an)
- Goodwill > 30 % du total des actifs (qualité du bilan)
- Stock-based compensation > 5 % des revenus
- Croissance des revenus sans croissance du FCF
- Insider selling massif récent
- Restatement comptable récent

## Garde-fous

- **Le screening Graham est un filtre, pas une analyse complète.** Une action qui passe doit ensuite faire l'objet d'une analyse fondamentale (moat, direction, risques structurels).
- **Ajuster les seuils au contexte sectoriel.** Les financières et les *asset-light tech* méritent des ajustements documentés (le P/B est peu pertinent pour un éditeur SaaS, le current ratio ne s'applique pas aux banques).
- **Cohérence devise.** Prix, BPA et dividendes doivent être dans la même devise. Pour un titre canadien interlisted (RY.TO vs RY), choisir une seule cotation pour le calcul.
- **Graham écrivait en 1949-1973.** L'environnement de taux et l'inflation étaient différents. La formule de valeur ajustée par le taux AAA reste pertinente, mais les seuils absolus (P/E ≤ 15, P/B ≤ 1.5) doivent être nuancés à l'environnement actuel — voir `references/formule-graham.md`.
