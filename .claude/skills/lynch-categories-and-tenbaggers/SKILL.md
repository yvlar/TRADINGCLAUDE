---
name: lynch-categories-and-tenbaggers
description: Applique le cadre de Peter Lynch (One Up on Wall Street, Beating the Street) — classification des actions en 6 catégories, identification des tenbaggers, ratio PEG, principe "invest in what you know". À utiliser dès que l'utilisateur mentionne Lynch, tenbagger, ten-bagger, "ten-bagger", PEG ratio, "invest in what you know", slow grower, stalwart, fast grower, cyclical, turnaround, asset play, ou veut classer une action selon son profil de croissance et son potentiel. Utilise toujours ce skill pour comprendre comment positionner une action dans le portefeuille selon son archétype.
---

# Lynch — Categories and Tenbaggers

Peter Lynch (Magellan Fund 1977-1990, +29 % CAGR) a inventé le concept de classification d'actions en archétypes pour adapter l'analyse au profil de chaque entreprise. Une action n'est pas évaluée de la même manière selon qu'elle est slow grower mature ou fast grower émergente.

## Quand utiliser quelle référence

| Catégorie | Référence |
|-----------|-----------|
| Slow growers | `references/lynch-slow-growers.md` |
| Stalwarts | `references/lynch-stalwarts.md` |
| Fast growers (potentiels tenbaggers) | `references/lynch-fast-growers.md` |
| Cyclicals | `references/lynch-cyclicals.md` |
| Turnarounds | `references/lynch-turnarounds.md` |
| Asset plays | `references/lynch-asset-plays.md` |

## Workflow

### Étape 1 — Classer l'action

Identifier la catégorie dominante en quelques minutes :
- **Croissance des revenus < 5 %/an** → Slow grower
- **Croissance des revenus 5-12 %/an stable** → Stalwart
- **Croissance des revenus > 20 %/an** → Fast grower
- **Cycles industriels visibles dans l'historique** → Cyclical
- **Récente détresse, redressement en cours** → Turnaround
- **Décote de marché vs valeur des actifs** → Asset play

```bash
python scripts/classify_lynch.py inputs.json
```

Le script analyse l'historique et propose la catégorie la plus probable avec justification.

### Étape 2 — Appliquer les critères propres à la catégorie

Chaque catégorie a ses propres tests. Lire la référence correspondante avant de conclure.

### Étape 3 — Pour les fast growers : test PEG et tenbagger

```bash
python scripts/peg_ratio.py --pe 18 --growth 22
```

PEG = P/E / taux de croissance. Lynch préconise PEG < 1.0 comme attractif.

Pour qualifier un potentiel **tenbagger** (×10 sur 5-10 ans) :
- Croissance bénéfices > 20 %/an durable
- Marges qui s'améliorent ou stables
- Encore loin de la saturation de marché
- Direction compétente
- Prix raisonnable (PEG ≤ 1.0)

### Étape 4 — Allocation dans le portefeuille

Lynch préconise un mix selon les catégories :

| Catégorie | Allocation typique | Holding period |
|-----------|--------------------|-----------------|
| Stalwarts | 30-40 % | Long terme (5+ ans) |
| Fast growers | 30-40 % | Long terme tant que la croissance dure |
| Cyclicals | 10-20 % | Selon position dans le cycle |
| Slow growers | 5-15 % | Pour le revenu de dividendes |
| Turnarounds | 5-15 % | 2-3 ans typique (sortie quand redressement confirmé) |
| Asset plays | 5-15 % | Jusqu'au catalyseur (vente, scission) |

## Le principe "Invest in what you know"

Lynch insiste : **les meilleures opportunités viennent souvent de l'observation quotidienne**, pas de la lecture de research reports. Un consommateur qui voit Costco bondé tous les samedis peut détecter le succès avant les analystes.

Mais il y a un piège : "I know the company because I'm a customer" ≠ analyse fondamentale. Le filtre Lynch demande après l'observation initiale :
1. Quelle est la pénétration de marché actuelle ?
2. La croissance est-elle profitable (marges + ROIC) ?
3. La valorisation laisse-t-elle de la place pour la croissance future ?

Sans ces tests, l'idée de consommateur reste superficielle.

## Garde-fous

- **La catégorisation peut changer**. Une fast grower devient stalwart quand la croissance ralentit (Microsoft 2002, Apple ~2018). Adapter la stratégie à mesure que la catégorie évolue.
- **PEG est imparfait**. Dépend fortement de l'estimation de croissance future, qui est subjective. Sanity check : utiliser le passé 5 ans **et** le consensus analyste **et** la croissance soutenable (ROIC × taux de réinvestissement).
- **Les tenbaggers sont rares**. Lynch a identifié quelques dizaines en 13 ans chez Magellan. La plupart des fast growers ne deviennent pas tenbaggers — beaucoup s'effondrent quand la croissance ralentit. Diversifier dans cette catégorie.
- **"Invest in what you know" peut être trompeur**. Aimer un produit ne signifie pas que la société qui le vend est un bon investissement. Test additionnel toujours requis.
- **Ignorer les forecasts macroéconomiques**. Lynch insistait : « Si vous passez 13 minutes par an à analyser les économistes, vous gaspillez 10 minutes ». Concentrer l'analyse sur les fundamentals de l'entreprise.
