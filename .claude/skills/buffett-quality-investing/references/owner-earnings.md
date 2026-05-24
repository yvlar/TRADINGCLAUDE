# Owner Earnings — La mesure de cash flow Buffett

Concept introduit par Buffett dans la lettre aux actionnaires Berkshire 1986. Réponse à un défaut majeur des Net Income et même du Free Cash Flow standard.

## Définition

> *« Owner earnings represent (a) reported earnings plus (b) depreciation, depletion, amortization and certain other non-cash charges, less (c) the average annual amount of capitalized expenditures for plant and equipment, etc., that the business requires to fully maintain its long-term competitive position and its unit volume. »*
> — Buffett, 1986

Formule simplifiée :

```
Owner Earnings = Net Income
              + Depreciation, Depletion, Amortization (non-cash)
              + Other non-cash charges
              − Maintenance Capex (capex pour préserver la position concurrentielle)
              ± Changes in Working Capital (si matériel)
```

## Pourquoi pas Net Income ?

Le Net Income comporte :
- D&A non-cash (qui surestiment les coûts économiques réels si l'actif réel ne se déprécie pas)
- Items non récurrents
- Effets fiscaux temporaires

Le Net Income peut sur- ou sous-estimer la cash flow économique réelle.

## Pourquoi pas Free Cash Flow standard ?

Le FCF standard (= CFO − Capex total) confond :
- Capex de **maintenance** (préserver la position)
- Capex de **croissance** (étendre le business)

Buffett insiste : seul le capex de maintenance doit être déduit pour calculer la "cash flow économique" disponible aux actionnaires.

Si l'entreprise réinvestit en croissance organique à ROIC élevé, ce capex de croissance n'est **pas un coût** — c'est un investissement qui crée de la valeur future.

## Le défi : estimer le capex de maintenance

Les entreprises ne publient **pas** la décomposition maintenance / croissance. Buffett admet cette difficulté :

> *« The number is, of course, an approximation. »*

### Méthodes d'approximation

#### Méthode 1 : Capex = D&A (pour entreprises mature stable)

Si l'entreprise est **stable** (revenus +/- 0-3 %/an), le capex total ≈ capex de maintenance ≈ D&A. C'est l'approche typique pour les utilities, banques.

```
Owner Earnings ≈ Net Income + Stock-based comp non-cash − (excess capex over D&A)
```

#### Méthode 2 : Capex / D&A ratio historique

Pour les entreprises avec croissance modérée, regarder le ratio capex/D&A historique :
- Si ratio = 1.0× : capex purement maintenance, FCF = Owner Earnings
- Si ratio = 1.5× : 33 % du capex est croissance — l'ajouter aux Owner Earnings
- Si ratio = 2.0× : 50 % capex croissance

#### Méthode 3 : Communication direction

Certaines directions excellentes (Brookfield, Constellation) décomposent explicitement maintenance vs growth capex dans leurs lettres ou earnings calls. Précieuse mais rare.

#### Méthode 4 : Regression sur revenus

Pour les entreprises matures :
- Maintenance capex ≈ D&A ajustée pour inflation
- Growth capex ≈ Revenue growth × Capex intensity historique

## Application au calcul de valeur

### Yield Owner Earnings

Owner Earnings / Enterprise Value = Owner Earnings Yield.

C'est le **rendement réel** que l'investisseur reçoit s'il payait le prix actuel sans levier.

**Niveaux typiques** :
- < 3 % : très cher
- 3-5 % : cher pour un compounder
- 5-8 % : raisonnable
- > 8 % : attractif

### DCF basé sur Owner Earnings

Plutôt que projeter FCF (qui inclut growth capex), projeter Owner Earnings croissants. Plus précis pour les entreprises en réinvestissement actif.

## Exemple : Coca-Cola 1988 (acheté par Berkshire)

D'après les chiffres approximatifs :
- Net Income : 1.0 G$
- D&A : 0.3 G$
- Capex total : 0.4 G$
- Capex maintenance estimé : 0.3 G$
- Stock-based comp : minimal en 1988

```
Owner Earnings = 1.0 + 0.3 − 0.3 = 1.0 G$
```

Vs Free Cash Flow standard = CFO − Capex total = ~0.9 G$.

Berkshire achète à market cap ~12 G$, soit Owner Earnings yield = 1.0/12 = **8.3 %**. Très attractif pour un compounder qualité.

Subséquemment Coca-Cola a multiplié ses Owner Earnings ×7-8 en 30 ans, et le multiple a expansé. Berkshire détient toujours.

## Exemple moderne : Apple FY2023

- Net Income : 96.9 G$
- D&A : 11.5 G$
- SBC (stock-based comp, non-cash) : 10.8 G$
- Capex total : 11.0 G$
- Capex maintenance estimé : ~9 G$ (croissance modérée)

```
Owner Earnings ≈ 96.9 + 11.5 + 10.8 − 9 = ~110 G$
```

Vs FCF standard = ~100 G$.

À une cap. boursière de ~3000 G$, Owner Earnings yield = 110/3000 = **3.7 %**. Pas bon marché.

⚠ Note : si on ne traite **pas** la SBC comme non-cash (les actions émises diluent les actionnaires existants), Owner Earnings serait inférieur. Buffett est ambigu sur ce traitement — la pratique académique moderne tend à **soustraire** la SBC.

## Pièges communs

### 1. Ignorer la stock-based compensation

La SBC est techniquement non-cash mais dilue les actionnaires. Beaucoup de tech companies ont des SBC excessives (>5 % des revenus) qui rendent les Owner Earnings flatteurs si on les considère "non-cash".

**Position prudente** : soustraire la SBC totale comme un coût économique réel.

### 2. Sous-estimer le capex de maintenance

Pour les entreprises capital-intensive (manufacturers, miners, telecoms), le capex de maintenance est souvent **équivalent** au capex total. Tenter d'allouer 40 % à "growth capex" peut sur-estimer Owner Earnings.

Test : quand l'entreprise a réduit son capex à zéro pendant une récession, ses revenus se sont-ils maintenus ou ont-ils décliné ? S'ils ont décliné = le capex était de maintenance.

### 3. Working capital non-récurrent

Les changes in working capital peuvent être lumpy. Pour Owner Earnings normalisés, prendre la moyenne sur 5 ans plutôt qu'une seule année.

### 4. Items non-récurrents non-cash

Restructuring charges, impairment, litigation provisions : techniquement non-cash mais souvent récurrents si on regarde sur 10 ans. Ne pas les ajouter aveuglément aux Owner Earnings.

## Synthèse

Owner Earnings est **le concept Buffett le plus important** pour quantifier la cash flow économique réelle. Plus précis que Net Income et FCF standard pour les compounders.

Le défi : estimer rigoureusement le capex de maintenance. Sans cette rigueur, Owner Earnings devient un calcul vague avec marge d'erreur 20-30 %.

Pour l'investisseur sérieux, calculer Owner Earnings sur 5-10 ans pour vérifier la **stabilité**. Les vrais compounders ont des Owner Earnings croissants graduellement, pas volatils.
