# Accruals Ratio (Sloan, 1996)

## Origine et utilité

Richard Sloan, professeur de comptabilité à University of Michigan (puis Berkeley). Article fondateur : *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings?* (The Accounting Review, 1996).

**La démonstration de Sloan** : les bénéfices peuvent être décomposés en deux composantes — la composante *cash* (CFO) et la composante *accruals* (la différence). La composante accruals est **moins persistante** que la composante cash : elle se retourne dans le futur. Pourtant, le marché les pondère également.

**Conséquence empirique** : les entreprises avec accruals élevés sous-performent dans les 1-3 années suivantes ; les entreprises avec accruals faibles sur-performent. Cet effet, **l'« anomalie des accruals »**, a été l'un des plus robustes dans la finance académique pendant 20 ans.

## Formule

### Version simple (accruals totaux)

```
Accruals_ratio = (Net Income - CFO) / Total Assets moyens
```

Où Total Assets moyens = (TA_t + TA_{t-1}) / 2.

### Version Sloan originale (accruals d'exploitation seulement)

```
Operating_Accruals = (ΔCA - ΔCash) - (ΔCL - ΔSTD - ΔTaxes_payable) - Depreciation
Accruals_ratio_op = Operating_Accruals / Total Assets moyens
```

Cette version isole les accruals **d'exploitation**, en excluant les variations de cash et de dette court terme. Plus rigoureuse mais demande plus de données.

## Pourquoi les accruals sont moins persistants

Un bénéfice "earned in cash" cette année a tendance à se reproduire l'année suivante (les clients qui paient continuent de payer). Un bénéfice "earned in accruals" — par exemple via une reconnaissance prématurée de revenu, ou une réduction de provisions — est mécaniquement *one-shot* : il faut générer un nouveau accrual l'année suivante pour maintenir le rythme, ce qui devient de plus en plus difficile.

C'est pourquoi les entreprises avec accruals élevés voient leurs bénéfices se *normaliser à la baisse* dans les années qui suivent.

## Interprétation par décile sectoriel

L'interprétation se fait **par rapport au secteur**, pas dans l'absolu :

| Position dans le secteur | Lecture |
|--------------------------|---------|
| Décile 1 (le plus bas) | Signal positif — bénéfices "réels" |
| Déciles 2-5 | Normal |
| Déciles 6-9 | Surveiller |
| Décile 10 (le plus haut) | Drapeau rouge — sous-performance attendue |

Pour un investisseur particulier qui n'a pas accès à toutes les données sectorielles, une heuristique grossière : un ratio total accruals > 0.10 (10 % des actifs) sur un seul exercice est suspect ; > 0.05 sur trois exercices consécutifs aussi.

## Liens avec les autres cadres

- **TATA dans le M-Score** est exactement ce ratio (avec coefficient 4.679, le plus élevé des 8 variables)
- **Critère #4 du F-Score** (CFO > Net Income) est une version binaire de l'idée Sloan
- **Signal #1 du C-Score** (divergence NI vs CFO) est aussi conceptuellement Sloan

C'est pourquoi calculer Sloan séparément n'apporte pas tant d'information **si** tu as déjà les trois autres scores. Son intérêt principal est dans le **classement décile par décile** au sein d'un secteur, pour comparer plusieurs candidats entre eux.

## Cas limites

- **Forte croissance organique** : génère mécaniquement des accruals positifs (besoin en fonds de roulement qui croît). Pas une manipulation.
- **Acquisition** : peut générer des accruals comptables sans manipulation
- **Saisonnalité** : un seul exercice peut être trompeur — moyenner sur 3 ans
- **Accruals négatifs très élevés** : pas nécessairement positif — peut signaler une entreprise qui se contracte ou qui décharge ses provisions

## Limite majeure : l'effet Goodhart

Sloan a publié son article en 1996. Depuis, les fonds quantitatifs trient massivement sur les accruals. **L'anomalie a largement disparu post-2005** dans les marchés liquides. Elle subsiste dans les small-caps et les marchés moins efficients.

Conclusion : utile comme **filtre supplémentaire**, pas comme stratégie principale.

## Source primaire

Sloan, Richard G. (1996). *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings?* The Accounting Review, 71(3), 289-315.

Mises à jour critiques : Richardson, Sloan, Soliman & Tuna (2005) — *Accrual Reliability, Earnings Persistence and Stock Prices*.
