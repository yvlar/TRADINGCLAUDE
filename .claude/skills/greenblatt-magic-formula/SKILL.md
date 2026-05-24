---
name: greenblatt-magic-formula
description: Applique la Magic Formula de Joel Greenblatt — classement systématique d'actions combinant rendement du capital investi (ROC) et rendement des bénéfices (Earnings Yield). Couvre aussi son approche des situations spéciales (You Can Be a Stock Market Genius) — spinoffs, restructurations, risk arbitrage. À utiliser dès que l'utilisateur mentionne Greenblatt, "magic formula", "formule magique", ROC + earnings yield, spinoffs, situations spéciales, ou veut un screening systématique combinant qualité et bon marché. Utilise toujours ce skill quand l'utilisateur veut classer un univers d'actions selon qualité + prix de manière mécanique.
---

# Greenblatt — Magic Formula

Classement systématique d'actions combinant deux métriques uniques — qualité (rendement du capital investi) et bon marché (rendement des bénéfices). C'est un **screening mécanique simple** qui a battu le marché historiquement, à condition d'être appliqué avec discipline pendant plusieurs années.

## Quand utiliser quoi

| Question | Référence |
|----------|-----------|
| Comment calculer ROC et Earnings Yield ? | `references/formules-magic-formula.md` |
| Comment construire le portefeuille ? | `references/portefeuille-discipline.md` |
| Spinoffs et situations spéciales | `references/situations-speciales.md` |

## Workflow

### Étape 1 — Définir l'univers

- **Capitalisation min** : 50 M$ (ou 100, 200 selon préférence)
- **Exclusions sectorielles** : financières, utilities, REITs (structure de bilan inadaptée)
- **Exclusions techniques** : ADR/société étrangère, EBIT négatif, restructuration majeure

### Étape 2 — Calculer les deux métriques

Pour chaque action :
```bash
python scripts/magic_formula_score.py --batch univers.json
```

Le script calcule :
- **ROC** = EBIT / (Working Capital net + PP&E net)
- **Earnings Yield** = EBIT / Enterprise Value

### Étape 3 — Classement combiné

```
Rang ROC (1 = meilleur) + Rang EY (1 = meilleur) = Score combiné
Trier par score croissant
```

Les 20-30 meilleurs scores constituent le portefeuille candidat.

### Étape 4 — Filtre qualitatif minimal (optionnel)

Greenblatt accepte un filtre minimal sur le top 30-50 :
- Éliminer les value traps évidents (déclin structurel)
- Éliminer les EBIT TTM non récurrents (gain exceptionnel, vente d'actifs)
- Éliminer les sociétés avec problèmes comptables documentés

**Garder ce filtre strict et minimal** — l'avantage de la formule réside dans son aspect mécanique.

## Pourquoi ces deux métriques uniquement

Greenblatt argumente : la **qualité** d'une entreprise est résumée par son ROC (combien de profit par dollar de capital investi), et le **prix** par son Earnings Yield (combien de profit par dollar payé pour l'entreprise entière, dette incluse).

Les deux ensemble = "good companies at bargain prices" en chiffres purs.

L'astuce du double classement (rang ROC + rang EY plutôt que ratio) permet d'éviter les actions qui sont extrêmes sur une dimension mais médiocres sur l'autre.

## Discipline d'application

Greenblatt insiste : la formule **peut sous-performer 2-3 ans consécutifs**. La majorité des investisseurs abandonnent dans ces périodes, ce qui maintient l'efficacité pour les disciplinés.

**Si l'investisseur n'est pas prêt à tenir 5 ans, ne pas commencer.**

## Au-delà de la formule — situations spéciales

Avant la Magic Formula, Greenblatt a écrit *You Can Be a Stock Market Genius* sur les situations spéciales (rendements > 50 %/an chez Gotham 1985-1995). Voir `references/situations-speciales.md` pour :
- Spinoffs (vente forcée mécanique post-séparation)
- Restructurations / sorties de Chapter 11
- Risk arbitrage de fusions
- Stub stocks

Ces stratégies demandent plus de travail que la formule mécanique, mais ont historiquement généré des rendements supérieurs.

## Garde-fous

- **La discipline est l'avantage, pas la formule.** La formule est connue depuis 2005 et fonctionne encore parce que la discipline est rare. Si l'investisseur n'a pas la psychologie pour traverser 2-3 ans de sous-performance, l'avantage disparaît.
- **Adaptation fiscale au Canada.** Greenblatt utilise un holding period de 1 an pour bénéficier des taux long-terme aux USA. Au Canada, le gain en capital est inclus à 50 % indépendamment de la durée — donc le délai de 1 an n'a pas d'effet fiscal direct. Ajuster la rotation aux préférences personnelles (mais conserver une rotation régulière).
- **Le filtre qualitatif est un compromis.** Plus on ajoute de filtres subjectifs, plus on s'éloigne du screen mécanique et perd l'avantage. Garder le filtre strict et limité.
- **La Magic Formula est un point d'entrée, pas une fin.** Pour des positions concentrées de plus de 5 % du portefeuille, faire l'analyse approfondie au-delà du screen.
- **Disponibilité des données.** Pour les marchés non-US, EBIT et capital opérationnel ne sont pas toujours immédiatement accessibles. Le site original de Greenblatt (magicformulainvesting.com) couvre surtout le marché US.
