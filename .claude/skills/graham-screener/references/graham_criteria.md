# Les 7 critères de Graham — référence détaillée

Source : *The Intelligent Investor*, Benjamin Graham, chapitre 14
(« Stock Selection for the Defensive Investor »), édition révisée 1973.

## 1. Taille adéquate de l'entreprise

**Original** : revenus annuels ≥ 100 M$ (industriel) ou actifs ≥ 50 M$ (services publics).
**Adaptation** : 100 M$ de 1973 ≈ 700 M$ aujourd'hui; le script utilise 2 G$ par
défaut pour rester dans les mid/large caps liquides. Justification : éliminer
les petites entreprises plus vulnérables aux chocs. Ajustable via `min_revenue`.

## 2. Situation financière suffisamment solide

**Original** : ratio de liquidité générale (actif courant / passif courant) ≥ 2,
ET dette à long terme ≤ fonds de roulement net (actif courant − passif courant).
**Piège sectoriel** : non pertinent pour banques et assureurs (structure de
bilan différente); sévère pour les entreprises à rotation rapide des stocks
(détaillants sains peuvent échouer ici).

## 3. Stabilité des bénéfices

**Original** : bénéfices positifs chacune des 10 dernières années.
**Adaptation** : yfinance fournit ~4-5 ans → le script évalue sur la fenêtre
disponible et marque `partial_data`. Une seule année de perte = FAIL (Graham
était strict là-dessus : la perte de 2023 de BMY la disqualifie, par exemple).

## 4. Historique de dividendes

**Original** : versements ininterrompus pendant 20 ans.
**Adaptation** : le script vérifie la continuité sur tout l'historique yfinance
disponible (souvent > 20 ans pour les dividendes, contrairement aux états
financiers). Une interruption = FAIL.

## 5. Croissance des bénéfices

**Original** : BPA en hausse d'au moins un tiers sur 10 ans, en comparant les
moyennes de 3 ans au début et à la fin (≈ 2,9 %/an composé).
**Adaptation** : CAGR ≥ 3 %/an sur la fenêtre disponible. Exigence volontairement
basse — Graham voulait éliminer les entreprises en déclin, pas trouver de la
croissance.

## 6. Ratio cours/bénéfice modéré

**Original** : prix ≤ 15 × les bénéfices moyens des 3 dernières années.
**Pourquoi la moyenne 3 ans** : lisser les pics et creux cycliques. C'est plus
sévère qu'un P/E forward — une entreprise dont les bénéfices viennent de
s'effondrer puis rebondissent (cas BMY 2023) échoue au test même si le P/E
forward semble bas. C'est voulu : Graham se méfiait des bénéfices « normalisés »
promis par la direction.

## 7. Ratio cours/valeur comptable modéré

**Original** : P/B ≤ 1,5, OU produit P/E × P/B ≤ 22,5 (permet un P/B plus haut
si le P/E est très bas, et inversement).
**Piège sectoriel** : pénalise structurellement les entreprises asset-light
(logiciel, marques) dont la valeur est dans les intangibles non capitalisés.
Graham l'assumait : ces entreprises relèvent de l'investisseur entreprenant,
pas du défensif.

## Le Graham Number

√(22,5 × BPA × valeur comptable par action) — le prix maximal cohérent avec
les critères 6 et 7 combinés. Marge de sécurité = (GN − prix) / GN. Une marge
positive ≥ 20-30 % était le territoire de chasse de Graham.

## Interprétation des scores

- **7/7** : rare en marché haussier. Analyse qualitative complète justifiée.
- **5-6/7** : candidat sérieux; examiner précisément quels critères échouent
  et pourquoi (sectoriel ? cyclique ? structurel ?).
- **3-4/7** : généralement éliminé du pilier value défensif; peut relever
  d'une thèse entreprenante (turnaround, actifs cachés).
- **≤ 2/7** : éliminé. Si le prix semble quand même « bas », c'est
  probablement un value trap.
