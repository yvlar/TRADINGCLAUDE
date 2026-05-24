# Scenarios Bull/Base/Bear avec Probabilités

Les scenarios pondérés sont la base de la **value-at-risk pratique** pour un investissement. Plutôt qu'un seul "prix cible", on articule un éventail de futurs possibles avec leurs probabilités.

## Pourquoi 3 scenarios

### Cohérence cognitive

Les humains pensent naturellement en termes de scenarios narratifs ("ça pourrait se passer comme ça, ou comme ça"). Plutôt que résister, structurer ce raisonnement.

### 3 est un compromis

- Moins (1-2) = trop simpliste
- Plus (5-10) = false précision et paralysie

3 scenarios capturent l'asymétrie principale : pessimiste, central, optimiste.

## Comment construire chaque scenario

### Scenario Bear (pessimiste)

**Question** : "Si la thèse échoue, comment échoue-t-elle ?"

Articulater :
- Les facteurs qui causent l'échec (1-3 spécifiques)
- L'impact quantitatif sur les fondamentaux (revenus, marges, FCF)
- L'impact sur le multiple de valorisation (multiple compression typique)
- Le prix résultant

**Note** : ce n'est PAS le pire cas absolu (faillite). C'est le scenario d'échec **réaliste** pondéré par sa probabilité.

### Scenario Base (médian)

**Question** : "Quelle est la trajectoire la plus probable ?"

Articulater :
- Hypothèses de croissance et marges modérées
- Évolution du multiple (souvent neutre, retour à la médiane historique)
- Impact des dividendes / buybacks
- Prix résultant sur l'horizon

### Scenario Bull (optimiste)

**Question** : "Si la thèse marche pleinement, qu'arrive-t-il ?"

Articulater :
- Les facteurs qui amplifient la thèse
- Marges et croissance au-dessus du base case
- Multiple expansion possible
- Prix résultant

**Important** : Bull n'est pas "tout va bien" — c'est un scenario réaliste où la thèse se réalise. Pas une fantaisie marketing.

## Probabilités

### Calibration

Pour la plupart des thèses :
- **Bear** : 20-30 %
- **Base** : 40-60 %
- **Bull** : 15-30 %

Total = 100 %.

### Cas particuliers

**Compounder à thèse forte** : bull 35 %, base 50 %, bear 15 %.

**Special situation incertaine** : bear 30 %, base 40 %, bull 30 %.

**Distressed** : bear 40-50 %, base 30 %, bull 20-30 %.

### Erreur typique

Beaucoup d'investisseurs sous-pondèrent le bear et surpondèrent le bull. Calibration honnête demande discipline.

Heuristique : si tu n'as **pas** identifié un scenario bear avec > 20 % de probabilité, tu n'as probablement pas fait l'inversion adéquate (croiser avec `munger-mental-models`).

## Calcul de l'Espérance (EV)

```
EV = Σ (probabilité × impact) - Prix d'achat
```

### Exemple

Position dans XYZ Corp.
- Bear (25 %) : prix descend à 60 (vs 100 actuel) = -40 %
- Base (50 %) : prix monte à 150 sur 5 ans = +50 %
- Bull (25 %) : prix monte à 250 sur 5 ans = +150 %

EV = 0.25 × (-40 %) + 0.50 × (+50 %) + 0.25 × (+150 %)
EV = -10 % + 25 % + 37.5 %
EV = +52.5 %

Sur 5 ans, EV de +52.5 % = ~8.8 %/an annualisé. **Marginalement positif** vs alternative S&P 500 (~7-9 %/an attendu).

### Heuristique de validation

| EV pondérée | Décision typique |
|-------------|-------------------|
| EV > +60 % sur 5 ans | Position size élevée justifiée |
| EV +30-60 % | Position normale |
| EV +10-30 % | Position prudente |
| EV < +10 % | Pas d'edge — passer ou indexer |
| EV négative | Refuser absolument |

Important : l'EV n'est pas la seule métrique. La **distribution** compte aussi (asymétrie, kurtosis).

## Application Kelly fractionnel

Pour position sizing optimal, voir `pabrai-dhandho-and-cloning/references/position-sizing-concentre.md`.

Formule simplifiée :
```
f* = (probabilité_gain × multiple_gain - probabilité_perte) / multiple_gain
```

Pour l'exemple ci-dessus :
- p_gain (combined base + bull) = 75 %
- p_perte = 25 %
- gain_moyen = (50 % × 0.5/0.75 + 150 % × 0.25/0.75) = 83 %
- perte_moyenne = 40 %

Kelly intégral = (0.75 × 0.83 - 0.25) / 0.83 = 0.45 = 45 %

Kelly fractionnel (Pabrai /4) = 11 % position size.

## Pièges des scenarios pondérés

### 1. Probabilités fantaisies

Donner une probabilité à 1 % près est faux. Préférer 5 % ou 10 % d'arrondis.

### 2. Optimism cachée dans les scenarios

Le scenario bear de la plupart des investisseurs est en fait un scenario "neutre". Vrai bear = perte significative (-30 % au minimum).

Discipline : pour chaque thèse, le scenario bear doit représenter **une perte permanente significative**, pas juste un multiple compression mineur.

### 3. Pas d'horizon temporel

"Le prix monte à 200" — sur quelle période ? L'EV doit être annualisée pour comparer aux alternatives.

### 4. Probabilités intuitives sans justification

Pourquoi le bear est-il à 25 % et non 35 % ? Articuler le raisonnement :
- Base rate historique de l'industrie
- Précédents comparables
- Quality de la direction
- Conditions de marché actuelles

### 5. Manque de cohérence avec l'analyse fondamentale

Si l'analyse Buffett-quality dit "wonderful business", le scenario bear ne peut pas être "faillite probable". Cohérence demandée.

## Templates de scenarios par type d'opportunité

### Compounder de qualité
- Bear (15-20 %) : Multiple compression de 30 % + croissance ralentie
- Base (50-60 %) : Compounding 12-15 %/an
- Bull (25-30 %) : Compounding 18-22 % + multiple expansion

### Cyclique au creux
- Bear (30 %) : Cycle plus profond et long que prévu, prix flat
- Base (40 %) : Récupération normale, multiplier ×2 sur 5 ans
- Bull (30 %) : Cycle exceptionnel, multiplier ×4 sur 5 ans

### Special situation (Spinoff)
- Bear (25 %) : Spinoff sous-performe, recombination
- Base (50 %) : Spinoff stable, retour à valeur fondamentale +30-50 %
- Bull (25 %) : Spinoff surperforme, +100-200 %

### Distressed
- Bear (40-50 %) : Faillite ou dilution massive, perte totale ou -70 %
- Base (30 %) : Restructuration réussit, recovery 100-200 %
- Bull (20-30 %) : Turnaround spectaculaire, recovery 300-500 %

## Synthèse

Les scenarios pondérés transforment une intuition vague en décision quantifiée. La rigueur du processus compte plus que la précision absolue des probabilités — qui sont par nature subjectives.

L'investisseur sérieux fait cet exercice **pour chaque position significative** et le révise annuellement.
