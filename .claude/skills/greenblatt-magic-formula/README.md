# greenblatt-magic-formula

Magic Formula de Joel Greenblatt — combine deux métriques (ROC + Earnings Yield) pour identifier mécaniquement les bonnes entreprises à des bons prix.

## À quoi ça sert

Joel Greenblatt (Gotham Capital, +30 % CAGR sur 20 ans) a popularisé une formule simple :
1. **Earnings Yield** = EBIT / Enterprise Value (proxy "bon prix")
2. **Return on Capital** = EBIT / (Net Working Capital + Net Fixed Assets) (proxy "bonne entreprise")

Classer chaque entreprise selon les deux métriques, additionner les rangs, acheter le top 20-30. Approche **mécanique** qui surperforme historiquement les indices.

Inclut aussi l'analyse des **special situations** (spinoffs, restructurations, sortie Chapter 11) du livre *You Can Be a Stock Market Genius*.

## Quand l'utiliser

- "Quel est le top 30 Magic Formula sur le S&P 500 ?"
- "Calcule le score Magic Formula pour Apple, Costco, et BCE"
- "Spinoff de Topicus from CSU — opportunité ?"
- Construction d'un portfolio mécanique value

## Quand ne pas l'utiliser

- Pour les financières (banques, assureurs) — la formule ne s'applique pas (capital structure différente)
- Pour les utilities régulées — capital intensity rend ROC peu informatif
- Pour les compounders à valorisation premium déjà reconnue

## Composants

```
greenblatt-magic-formula/
├── SKILL.md
├── references/
│   ├── formules.md                    ← ROC, Earnings Yield, calculs détaillés
│   ├── portefeuille-discipline.md     ← Règles d'achat/vente, rotation annuelle
│   └── situations-speciales.md        ← Spinoffs, risk arbitrage, recaps
├── scripts/
│   └── magic_formula_rank.py          ← Classement combiné
└── evals/
    ├── evals.json
    └── test_universe.json             ← 6 actions test, AAPL et ULTA tied #1
```

## Exemples d'utilisation

### Via prompt

> "Applique la Magic Formula à un univers de 6 stocks (AAPL, MSFT, COST, ULTA, BCE, CSU). Lequel rank en premier ?"

### Via script direct

```bash
cd greenblatt-magic-formula
python scripts/magic_formula_rank.py evals/test_universe.json
```

Output :
```
MAGIC FORMULA RANKING
Ticker   ROC%    EY%     Rank ROC  Rank EY  Combined
AAPL     45.2    5.5     2         1        3 ← #1
ULTA     42.0    6.1     3         2        5
MSFT     38.0    4.2     4         3        7
COST     22.5    3.5     5         4        9
CSU      28.1    3.8     6         5        11
BCE      8.5     2.1     7         6        13
```

## Discipline du portefeuille

Greenblatt insiste sur les **règles strictes** pour bénéficier de la formule :
- 20-30 positions de taille égale
- Rotation annuelle (vendre les positions vieilles d'un an, racheter le nouveau top 20-30)
- Pas de vente "discretionnaire" sur les pertes
- Tax management : vendre les losers à 11 mois (court terme USA), winners à 13 mois

## Special situations (chap. complémentaire)

Le skill couvre aussi les special situations Greenblatt :
- **Spinoffs** : analyse de la nouvelle entité indépendante
- **Risk arbitrage** : merger spreads
- **Recapitalizations** : changements de structure capitale
- **LEAPS sur stub stocks** : positions optionées sur situations complexes

## Ce qu'il ne fait pas

- Ne vérifie pas la qualité des chiffres (croiser avec `earnings-quality-fraud-detection`)
- Ne couvre pas les financières
- Ne remplace pas l'analyse fondamentale pour les positions concentrées (>5 %)

## Garde-fous

- La formule a sous-performé 2014-2020 (cycle où les compounders premium ont gagné)
- Sur des cycles 5-10 ans, surperformance historique ~3-5 %/an vs S&P 500
- Ne fonctionne pas en sommet de cycle où "tout est cher"
- Les value traps existent — la rotation annuelle limite l'exposition

## Voir aussi

- [graham-stock-screening](../graham-stock-screening/) — alternative plus stricte
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — pour les special situations avec marge
- [pabrai-dhandho-and-cloning](../pabrai-dhandho-and-cloning/) — Pabrai a explicitement cloné la Magic Formula
