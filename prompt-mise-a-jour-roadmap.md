# Sprint 38 — Scoring composite unifié
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# RÔLE

Tu es un développeur full-stack senior spécialiste React + FastAPI **ET ingénieur IA appliqué**.
Tu maîtrises React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS, Tanstack Query,
FastAPI, SSE (Server-Sent Events), et les patterns de production pour les SPA.
Tu maîtrises aussi Docker Compose, Caddy (reverse proxy), TLS automatique, homelab (backup, monitoring, sécurité),
GitHub Actions, workflows CI/CD, et les patterns de tests automatisés.

**En plus**, tu maîtrises les patterns d'évaluation LLM (golden datasets, pytest evals, drift metrics),
la validation d'outputs JSON depuis Claude (Tool Use vs prompt-JSON), et les stratégies
anti-hallucination pour les systèmes financiers IA. Tu sais concevoir des scores composites
pondérés déterministes qui agrègent les verdicts multi-frameworks en signal d'investissement 0-100.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

Lis ces fichiers dans cet ordre exact. Ne commence pas à coder sans avoir terminé cette étape.

1. `ROADMAP.md` — section "Sprint 38" (critères de succès, ce qui reste à faire)
2. `app/orchestrator/core.py` — `AnalyzeResponse` (champs disponibles : graham, buffett, dorsey_moat, earnings_quality, stock_valuation, marks_cycles, inter_skill_conflicts)
3. `app/skills/tier2/graham_analysis/schemas.py` — `GrahamAnalysisOutput.defensive_verdict` (`@computed_field` : PASSE/BORDERLINE/REJETER)
4. `app/skills/tier2/buffett_quality/schemas.py` — `BuffettQualityOutput.verdict` + `confidence_score`
5. `app/skills/tier2/dorsey_moat/schemas.py` — `DorseyMoatOutput.moat_type` (WIDE/NARROW/NONE) + `confidence_score`
6. `app/skills/tier2/earnings_quality/schemas.py` — `EarningsQualityOutput.verdict` (FIABLE/SURVEILLER/REJETER) + `confidence_score`

---

# ÉTAT DU PROJET À CE JOUR

| Champ | Valeur |
|-------|--------|
| Version | 3.1.0 |
| Phase active | Phase 3 — Pipeline de synthèse |
| Sprint actif | **Sprint 38 — Scoring composite unifié 🔄** |
| Dernier sprint complété | Sprint 37 — Validation anti-hallucination ✅ |

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

## Suite de tests opérationnelle (Sprints 13-37)
- `tests/conftest.py` — fixtures `client`, `mock_claude_graham`, `db_cleanup`, `_SKILL_PROMPT_PATCHES`, `mock_obs_redis`, `obs_service`
- `tests/test_schemas.py` — 92 tests Pydantic, 10 schemas couverts + validateurs Sprint 37
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
- `tests/test_ticker_sanitizer.py` — 28 tests sanitize_ticker() ✅ (Sprint 36)
- `tests/evals/test_graham_evals.py` — **20/20 tests @pytest.mark.evals** ✅ (Sprint 36)
- `frontend/src/__tests__/AnalyzeForm.test.tsx` — 12 tests Vitest
- `frontend/src/__tests__/ScreenerTable.test.tsx` — 6 tests Vitest
- `frontend/src/__tests__/WorkflowSelector.test.tsx` — 5 tests Vitest
- `frontend/src/__tests__/useMetrics.test.ts` — 5 tests Vitest
- `frontend/src/__tests__/api.test.ts` — 6 tests Vitest
- `frontend/src/__tests__/WatchlistPage.test.tsx` — 6 tests Vitest
- `frontend/src/__tests__/LoginPage.test.tsx` — 5 tests Vitest
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
- Total suite backend : **851 passés** (hors E2E et evals), 1 xfail, 25 échecs pré-existants non bloquants
- Total suite frontend : **50 tests Vitest verts**
- Total E2E : **19 tests Playwright verts**
- Total evals : **20/20 PASS (100 %)** ✅ (Sprint 36)

## Infrastructure opérationnelle (Sprints 11-37)
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
- `app/orchestrator/core.py` : `stream_company_analysis()` async generator + `sanitize_ticker()` + `inter_skill_conflicts` ✅ (Sprint 37)
- `app/utils/ticker_sanitizer.py` : `sanitize_ticker()`, regex `^[A-Z0-9]{1,6}(\.[A-Z]{1,2})?$`, HTTP 422 ✅ (Sprint 36)
- `tests/evals/__init__.py` + `tests/evals/conftest.py` : infrastructure eval, fixture `eval_client` ✅ (Sprint 36)
- `tests/evals/fixtures/__init__.py` : `load_graham_golden()` ✅ (Sprint 36)
- `tests/evals/fixtures/graham_golden.json` : 20 cas calibrés, **20/20 PASS** ✅ (Sprint 36)
- `tests/evals/eval_runner.py` : `EvalResult`, `EvalReport`, `EvalRunner` avec `_compute_drift` ✅ (Sprint 36)
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
- **Eval framework** : `tests/evals/`, marqueur `@pytest.mark.evals`, appels Claude RÉELS intentionnels — Sprint 36
- **Ticker sanitisation** : `app/utils/ticker_sanitizer.py`, regex `^[A-Z0-9]{1,6}(\.[A-Z]{1,2})?$`, HTTP 422 explicite — Sprint 36
- **defensive_verdict** : `@computed_field` déterministe sur `GrahamAnalysisOutput` — seuils ≥6=PASSE, 4-5=BORDERLINE, ≤3=REJETER — jamais via prompt — Sprint 36
- **defensive_score** : `@computed_field` déterministe — `sum(1 for c in criteria_defensif if c.passe)` — jamais via prompt — Sprint 36
- **pe nullable** : `GrahamRatios.pe: float | None = Field(None)` — sociétés déficitaires (NKLA, RIVN, AMC…) — Sprint 36
- **Format golden dataset** : clé `inputs`, `defensive_score_range: [min, max]`, `must_pass_criteria`, `must_red_flag` — Sprint 36
- **confidence_score** : toujours calculé de façon déterministe post-execute() — ne jamais demander à Claude de s'auto-évaluer — Sprint 37
- **Validateurs GrahamRatios** : WARNING log seulement (pe<0, pb<0, eps_growth_10y>5, triangle pe/price/eps_ttm) — jamais HTTP 422 sur incohérence — Sprint 37
- **inter_skill_conflicts** : `list[str]` dans `AnalyzeResponse`, calculé par `_detect_inter_skill_conflicts()` dans core.py — Sprint 37

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

# TÂCHE — SPRINT 38 : Scoring composite unifié

**Objectif :** Agréger les verdicts de 6 skills en un score composite pondéré 0-100 qui donne
un signal d'investissement synthétique unique. Ce score est **100 % déterministe** — calculé
depuis les champs Pydantic post-exécution, jamais demandé à Claude.

**Philosophie :** Le score composite n'est pas un verdict IA. C'est une réduction dimensionnelle
déterministe des verdicts multi-frameworks. L'analyste humain reste décideur final.

---

## Pondérations

| Skill | Pondération | Champ source | Mapping verdict → score brut |
|-------|------------|-------------|------------------------------|
| `graham_analysis` | 20 % | `defensive_verdict` | PASSE=1.0, BORDERLINE=0.5, REJETER=0.0 |
| `buffett_quality` | 20 % | `verdict` | COMPOUNDER=1.0, QUALITÉ=0.75, PASSABLE=0.5, REJETER=0.0 |
| `stock_valuation` | 20 % | `verdict_global` | SOUS-ÉVALUÉ=1.0, JUSTE PRIX=0.5, SURÉVALUÉ=0.0 |
| `dorsey_moat` | 15 % | `moat_type` | WIDE=1.0, NARROW=0.5, NONE=0.0 |
| `earnings_quality` | 15 % | `verdict` | FIABLE=1.0, SURVEILLER=0.5, REJETER=0.0 |
| `marks_cycles` | 10 % | `signal_positionnement` | contient "ACHETEUR"→1.0, "NEUTRE"→0.5, sinon→0.0 |

**Score composite final = Σ(score_brut_i × poids_i × confidence_score_i) / Σ(poids_i × confidence_score_i) × 100**

Si un skill est absent (None) ou si `confidence_score == 0.0`, son poids est exclu du dénominateur
(ne pénalise pas le score pour données manquantes).

---

## Livrable 1 — `app/services/composite_score.py`

Créer le service de scoring composite :

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

WEIGHTS: dict[str, float] = {
    "graham": 0.20,
    "buffett": 0.20,
    "stock_valuation": 0.20,
    "dorsey_moat": 0.15,
    "earnings_quality": 0.15,
    "marks_cycles": 0.10,
}


@dataclass
class CompositeScore:
    score: float  # 0.0 à 100.0, arrondi 1 décimale
    label: str    # "FORT" ≥70, "MODÉRÉ" 45-69, "FAIBLE" <45
    skills_inclus: list[str]  # skills ayant contribué au score
    skills_exclus: list[str]  # skills absents ou confidence=0
    detail: dict[str, float]  # score brut par skill (avant pondération)


def _map_graham(verdict: str | None) -> float | None:
    mapping = {"PASSE": 1.0, "BORDERLINE": 0.5, "REJETER": 0.0}
    return mapping.get(verdict) if verdict else None


def _map_buffett(verdict: str | None) -> float | None:
    mapping = {"COMPOUNDER": 1.0, "QUALITÉ": 0.75, "PASSABLE": 0.5, "REJETER": 0.0}
    return mapping.get(verdict) if verdict else None


def _map_valuation(verdict: str | None) -> float | None:
    if verdict is None:
        return None
    v = verdict.upper()
    if "SOUS" in v:
        return 1.0
    if "JUSTE" in v:
        return 0.5
    if "SUR" in v:
        return 0.0
    return None


def _map_moat(moat_type: str | None) -> float | None:
    mapping = {"WIDE": 1.0, "NARROW": 0.5, "NONE": 0.0}
    return mapping.get(moat_type) if moat_type else None


def _map_earnings(verdict: str | None) -> float | None:
    mapping = {"FIABLE": 1.0, "SURVEILLER": 0.5, "REJETER": 0.0}
    return mapping.get(verdict) if verdict else None


def _map_marks(signal: str | None) -> float | None:
    if signal is None:
        return None
    s = signal.upper()
    if "ACHETEUR" in s:
        return 1.0
    if "NEUTRE" in s:
        return 0.5
    return 0.0


def compute_composite_score(
    graham_verdict: str | None = None,
    graham_confidence: float = 0.0,
    buffett_verdict: str | None = None,
    buffett_confidence: float = 0.0,
    valuation_verdict: str | None = None,
    valuation_confidence: float = 0.0,
    moat_type: str | None = None,
    moat_confidence: float = 0.0,
    earnings_verdict: str | None = None,
    earnings_confidence: float = 0.0,
    marks_signal: str | None = None,
    marks_confidence: float = 1.0,  # marks_cycles n'a pas de confidence_score — défaut 1.0
) -> CompositeScore:
    """Calcule le score composite 0-100 depuis les verdicts des 6 skills pondérés."""
    raw_scores = {
        "graham": (_map_graham(graham_verdict), graham_confidence),
        "buffett": (_map_buffett(buffett_verdict), buffett_confidence),
        "stock_valuation": (_map_valuation(valuation_verdict), valuation_confidence),
        "dorsey_moat": (_map_moat(moat_type), moat_confidence),
        "earnings_quality": (_map_earnings(earnings_verdict), earnings_confidence),
        "marks_cycles": (_map_marks(marks_signal), marks_confidence),
    }

    numerateur = 0.0
    denominateur = 0.0
    skills_inclus: list[str] = []
    skills_exclus: list[str] = []
    detail: dict[str, float] = {}

    for skill_key, (raw, confidence) in raw_scores.items():
        poids = WEIGHTS[skill_key]
        if raw is None or confidence == 0.0:
            skills_exclus.append(skill_key)
            continue
        contribution = raw * poids * confidence
        numerateur += contribution
        denominateur += poids * confidence
        skills_inclus.append(skill_key)
        detail[skill_key] = round(raw, 4)

    if denominateur == 0.0:
        score = 0.0
    else:
        score = round((numerateur / denominateur) * 100, 1)

    if score >= 70:
        label = "FORT"
    elif score >= 45:
        label = "MODÉRÉ"
    else:
        label = "FAIBLE"

    return CompositeScore(
        score=score,
        label=label,
        skills_inclus=skills_inclus,
        skills_exclus=skills_exclus,
        detail=detail,
    )
```

---

## Livrable 2 — `composite_score` dans `AnalyzeResponse` (core.py)

Dans `app/orchestrator/core.py` :

**Import :**
```python
from app.services.composite_score import CompositeScore, compute_composite_score
```

**Champ dans `AnalyzeResponse` :**
```python
composite_score: CompositeScore | None = Field(
    default=None,
    description="Score composite pondéré 0-100 — calculé de façon déterministe depuis les verdicts des skills.",
)
```

**Appel dans `run_company_analysis()` et `stream_company_analysis()`,
après avoir collecté tous les résultats de skills :**

```python
composite = compute_composite_score(
    graham_verdict=graham_output.defensive_verdict if graham_output else None,
    graham_confidence=graham_output.confidence_score if graham_output else 0.0,
    buffett_verdict=buffett_output.verdict if buffett_output else None,
    buffett_confidence=buffett_output.confidence_score if buffett_output else 0.0,
    valuation_verdict=valuation_output.verdict_global if valuation_output else None,
    valuation_confidence=getattr(valuation_output, "confidence_score", 0.0) if valuation_output else 0.0,
    moat_type=dorsey_output.moat_type if dorsey_output else None,
    moat_confidence=dorsey_output.confidence_score if dorsey_output else 0.0,
    earnings_verdict=earnings_output.verdict if earnings_output else None,
    earnings_confidence=earnings_output.confidence_score if earnings_output else 0.0,
    marks_signal=marks_output.signal_positionnement if marks_output else None,
    marks_confidence=1.0,  # marks_cycles: pas de confidence_score — toujours 1.0
)
```

Passer `composite_score=composite` à `AnalyzeResponse(...)`.

---

## Livrable 3 — `tests/test_composite_score.py`

Tests unitaires exhaustifs du service de scoring :

```python
"""Tests unitaires pour compute_composite_score()."""
import pytest
from app.services.composite_score import CompositeScore, compute_composite_score, WEIGHTS

class TestComputeCompositeScoreBasique:
    def test_tous_skills_presents_fort(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
            valuation_verdict="SOUS-ÉVALUÉ", valuation_confidence=1.0,
            moat_type="WIDE", moat_confidence=1.0,
            earnings_verdict="FIABLE", earnings_confidence=1.0,
            marks_signal="ACHETEUR AGRESSIF", marks_confidence=1.0,
        )
        assert cs.score == 100.0
        assert cs.label == "FORT"
        assert len(cs.skills_inclus) == 6
        assert cs.skills_exclus == []

    def test_tous_skills_rejeter_faible(self):
        cs = compute_composite_score(
            graham_verdict="REJETER", graham_confidence=1.0,
            buffett_verdict="REJETER", buffett_confidence=1.0,
            valuation_verdict="SURÉVALUÉ", valuation_confidence=1.0,
            moat_type="NONE", moat_confidence=1.0,
            earnings_verdict="REJETER", earnings_confidence=1.0,
            marks_signal="VENDEUR", marks_confidence=1.0,
        )
        assert cs.score == 0.0
        assert cs.label == "FAIBLE"

    def test_skills_absents_exclus_du_denominateur(self):
        """Un skill absent (verdict=None) ne doit pas pénaliser le score."""
        cs_complet = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        cs_seul_graham = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
        )
        # Les deux devraient avoir le même score puisque buffett COMPOUNDER = 1.0
        assert cs_complet.score == cs_seul_graham.score == 100.0

    def test_confidence_zero_exclut_skill(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=0.0,  # exclu
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        assert "graham" in cs.skills_exclus
        assert "buffett" in cs.skills_inclus
        assert cs.score == 100.0

    def test_aucun_skill_score_zero(self):
        cs = compute_composite_score()
        assert cs.score == 0.0
        assert cs.label == "FAIBLE"
        assert cs.skills_inclus == []
        assert len(cs.skills_exclus) == 6

class TestLabels:
    def test_label_fort_a_70(self):
        # Graham PASSE (1.0) × 20% + buffett COMPOUNDER (1.0) × 20% = 0.4/0.4 → 100 → FORT
        cs = compute_composite_score(graham_verdict="PASSE", graham_confidence=1.0,
                                     buffett_verdict="COMPOUNDER", buffett_confidence=1.0)
        assert cs.label == "FORT"

    def test_label_modere_entre_45_et_70(self):
        # Mélange PASSE et REJETER doit donner ~50
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="REJETER", buffett_confidence=1.0,
        )
        assert cs.label in ("MODÉRÉ", "FAIBLE")  # selon la moyenne

    def test_score_plage_0_100(self):
        cs = compute_composite_score(
            graham_verdict="BORDERLINE", graham_confidence=0.7,
            buffett_verdict="PASSABLE", buffett_confidence=0.5,
            marks_signal="NEUTRE", marks_confidence=1.0,
        )
        assert 0.0 <= cs.score <= 100.0

class TestDetailEtPoids:
    def test_poids_somme_a_1(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_detail_contient_skills_inclus(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        assert "graham" in cs.detail
        assert "buffett" in cs.detail

    def test_confidence_module_score(self):
        """confidence=0.5 doit pondérer moitié du poids habituel."""
        cs_full = compute_composite_score(graham_verdict="PASSE", graham_confidence=1.0)
        cs_half = compute_composite_score(graham_verdict="PASSE", graham_confidence=0.5)
        # Les deux donnent 100.0 car seul graham contribue — même ratio numérateur/dénominateur
        assert cs_full.score == cs_half.score == 100.0

class TestMarksMapping:
    def test_acheteur_agressif(self):
        cs = compute_composite_score(marks_signal="ACHETEUR AGRESSIF", marks_confidence=1.0)
        assert cs.score == 100.0

    def test_neutre(self):
        cs = compute_composite_score(marks_signal="NEUTRE", marks_confidence=1.0)
        assert cs.score == 50.0

    def test_vendeur(self):
        cs = compute_composite_score(marks_signal="VENDEUR OFFENSIF", marks_confidence=1.0)
        assert cs.score == 0.0

    def test_signal_inconnu_exclu(self):
        cs = compute_composite_score(marks_signal=None, marks_confidence=1.0)
        assert "marks_cycles" in cs.skills_exclus
```

---

## Critères de succès Sprint 38

- [ ] `pytest tests/test_composite_score.py -v` → tous verts (≥ 18 tests)
- [ ] `composite_score` présent dans `AnalyzeResponse` (champ Pydantic + dataclass)
- [ ] `compute_composite_score()` appelé dans `run_company_analysis()` et `stream_company_analysis()`
- [ ] Score varie selon les verdicts (pas un zéro fixe ou une constante)
- [ ] Skills absents n'influencent pas le dénominateur (pas de pénalité données manquantes)
- [ ] `pytest -m "not e2e and not evals"` → 851+ tests CI verts (pas de régression)
- [ ] `pytest tests/evals/ -m evals` → 20/20 toujours verts après les changements

---

# SPRINTS PLANIFIÉS (39-48)

| Sprint | Objectif | Dépendance | Complexité |
|--------|---------|-----------|-----------|
| **Sprint 39** | Performance tracking (`price_at_analysis` + `GET /performance/{ticker}` + calcul rétrospectif) | — | Moyenne |
| **Sprint 40** | Tests E2E SSE — Playwright streaming (progression skill-par-skill, erreur, complete) | — | Faible |
| **Sprint 41** | Dashboard métriques qualité IA — composite_score + drift + conflicts dans le frontend React | Sprint 37 + 38 | Moyenne |
| **Sprint 42** | Tool Use pilote — `graham_analysis` + `earnings_quality` (remplace `_parse_claude_json`) | **Sprint 36 drift ≤ 2% HARD** | Haute |
| **Sprint 43** | Tool Use complet — 13 skills restants | **Sprint 42 ≥ 90 % pass** | Haute |
| **Sprint 44** | Multi-model strategy — Haiku × 4 skills (`greenblatt`, `yahoo_finance_extractor`, `sedar_plus_extractor`, `lynch_categories`) | **Sprint 42 baseline Sonnet établie** | Moyenne |
| **Sprint 45** | Screener composite — `/screen` retourne `composite_score` + tri/filtre par label (FORT/MODÉRÉ/FAIBLE) | Sprint 38 | Moyenne |
| **Sprint 46** | Watchlist alertes composite — alerte si composite_score chute de >15 pts vs baseline sauvegardée | Sprint 38 + 39 | Moyenne |
| **Sprint 47** | Export CSV/Excel — rapport screener multi-tickers avec composite_score + tous verdicts skills | Sprint 38 | Faible |
| **Sprint 48** | Backtesting composite — simulation rétrospective du signal composite sur portefeuille historique | Sprint 38 + 39 | Haute |

> **Note dépendances dures :**
> - Sprint 42 NE PEUT PAS commencer avant que les evals montrent `verdict_drift_rate ≤ 2 %`
> - Sprint 44 NE PEUT PAS commencer avant que Sprint 42 établisse la baseline Sonnet pour les 4 skills ciblés
> - Sonnet reste obligatoire pour `canadian_tax` et `marks_cycles` — jugement qualitatif non délégable à Haiku
> - Sprint 41 dépend des métriques structurées produites par Sprint 37 et 38

---

# CONTRAINTES ABSOLUES (rappel)

- Ne jamais appeler `client.messages.create()` directement — utiliser `call_claude_with_retry()`
- Aucun `print()` — `logging.getLogger(__name__)` partout (backend)
- Ne pas modifier `SkillBase`, `UsageDetail`, `Citation` dans `app/skills/base.py`
- Typage strict : `"strict": true` en TypeScript, pas de `any` non justifié
- `__init__.py` vides — pas de re-exports (backend)
- **Les tests CI standard ne doivent consommer aucun token Claude réel** — `call_claude_with_retry` patché obligatoirement dans tous les tests hors `evals`
- **Les tests `@pytest.mark.evals` font des appels Claude RÉELS** — ne jamais patcher dans `tests/evals/`
- Les tests backend doivent tourner **sans Docker** (fixtures mockées pour DB/Redis)
- Marquer `@pytest.mark.e2e` les tests E2E Playwright (séparables par `-m "not e2e"`)
- Marquer `@pytest.mark.evals` les tests du golden dataset (séparables par `-m "not evals"`)
- Marquer `@pytest.mark.integration` les tests qui nécessitent une vraie DB
- **CI standard** : `pytest -m "not e2e and not evals"` — aucune clé Claude requise
- Les clés Redis `obs:*` ne doivent PAS entrer en collision avec les clés `analysis:*` du cache
- **Frontend** : pas de `any` TypeScript, composants shadcn/ui purs (pas de CSS custom sauf Tailwind)
- **CI** : aucun secret GitHub requis pour la suite de tests standard (E2E et evals exclus)
- **GET /extract** retourne désormais `ExtractResponse {graham, earnings_quality}` — ne pas revenir à `GrahamRatios` seul
- **SSE endpoint** : POST /analyze-stream, pas GET — EventSource natif non utilisé
- **confidence_score** : toujours calculé de façon déterministe post-execute() — ne jamais demander à Claude de s'auto-évaluer
- **Ticker sanitiser** : HTTP 422 explicite sur ticker invalide — pas de rejet silencieux
- **defensive_verdict** : toujours lu depuis `graham.defensive_verdict` (computed_field) — jamais depuis `graham.verdict`
- **defensive_score** : `@computed_field` déterministe — `sum(passe=True in criteria_defensif)` — ne jamais laisser Claude compter
- **pe nullable** : `pe: float | None` — ne pas re-rendre obligatoire
- **Eval golden dataset** : ne jamais patcher `call_claude_with_retry` dans `tests/evals/` — les appels sont intentionnellement réels
- **Validateurs financiers Sprint 37** : WARNING log seulement, jamais HTTP 422 sur incohérence — les données imparfaites doivent passer
- **inter_skill_conflicts** : calculé par `_detect_inter_skill_conflicts()` — pure function niveau module, pas méthode de classe
- **composite_score** : calculé par `compute_composite_score()` dans `app/services/composite_score.py` — jamais demandé à Claude — Sprint 38
- **Skills absents** : confidence=0.0 ou verdict=None excluent le skill du dénominateur — pas de pénalité score — Sprint 38

---

*Roadmap mise à jour le 2026-05-13 — Yves / TradingClaude*
*Sprint 37 complété : Validation anti-hallucination — validateurs GrahamRatios WARNING-only + confidence_score ×4 skills + inter_skill_conflicts déterministe — 851 tests CI verts*
*Sprints 39-48 planifiés : Performance tracking → E2E SSE → Dashboard → Tool Use pilote → Tool Use complet → Multi-model → Screener composite → Alertes composite → Export → Backtesting*
