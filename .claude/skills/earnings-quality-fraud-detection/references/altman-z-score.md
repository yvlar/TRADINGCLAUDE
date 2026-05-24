# Z-Score (Altman, 1968)

## Origine et utilité

Edward Altman, NYU Stern, 1968. Premier modèle mathématique de prédiction de faillite, basé sur l'analyse discriminante multivariée. Échantillon original : 66 entreprises industrielles cotées américaines, dont la moitié avait fait faillite entre 1946 et 1965. **Précision : ~95 % à un an, ~72 % à deux ans.**

C'est probablement le modèle de scoring financier le plus enseigné au monde. Il existe en plusieurs variantes selon le profil d'entreprise.

## Formule originale (Z) — entreprises industrielles cotées

```
Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
```

| Variable | Définition | Signification économique |
|----------|------------|--------------------------|
| X1 | Working Capital / Total Assets | Liquidité court terme |
| X2 | Retained Earnings / Total Assets | Profitabilité cumulative |
| X3 | EBIT / Total Assets | Rentabilité opérationnelle |
| X4 | Market Value of Equity / Total Liabilities | Solvabilité (perspective marché) |
| X5 | Sales / Total Assets | Efficience d'utilisation des actifs |

## Seuils d'interprétation (modèle Z original)

| Z-Score | Zone | Probabilité de faillite à 2 ans |
|---------|------|--------------------------------|
| Z > 2.99 | Sûre | Très faible |
| 1.81 < Z < 2.99 | Grise (zone d'ignorance) | Modérée — incertain |
| Z < 1.81 | Détresse | Élevée |

## Variantes pour autres profils d'entreprise

### Z' — entreprises industrielles privées (Altman, 1983)

Remplace X4 (Market Value of Equity) par Book Value of Equity puisque les privées n'ont pas de prix de marché.

```
Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4_book + 0.998×X5
```

Seuils : Z' > 2.90 sûr, Z' < 1.23 détresse.

### Z'' — non-industriel et marchés émergents (Altman, 1995)

Exclut X5 (Sales/TA) parce que ce ratio dépend trop du secteur et fausse la comparaison entre services, retail et industrie.

```
Z'' = 6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×X4
```

Seuils : Z'' > 2.60 sûr, 1.10 < Z'' < 2.60 grise, Z'' < 1.10 détresse.

Pour les marchés émergents, ajouter +3.25 au score brut pour calibrer.

## Quelle variante utiliser

| Profil de l'entreprise | Variante |
|------------------------|----------|
| Industriel coté (US/EU mature) | Z (original) |
| Industriel privé | Z' |
| Service, retail, tech | Z'' |
| Marché émergent | Z'' + 3.25 |
| Banque, assureur, REIT | **Aucune** — modèle inapplicable |
| Utility régulée | Z'' avec prudence |

## Cas limites

- **Capex récent massif** (modernisation industrielle) : peut comprimer X1 temporairement et donner un faux signal de détresse
- **Rachats d'actions agressifs** : réduit le book value of equity, peut faire chuter Z'
- **Goodwill important** : gonfle les actifs sans capacité productive — peut artificiellement gonfler le Z (faux positif rassurant)
- **Cycle de vie** : les jeunes entreprises ont mécaniquement un X2 (retained earnings) faible — Z bas n'implique pas faillite, juste jeunesse

## Interprétation pour l'investisseur value

Le Z-Score n'est pas un screen d'achat — c'est un screen **d'élimination**. Une action avec Z-Score < 1.81 ne devrait pas être achetée comme value pure, sauf si tu maîtrises le distressed investing à la Klarman.

Pour les actions Graham (chap. 14 défensif), exiger Z > 2.99 est une bonne discipline.
Pour les Klarman (situations spéciales / distressed), 1.81 < Z < 2.99 est l'univers de chasse.

## Source primaire

Altman, Edward I. (1968). *Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy*. The Journal of Finance, 23(4), 589-609.

Mises à jour : Altman (1983), Altman, Hartzell & Peck (1995), Altman et al. (2017) — *Financial Distress Prediction in an International Context: A Review and Empirical Analysis of Altman's Z-Score Model*.
