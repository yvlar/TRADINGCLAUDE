---
name: damodaran-narrative-and-numbers
description: Applique le cadre d'Aswath Damodaran (NYU Stern) — alignement entre la narrative (story) et les numbers (modèle financier), test possible / plausible / probable, valorisation rigoureuse y compris pour entreprises non rentables ou en transformation. À utiliser dès que l'utilisateur mentionne Damodaran, story stocks, narrative et numbers, "story to numbers", possible vs probable, ERP, prime de risque actions, valorisation de croissance non profitable, ou veut sanity-check une thèse en confrontant story et chiffres. Utilise toujours ce skill pour les valorisations d'entreprises en transformation, jeunes SaaS non rentables, ou stories controversées.
---

# Damodaran — Narrative and Numbers

Aswath Damodaran (NYU Stern) a popularisé l'idée que **toute valorisation est une histoire racontée en chiffres**. Si l'histoire et les chiffres ne s'alignent pas, la valorisation est fausse — soit l'histoire est incohérente, soit les chiffres l'ont trahie.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Test possible / plausible / probable | `references/test-narrative.md` |
| Valoriser une story stock non rentable | `references/valorisation-story-stocks.md` |
| Sanity check d'un DCF par cohérence dynamique | `references/coherence-dynamique.md` |
| ERP implicite et country risk | `references/erp-country-risk.md` |

## Workflow

### Étape 1 — Articuler la story

En **une page maximum** :
- Que vend cette entreprise et à qui ?
- Quel est le marché total adressable (TAM) ?
- Quelle est la position concurrentielle ?
- Qu'est-ce qui doit être vrai pour que cette story réussisse ?

Sans cette étape, le DCF est mécanique sans signification.

### Étape 2 — Tester la story

Trois niveaux progressifs :

| Niveau | Question | Filtre |
|--------|----------|--------|
| **Possible** | Cela peut-il arriver ? | Cohérence logique de base |
| **Plausible** | Cela arrive-t-il généralement dans des situations comparables ? | Précédents historiques |
| **Probable** | Cela arrivera-t-il pour cette entreprise spécifique ? | Évidence empirique propre |

Une story doit passer **probable** (pas seulement possible) pour justifier un investissement.

### Étape 3 — Traduire en chiffres

```bash
python scripts/dcf_story.py inputs.json
```

Le script demande explicitement :
- Croissance des revenus année par année (pas un seul taux moyen)
- Évolution de la marge opérationnelle
- Taux de réinvestissement
- ROIC implicite

Et **vérifie la cohérence** : le triangle ROIC × Reinvestment = Growth doit tenir.

### Étape 4 — Test de cohérence dynamique

```bash
python scripts/check_coherence.py inputs.json
```

Vérifie :
- Le ROIC implicite peut-il être atteint ? (vs benchmark sectoriel et historique)
- La trajectoire de marges est-elle réaliste ? (vs leaders du secteur)
- Le réinvestissement est-il financiable ? (cash flow + dette acceptable)

Si l'un des trois est invalide, **la valorisation est cassée** indépendamment du résultat numérique.

### Étape 5 — Range de valeurs, pas point-cible

Damodaran insiste : présenter une **fourchette** (P10, P50, P90) issue de Monte-Carlo, pas un seul prix-cible. La précision fictive est l'erreur la plus courante des DCF amateurs.

## Le ERP (Equity Risk Premium) en 2026

Damodaran calcule l'ERP implicite mensuellement sur son site (NYU Stern). Valeur de référence début 2026 :
- **Mature market ERP** : ~4.23 %
- **US 10-year T-Note** : ~4.5 %
- **Required return on equity** (S&P 500) : ~8.7 %

Pour un investisseur canadien :
- **Canada 10-year** : ~3.5-4 %
- **Country risk premium** : 0 (Canada AAA)
- **ERP appliqué** : 4.23 %

Voir `references/erp-country-risk.md` pour la mise à jour de ces valeurs et l'ajustement par pays émergent.

## Garde-fous

- **Possible ≠ probable.** Une story Tesla 2018 (révolution autonome) était possible. Probable = beaucoup moins clair. Investir uniquement sur le probable.
- **Les chiffres doivent contraindre la story.** Si tu estimes une croissance qui implique un ROIC > 50 % à long terme, la story est cassée — ce ROIC est physiquement impossible à maintenir.
- **Story stocks demandent un margin of error large.** L'incertitude sur les paramètres (g, marges, ROIC long terme) est si grande que la fourchette de valeurs s'étend typiquement de 50 % à 200 % du prix de marché. Acheter uniquement quand le prix est clairement dans la moitié basse.
- **Les narratives évoluent**. Une story qui était plausible il y a 5 ans peut être devenue improbable. Réviser annuellement.
- **Damodaran lui-même se trompe**. Il a été en désaccord avec le marché sur Tesla pendant des années (sous-estimait le potentiel). Personne n'a la vérité absolue — la rigueur du processus compte plus que la justesse du résultat.
