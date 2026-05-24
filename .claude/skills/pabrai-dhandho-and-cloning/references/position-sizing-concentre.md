# Position Sizing Concentré (méthode Pabrai)

Pabrai pratique une **concentration extrême** : 8-15 positions au total, avec position size 5-25 % par opportunité. Cette concentration est inhabituelle vs la diversification "20-30 positions" de la finance académique.

## Pourquoi concentrer

### 1. Les bonnes opportunités sont rares
Pabrai dit que sur 20 ans, il a peut-être eu **30-40 vraies bonnes idées**. Diluer ces 30-40 idées sur 50 positions revient à noyer les gains.

### 2. La conviction guide l'allocation
Si tu trouves une opportunité 5-bagger avec 70 % de probabilité, l'allouer à 2 % du portefeuille est sous-optimal. Allouer 15-20 % capture la valeur.

### 3. La connaissance approfondie est limitée
Tu ne peux pas connaître intimement 50 entreprises. Tu peux suivre 10-15 en profondeur. Concentration aligne la position size avec la qualité de l'analyse.

## Méthodes de position sizing

### Kelly Criterion (théorique)

```
f* = (bp - q) / b
```

Où :
- f* = fraction du capital à allouer
- b = ratio gain/perte (asymétrie)
- p = probabilité de gain
- q = probabilité de perte (1-p)

### Exemple
Opportunité avec :
- Gain attendu : +200 % (b = 2)
- Probabilité de gain : 60 % (p = 0.6, q = 0.4)
- Perte attendue : -50 %

f* = (2 × 0.6 - 0.4) / 2 = 0.4 = **40 % du capital**

### Pourquoi pas le Kelly intégral

Kelly intégral est mathématiquement optimal pour maximiser la croissance long-terme **à condition** que les probabilités soient connues exactement. En investissement, **les probabilités sont estimées** avec marge d'erreur importante.

Conséquence : appliquer Kelly intégral mène à des positions trop grandes, drawdowns extrêmes.

### Kelly fractionnel (Pabrai)

Pabrai applique typiquement **Kelly / 4** ou **Kelly / 2** :

Reprenant l'exemple : Kelly intégral 40 %, Kelly fractionnel 10-20 %.

Cette approche :
- Maintient l'avantage de concentration sur convictions fortes
- Limite l'erreur si l'estimation des probabilités est trop optimiste
- Permet de survivre aux drawdowns

### Plafond pratique 25 %

Même avec Kelly fractionnel, Pabrai plafonne à **25 % par position individuelle**. Au-delà, le risque idiosyncratique (fraude, événement noir-cygne) devient inacceptable.

## Construction du portefeuille Pabrai typique

### Configuration cible
- **8-15 positions au total**
- **Top 3-4 positions** : 15-25 % chacune (= 50-70 % du portefeuille)
- **Mid positions** : 5-10 % (= 20-30 %)
- **Cash** : 5-15 % (réserve d'opportunité)

### Pas de "filler positions"
Pabrai n'ajoute pas de positions à 1-2 % "pour la diversification". Soit la position mérite 5 %+, soit elle ne mérite pas la place.

## Gestion des drawdowns

Une position à 20 % qui chute -50 % = -10 % du portefeuille total. Trois positions de 20 % qui chutent ensemble en récession = -30 % drawdown.

**Pabrai accepte explicitement ces drawdowns**. Le track record :
- 2008-2009 : Pabrai Funds drawdown ~-65 %
- 2009-2018 : récupération + appréciation supplémentaire massif
- Net 1999-2018 : +25 % CAGR

Sans le tempérament pour traverser -50 % drawdowns, **ne pas appliquer cette stratégie**. La concentration amplifie tout — gains et pertes.

## Diversification minimum acceptable

Pabrai concentre mais maintient une diversification **minimum** :
- **Pas plus de 50 % dans un seul secteur**
- **Pas plus de 30 % dans une seule géographie** (US, India, Canada)
- **Pas plus de 25 % corrélés** (ex: 25 % de banques régionales = position quasi-unique)

Cette discipline minimale évite les catastrophes liées à un seul facteur de risque.

## Comparaison avec autres approches

| Stratégie | # positions | Top size | Drawdown attendu |
|-----------|-------------|----------|-------------------|
| Index SP500 | 500 | 7 % (Apple) | -30 à -40 % |
| Buffett (Berkshire actuel) | 50 long + private | 35 % (Apple) | -30 à -45 % |
| **Pabrai** | 8-15 | 25 % | -50 à -70 % |
| Munger (Daily Journal) | 5 | 50 % | -60 à -80 % |
| Klarman | 30+ avec hedges | 10 % | -10 à -25 % |

Pabrai est plus concentré que Buffett mais moins que Munger. Klarman fait l'inverse — diversifie + hedge pour limiter drawdowns.

## Adaptation pour investisseur particulier

Un particulier peut considérer :

### Version 75 % concentration
- 12 positions cibles
- Top 3 à 15-18 % chacune
- Mid 9 à 4-7 %
- Cash 5-10 %

### Version 50 % concentration (plus prudente)
- 20 positions cibles
- Top 3 à 8-10 %
- Mid 17 à 3-5 %
- Cash 5-10 %

Le choix dépend du **tempérament personnel** face aux drawdowns. Tester sur petits montants d'abord.

## Quand sortir / réduire une position

Pabrai vend ou réduit quand :
- **La thèse a été jouée** (le mispricing s'est corrigé)
- **La thèse est cassée** (nouveaux faits invalident la logique)
- **Une meilleure opportunité** demande capital
- **Position devient > 30 %** par appréciation (rebalancing forcé)

Ne **pas vendre** parce que :
- Le prix a monté de 50 % mais la thèse est intacte
- Les analystes downgrade à des niveaux ridicules
- Tu as besoin "d'engager les profits"
- Tu paniques en marché baissier

## Conclusion

La concentration Pabrai amplifie l'edge de la sélection. Sans edge réel (capacité de sélection supérieure au marché), la concentration est destructrice. Pour un débutant : commencer avec une concentration modérée (15-20 positions), monter progressivement à mesure que la conviction et le track record personnel se construisent.
