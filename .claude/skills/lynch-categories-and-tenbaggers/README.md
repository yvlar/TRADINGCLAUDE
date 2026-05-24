# lynch-categories-and-tenbaggers

Méthode Peter Lynch — classification des actions en 6 catégories distinctes, avec stratégie adaptée à chaque archétype, et identification des tenbaggers (×10 sur 5-10 ans).

## À quoi ça sert

Peter Lynch (Magellan Fund 1977-1990, +29 % CAGR) a popularisé l'idée qu'une action n'est pas évaluée de la même manière selon son **archétype** :

| Catégorie | Croissance | Stratégie | Holding |
|-----------|------------|-----------|---------|
| **Slow growers** | < 5 %/an | Dividendes | Long |
| **Stalwarts** | 5-12 %/an | Réévaluation à valeur moyenne | Long |
| **Fast growers** | > 20 %/an | Tenbaggers potentiels | Tant que ça pousse |
| **Cyclicals** | Volatile | Bottom du cycle | 2-5 ans |
| **Turnarounds** | Récupération | Si plan crédible | 2-3 ans |
| **Asset plays** | Cap < actifs | Catalyseur requis | Jusqu'à révélation |

Inclut le **ratio PEG** (P/E / croissance %) pour les fast growers : < 1.0 attractif.

## Quand l'utiliser

- "Costco est-il fast grower ou stalwart selon Lynch ?"
- "PEG ratio de Constellation à P/E 30 et croissance 22 %?"
- "Magna est-elle cyclique ?"
- "Boeing est-il un turnaround intéressant ?"
- Pour structurer un portfolio diversifié par archétypes

## Quand ne pas l'utiliser

- Pour les financières (banques, assureurs) — Lynch traite séparément
- Pour les commodities pures (or, pétrole brut) — la catégorisation s'applique mal

## Composants

```
lynch-categories-and-tenbaggers/
├── SKILL.md
├── references/
│   ├── lynch-slow-growers.md       ← BCE, utilities
│   ├── lynch-stalwarts.md          ← Costco, RBC
│   ├── lynch-fast-growers.md       ← CSU, Shopify, tenbaggers
│   ├── lynch-cyclicals.md          ← Magna, Stelco
│   ├── lynch-turnarounds.md        ← Chrysler 1979, Apple 1997
│   └── lynch-asset-plays.md        ← Décote NAV, holdings
├── scripts/
│   ├── classify_lynch.py           ← Classification automatique
│   └── peg_ratio.py                ← PEG avec verdict
└── evals/
    ├── evals.json
    └── test_csu.json               ← CSU = Fast Grower (high confidence)
```

## Le ratio PEG

```
PEG = P/E forward / Taux de croissance bénéfice (%)
```

Seuils Lynch :
- **PEG < 0.5** : très attractif
- **PEG 0.5 - 1.0** : attractif
- **PEG 1.0 - 2.0** : équitable
- **PEG > 2.0** : surévalué

## Exemples d'utilisation

### Via prompt

> "Classe Constellation Software selon les 6 catégories Lynch et calcule son PEG"

### Via script direct

```bash
cd lynch-categories-and-tenbaggers
python scripts/classify_lynch.py evals/test_csu.json
python scripts/peg_ratio.py --pe 30 --growth 22
```

Output CSU :
```
CLASSIFICATION : Fast Grower (high confidence)
- Croissance revenus 18%, bénéfices 22%
- Volatilité faible (5%)
- Pas en distress

PEG = 30 / 22 = 1.36
🟡 ÉQUITABLEMENT VALORISÉ
```

## Identifier un tenbagger potentiel

Lynch identifie 5 conditions pour un tenbagger :

1. **Croissance soutenable** : pénétration < 30 %, beaucoup de marché à capturer
2. **Pricing power émergent** : marges en amélioration
3. **Économies d'échelle** : ROIC s'améliore avec volume
4. **Direction compétente** : insider holdings + allocation intelligente
5. **Multiple raisonnable** : PEG ≤ 1.0 au point d'entrée

Sans les 5, un fast grower peut crash quand la croissance ralentit.

## Allocation type Lynch

| Catégorie | % portfolio | Position size individuelle |
|-----------|-------------|------------------------------|
| Stalwarts | 30-40 % | 3-7 % |
| Fast growers | 30-40 % | 3-5 % (diversifier) |
| Cyclicals | 10-20 % | 2-5 % |
| Slow growers | 5-15 % | 2-5 % (revenu) |
| Turnarounds | 5-15 % | 2-4 % |
| Asset plays | 5-15 % | 3-8 % |

## "Invest in what you know"

Lynch insiste sur l'observation quotidienne comme source d'idées :
- Voir Costco bondé chaque samedi
- Acheter le café préféré de la collègue
- Remarquer une chaîne en expansion

Mais : observation **≠** analyse. Toujours vérifier les fondamentaux après l'observation.

## Ce qu'il ne fait pas

- Ne se substitue pas à l'analyse fondamentale (PEG ne valide pas seul un investissement)
- Ne valorise pas les financières correctement
- Les catégories peuvent **changer** (fast grower → stalwart), surveiller annuellement

## Garde-fous

- Le PEG dépend fortement de l'**estimation de g** future (subjective)
- Les fast growers sont sur-représentés parmi les fraudes (croiser avec earnings-quality)
- "Invest in what you know" peut tromper : aimer un produit ≠ entreprise rentable
- Lynch ignorait les forecasts macro — ne pas y consacrer trop de temps

## Voir aussi

- [damodaran-narrative-and-numbers](../damodaran-narrative-and-numbers/) — pour valider les fast growers (story stocks)
- [dorsey-moat-analysis](../dorsey-moat-analysis/) — durabilité de l'avantage des stalwarts
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — discipline pour les turnarounds
