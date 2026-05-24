# Cohérence dynamique d'un modèle de valorisation

Le test ultime que beaucoup de DCF amateurs échouent — vérifier que les paramètres clés sont cohérents entre eux et avec la réalité économique.

## La relation fondamentale

```
Croissance soutenable = ROIC × Taux de réinvestissement
```

Cette équation lie les trois paramètres centraux d'un modèle. Si elle ne tient pas, **au moins un paramètre est faux**.

### Démonstration intuitive

Pour qu'une entreprise grandisse, elle doit investir. Le retour sur cet investissement marginal détermine la croissance future. Si elle investit 50 % de ses bénéfices à un ROIC de 20 %, elle peut croître à 10 % (50 % × 20 % = 10 %).

Si elle veut croître à 15 % avec un ROIC de 20 %, elle doit réinvestir 75 %. Si elle veut croître à 15 % avec ROIC de 30 %, elle peut réinvestir 50 %.

## Test pratique

### Étape 1 — Inférer le ROIC implicite

```
ROIC implicite = Croissance projetée / Taux de réinvestissement projeté
```

### Étape 2 — Comparer aux benchmarks

Le ROIC implicite doit être :
- **Supérieur au WACC** (sinon pas de moat — l'entreprise détruit de la valeur)
- **Cohérent avec l'historique** de l'entreprise
- **Cohérent avec les leaders sectoriels** (atteindre 30 % ROIC dans un secteur où la médiane est 12 % est extrêmement rare)

### Étape 3 — Vérifier sur la durée

Le ROIC élevé doit être **maintenable**. Vérifier la durée pour laquelle ce ROIC tient avant que la concurrence ne le compresse :

| ROIC | Durée typique avant convergence |
|------|----------------------------------|
| 15 % | 10-15 ans pour les leaders avec moat |
| 20 % | 7-10 ans pour les leaders avec moat fort |
| 30 % | 5-7 ans, exceptionnel |
| > 40 % | Quasi-impossible à maintenir > 5 ans |

## Exemple de cohérence cassée

### Modèle initial
- Croissance projetée 5 ans : 25 %/an
- Marge opérationnelle stable : 20 %
- Taux de réinvestissement projeté : 40 % de l'EBITDA

### Inférence
ROIC implicite = 25 % / 40 % = **62.5 %**

### Test
62.5 % est plus élevé que tous les leaders historiques de la majorité des secteurs. Les rares entreprises avec ROIC > 50 % (Apple à son sommet, Mastercard) sont des outliers extrêmes.

→ **Modèle cassé**. Soit la croissance est trop élevée, soit le réinvestissement est trop bas, soit la marge est irréaliste.

### Correction
Trois choix possibles :
1. **Réduire la croissance** à un niveau cohérent avec ROIC plausible : 25 % × ROIC 25 % = 6.25 % de croissance soutenable seulement
2. **Augmenter le réinvestissement** : 25 % / ROIC 25 % = 100 % de réinvestissement (= toute la marge réinvestie, FCF libre = 0)
3. **Accepter ROIC > 50 %** mais sur durée très courte (3-5 ans), avec convergence vers 15-20 % ensuite

## Test additionnel : capacité opérationnelle

Au-delà du ROIC, vérifier que le modèle est **opérationnellement faisable** :

### Capacité de production
Une croissance de 30 %/an pendant 5 ans demande de doubler la capacité ~2 fois. Est-ce faisable ?
- Pour un SaaS : oui (capacité est essentiellement du compute)
- Pour un manufacturier : non sans capex monumental
- Pour un service : limité par le recrutement humain

### Talent disponible
Une croissance forte demande l'embauche de talent. Le marché du talent permet-il cela à coût raisonnable ?

### Marché total adressable (TAM)
La croissance projetée mène l'entreprise à quelle part du TAM mature ? Si > 60 % du TAM, c'est probablement irréaliste sauf monopole structurel.

## Tableau de cohérence à compléter

Pour chaque modèle de valorisation, remplir :

| Paramètre | Valeur projetée | Benchmark sectoriel | Cohérent ? |
|-----------|-----------------|---------------------|------------|
| Croissance des revenus | x % | y % (médiane) | ? |
| Marge opérationnelle | x % | y % (leader) | ? |
| ROIC implicite | x % | y % (leader) | ? |
| Taux de réinvestissement | x % | y % (typique secteur) | ? |
| Durée de croissance haute | x ans | y ans (typique) | ? |
| Part de marché finale | x % | y % (TAM réaliste) | ? |

Si > 2 paramètres sont incohérents avec les benchmarks, le modèle est cassé.

## Conclusion

La cohérence dynamique transforme un DCF d'exercice de prévision en outil d'analyse rigoureuse. Toute valorisation publiée par un investisseur professionnel passe par ce test — pas seulement le calcul de la VPN.
