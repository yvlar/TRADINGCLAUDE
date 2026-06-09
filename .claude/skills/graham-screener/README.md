# graham-screener

Screening mécanique des 7 critères de Graham (chapitre 14) sur un univers complet de titres, avec export des candidats vers Qdrant.

## À quoi ça sert

Transformer le filtre Graham — normalement appliqué titre par titre — en screening d'univers complet (ex. S&P 500) :
- **Score composite /7** : verdict PASS/FAIL/N/A par critère, classement par score puis marge de sécurité
- **Graham Number** : √(22,5 × BPA × BVPS) + marge de sécurité vs prix courant
- **Pipeline Qdrant** : les candidats deviennent des documents datés interrogeables (collection `graham_screening`)

Le résultat est un **filtre d'élimination, jamais une recommandation d'achat** — c'est le pont entre le pilier value (analyse discrétionnaire) et le pilier algorithmique (règles mécaniques).

## Quand l'utiliser

- "Passe ces tickers au filtre Graham"
- "Screen le S&P 500 et donne-moi les candidats value"
- "Lesquels de ces titres sont de la vraie value ?"
- Validation quantitative avant une analyse value qualitative approfondie

## Quand ne pas l'utiliser

- Pour analyser UN titre en profondeur avec citations RAG — utiliser le skill API `graham_analysis` (`graham-stock-screening`)
- Pour classer par qualité + prix combinés — utiliser `greenblatt-magic-formula`
- Pour des banques, REIT, techs asset-light — les critères Graham les pénalisent structurellement

## Composants

```
graham-screener/
├── SKILL.md
├── references/
│   └── graham_criteria.md      ← 7 critères détaillés, seuils 1973 vs adaptations
├── scripts/
│   ├── graham_screener.py      ← Moteur : 7 critères, score, Graham Number, CSV
│   ├── batch_screen.py         ← Lot : univers S&P 500, checkpoint/reprise, JSONL
│   └── ingest_qdrant.py        ← Ingestion Qdrant (text-embedding-3-small ou dummy)
├── assets/
│   ├── sample_data.json        ← 4 titres démo (VALUECO 7/7, TRAPCO value trap…)
│   └── universes.json          ← Liste de repli S&P 500 (sous-ensemble large caps)
└── evals/
    ├── evals.json              ← Trigger evals (format maison)
    └── functional_evals.json   ← Assertions fonctionnelles sur les scripts
```

## Exemples d'utilisation

### Screening ciblé

```bash
python .claude/skills/graham-screener/scripts/graham_screener.py \
    --tickers BMY,NKE,LMT,STZ,PFE --output results.csv
```

### Univers complet → Qdrant

```bash
python .claude/skills/graham-screener/scripts/batch_screen.py --universe sp500 --min-score 5
python .claude/skills/graham-screener/scripts/ingest_qdrant.py \
    --input output/candidates.jsonl --collection graham_screening
```

### Test hors-ligne de bout en bout

```bash
python .claude/skills/graham-screener/scripts/batch_screen.py --universe demo --output-dir /tmp/t
python .claude/skills/graham-screener/scripts/ingest_qdrant.py \
    --input /tmp/t/candidates.jsonl --url ":memory:" --embedder dummy
```

Output type :
```
GRAHAM SCREENER — 4 titres analysés
Ticker  Score   Prix      Graham №    Marge séc.  Données
VALUECO 7/7     42.0      59.59       +29.5 %     partielles
...
Rappel : un score élevé = mérite une analyse qualitative (moat, thèse),
jamais un signal d'achat.
```

## Ce qu'il ne fait pas

- Ne recommande pas d'achat — un 7/7 signifie « mérite une analyse qualitative complète », rien de plus
- Ne vérifie pas la qualité des bénéfices (croiser avec `earnings-quality-fraud-detection`)
- N'élimine pas le risque de value trap — le filtre mesure le prix, pas le catalyseur

## Garde-fous

- yfinance ne fournit que ~4-5 ans d'états financiers : les critères 3, 4 et 5 (conçus pour 10-20 ans) portent le drapeau `partial_data` — un PASS sur fenêtre courte est plus faible qu'un PASS sur 10 ans. Ne jamais masquer cette limite dans la synthèse.
- Critères inadaptés aux banques (current ratio), techs asset-light (P/B) et REIT — le signaler si l'univers en contient
- Vérifier les chiffres critiques aux états financiers (10-K/10-Q) avant toute décision

## Voir aussi

- [graham-stock-screening](../graham-stock-screening/) — analyse Graham unitaire approfondie (skill API tier2 `graham_analysis`)
- [greenblatt-magic-formula](../greenblatt-magic-formula/) — classement mécanique qualité + prix
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — approfondir la notion de marge de sécurité
