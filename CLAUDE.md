# TradingClaude — Index Claude Code

*Phase 3 active — Sprint 117 (à définir) · dernier complété : Sprint 116 ✅ · v10.3.0 — Dernière mise à jour : 2026-05-27*

---

## Identité

**TradingClaude** est le copilote financier IA de Yves Larivière (développeur C++/Java/React, Québec).  
Système d'analyse d'investissement multi-frameworks : API FastAPI + 18 skills (16 tier2 + 2 tier1) + RAG Qdrant + frontend React.  
C'est un outil d'**analyse fondamentale** (TSX, NYSE, NASDAQ) — **pas un bot de trading**.  
**Distinct** du bot de trading C++ Interactive Brokers (projet séparé).

---

## Four-pillar — Portefeuille

| Pilier | Description |
|--------|-------------|
| ETF passif | Core — diversification large (XEQT, VFV) |
| Thématique | Uranium, énergie IA, secteurs ciblés |
| Valeur | Approche Graham/Buffett — screener fondamental |
| Algo/Systématique | Stratégies quantitatives backtestées |

---

## Phases & sprint actif

| Phase | État | Description |
|-------|------|-------------|
| Phase 0 | ✅ | API FastAPI + graham_analysis + PostgreSQL |
| Phase 1 | ✅ | RAG Qdrant, get_citations(), Langfuse, retry backoff |
| Phase 2 | ✅ | 18 skills en production, extracteurs tier1, screener multi-tickers |
| Phase 3 | 🔄 | Pipeline de synthèse — rapports PDF (mensuel / ticker / screener / watchlist), auth JWT, dashboard métriques v2, recherche sémantique, refonte micro-UX |

Source de vérité de l'état courant : [`ROADMAP.md`](ROADMAP.md) (sprint actif, version, ce qui fonctionne aujourd'hui) et [`prompt-mise-a-jour-roadmap.md`](prompt-mise-a-jour-roadmap.md) (carte d'embarquement du prochain sprint).

---

## Stack

| Couche | Technologies |
|--------|-------------|
| Service | Python 3.11, FastAPI ≥ 0.136, Anthropic SDK ≥ 0.40, asyncpg, Pydantic v2, Celery, Langfuse |
| Infrastructure | PostgreSQL 16, Qdrant v1.9, Redis 7, Docker Compose (5 services : `copilote`, `worker`, `postgres`, `qdrant`, `redis`) |
| Frontend | React 18 + TypeScript strict, Vite (port 5173 → proxy :8000), Tailwind CSS + shadcn/ui, recharts, @tanstack/react-query, react-router |
| Modèles Claude | Défaut `claude-sonnet-4-6` (`CLAUDE_MODEL`) · `claude-haiku-4-5-20251001` pour certains skills (`CLAUDE_HAIKU_MODEL`) — jamais hardcodé, toujours via env/`self._model` |

> Les versions exactes vivent dans `requirements.txt` (backend) et `frontend/package.json` (frontend) — s'y référer plutôt que de mémoriser un numéro.

---

## Structure du dépôt

```
app/                      # Backend FastAPI
├── api/main.py           # App FastAPI, lifespan, montage des ~23 routers
├── api/endpoints/        # 1 router par domaine (analyze_stream, screen, watchlist,
│                         #   auth, admin, annotations, compare, *_report, evals, …)
├── orchestrator/         # core.py (Orchestrator), router.py (WORKFLOWS)
├── skills/
│   ├── base.py           # SkillBase — contrat commun, prompt caching, tool schema
│   ├── tier1/            # Extracteurs données brutes : yahoo_finance.py, sedar_plus.py
│   └── tier2/<skill>/    # 16 frameworks : skill.py + schemas.py + __init__.py
├── services/             # Logique métier (screener, cache, PDF, alertes, auth, email…)
├── rag/                  # Client Qdrant, embeddings OpenAI, service de recherche
├── models/               # Modèles Pydantic transverses (auth, watchlist, evals…)
├── middleware/           # auth (JWT cookie), csrf (double-submit), rate_limit (Redis)
├── observability/        # Client Langfuse
├── workers/              # Celery app + tasks (screener planifié, alertes, rapports)
└── utils/                # retry (429/529), costs (pricing par modèle), ticker_sanitizer, tool_schema

frontend/src/             # SPA React 18 + TS
├── pages/                # 1 page par route (Analyze, Screener, History, Watchlist,
│                         #   Dashboard, Compare, Esg, Alerts, Search, Admin, auth…)
├── components/           # Composants + components/ui (shadcn/ui)
├── api/                  # Clients fetch typés par domaine + client.ts (CSRF/cookies)
├── contexts/             # AuthContext
├── types/index.ts        # Types TypeScript centralisés (zéro `any`)
└── __tests__/            # Tests Vitest (1 par composant/page)

.claude/
├── rules/                # 16 règles de convention (voir table de pointeurs)
├── skills/<skill>/       # SKILL.md + references/ — source de vérité conceptuelle (RAG)
├── prompts/              # Prompts réutilisables (bootstrap, exécution de sprint…)
└── docs/                 # Notes projet

tests/                    # Pyramide pytest : api/ services/ skills/ orchestrator/
│                         #   workers/ + evals/ (Claude réel) + e2e/ (Playwright) + load/
docs/                     # architecture-copilote-financier.md, cheatsheet.md
infra/                    # postgres (init.sql + migrations), caddy, monitoring, backup
scripts/                  # analyze_cli.py (CLI), ingest_rag.py (peuplement Qdrant)
```

---

## Orchestrateur — workflows

`POST /analyze` route vers une séquence de skills selon le champ `workflow` (`app/orchestrator/router.py`). Un skill `optional=True` peut échouer sans faire échouer l'analyse globale.

| Workflow | Skills (1er = obligatoire) |
|----------|----------------------------|
| `value_graham` | graham_analysis → earnings_quality, stock_valuation, thesis_builder, canadian_tax |
| `compounder_buffett` | graham_analysis → earnings_quality, dorsey_moat, buffett_quality, fisher, valuation, thesis, munger, marks, canadian_tax (10 steps) |
| `fast_grower_lynch` | lynch_categories → damodaran, valuation, thesis, munger, canadian_tax |
| `special_situation` | graham_analysis → klarman_margin, greenblatt, thesis |
| `distressed_pabrai` | pabrai_dhandho → klarman_margin, earnings_quality, thesis, canadian_tax |

Procédure d'ajout d'un workflow et détails de parallélisme : [`api-orchestrator.md`](.claude/rules/api-orchestrator.md) + [`gotchas-operationnels.md`](.claude/rules/gotchas-operationnels.md) (`max_parallel=3` pour `compounder_buffett`).

---

## Conventions universelles

- **Langue** : commentaires/docstrings/variables métier en **français** ; code (fonctions, classes, modules) en **anglais**
- **Typage strict** : zéro `any` en TypeScript, type hints partout en Python (Pydantic v2)
- **Async/await** obligatoire pour tous les appels I/O (DB, API Claude, Redis, httpx) — jamais de driver synchrone ni `time.sleep()`
- **Commentaires** uniquement si le WHY n'est pas évident — jamais de paraphrase du code
- **Secrets** : toujours via `.env` (jamais commité) ; toute nouvelle clé doit apparaître dans `.env.example` avec une valeur factice

→ Détails complets dans `.claude/rules/conventions-code-base.md`

---

## Commandes essentielles

```bash
# Infrastructure
docker-compose up -d                        # démarrer les 5 services
curl localhost:8000/healthz                 # vérifier service + PostgreSQL + Qdrant

# API
curl -X POST localhost:8000/analyze -H "Content-Type: application/json" -d '{"ticker":"BNS.TO"}'
curl -X POST localhost:8000/screen  -H "Content-Type: application/json" -d '{"tickers":["BNS.TO","TD.TO"]}'
python scripts/analyze_cli.py BNS.TO        # analyse en ligne de commande

# Tests backend
python -m pytest tests/ --ignore=tests/e2e  # exclut Playwright (et evals = Claude réel)

# Frontend (port 5173)
cd frontend && npm run dev                   # dev server (proxy → :8000)
cd frontend && npm test                      # Vitest
cd frontend && npm run typecheck             # tsc --noEmit (doit être 0 erreur)
```

Commandes complètes : [`docs/cheatsheet.md`](docs/cheatsheet.md)

---

## Workflow de fin de sprint (automatique — ne pas demander confirmation)

Un sprint n'est terminé qu'après ces 3 étapes : (1) mettre à jour `ROADMAP.md`, (2) réécrire `prompt-mise-a-jour-roadmap.md` pour le sprint suivant, (3) créer un commit git incluant tous les fichiers du sprint. Détails : [`workflow-sprint.md`](.claude/rules/workflow-sprint.md).

---

## Table de pointeurs → `.claude/rules/`

| Fichier | Portée | Responsabilité |
|---------|--------|----------------|
| [`conventions-code-base.md`](.claude/rules/conventions-code-base.md) | universel | Bilingue FR/EN, typage strict, async/await, commentaires WHY |
| [`conventions-python.md`](.claude/rules/conventions-python.md) | `**/*.py` | Pattern `execute()`, docstrings, style Python |
| [`conventions-frontend.md`](.claude/rules/conventions-frontend.md) | `frontend/**` | React 18, TypeScript strict, Vite, structure pages/composants |
| [`variables-financieres.md`](.claude/rules/variables-financieres.md) | `app/**/*.py`, `frontend/src/**`, `analyses/**` | Tableau 14 variables financières standardisées (snake_case/camelCase) |
| [`api-skills-tier2.md`](.claude/rules/api-skills-tier2.md) | `app/skills/tier2/**` | SkillBase, prompt caching > 1024 tokens, Pydantic, procédure ajout skill |
| [`api-architecture.md`](.claude/rules/api-architecture.md) | `app/**` | Modèle `claude-sonnet-4-6`, `cost_usd` persisté, sections architecture |
| [`api-orchestrator.md`](.claude/rules/api-orchestrator.md) | `app/orchestrator/**` | Pattern WORKFLOWS (5 workflows), procédure ajout, `compounder_buffett` 10 steps |
| [`donnees-financieres.md`](.claude/rules/donnees-financieres.md) | `app/skills/**`, `analyses/**` | Validation None/div0, source+date, suffixe `.TO`, `current_ratio` banques |
| [`format-analyses.md`](.claude/rules/format-analyses.md) | `analyses/**` | FR, orienté décision, calculs intermédiaires, structure BNS-2026-05.md |
| [`comptes-canadiens-fiscalite.md`](.claude/rules/comptes-canadiens-fiscalite.md) | `canadian_tax/**`, `analyses/**` | CELI/REER/CELIAPP, fiscalité QC, Smith Manœuvre, allocation par compte |
| [`tests-pyramide.md`](.claude/rules/tests-pyramide.md) | `tests/**`, `__tests__/**` | Pyramide 5 niveaux, patch `call_claude_with_retry`, fixture `client` |
| [`workflow-sprint.md`](.claude/rules/workflow-sprint.md) | universel | Fin de sprint : ROADMAP.md + prompt-mise-a-jour-roadmap.md + commit git — 3 étapes automatiques |
| [`autonomie-confirmations.md`](.claude/rules/autonomie-confirmations.md) | universel | Actions libres vs 5 exceptions à confirmation obligatoire |
| [`securite.md`](.claude/rules/securite.md) | universel | Clés API dans `.env`, `.env.example` obligatoire, pas de secrets dans les logs |
| [`base-connaissances-skills.md`](.claude/rules/base-connaissances-skills.md) | universel | 16+2 skills, SKILL.md + references/ à consulter, flag esg_simplified |
| [`gotchas-operationnels.md`](.claude/rules/gotchas-operationnels.md) | `app/services/**`, `app/workers/**` | Timeouts screener, `max_parallel=3` pour `compounder_buffett` |

---

## Confirmation obligatoire avant d'agir

Actions **locales et réversibles** → agir directement. Ces 5 actions exigent une confirmation préalable de Yves : `git push`, `docker-compose down`, suppression de fichiers, modification de `.env`, opérations DB destructives (`DROP`/`DELETE` sans `WHERE`). Détails : [`autonomie-confirmations.md`](.claude/rules/autonomie-confirmations.md).

---

## Ce projet N'est PAS

- ❌ Le bot C++ Interactive Brokers (EMA/RSI sur QQQ) — projet séparé
- ❌ CoRoute (carpooling Java/GLO-2004) — projet séparé
- ❌ Ninja Sasquatch Games (React board games) — projet séparé
