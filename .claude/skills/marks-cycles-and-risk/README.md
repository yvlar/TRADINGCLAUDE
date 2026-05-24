# marks-cycles-and-risk

Cadre Howard Marks (Oaktree Capital) — pendule du sentiment de marché, second-level thinking, redéfinition du risque comme perte permanente plutôt que volatilité.

## À quoi ça sert

Howard Marks (Oaktree, ~190 G$ AUM) écrit les *memos* trimestriels les plus lus en finance depuis 30+ ans. Trois concepts centraux :

1. **Pendule du sentiment** : le marché oscille entre euphorie et panique, rarement au centre — adapter l'allocation contre-cyclique
2. **Second-level thinking** : différer du consensus pour générer de l'alpha (vs first-level "good company = good stock")
3. **Risque = perte permanente** : pas la volatilité (définition académique), mais la probabilité de capital permanently impaired

## Quand l'utiliser

- "Où sommes-nous dans le cycle de marché début 2026 ?"
- "Mon CAPE est à 32, devrais-je réduire mon exposition ?"
- "Le risque c'est la volatilité ou autre chose ?"
- "Cash position 40% en bull market, justifiable ?"
- Avant toute décision d'allocation tactique (cash vs equity)

## Quand ne pas l'utiliser

- Pour la sélection d'actions individuelles (utiliser autres skills)
- Pour le timing court-terme (Marks rejette explicitement)
- Pour des stratégies passives indicielles

## Composants

```
marks-cycles-and-risk/
├── SKILL.md
├── references/
│   ├── pendule-sentiment.md         ← 10 indicateurs + zones d'allocation
│   ├── risque-perte-permanente.md   ← Volatilité vs risque réel
│   └── second-level-thinking.md     ← Différer du consensus
├── scripts/
│   └── cycle_position.py            ← Score -10 à +10 + allocation suggérée
└── evals/
    ├── evals.json
    └── test_2026.json               ← Position 2026 estimée +3 (optimisme normal)
```

## Le pendule — 10 indicateurs

| Catégorie | Indicateur | Source |
|-----------|------------|--------|
| Valorisation | CAPE Shiller | shillerdata.com |
| Valorisation | Buffett Indicator | gurufocus.com |
| Crédit | High-yield spread | FRED |
| Crédit | Loan covenants | S&P Global |
| Volatilité | VIX | CBOE |
| Sentiment | AAII Bull/Bear | aaii.com |
| Activité | IPO volume | wsj.com |
| Activité | SPAC issuance | SPACTrack |
| Levier | Margin debt growth | FINRA |
| Médias | Magazine covers, narratives | qualitatif |

## Allocation contre-cyclique

| Position pendule (-10 à +10) | Cash | Equity | Action |
|------------------------------|------|--------|--------|
| +8 à +10 (euphorie extrême) | 60-80 % | 20-40 % | Liquider, refuser FOMO |
| +3 à +7 (optimisme normal) | 20-40 % | 60-80 % | Sélectivité accrue |
| -2 à +2 (neutre) | 10-20 % | 80-90 % | Allocation standard |
| -7 à -3 (pessimisme normal) | 0-10 % | 90-100 % | Acheter graduellement |
| -10 à -8 (panique extrême) | 0 % | 100 %+ | Déployer agressivement |

## Exemples d'utilisation

### Via prompt

> "Évalue la position du pendule au 30 avril 2026 avec CAPE 32, HY spreads 320 bps, VIX 16, AAII bulls 45%"

### Via script direct

```bash
cd marks-cycles-and-risk
python scripts/cycle_position.py evals/test_2026.json
```

Output :
```
POSITION SUR LE PENDULE — 2026-04
CAPE 32      : +1
Buffett 165% : +1
HY 320 bps   : +1
VIX 16       :  0
AAII bull 45 : +1
...

Score normalisé : +3.0
Zone : Optimisme normal
Allocation : 20-40% cash, 60-80% equity

Action : Sélectivité accrue, vendre les positions chères.
```

## Risque selon Marks

> *« Risk is the probability of permanent loss of capital. »*

Différence radicale avec la définition académique (volatilité = écart-type) :

| Cas | Volatilité (académique) | Risque réel (Marks) |
|-----|--------------------------|----------------------|
| Action oscillant 80-120 autour de VI 100 | Élevée | **Faible** (prix oscille autour valeur) |
| Action stable à 95 mais VI = 50 | Faible | **Très élevée** (sur-évaluation) |

Conséquence : un compounder à un prix excessif est **risqué**, indépendamment de sa stabilité de cours.

## Second-level thinking

> *"It's a good company, therefore it's a good investment."* ← First-level (commun)

> *"It's a good company, but everyone knows it. Price reflects this. Will my expectation differ from consensus enough to generate alpha?"* ← Second-level (rare)

Trois sources d'edge en second-level :
1. **Plus d'information** (rare aujourd'hui)
2. **Meilleure interprétation** (lecture massive)
3. **Meilleur tempérament** (le plus durable)

## Ce qu'il ne fait pas

- Ne donne pas le timing exact des tops/bottoms (Marks lui-même rate souvent)
- Ne fournit pas les data temps réel des indicateurs (manuel ou web_search)
- Ne valide pas les positions individuelles (croiser avec value skills)

## Garde-fous

- Le pendule peut **rester aux extrêmes 1-3 ans** avant le retournement (1996-1999)
- Cash position élevée = **sous-performance** en bull market prolongé (coût de l'optionnalité)
- Marks lui-même achète "trop tôt" en début de cycle baissier
- Indicateurs sont **partiellement subjectifs** — la discipline du processus compte plus que la précision

## Voir aussi

- [klarman-margin-of-safety](../klarman-margin-of-safety/) — Klarman partage la philosophie d'absolute return
- [munger-mental-models](../munger-mental-models/) — biais cognitifs comme drivers du pendule
- [pabrai-dhandho-and-cloning](../pabrai-dhandho-and-cloning/) — Pabrai applique aussi le contrarianism
- Memos d'Howard Marks sur oaktreecapital.com (gratuits)
