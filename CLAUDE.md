# TradingClaude — Index Claude Code

*Phase 3 active — Sprint 113 — Dernière mise à jour : 2026-05-26*

---

## Identité

**TradingClaude** est le copilote financier IA de Yves Larivière (développeur C++/Java/React, Québec).  
Système d'analyse d'investissement multi-frameworks : API FastAPI + 18 skills (16 tier2 + 2 tier1) + RAG Qdrant + frontend React.  
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
| Phase 3 | 🔄 Sprint 81 | Rapport PDF mensuel automatisé, page ESG, export annotations |

---

## Stack

| Couche | Technologies |
|--------|-------------|
| Service | Python 3.11, FastAPI ≥ 0.115, Anthropic SDK ≥ 0.40, asyncpg, Pydantic v2, Celery, Langfuse |
| Infrastructure | PostgreSQL 16, Qdrant v1.9, Redis 7, Docker Compose (5 services) |
| Frontend | React 18 + TypeScript strict, Vite 5 (port 5173 → proxy :8000), Tailwind CSS 3 + shadcn/ui |

---

## Conventions universelles

- **Langue** : commentaires/docstrings/variables métier en **français** ; code (fonctions, classes, modules) en **anglais**
- **Typage strict** : zéro `any` en TypeScript, type hints partout en Python
- **Async/await** obligatoire pour tous les appels I/O (DB, API Claude, Redis)
- **Commentaires** uniquement si le WHY n'est pas évident — jamais de paraphrase du code

→ Détails complets dans `.claude/rules/conventions-code-base.md`

---

## Commandes essentielles

```bash
docker-compose up -d                        # démarrer l'infrastructure
curl localhost:8000/healthz                 # vérifier le service
curl -X POST localhost:8000/analyze -H "Content-Type: application/json" -d '{"ticker":"BNS.TO"}'
curl -X POST localhost:8000/screen  -H "Content-Type: application/json" -d '{"tickers":["BNS.TO","TD.TO"]}'
cd frontend && npm run dev                  # frontend port 5173
python -m pytest tests/ --ignore=tests/e2e # tests backend
```

Commandes complètes : [`docs/cheatsheet.md`](docs/cheatsheet.md)

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
| [`api-orchestrator.md`](.claude/rules/api-orchestrator.md) | `app/orchestrator/**` | Pattern WORKFLOWS, procédure ajout workflow, `compounder_buffett` 10 steps |
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

## Ce projet N'est PAS

- ❌ Le bot C++ Interactive Brokers (EMA/RSI sur QQQ) — projet séparé
- ❌ CoRoute (carpooling Java/GLO-2004) — projet séparé
- ❌ Ninja Sasquatch Games (React board games) — projet séparé
