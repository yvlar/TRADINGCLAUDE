# Construction du portefeuille — discipline d'application

## Méthodologie originelle Greenblatt (*The Little Book*)

### Composition
- **20-30 positions** approximativement **équipondérées**
- Choisir les top 20-30 du score combiné, après filtre sectoriel et qualitatif minimal
- Pondération égale (3.3 %-5 % par position)

### Holding period
- **1 an exactement** par position pour optimisation fiscale aux USA (taux long-terme déclenché à 365 jours)
- Au Canada, le délai n'a pas d'effet fiscal (gain en capital toujours à 50 %), mais la rotation régulière reste recommandée pour cohérence avec le screen

### Rotation graduelle
Pour éviter le timing du marché et lisser les rentrées/sorties :
- Acheter 5-7 positions tous les 2-3 mois sur la première année
- Au bout de 12 mois, le portefeuille est complet
- Ensuite : chaque mois, vendre les positions qui ont 12 mois et acheter de nouvelles selon le screen mis à jour

### Mise à jour du screen
- Recalculer mensuellement les rangs ROC + EY sur l'univers
- Les actions vendues mensuellement sont remplacées par les nouveaux top 20-30

## Discipline psychologique

Greenblatt insiste **constamment** sur la discipline :

> *« The reason this strategy works is precisely because most people give up on it. »*

### Périodes de sous-performance attendues

Backtest 1988-2004 (période originale du livre) :
- 17 ans cumulés : +30 % par an environ vs +12 % S&P 500
- **Mais** : 5 années où la formule a sous-performé l'index
- **Et** : 2 années consécutives de sous-performance significative

L'investisseur typique abandonne après 18-24 mois de sous-performance. C'est précisément ce qui maintient l'efficacité de la formule pour les disciplinés.

### Test psychologique

Avant de commencer, se poser **par écrit** :
- Si la formule sous-performe le marché de 10 % en 2 ans cumulés, est-ce que je continue ?
- Si tous mes amis ridiculisent mes positions "ennuyeuses", est-ce que je continue ?
- Si je vois un autre stratégie performer mieux pendant 3 ans, est-ce que je résiste à pivoter ?

Si la réponse à toutes les questions n'est pas un "oui" sincère, ne pas commencer.

## Variantes adaptées

### Concentration plus forte (15 positions)
Certains praticiens utilisent les top 10-15 plutôt que 20-30 pour amplifier le rendement. Compromis :
- Volatilité supérieure
- Sensibilité aux outliers individuels (un fraudster détecté tardivement = -50 % sur une position majeure)

### Filtre qualité supplémentaire (Piotroski overlay)
Combiner Magic Formula et F-Score Piotroski :
- Top 50 par Magic Formula
- Filtrer ceux avec F-Score ≥ 7
- Garder 20-30 dans le portefeuille

Cette combinaison améliore typiquement les résultats backtest mais perd en simplicité.

### Equal-weight vs market cap-weight
Greenblatt préconise l'**equal weight**. Une variante minoritaire utilise la cap-weight pour réduire la volatilité, mais perd l'effet "small cap premium" qui était une partie de l'avantage.

## Pièges courants

### 1. Sélection arbitraire dans le top
"Je préfère cette position parce que j'aime son business" — c'est exactement ce que Greenblatt veut éviter. La sélection mécanique n'est pas négociable.

### 2. Surveillance excessive
La formule fonctionne sans intervention. Vérifier les positions chaque jour est inutile et conduit aux décisions émotionnelles.

### 3. Oubli de la rotation
Garder une position au-delà de 12 mois "parce qu'elle a bien performé" enfreint la discipline. La performance individuelle d'une position est moins importante que la cohérence du processus.

### 4. Re-paramétrage continu
"Je vais essayer avec top 50, puis avec top 15" — perdre la confiance dans la stratégie de base. Choisir un paramétrage et tenir au moins 3 ans.

## Outils gratuits

### magicformulainvesting.com (site original de Greenblatt)
Inscription gratuite. Donne le top 30 de l'univers US par capitalisation choisie (50M, 200M, 1G, 5G).

### Stockopedia, GuruFocus, Old School Value
Implémentations sur abonnement, avec options de filtrage personnalisées.

### Implémentation maison
Pour le marché canadien, peu d'outils gratuits. Possible avec :
- Données SEDAR+ (états financiers gratuits)
- Tableur calculant ROC et EY pour une liste curated de tickers TSX
- Le script `magic_formula_score.py` peut traiter un univers fourni en JSON
