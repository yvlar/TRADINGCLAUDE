# Sprint 36 — À définir
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# RÔLE

Tu es un développeur full-stack senior spécialiste React + FastAPI.
Tu maîtrises React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS, Tanstack Query,
FastAPI, SSE (Server-Sent Events), WebSocket natif (navigateur), et les patterns de production pour les SPA.
Tu maîtrises aussi Docker Compose, Caddy (reverse proxy), TLS automatique (Let's Encrypt / local),
et les patterns de déploiement homelab (backup, monitoring, sécurité).
Tu maîtrises aussi GitHub Actions, les workflows CI/CD, et les patterns de tests automatisés.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

Lis ces fichiers dans cet ordre exact. Ne commence pas à coder sans avoir terminé cette étape.

1. `ROADMAP.md` — section "Sprint 36"
2. `app/orchestrator/core.py` — `run_company_analysis` et `stream_company_analysis` : pipeline actuel
3. `app/api/main.py` — endpoints enregistrés + lifespan
4. `app/api/endpoints/analyze_stream.py` — endpoint SSE actuel (Sprint 35)
5. `frontend/src/pages/AnalyzePage.tsx` — page streaming actuelle (Sprint 35)

---

# ÉTAT DU PROJET À CE JOUR

| Champ | Valeur |
|-------|--------|
| Version | 3.0.0 |
| Phase active | Phase 3 — Pipeline de synthèse |
| Sprint actif | **Sprint 36 — À définir** |
| Dernier sprint complété | Sprint 35 — SSE Streaming ✅ |

## Skills opérationnels (ne pas modifier)
- `graham_analysis` → `app/skills/tier2/graham_analysis/`
- `earnings_quality` → `app/skills/tier2/earnings_quality/`
- `dorsey_moat` → `app/skills/tier2/dorsey_moat/`
- `buffett_quality` → `app/skills/tier2/buffett_quality/`
- `stock_valuation_triangulation` → `app/skills/tier2/stock_valuation/`
- `investment_thesis_builder` → `app/skills/tier2/thesis_builder/`
- `munger_mental_models` → `app/skills/tier2/munger_mental/`
- `canadian_tax_considerations` → `app/skills/tier2/canadian_tax/`
- `lynch_categories` → `app/skills/tier2/lynch_categories/`
- `fisher_scuttlebutt` → `app/skills/tier2/fisher_scuttlebutt/`
- `klarman_margin` → `app/skills/tier2/klarman_margin/`
- `greenblatt` → `app/skills/tier2/greenblatt/`
- `damodaran_narrative` → `app/skills/tier2/damodaran_narrative/`
- `marks_cycles` → `app/skills/tier2/marks_cycles/`
- `pabrai_dhandho` → `app/skills/tier2/pabrai_dhandho/`
- `yahoo_finance_extractor` → `app/skills/tier1/yahoo_finance.py`
- `sedar_plus_extractor` → `app/skills/tier1/sedar_plus.py`

## Suite de tests opérationnelle (Sprints 13-35)
- `tests/conftest.py` — fixtures `client`, `mock_claude_graham`, `db_cleanup`, `_SKILL_PROMPT_PATCHES`, `mock_obs_redis`, `obs_service`
- `tests/test_schemas.py` — 64 tests Pydantic, 10 schemas couverts
- `tests/test_integration_sync.py` — tests endpoints sync
- `tests/test_integration_async.py` — tests endpoints async
- `tests/test_middleware.py` — 8 tests Auth + RateLimit
- `tests/test_lynch_categories.py` — 36 tests (Sprint 14)
- `tests/test_fisher_scuttlebutt.py` — 38 tests (Sprint 14)
- `tests/test_klarman_margin.py` — 37 tests (Sprint 14)
- `tests/test_greenblatt.py` — tests (Sprint 15)
- `tests/test_damodaran.py` — tests (Sprint 15)
- `tests/test_marks_cycles.py` — tests (Sprint 15)
- `tests/test_pabrai_dhandho.py` — tests (Sprint 15)
- `tests/test_screener.py` — 12 tests ScreenerService + endpoint (Sprint 17)
- `tests/test_analysis_cache.py` — 8 tests AnalysisCacheService + orchestrateur (Sprint 17)
- `tests/test_observability.py` — 10 tests ObservabilityService (Sprint 18)
- `tests/test_telemetry.py` — 8 tests endpoints /telemetry (Sprint 18)
- `tests/test_load_smoke.py` — 6 tests smoke locust (Sprint 19)
- `tests/test_report.py` — 10 tests ReportService + endpoint /report (Sprint 20)
- `tests/test_workflow_router.py` — 9 tests WorkflowRouter + WebSocket ✅ (corrigés Sprint 29)
- `tests/test_yahoo_finance.py` — 22 tests (Sprint 8 + Sprint 33)
- `tests/test_analyze_stream.py` — 8 tests SSE (Sprint 35) ✅
- `frontend/src/__tests__/AnalyzeForm.test.tsx` — 12 tests Vitest (Sprint 22 × 6 + Sprint 32 × 3 + Sprint 33 × 3)
- `frontend/src/__tests__/ScreenerTable.test.tsx` — 6 tests Vitest (Sprint 22)
- `frontend/src/__tests__/WorkflowSelector.test.tsx` — 5 tests Vitest (Sprint 22)
- `frontend/src/__tests__/useMetrics.test.ts` — 5 tests Vitest (Sprint 22)
- `frontend/src/__tests__/api.test.ts` — 6 tests Vitest (Sprint 22)
- `frontend/src/__tests__/WatchlistPage.test.tsx` — 6 tests Vitest (Sprint 27)
- `frontend/src/__tests__/LoginPage.test.tsx` — 5 tests Vitest (Sprint 28)
- `frontend/src/__tests__/AnalyzePage.test.tsx` — 5 tests Vitest streaming (Sprint 35) ✅
- `tests/test_watchlist.py` — 7 tests (Sprint 23)
- `tests/test_price_alert.py` — 7 tests (Sprint 24)
- `tests/test_email_service.py` — 4 tests (Sprint 25)
- `tests/test_weekly_report.py` — 3 tests (Sprint 25)
- `tests/test_healthz_prod.py` — 2 tests healthz (Sprint 26)
- `tests/e2e/test_e2e_auth.py` — 4 tests Playwright E2E (Sprint 30)
- `tests/e2e/test_e2e_analyze.py` — 5 tests Playwright E2E (Sprint 30)
- `tests/e2e/test_e2e_screener.py` — 3 tests Playwright E2E (Sprint 30)
- `tests/e2e/test_e2e_watchlist.py` — 4 tests Playwright E2E (Sprint 30)
- `tests/e2e/test_e2e_sprint33.py` — 3 tests Playwright E2E (Sprint 34)
- Total suite backend : ~789 passés (hors E2E), 1 xfail, 0 échec
- Total suite frontend : **50 tests Vitest verts**
- Total E2E : **19 tests Playwright verts**

## Infrastructure opérationnelle (Sprints 11-35)
- `app/workers/celery_app.py` : instance Celery, broker Redis, beat_schedule ✅
- `app/workers/tasks.py` : run_full_analysis + run_watchlist_analysis + run_price_alert_check + run_weekly_watchlist_report ✅
- `app/services/email_service.py` : EmailService — SMTP stdlib ou SendGrid ✅
- `app/middleware/auth.py` : BearerTokenMiddleware ✅
- `app/middleware/rate_limit.py` : RateLimitMiddleware ✅
- `app/api/endpoints/jobs.py` : POST /analyze-async, GET /jobs/{job_id} ✅
- `app/api/endpoints/screen.py` : POST /screen + DELETE /cache/{ticker} ✅
- `app/api/endpoints/telemetry.py` : GET /telemetry/summary|costs|cache|latency ✅
- `app/api/endpoints/report.py` : POST /report + GET /report/{analysis_id} ✅
- `app/api/endpoints/ws_metrics.py` : WebSocket /ws/metrics ✅
- `app/api/endpoints/watchlist.py` : POST/GET/DELETE /watchlist + POST /{id}/analyze + GET /{id}/price-status ✅
- `app/api/endpoints/extract.py` : GET /extract → ExtractResponse {graham, earnings_quality} ✅ (Sprint 33)
- `app/api/endpoints/analyze_stream.py` : POST /analyze-stream — StreamingResponse SSE ✅ (Sprint 35)
- `app/orchestrator/router.py` : WorkflowRouter + 5 workflows ✅ (corrigé Sprint 29)
- `app/orchestrator/core.py` : `stream_company_analysis()` async generator (skill_start/skill_result/complete/cached/error) ✅ (Sprint 35)
- `frontend/` : React 18 + Vite 5 + TypeScript strict + shadcn/ui + Tanstack Query v5 ✅
- `frontend/src/contexts/AuthContext.tsx` : AuthProvider + useAuth ✅ (Sprint 28)
- `frontend/src/components/ProtectedRoute.tsx` : redirige /login si non authentifié ✅ (Sprint 28)
- `frontend/src/pages/LoginPage.tsx` : formulaire clé API ✅ (Sprint 28)
- `frontend/src/components/StreamingProgress.tsx` : composant skill-par-skill (active/done/verdict) ✅ (Sprint 35)
- `frontend/src/pages/AnalyzePage.tsx` : for-await SSE + partialResult + activeSkill + completedSkills ✅ (Sprint 35)
- `frontend/src/api/analyze.ts` : `streamAnalyze()` fetch + ReadableStream + SSE parsing ✅ (Sprint 35)
- `frontend/src/types/index.ts` : SSEEvent discriminated union ✅ (Sprint 35)
- `tests/e2e/` : 19 tests Playwright (auth×4, analyze×5, screener×3, watchlist×4, sprint33×3) ✅ (Sprint 34)
- `.github/workflows/ci.yml` : pipeline CI/CD — backend pytest + frontend vitest ✅ (Sprint 31)
- `Auto-fill AnalyzeForm` : bouton Auto-fill + `getExtract()` → `ExtractResponse` + earnings_quality ✅ (Sprint 32 + 33)
- Redis : broker Celery + rate limiting + stockage jobs TTL 24h + cache analyses + observabilité
- PostgreSQL : tables `analysis_history` + `watchlist`
- Qdrant : collection `investment_knowledge` (RAG optionnel)

## Décisions d'architecture closes
- **Embedding** : `text-embedding-3-small` (OpenAI) — Sprint 12
- **Chunking RAG** : sections h2/h3 — Sprint 2
- **Auth** : Bearer token simple — Sprint 11
- **Frontend auth** : localStorage clé `api_token`, fallback VITE_API_KEY pour CI/headless — Sprint 28
- **Broker Celery** : Redis — Sprint 11
- **Cache analyses** : clé `analysis:{ticker}:{workflow}:{ratios_hash}`, TTL `ANALYSIS_CACHE_TTL` — Sprint 17
- **Observabilité** : clés Redis `obs:*` séparées de `analysis:*` — Sprint 18
- **PDF** : reportlab, Helvetica, A4 portrait — Sprint 20
- **WorkflowRouter** : 5 workflows, graham/ratios optionnels dans AnalyzeRequest/Response — Sprint 21
- **WebSocket /ws/metrics** : auth exemptée via `/ws` dans EXEMPT_PREFIXES — Sprint 21
- **Frontend** : React 18 + Vite 5 + TypeScript strict + shadcn/ui, proxy Vite — Sprint 22
- **Watchlist stockage** : PostgreSQL (Option A) — Sprint 23
- **Alertes prix** : seuil ±10 % vs `valeur_intrinseque_ajustee`, beat quotidien 08h00 UTC — Sprint 24
- **Email** : SMTP stdlib + SendGrid import conditionnel — Sprint 25
- **Reverse proxy** : Caddy 2 Alpine, TLS Let's Encrypt — Sprint 26
- **Tests E2E** : Playwright + uvicorn thread + call_claude_with_retry patché par module — Sprint 30
- **CI/CD** : GitHub Actions, 2 jobs parallèles, pas de secrets requis — Sprint 31
- **GET /extract** : `ExtractResponse {graham, earnings_quality}` — breaking change Sprint 33 (consommateur unique : AnalyzeForm)
- **Qualité bénéfices UI** : Auto-fill requis (pas de formulaire manuel) — Sprint 33
- **SSE endpoint** : POST /analyze-stream (pas GET/EventSource) — fetch() + ReadableStream, Bearer token dans headers — Sprint 35

## Variables d'environnement requises (production)
```bash
ANTHROPIC_API_KEY=...
DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379/0
API_KEY=...
CLAUDE_MODEL=claude-sonnet-4-6
QDRANT_URL=http://qdrant:6333
OPENAI_API_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
ANALYSIS_CACHE_TTL=86400
COST_ALERT_THRESHOLD_USD=1.0
REPORT_OUTPUT_DIR=reports
VITE_API_URL=
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
REPORT_EMAIL_TO=...
SENDGRID_API_KEY=...
DOMAIN=...
CADDY_EMAIL=...
BACKUP_DIR=/backups
```

---

# TÂCHE — SPRINT 36 : À définir

**Objectif :** Choisir parmi les sprints suggérés ci-dessous, puis implémenter.

> **Avant de commencer :** Lire `ROADMAP.md` section "Sprint 36" pour voir si un objectif
> a déjà été défini. Sinon, proposer à Yves l'un des sprints suggérés.

## Sprints suggérés (à valider avec Yves)

| Sprint suggéré | Objectif | Complexité | Justification |
|----------------|---------|-----------|---------------|
| **Validation anti-hallucination** | Sanity checks financiers avant appel Claude (`pe < 0`, ROIC > 200 %, eps/pe incohérent) + `confidence_score` dans chaque skill output + détection contradictions inter-skills | Moyenne | Confiance : les schemas Pydantic valident les types mais pas la cohérence financière des ratios — un P/E négatif ou ROIC aberrant passe sans avertissement |
| **Scoring composite unifié** | Moteur 0-100 agrégé (Graham 20 %, Buffett 20 %, Moat 15 %, Earnings 15 %, Valuation 20 %, Cycle 10 %) → `composite_score` + `conviction_level` dans `AnalyzeResponse` | Moyenne | Comparabilité : 15 verdicts textuels isolés ne permettent pas de comparer deux tickers ni de suivre un score dans le temps |
| **Performance tracking** | Stocker `price_at_analysis` + `intrinsic_value_at_analysis` dans `analysis_history` → endpoint `GET /performance/{ticker}` + calcul rétrospectif 3m/6m/1y via Celery beat | Moyenne | Validation empirique : impossible de mesurer si le système identifie réellement de bonnes opportunités sans historique prix |
| **Tests E2E SSE (Sprint 35)** | Couvrir le flux streaming par des tests Playwright : progression skill-par-skill visible, message d'erreur, résultat final | Faible | Complétude : le SSE est testé en unitaire et intégration, mais pas end-to-end depuis un vrai navigateur |

## Contraintes générales (toujours applicables)

- TypeScript strict, shadcn/ui, Tanstack Query v5
- Couverture tests : tout nouveau composant React → test composant ; tout nouvel endpoint → test intégration
- Aucun appel Claude réel dans les tests (`call_claude_with_retry` patché)
- CI doit rester verte (50 tests Vitest + backend passés)

---

# PROCHAINS SPRINTS (roadmap planifiée)

| Sprint | Objectif | Complexité |
|--------|---------|-----------|
| **Sprint 36** | À définir (voir sprints suggérés dans la section TÂCHE) | — |
| **Sprint 37** | Scoring composite unifié | Moyenne |
| **Sprint 38** | Performance tracking | Moyenne |
| **Sprint 39** | Tests E2E SSE | Faible |

---

# SPRINTS SUGGÉRÉS (hors roadmap — à valider avec Yves)

| Sprint suggéré | Objectif | Complexité | Justification |
|----------------|---------|-----------|---------------|
| **Validation anti-hallucination** | Sanity checks financiers + `confidence_score` + détection contradictions inter-skills | Moyenne | Confiance : un P/E négatif ou ROIC aberrant passe sans avertissement actuellement |
| **Scoring composite unifié** | Moteur 0-100 agrégé sur 6 dimensions → `composite_score` + `conviction_level` | Moyenne | Comparabilité : 15 verdicts textuels isolés ne permettent pas de comparer deux tickers |
| **Performance tracking** | `price_at_analysis` + `intrinsic_value_at_analysis` → `GET /performance/{ticker}` + calcul rétrospectif | Moyenne | Validation empirique : mesurer si le système est réellement prédictif |
| **Tests E2E SSE** | Playwright : progression skill-par-skill, erreur streaming, résultat final après complete | Faible | Complétude de la pyramide de test sur le Sprint 35 |

---

# CONTRAINTES ABSOLUES (rappel)

- Ne jamais appeler `client.messages.create()` directement — utiliser `call_claude_with_retry()`
- Aucun `print()` — `logging.getLogger(__name__)` partout (backend)
- Ne pas modifier `SkillBase`, `UsageDetail`, `Citation` dans `app/skills/base.py`
- Typage strict : `"strict": true` en TypeScript, pas de `any` non justifié
- `__init__.py` vides — pas de re-exports (backend)
- **Les tests E2E ne doivent consommer aucun token Claude réel** — `call_claude_with_retry` patché obligatoirement
- Les tests backend doivent tourner **sans Docker** (fixtures mockées pour DB/Redis)
- Marquer `@pytest.mark.e2e` les tests E2E (séparables par `-m "not e2e"`)
- Marquer `@pytest.mark.integration` les tests qui nécessitent une vraie DB
- Les clés Redis `obs:*` ne doivent PAS entrer en collision avec les clés `analysis:*` du cache
- **Frontend** : pas de `any` TypeScript, composants shadcn/ui purs (pas de CSS custom sauf Tailwind)
- **CI** : aucun secret GitHub requis pour la suite de tests standard (E2E exclus)
- **GET /extract** retourne désormais `ExtractResponse {graham, earnings_quality}` — ne pas revenir à `GrahamRatios` seul
- **SSE endpoint** : POST /analyze-stream, pas GET — EventSource natif non utilisé

---

# TEMPLATE SPRINT 37 (pour la prochaine mise à jour)

Une fois le Sprint 36 complété, mettre à jour ce fichier avec :

## Changements à effectuer dans ce fichier pour Sprint 37

1. **Titre** : `# Sprint 37 — [Objectif depuis ROADMAP.md ou Sprints suggérés]`
2. **Sprint actif** : Sprint 37
3. **Dernier sprint complété** : `Sprint 36 — [Objectif Sprint 36] ✅`
4. **Infrastructure** : ajouter les éléments Sprint 36 ✅ dans la liste
5. **Lecture obligatoire** : remplacer les fichiers Sprint 36 par les exemples Sprint 37
6. **TÂCHE** : Remplacer par le contenu Sprint 37
7. **SPRINTS SUGGÉRÉS** : retirer le sprint Sprint 36 (complété), ajouter nouveaux si pertinent
8. **ROADMAP.md** : passer Sprint 36 → ✅, Sprint 37 → 🔜

---

*Roadmap mise à jour le 2026-05-10 — Yves / TradingClaude*
*Sprint 35 complété : SSE Streaming — POST /analyze-stream + stream_company_analysis() async generator + StreamingProgress React + streamAnalyze() fetch/ReadableStream + 8 tests intégration backend + 5 tests Vitest frontend — 50 tests Vitest verts — version 3.0.0*
*Sprint 36 : À définir*
