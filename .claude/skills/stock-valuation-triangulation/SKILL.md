---
name: stock-valuation-triangulation
description: Estime la valeur intrinsèque d'une action par triangulation de trois méthodes — DCF avec WACC explicité, multiples comparables (EV/EBITDA, P/E forward), et méthode sectorielle (SOTP, NAV, FFO selon le secteur). À utiliser dès que l'utilisateur demande "combien vaut" une action, mentionne juste valeur, valeur intrinsèque, DCF, WACC, CMPC, multiples comparables, EV/EBITDA, P/E forward, somme des parties, SOTP, ou veut estimer si une action est sous-évaluée. Produit une fourchette basse/centrale/haute avec matrice de sensibilité. Utilise toujours ce skill avant toute recommandation d'achat ou de vente pour disposer d'une fourchette de juste valeur défendable.
---

# Stock Valuation Triangulation

Estime la valeur intrinsèque d'une action par **trois méthodes complémentaires**, parce qu'aucune méthode prise isolément n'est fiable : un DCF est ultra-sensible aux hypothèses lointaines, des comparables peuvent reproduire un mispricing sectoriel, et une méthode sectorielle ignore les caractéristiques individuelles. La triangulation par trois méthodes donne une fourchette robuste.

## Quand utiliser quelle méthode

| Type d'entreprise | Méthode dominante | Référence |
|-------------------|-------------------|-----------|
| Mature, FCF stables | DCF (50% du poids) | `references/dcf.md` |
| Cyclique, jeune, en transformation | Comparables (50%) | `references/comparables.md` |
| Holding, conglomérat | Somme des parties (SOTP) | `references/sectoriel.md` |
| Banque, assureur | Book value × ROE / coût des CP | `references/sectoriel.md` |
| REIT (immobilier coté) | NAV ou FFO multiple | `references/sectoriel.md` |
| Ressources naturelles | Valeur des réserves prouvées | `references/sectoriel.md` |
| SaaS jeune | Rule of 40 + ARR multiple | `references/sectoriel.md` |

## Workflow recommandé

### Étape 1 — Récupérer les données

États financiers récents (3 derniers exercices), structure de capital, bêta, taux sans risque pertinent à la devise (10 ans CAD pour TSX, 10 ans USD pour NYSE/NASDAQ), 4-6 pairs comparables nommés.

### Étape 2 — Calculer le DCF

Le DCF est le calcul le plus sensible aux erreurs arithmétiques. **Utilise le script bundled** :

```bash
python scripts/compute_dcf.py inputs.json
```

Le script prend en entrée les FCF projetés, le CMPC et la croissance perpétuelle, et sort la valeur d'entreprise, la valeur des capitaux propres, et la **matrice de sensibilité 5×5** (CMPC ± 1 % × g ± 0.5 %). Cette matrice est la valeur ajoutée principale — la plupart des erreurs de DCF viennent du fait qu'on présente un seul chiffre au lieu d'une fourchette.

Pour le calcul du CMPC :
```bash
python scripts/compute_wacc.py
```

Voir `references/dcf.md` pour le détail des hypothèses à justifier.

### Étape 3 — Comparables

Identifier 4-6 pairs **nommés explicitement** (justifier la sélection). Utiliser la **médiane** des multiples sectoriels (plus robuste que la moyenne). Les multiples principaux :

```bash
python scripts/compute_multiples.py inputs.json
```

Voir `references/comparables.md` pour le choix du multiple par secteur.

### Étape 4 — Méthode sectorielle

Choisir selon le secteur (voir tableau ci-dessus et `references/sectoriel.md`).

### Étape 5 — Triangulation

```bash
python scripts/triangulate.py dcf_result.json comparables_result.json sectoriel_result.json
```

Sortie : fourchette pondérée basse / centrale / haute, avec justification des pondérations.

## Pourquoi triangulation et pas une seule méthode

Un DCF avec un CMPC de 9 % vs 10 % peut produire des valeurs qui diffèrent de 30-40 %. Les comparables peuvent être justes en relatif mais faux en absolu si le secteur entier est mispricé. Une méthode sectorielle ignore les caractéristiques propres à l'entreprise.

Quand les trois méthodes convergent à 10-15 % près, la fourchette de juste valeur est solide. Quand elles divergent de plus de 30 %, c'est un signal **d'investiguer plutôt que de moyenner aveuglément** — il y a probablement une hypothèse structurellement fausse dans l'une des trois méthodes.

## Garde-fous

- **Hypothèses explicites toujours** : une valorisation sans CMPC, croissance, marges et durée de croissance haute documentés n'a aucune valeur défendable. Les scripts forcent à expliciter chaque hypothèse.
- **Sensibilité non négociable** : la matrice CMPC × g est obligatoire — un investisseur ne devrait jamais voir un seul chiffre sans son écart-type.
- **Cohérence devise** : FCF, CMPC et dette doivent être dans la même devise. Si conversion, expliciter le taux et la date.
- **Précision fictive** : présenter une fourchette (basse / centrale / haute), jamais un prix-cible à 2 décimales. Damodaran appelle ça *« the false precision trap »*.
- **Inapplicabilités** : pour les financières (banques, assureurs), le DCF classique est inapplicable — utiliser le modèle sectoriel approprié dans `references/sectoriel.md`.
