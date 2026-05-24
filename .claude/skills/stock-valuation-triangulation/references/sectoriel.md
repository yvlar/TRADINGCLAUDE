# Méthodes sectorielles

Quand le DCF classique n'est pas adapté ou que les multiples comparables ne suffisent pas, certains secteurs ont leur propre méthode.

## Holdings et conglomérats — Somme des parties (SOTP)

```
Valeur SOTP = Σ (Valeur de chaque segment) − Coûts du holding − Dette nette
```

Pour chaque segment :
- Soit valoriser par DCF dédié si le segment a des FCF identifiables
- Soit valoriser par multiple sectoriel approprié au segment
- Appliquer une **décote de holding** de 10-20 % pour refléter la complexité et les coûts de structure

### Exemple : Power Corporation du Canada (POW.TO)
- Great-West Lifeco (assurance) : valoriser comme assureur via P/B × ROE
- IGM Financial (gestion d'actifs) : valoriser via multiple AUM ou P/E
- Power Sustainable, Sagard, GBL Group : participations de capital-investissement à valoriser au PBR ou NAV
- Total SOTP − dette holding − décote = valeur intrinsèque

## Banques et assureurs — Méthode P/B × ROE

Le DCF classique ne marche pas (les FCF des banques n'ont pas le même sens). Méthode standard :

```
Valeur = Book Value tangible × Multiple P/B justifié

Multiple P/B justifié = (ROE durable − g) / (Coût des CP − g)
```

Où :
- ROE durable = ROE moyen sur le cycle complet (pas le pic)
- Coût des CP = via CAPM
- g = croissance perpétuelle des CP (typiquement 2-3 %)

### Exemple : Royal Bank of Canada
- ROE durable ~16 %
- Coût des CP ~9-10 %
- g = 3 %
- P/B justifié = (16% − 3%) / (9.5% − 3%) = 2.0×

À comparer avec le P/B actuel (~1.8× en 2026). Si actuel > justifié → surévalué.

## REIT (immobilier coté) — NAV ou FFO multiple

### NAV (Net Asset Value)
Valeur des immeubles évalués individuellement (par cap rate sectoriel) − dette nette.

```
NAV par action = (Σ NOI par immeuble / cap rate sectoriel − dette) / actions
```

Cap rates typiques 2026 : 5-6 % pour retail prime, 4-5 % pour industriel logistique, 6-7 % pour bureaux secondaires.

### FFO multiple
```
FFO (Funds From Operations) = Bénéfice net + dépréciation immobilière − gains sur ventes
P/FFO multiple ≈ 12-18× pour REITs de qualité matures
```

## Ressources naturelles — Valeur des réserves prouvées

```
Valeur = Σ (Réserves prouvées par puits/mine × prix de la commodité × marge − coûts d'extraction futurs actualisés)
```

Pour le pétrole : utiliser le prix forward du WTI ou Brent (pas le spot). Pour les mines, le prix du métal × grade × taux de récupération. Damodaran a des tables de NAV par baril/once par compagnie.

## SaaS jeunes — Rule of 40 + ARR multiple

Pour les entreprises non rentables mais en forte croissance :

```
Rule of 40 = Croissance des revenus (%) + Marge FCF (%)
```

Si Rule of 40 > 40 % → entreprise en bonne santé fondamentale. Multiple ARR justifié élevé.

```
EV / ARR forward = typiquement 5-8× pour SaaS mature, 8-15× pour Rule of 40 > 50%
```

Mais attention : les multiples ARR ont chuté massivement en 2022-2023 après la bulle 2021. Les multiples 2026 sont normalisés autour de 5-8× pour la majorité des SaaS.

## Cycliques matures — Marges normalisées

Pour autos, chimie, sidérurgie, papier :

```
EBITDA normalisé = Revenus actuels × Marge moyenne sur cycle complet (10-15 ans)
Valeur = EBITDA normalisé × Multiple cycle median
```

Le piège classique : utiliser la marge actuelle. En sommet de cycle, les marges sont anormalement hautes ; en creux, anormalement basses. **Toujours normaliser** sur un cycle entier.

## Quand chaque méthode prime

| Situation | Méthode dominante |
|-----------|-------------------|
| Holding type Berkshire/POW | SOTP (50-70 % du poids) |
| Banque, assureur | P/B × ROE (60-70 %) |
| REIT | NAV (40 %) + FFO multiple (40 %) |
| Pétrolière E&P | NAV des réserves (60 %) |
| Mine | NAV des réserves au prix forward (60 %) |
| SaaS croissance | Rule of 40 + ARR multiple (50 %) |
| Cyclique matériaux | EBITDA normalisé × multiple cycle (50 %) |
| Autre / mature standard | DCF (50 %) + comparables (30 %) |
