# Base de connaissances — skills d'analyse

<!-- Rule universelle : chargée à chaque session. -->

## Quand cette règle s'applique

Avant toute analyse financière et avant d'écrire ou modifier le prompt d'un skill tier2. S'applique également quand une donnée financière semble manquer ou qu'une hypothèse est discutable.

## Règles

### Protocole obligatoire avant analyse ou codage

1. Lire `.claude/skills/{nom-skill}/SKILL.md` — logique métier, workflow, critères du framework
2. Consulter `.claude/skills/{nom-skill}/references/*.md` — formules précises, seuils, tableaux de décision
3. Si un skill requis est absent ou son SKILL.md incomplet → **le signaler avant de continuer**
4. Si une hypothèse financière est discutable ou des données manquent → **le signaler explicitement**

### Catalogue des skills — 16 tier2 + 2 tier1 = 18 en production + 1 outil batch

#### Skills tier2 — frameworks d'analyse conceptuels

| Skill (code API) | SKILL.md dans `.claude/skills/` | Code dans `app/skills/tier2/` |
|---|---|---|
| `graham_analysis` | `graham-stock-screening/` | `graham_analysis/` |
| `earnings_quality` | `earnings-quality-fraud-detection/` | `earnings_quality/` |
| `dorsey_moat` | `dorsey-moat-analysis/` | `dorsey_moat/` |
| `buffett_quality` | `buffett-quality-investing/` | `buffett_quality/` |
| `stock_valuation_triangulation` | `stock-valuation-triangulation/` | `stock_valuation/` |
| `investment_thesis_builder` | `investment-thesis-builder/` | `thesis_builder/` |
| `munger_mental_models` | `munger-mental-models/` | `munger_mental/` |
| `canadian_tax_considerations` | `canadian-tax-considerations/` | `canadian_tax/` |
| `lynch_categories` | `lynch-categories-and-tenbaggers/` | `lynch_categories/` |
| `fisher_scuttlebutt` | `fisher-scuttlebutt/` | `fisher_scuttlebutt/` |
| `klarman_margin` | `klarman-margin-of-safety/` | `klarman_margin/` |
| `greenblatt` | `greenblatt-magic-formula/` | `greenblatt/` |
| `damodaran_narrative` | `damodaran-narrative-and-numbers/` | `damodaran_narrative/` |
| `marks_cycles` | `marks-cycles-and-risk/` | `marks_cycles/` |
| `pabrai_dhandho` | `pabrai-dhandho-and-cloning/` | `pabrai_dhandho/` |
| `esg_simplified` | `esg-simplified/` | `esg_simplified/` |

#### Extracteurs tier1 (données brutes — pas de SKILL.md conceptuel)

| Skill (code API) | Fichier |
|---|---|
| `yahoo_finance_extractor` | `app/skills/tier1/yahoo_finance.py` |
| `sedar_plus_extractor` | `app/skills/tier1/sedar_plus.py` |

#### Outil batch (pas un skill LLM — screening mécanique + ingestion Qdrant)

| Outil | SKILL.md dans `.claude/skills/` | Scripts |
|---|---|---|
| `graham-screener` | `graham-screener/` | `.claude/skills/graham-screener/scripts/` |

Ce skill applique les 7 critères Graham mécaniquement sur un univers entier (ex. S&P 500),
sans appel Claude, et ingère les candidats dans la collection Qdrant `graham_screening`
(embedder `text-embedding-3-small`, 1536 dims, aligné sur `investment_knowledge`).
Pont entre le pilier value (analyse discrétionnaire) et le pilier algorithmique.

Scripts :
- `graham_screener.py` — moteur 7 critères, score/7, Graham Number, CSV
- `batch_screen.py` — lot avec checkpoint/reprise, export `candidates.jsonl`
- `ingest_qdrant.py` — upsert Qdrant idempotent (URL depuis `$QDRANT_URL`)

Test hors-ligne de bout en bout :
```bash
python .claude/skills/graham-screener/scripts/batch_screen.py --universe demo --output-dir /tmp/t
python .claude/skills/graham-screener/scripts/ingest_qdrant.py --input /tmp/t/candidates.jsonl --url ":memory:" --embedder dummy
```

### Note sur les comptages

- **16 skills tier2** en production = 15 frameworks originaux + `esg_simplified` (Sprint 70)
- **18 en production** = 16 tier2 + 2 tier1
- **1 outil batch** = `graham-screener` (scripts purement mécaniques, pas de LLM)
- Le dossier `.claude/skills/` contient **17 SKILL.md** (16 tier2 + 1 batch)
- Pour les skills tier2 : `app/skills/tier2/` est la source de vérité du code ; `.claude/skills/` est la source de vérité conceptuelle (formules, seuils, frameworks académiques)

### Cohérence du corpus RAG

Les ~69 documents `references/*.md` dans `.claude/skills/` alimentent le RAG Qdrant (collection `investment_knowledge`). Tout nouveau skill tier2 doit avoir son SKILL.md + `references/` pour maintenir la cohérence du corpus. L'outil batch `graham-screener` alimente sa propre collection `graham_screening` via `ingest_qdrant.py`.
