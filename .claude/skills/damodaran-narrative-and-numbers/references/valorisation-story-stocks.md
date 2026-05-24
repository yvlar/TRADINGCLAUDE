# Valoriser les Story Stocks (Damodaran)

Les *story stocks* — entreprises non rentables, en transformation, ou avec une trajectoire de croissance non standard — résistent au DCF classique. Damodaran propose un cadre adapté.

## Pourquoi le DCF classique échoue

Un DCF standard exige des FCF projetés sur 5-10 ans. Pour une entreprise qui :
- N'a pas encore de profitabilité
- A des marges qui se transforment fortement année après année
- Investit lourdement avant de capter la valeur

→ projecter mécaniquement les FCF actuels reproduit les pertes ad infinitum, donnant une valeur négative absurde.

## Le DCF en deux phases (Damodaran)

L'approche de base :

```
Phase 1 (5-10 ans) : Croissance haute, marges en transformation
  - Année 1-3 : pertes ou bas profits, investissements lourds
  - Année 4-7 : montée en marges
  - Année 8-10 : marges proche du long-terme

Phase 2 (perpétuité) : État stable
  - Croissance modérée (g terminal)
  - Marges et ROIC normalisés
```

## Étape 1 — Définir l'état stable

Avant de modéliser la transition, il faut savoir où on va :
- **Marge opérationnelle long-terme** : basée sur les leaders du secteur ou sur des analogues mature.
- **ROIC long-terme** : doit être ≥ WACC (sinon pas de moat). Typiquement 15-25 % pour les bonnes entreprises.
- **Croissance perpétuelle** : 2-3 % typique (proche de l'inflation long-terme).

## Étape 2 — Modéliser la transition

Croissance des revenus :
- Année 1-3 : forte (40-100 % pour SaaS, 20-40 % pour autres)
- Année 4-7 : décélération graduelle
- Année 8-10 : convergence vers la croissance perpétuelle

Marge opérationnelle :
- Trajectoire crédible vers la marge long-terme
- Lente au début (investissements), accélération avec l'échelle

Ratio de réinvestissement :
- Élevé en phase de croissance (capex, R&D, S&M agressifs)
- Diminue avec maturité

## Étape 3 — Cohérence dynamique

**Le test ultime** : la trajectoire doit satisfaire la relation fondamentale :

```
Croissance soutenable = ROIC × Taux de réinvestissement
```

Si la projection viole cette relation, l'un des paramètres est faux.

Exemple : projeter 30 % de croissance pendant 10 ans avec 60 % de réinvestissement → ROIC implicite = 50 %. Test : un ROIC de 50 % est-il atteignable et durable ? Pour la plupart des entreprises, non — la story est incohérente.

## Étape 4 — Test contre les pairs

Les paramètres long-terme doivent être **cohérents avec les leaders du secteur** :

| Paramètre | Plausibilité |
|-----------|---------------|
| Marge opérationnelle | ≤ Marge des 2-3 leaders historiques |
| ROIC | ≤ ROIC des 2-3 leaders historiques |
| Taille mature | Cohérent avec le TAM réaliste |

Si tu projettes des paramètres meilleurs que tous les leaders historiques de l'industrie, tu projettes que cette entreprise sera **la meilleure de toute l'histoire de son secteur**. À justifier sérieusement.

## Étape 5 — Probabilité de survie

Les story stocks ont un risque réel d'échec. Damodaran propose d'introduire une probabilité de survie explicite :

```
Valeur intrinsèque = (Probabilité de succès × Valeur en cas de succès) +
                    (Probabilité d'échec × Valeur en cas d'échec)
```

Pour une SaaS pré-profitabilité avec 70 % de chance d'atteindre l'état stable :
- Valeur si succès : 100 USD/action
- Valeur si échec : 5 USD/action (liquidation/rachat à bas prix)
- Espérance : 0.7 × 100 + 0.3 × 5 = 71.5 USD/action

## Étape 6 — Sensibilité Monte-Carlo

Pour les story stocks, les paramètres critiques (croissance, marge, ROIC, durée de croissance haute) ont une variance énorme. Une simulation Monte-Carlo (1000+ scénarios avec distributions de paramètres) donne une fourchette honnête.

Damodaran utilise typiquement :
- Distribution **triangulaire** sur la marge long-terme (min, mode, max)
- Distribution **lognormale** sur la croissance
- Distribution **uniforme** sur la durée de croissance haute (5 à 10 ans)

Output : distribution des valeurs intrinsèques. P10 = pessimiste, P50 = central, P90 = optimiste.

## Cas particuliers

### Pre-revenue stage (biotech avec un seul candidat médicament)

Damodaran utilise un **modèle d'option** : la valeur de l'entreprise = valeur de l'option d'avoir un médicament approuvé × probabilité × valeur si approuvé.

Méthode Black-Scholes adaptée. Hors scope de ce skill — voir littérature spécialisée.

### Crypto et actifs sans cash flows

Damodaran a écrit explicitement que **les actifs sans cash flows ne se valorisent pas** au sens financier. Ils se "pricent" par offre/demande mais n'ont pas de valeur intrinsèque calculable.

Cela inclut Bitcoin, NFTs, crypto en général. À traiter comme des actifs spéculatifs, pas des investissements.

### Entreprises en distress

Pour une entreprise en distress (forte probabilité de faillite), le DCF classique surestime la valeur car il ignore le risque de zéro.

Modèle : valeur = (1 - P(faillite)) × DCF + P(faillite) × valeur de liquidation

Voir aussi `klarman-margin-of-safety` pour situations distressed.

## Pièges courants

### 1. Optimisme caché dans les marges long-terme

Le piège classique : projeter une marge long-terme de 30 % pour une entreprise dont le secteur a une médiane à 12 %. Justification implicite : "elle sera meilleure". Sans evidence solide, **plafonner à la médiane sectorielle**.

### 2. Durée de croissance haute irréaliste

10 ans à +30 %/an est extrême. La majorité des entreprises ne maintiennent pas une croissance > 20 % au-delà de 5-7 ans. Rule of thumb : durée 5-7 ans, sauf evidence exceptionnelle.

### 3. Réinvestissement insuffisant

Pour soutenir une forte croissance, il faut massivement investir. Si ton modèle a 50 % de croissance avec 20 % de réinvestissement, ROIC implicite = 250 % — impossible.

### 4. Ignorance du capital nouveau

Pour financer le réinvestissement massif, l'entreprise émettra typiquement de nouvelles actions (dilution) ou de la dette. Modéliser explicitement la dilution attendue dans la valeur par action.

## Synthèse

Les story stocks sont valorisables **si et seulement si** :
1. La story passe le test "probable"
2. Les paramètres long-terme sont cohérents avec les leaders historiques
3. La cohérence dynamique (ROIC × Reinvestment = Growth) tient
4. La probabilité de survie est explicite
5. La fourchette de valeurs est large mais comportable

Si l'un de ces points échoue, la "valorisation" est un exercice de fiction.
