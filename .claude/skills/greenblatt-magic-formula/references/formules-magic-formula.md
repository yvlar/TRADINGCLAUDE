# Formules de la Magic Formula

## Return on Capital (ROC)

Différence importante avec le ROIC standard : Greenblatt utilise le **capital opérationnellement nécessaire**, pas le total des capitaux employés.

```
ROC = EBIT / (Net Working Capital + Net PP&E)
```

### Net Working Capital (de Greenblatt)

```
NWC = max(0, (Current Assets - excess cash) - (Current Liabilities - interest-bearing debt))
```

Exclusions :
- **Excess cash** : exclure le cash au-delà du besoin opérationnel (typiquement on garde 1-3 % des revenus comme cash opérationnel, le reste est "excess")
- **Interest-bearing short-term debt** : exclure des passifs courants car déjà capturée par le numérateur EBIT (avant intérêts)

### Net PP&E

Property, Plant & Equipment **net** des amortissements accumulés (= valeur comptable nette).

### Pourquoi pas le total des actifs ?

Greenblatt argumente que le goodwill, les intangibles d'acquisition et les investissements financiers gonflent artificiellement le capital sans refléter le besoin opérationnel réel. Une entreprise qui a payé 10 G$ de goodwill pour une acquisition n'a pas besoin de ce 10 G$ pour générer son EBIT actuel.

C'est une simplification, mais c'est une simplification **utile** : elle compare les entreprises sur leur capacité opérationnelle pure, ignorant les choix d'acquisition passés.

## Earnings Yield

```
Earnings Yield = EBIT / Enterprise Value
```

### Enterprise Value

```
EV = Capitalisation boursière + Total Debt - Cash & Equivalents
```

### Pourquoi EBIT/EV plutôt que 1/PER

Trois raisons :

1. **EBIT est neutre vis-à-vis de la structure de capital** — comparable entre une société endettée et une non endettée
2. **EV inclut la dette au numérateur**, donc cohérent avec EBIT au dénominateur
3. **Évite les distortions fiscales** — taux d'imposition différents entre juridictions n'affectent pas EBIT/EV

C'est l'inverse mathématique du multiple **EV/EBIT** :
- EV/EBIT = 10× ↔ Earnings Yield = 10 %
- EV/EBIT = 5× ↔ Earnings Yield = 20 %

Plus l'Earnings Yield est haut, plus l'entreprise est "bon marché" (plus de profit par dollar payé).

## Le classement combiné

Pour chaque action de l'univers :

1. **Calculer ROC** → classer du plus haut au plus bas → rang ROC (1 = meilleur)
2. **Calculer EY** → classer du plus haut au plus bas → rang EY (1 = meilleur)
3. **Score = rang ROC + rang EY** (plus bas = meilleur)
4. Trier par score croissant

### Exemple sur 5 actions

| Action | ROC | Rang ROC | EY | Rang EY | Score |
|--------|-----|----------|-----|---------|-------|
| A | 35 % | 2 | 12 % | 3 | **5** |
| B | 50 % | 1 | 8 % | 5 | **6** |
| C | 25 % | 3 | 18 % | 1 | **4** ← meilleur |
| D | 20 % | 4 | 15 % | 2 | **6** |
| E | 15 % | 5 | 10 % | 4 | **9** |

L'action C remporte parce qu'elle combine **bonne qualité** (rang 3 ROC) **et bon prix** (rang 1 EY) sans être extrême sur aucune dimension.

## Pourquoi pas une simple multiplication ROC × EY ?

Greenblatt a testé plusieurs combinaisons. Le double classement par rangs :
- Évite la dominance par les valeurs extrêmes
- Crée des "punitions" symétriques pour les positions médiocres sur l'une des deux dimensions
- Marche mieux empiriquement en backtest

Une entreprise avec ROC 100 % mais EY 1 % aurait un produit attractif (1 %) mais reste très chère. Le double classement la pénalise correctement.

## Métriques exclues (intentionnellement)

Greenblatt **n'utilise pas** :
- Croissance des revenus / bénéfices
- Marges
- Dette totale
- Dividendes
- Croissance du FCF

L'argument : ces métriques sont déjà encodées dans ROC et EY (une entreprise endettée a un EV élevé, une entreprise en déclin a EBIT TTM faible). Ajouter des métriques redondantes augmente la complexité sans améliorer le résultat.

C'est l'**Occam's razor** appliqué au screening value.
