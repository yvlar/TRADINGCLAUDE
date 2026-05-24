# Multiples comparables

## Principe

Valoriser une entreprise par les multiples que le marché applique à ses pairs. Méthode rapide et ancrée dans les prix de marché actuels, mais avec un piège : si tout le secteur est mispricé, les comparables reproduisent l'erreur.

## Multiples principaux

### EV/EBITDA forward
**Le multiple le plus utilisé pour les industriels matures.** Insensible à la structure de capital (numérateur EV inclut la dette, dénominateur EBITDA est avant intérêts).

```
EV = Capitalisation + Dette − Cash − Investissements de portefeuille
EV/EBITDA = EV / EBITDA forward 12 mois
```

Typiquement 6-8× pour les cycliques matures, 10-12× pour les leaders qualité, 15-20× pour les compounders avec moat fort.

### P/E forward
Sensible à la structure de capital (au numérateur, le P inclut le levier ; au dénominateur, l'EPS est après intérêts). À utiliser surtout pour des comparaisons inter-secteurs ou inter-pays, jamais isolément.

### P/FCF
Plus robuste que le P/E pour distinguer les bénéfices "cash" des bénéfices comptables gonflés. Utile pour les industries où les accruals sont importants (cycliques, pharma).

### EV/Revenus
Pour les entreprises **non rentables** (jeunes SaaS, biotechs en phase clinique). Très volatil, à utiliser avec beaucoup de prudence.

### P/B tangible
Pour les **financières et l'immobilier**. Inutile pour les asset-light (SaaS, services). Au Canada, particulièrement utile pour les banques (RBC, TD, BMO trade typiquement 1.5-2× P/B).

## Choix des pairs

**Bon pair = même business model, taille comparable, géographie similaire, phase de cycle de vie similaire.**

Exemples :
- Pour Constellation Software (CSU.TO) : Topicus (TOI.V), Lumine Group (LMN.V), Verisk (VRSK), Roper Technologies (ROP) — tous des serial acquirers de logiciels verticaux
- Pour CN Rail (CNR.TO) : CP (CP.TO), Union Pacific (UNP), CSX, Norfolk Southern (NSC) — chemins de fer Class I

**Mauvais pair** : même secteur GICS mais profil radicalement différent. Comparer Boeing à Lockheed Martin sur EV/EBITDA est un piège — Boeing est cyclique commercial, Lockheed est défense gouvernementale.

## Méthode robuste : la médiane

**Toujours utiliser la médiane, jamais la moyenne.** Une moyenne est dominée par les extrêmes (un pair à 30× tire toute la moyenne vers le haut). La médiane reflète mieux le multiple typique du secteur.

```
Multiple cible = médiane des 4-6 pairs comparables
Valeur estimée = Multiple cible × métrique de l'entreprise
```

## Ajustements pour la qualité

Une entreprise mérite une **prime sur le multiple médian** si :
- ROIC supérieur de plus de 5 points à la médiane sectorielle
- Croissance attendue supérieure de plus de 30 % à la médiane sectorielle
- Moat manifestement plus large
- Direction qui a démontré une allocation de capital supérieure

Une **décote** est justifiée si :
- ROIC inférieur, marges en érosion
- Concentration clients/géographique élevée
- Gouvernance problématique
- Dette excessive

Ajustements typiques : ± 10-25 % du multiple médian.

## Pièges classiques

1. **Choisir les pairs après-coup** : sélectionner les pairs qui valident le prix-cible désiré. Définir les pairs **avant** de connaître le résultat.
2. **Mélanger forward et trailing** : EBITDA forward des pairs vs EBITDA trailing de l'entreprise = comparaison fausse.
3. **Ignorer le levier** : utiliser P/E pour comparer une entreprise très endettée à un pair sans dette donne un résultat biaisé.
4. **Pairs hors géographie** : un multiple US n'est pas applicable tel quel à un pair canadien (différence de fiscalité, de couverture analytique, de liquidité).

## Sources de données

- Pour les multiples sectoriels US : Damodaran publie des tables sectorielles gratuites
- Pour le Canada : TMX Money, S&P Capital IQ (payant), GuruFocus
- Toujours **vérifier la fraîcheur** : un multiple basé sur des earnings de Q3 alors qu'on est en Q1 suivant est obsolète
