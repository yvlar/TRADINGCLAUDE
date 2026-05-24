---
name: buffett-quality-investing
description: Applique le cadre de Warren Buffett — quatre filtres ("a business I can understand", "favorable long-term economics", "able and trustworthy management", "very attractive price"), owner earnings, "wonderful businesses at fair prices", influence Munger sur l'évolution Graham → Buffett-Munger. À utiliser dès que l'utilisateur mentionne Buffett, Berkshire, "wonderful businesses", owner earnings, four filters, "circle of competence", or asks about Buffett's investment philosophy. Utilise toujours ce skill pour les analyses long-terme de compounders ou pour comprendre l'évolution de la pensée value.
---

# Buffett — Quality Investing

Warren Buffett (Berkshire Hathaway, 1965-présent, +20 % CAGR sur 60 ans) a évolué du *deep value* Graham vers le *quality investing* sous l'influence de Munger : *« It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price. »*

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Les 4 filtres et leur application | `references/4-filtres-buffett.md` |
| Owner earnings — calcul et interprétation | `references/owner-earnings.md` |
| Évolution Graham → Buffett-Munger | `references/evolution-graham-buffett.md` |
| Lecture des annual letters | `references/annual-letters.md` |

## Workflow

### Étape 1 — Filtre 1 : Cercle de compétence

> *« You don't have to be an expert on every company, or even many. You only have to be able to evaluate companies within your circle of competence. The size of that circle is not very important; knowing its boundaries, however, is vital. »*

**Test** : peux-tu écrire en 3-5 phrases comment cette entreprise gagne de l'argent, qui sont ses clients principaux, quels sont les 2-3 risques principaux ?

Si non, **hors cercle de compétence** — passer.

### Étape 2 — Filtre 2 : Économie long-terme favorable

L'entreprise a-t-elle :
- Un moat durable (croiser avec `dorsey-moat-analysis`) ?
- ROIC élevé maintenu sur 10+ ans ?
- Pricing power vérifiable ?
- Capital-efficiency (peu de capex pour maintenir l'activité) ?

```bash
python scripts/buffett_quality_score.py inputs.json
```

Le script évalue les métriques quantitatives de qualité (ROIC, gross margin durabilité, FCF/Revenu).

### Étape 3 — Filtre 3 : Direction compétente et intègre

Croiser avec `fisher-scuttlebutt` (15 points + scuttlebutt) et `munger-mental-models` (test des biais).

**Critères Buffett spécifiques** :
- Allocation de capital exemplaire (voir `references/4-filtres-buffett.md`)
- Communication transparente (lettres aux actionnaires franches)
- Compensation modeste vs création de valeur

### Étape 4 — Filtre 4 : Prix attractif

Pour Buffett **moderne** (post-Munger) :
- Pas besoin de discount Graham 50 % — un prix "fair" suffit pour les wonderful businesses
- Mais **toujours un prix**, jamais à n'importe quelle valorisation
- Multiple raisonnable vs croissance + ROIC

```bash
python scripts/owner_earnings.py inputs.json
```

Calcule les owner earnings et le rendement actuel sur ce flux normalisé.

### Étape 5 — Si les 4 filtres passent : holding period long-terme

Buffett répète : *« Our favorite holding period is forever. »*

En pratique :
- 5-10 ans minimum (See's Candies, Coca-Cola)
- Vente uniquement si fondamentaux changent (perte de moat, dégradation direction)
- Pas de vente sur volatilité de prix

## Le concept central : "Wonderful businesses at fair prices"

Évolution philosophique critique (1972, sous l'influence de Munger) :
- **Buffett 1.0 (Graham era)** : "Cigar butts" — entreprises médiocres très bon marché
- **Buffett 2.0 (Munger era)** : "Wonderful businesses" à des prix raisonnables

Le second approche surpasse le premier sur le très long-terme parce que :
1. Le compounding fonctionne sur la durée seulement avec des wonderful businesses
2. Les cigar butts donnent un seul puff (×2-3) puis sont dust
3. Le tax drag des trades fréquents érode les rendements

## Garde-fous

- **Le cercle de compétence n'est pas extensible par enthousiasme**. Buffett a évité tech pendant 50 ans — pas par snobisme mais par humility. Quand il a investi dans Apple en 2016, c'est parce qu'il avait passé 4 ans à étudier (et Apple s'était mué en consumer staple sous l'angle de l'écosystème).
- **"Quality" est trop souvent un cliché**. Beaucoup d'entreprises se prétendent "quality" sans le mériter. Vérifier rigoureusement : 10+ ans de ROIC > WACC, marges durables, pas de "diworsification".
- **Wonderful business à prix excessif = mauvais investissement**. Buffett rappelle constamment : il faut **les deux** (qualité + prix). Apple à 30× P/E peut être un mauvais investissement même si l'entreprise est exceptionnelle.
- **Buffett lui-même se trompe**. Il a perdu sur IBM, Tesco, Lubrizol's CFO, Dexter Shoes. Personne n'est infaillible — la rigueur compte plus que le résultat.
- **L'approche Buffett demande patience extrême**. Acheter à 50 % du prix juste arrive rarement (1-2 fois par décennie pour la plupart des compounders). Sans patience pour attendre, indexer plutôt.
