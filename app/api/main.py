from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID

import anthropic
import httpx
import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints.admin import _require_admin
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.analyze_stream import router as analyze_stream_router
from app.api.endpoints.annotations import router as annotations_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.backtest import router as backtest_router
from app.api.endpoints.billing import router as billing_router
from app.api.endpoints.compare import router as compare_router
from app.api.endpoints.composite_history import router as composite_history_router
from app.api.endpoints.esg_history import router as esg_history_router
from app.api.endpoints.evals import router as evals_router
from app.api.endpoints.export import router as export_router
from app.api.endpoints.extract import router as extract_router
from app.api.endpoints.jobs import router as jobs_router
from app.api.endpoints.monthly_report import router as monthly_report_router
from app.api.endpoints.performance import router as performance_router
from app.api.endpoints.preferences import router as preferences_router
from app.api.endpoints.quota import router as quota_router
from app.api.endpoints.report import router as report_router
from app.api.endpoints.screen import router as screen_router
from app.api.endpoints.screener_report import router as screener_report_router
from app.api.endpoints.semantic_search import router as semantic_search_router
from app.api.endpoints.telemetry import router as telemetry_router
from app.api.endpoints.ticker_report import router as ticker_report_router
from app.api.endpoints.usage import router as usage_router
from app.api.endpoints.watchlist import router as watchlist_router
from app.api.endpoints.ws_metrics import router as ws_metrics_router
from app.db.pool import create_runtime_pool
from app.logging_config import configure_logging
from app.middleware.auth import BearerTokenMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.tenant import TenantContextMiddleware
from app.observability.langfuse_client import LangfuseTracer
from app.orchestrator.core import (
    AnalyzeRequest,
    AnalyzeResponse,
    HistoryResponse,
    MetricsResponse,
    Orchestrator,
    PagedHistoryResponse,
    SkillAnalysesResponse,
)
from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.rag.service import RagService
from app.services.alert_history_service import AlertHistoryService
from app.services.analysis_cache import AnalysisCacheService
from app.services.annotation_service import AnnotationService
from app.services.api_key_service import ApiKeyRecord as _ApiKeyRecord
from app.services.api_key_service import ApiKeyService
from app.services.audit_log_service import AuditLogService
from app.services.auth_token_service import AuthTokenService
from app.services.compare_service import CompareService
from app.services.composite_history_service import CompositeHistoryService
from app.services.esg_history_service import EsgHistoryService
from app.services.eval_drift_service import EvalDriftService
from app.services.monthly_report_service import MonthlyReportService
from app.services.observability import ObservabilityService
from app.services.password_reset_service import PasswordResetService
from app.services.pdf_report_service import PdfReportService
from app.services.quota_service import QuotaExceededError, QuotaService
from app.services.screener import ScreenerService
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.slack_service import SlackService
from app.services.stripe_service import StripeService
from app.services.usage_event_service import UsageEventService
from app.services.user_service import UserService
from app.services.watchlist_pdf_service import WatchlistPdfService
from app.services.watchlist_service import WatchlistService
from app.services.webhook_service import WebhookService
from app.skills.base import SkillConfig
from app.skills.tier1.sedar_plus import SedarPlusExtractor
from app.skills.tier1.yahoo_finance import YahooFinanceExtractor
from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
from app.skills.tier2.canadian_tax.skill import CanadianTaxSkill
from app.skills.tier2.damodaran_narrative.skill import DamodararNarrativeSkill
from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
from app.skills.tier2.esg_simplified.skill import EsgSimplifiedSkill
from app.skills.tier2.fisher_scuttlebutt.skill import FisherScuttlebuttSkill
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill
from app.skills.tier2.greenblatt.skill import GreenblattSkill
from app.skills.tier2.klarman_margin.skill import KlarmanMarginSkill
from app.skills.tier2.lynch_categories.skill import LynchCategoriesSkill
from app.skills.tier2.marks_cycles.skill import MarksCyclesSkill
from app.skills.tier2.munger_mental.skill import MungerMentalSkill
from app.skills.tier2.pabrai_dhandho.skill import PabraiDhandhoSkill
from app.skills.tier2.stock_valuation.skill import StockValuationSkill
from app.skills.tier2.thesis_builder.skill import ThesisBuilderSkill
from app.utils.env import is_dev_environment
from app.utils.error_sanitization import log_internal_error, sanitized_http_500
from app.utils.quota_http import quota_exceeded_http
from app.utils.retry import _DEFAULT_MAX_RETRIES, _DEFAULT_TIMEOUT_S
from app.utils.security_config import require_secure_db_url, resolve_app_database_url

configure_logging()
logger = logging.getLogger(__name__)

_VERSION = "3.0.0"


def _get_env(key: str, default: str | None = None) -> str:
    """Lit une variable d'environnement, lève une erreur explicite si absente et sans défaut."""
    value = os.environ.get(key, default)
    if value is None:
        raise RuntimeError(f"Variable d'environnement manquante : {key}")
    return value


def _init_langfuse_if_configured():
    """Retourne une instance Langfuse si les clés sont présentes, sinon None."""
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if not lf_secret:
        return None
    try:
        from langfuse import Langfuse  # type: ignore[import]

        return Langfuse(
            secret_key=lf_secret,
            public_key=_get_env("LANGFUSE_PUBLIC_KEY"),
            host=_get_env("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except ImportError:
        logger.warning("Package langfuse non installé — traces Langfuse (ObservabilityService) désactivées")
        return None
    except Exception:
        logger.exception("Erreur lors de l'initialisation de Langfuse — mode Redis-only")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialisation et fermeture des ressources partagées."""
    api_key = _get_env("ANTHROPIC_API_KEY")
    model = _get_env("CLAUDE_MODEL", "claude-sonnet-4-6")
    # Haiku pour skills mécaniques/quantitatifs — réduction coût ~60 % sur ces appels
    haiku_model = _get_env("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5-20251001")
    # Pool runtime sous le rôle `app_runtime` (NOSUPERUSER/NOBYPASSRLS) → la RLS s'applique.
    # `DATABASE_URL` (rôle `copilote` propriétaire) est réservé aux migrations Alembic.
    db_url = resolve_app_database_url()
    require_secure_db_url(db_url)
    qdrant_url = _get_env("QDRANT_URL", "http://qdrant:6333")
    qdrant_coll = _get_env("QDRANT_COLLECTION", "investment_knowledge")
    redis_url = _get_env("REDIS_URL", "redis://redis:6379/0")
    openai_key = os.environ.get("OPENAI_API_KEY")
    top_k = int(_get_env("RAG_TOP_K", "5"))

    timeout_s = float(_get_env("CLAUDE_TIMEOUT_S", str(_DEFAULT_TIMEOUT_S)))
    max_retries = int(_get_env("CLAUDE_MAX_RETRIES", str(_DEFAULT_MAX_RETRIES)))
    cache_ttl = int(_get_env("ANALYSIS_CACHE_TTL", "86400"))

    # Pool API (tailles 2/10) ; l'invariant DSN+setup vit dans le helper. Threading tenant
    # non câblé sur ce pool → défaut legacy (E3-S4).
    db_pool = await create_runtime_pool(min_size=2, max_size=10)

    # Aucun DDL au boot : le schéma est porté par Alembic et appliqué hors du process
    # API (`alembic upgrade head` via l'entrypoint). Un rôle en lecture seule sur le
    # schéma migré démarre donc l'app sans erreur.

    anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)

    rag_client = RagClient(url=qdrant_url, collection=qdrant_coll)
    await rag_client.ensure_collection()

    rag_service: RagService | None = None
    if openai_key:
        embedder = EmbeddingClient(api_key=openai_key)
        rag_service = RagService(rag_client=rag_client, embedder=embedder)
        logger.info("RAG activé — collection '%s'", qdrant_coll)
    else:
        logger.warning("OPENAI_API_KEY absente — RAG désactivé, citations = []")

    tracer: LangfuseTracer | None = None
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if lf_secret:
        tracer = LangfuseTracer(
            secret_key=lf_secret,
            public_key=_get_env("LANGFUSE_PUBLIC_KEY"),
            host=_get_env("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    else:
        logger.warning("LANGFUSE_SECRET_KEY absente — traçage Langfuse désactivé")

    skill_config = SkillConfig(
        timeout_s=timeout_s,
        max_retries=max_retries,
        tracer=tracer,
    )

    graham_skill = GrahamAnalysisSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    earnings_skill = EarningsQualitySkill(
        client=anthropic_client,
        model=haiku_model,  # skill mécanique — M-Score/Z-Score/F-Score formulaiques
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    dorsey_skill = DorseyMoatSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    buffett_skill = BuffettQualitySkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    valuation_skill = StockValuationSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    thesis_skill = ThesisBuilderSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    munger_skill = MungerMentalSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    canadian_tax_skill = CanadianTaxSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    lynch_skill = LynchCategoriesSkill(
        client=anthropic_client,
        model=haiku_model,  # skill mécanique — PEG ratio + catégorie Lynch formulaiques
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    fisher_skill = FisherScuttlebuttSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    klarman_skill = KlarmanMarginSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    greenblatt_skill = GreenblattSkill(
        client=anthropic_client,
        model=haiku_model,  # skill mécanique — ROC + Earnings Yield formulaiques
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    damodaran_skill = DamodararNarrativeSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    marks_skill = MarksCyclesSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    pabrai_skill = PabraiDhandhoSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    esg_skill = EsgSimplifiedSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    usage_event_service = UsageEventService(db_pool=db_pool)
    orchestrator = Orchestrator(
        db_pool=db_pool,
        usage_event_service=usage_event_service,
        graham_skill=graham_skill,
        earnings_skill=earnings_skill,
        dorsey_skill=dorsey_skill,
        buffett_skill=buffett_skill,
        valuation_skill=valuation_skill,
        thesis_skill=thesis_skill,
        munger_skill=munger_skill,
        canadian_tax_skill=canadian_tax_skill,
        lynch_skill=lynch_skill,
        fisher_skill=fisher_skill,
        klarman_skill=klarman_skill,
        greenblatt_skill=greenblatt_skill,
        damodaran_skill=damodaran_skill,
        marks_skill=marks_skill,
        pabrai_skill=pabrai_skill,
        esg_skill=esg_skill,
    )

    yahoo_extractor = YahooFinanceExtractor()
    sedar_extractor = SedarPlusExtractor()

    redis_pool = aioredis.from_url(redis_url, decode_responses=True)

    analysis_cache = AnalysisCacheService(redis_client=redis_pool, ttl_seconds=cache_ttl)

    # Quotas par plan (E4-S2) : compteur mensuel d'analyses + borne taille screener par tenant.
    quota_service = QuotaService(db_pool=db_pool, redis_client=redis_pool)

    screener = ScreenerService(
        orchestrator=orchestrator,
        extractor=yahoo_extractor,
        cache=analysis_cache,
    )

    langfuse_client = _init_langfuse_if_configured()
    obs_service = ObservabilityService(
        redis_client=redis_pool,
        langfuse_client=langfuse_client,
        daily_threshold_usd=float(os.getenv("COST_ALERT_THRESHOLD_USD", "1.0")),
    )

    audit_log_service = AuditLogService(db_pool=db_pool)
    alert_history_service = AlertHistoryService(db_pool=db_pool)
    annotation_service = AnnotationService(db_pool=db_pool, audit_log=audit_log_service)
    compare_service = CompareService(db_pool=db_pool)
    watchlist_service = WatchlistService(db_pool=db_pool, audit_log=audit_log_service)
    webhook_service = WebhookService()
    slack_service = SlackService()
    composite_history_service = CompositeHistoryService(db_pool=db_pool)
    esg_history_service = EsgHistoryService(db_pool=db_pool)
    eval_drift_service = EvalDriftService(redis_client=redis_pool)
    api_key_service = ApiKeyService(db_pool=db_pool, audit_log=audit_log_service)
    pdf_report_service = PdfReportService()
    screener_pdf_service = ScreenerPdfService()
    watchlist_pdf_service = WatchlistPdfService()
    monthly_report_service = MonthlyReportService()
    user_service = UserService(db_pool=db_pool)
    auth_token_service = AuthTokenService(db_pool=db_pool, redis_client=redis_pool)
    password_reset_service = PasswordResetService()

    # Facturation Stripe (E4-S7) — désactivée tant que les clés ne sont pas configurées.
    stripe_price_by_plan = {
        plan: price
        for plan, env in (("free", "STRIPE_PRICE_FREE"), ("pro", "STRIPE_PRICE_PRO"))
        if (price := os.environ.get(env))
    }
    stripe_service = StripeService(
        db_pool=db_pool,
        secret_key=os.environ.get("STRIPE_SECRET_KEY"),
        webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
        price_by_plan=stripe_price_by_plan,
        meter_event_name=os.environ.get("STRIPE_METER_EVENT_NAME"),
    )

    app.state.audit_log_service = audit_log_service
    app.state.usage_event_service = usage_event_service
    app.state.alert_history_service = alert_history_service
    app.state.annotation_service = annotation_service
    app.state.compare_service = compare_service
    app.state.orchestrator = orchestrator
    app.state.db_pool = db_pool
    app.state.rag_service = rag_service
    app.state.qdrant_url = qdrant_url
    app.state.yahoo_extractor = yahoo_extractor
    app.state.sedar_extractor = sedar_extractor
    app.state.redis_pool = redis_pool
    app.state.analysis_cache = analysis_cache
    app.state.quota_service = quota_service
    app.state.screener = screener
    app.state.observability = obs_service
    app.state.watchlist_service = watchlist_service
    app.state.webhook_service = webhook_service
    app.state.slack_service = slack_service
    app.state.composite_history_service = composite_history_service
    app.state.esg_history_service = esg_history_service
    app.state.eval_drift_service = eval_drift_service
    app.state.api_key_service = api_key_service
    app.state.pdf_report_service = pdf_report_service
    app.state.screener_pdf_service = screener_pdf_service
    app.state.watchlist_pdf_service = watchlist_pdf_service
    app.state.monthly_report_service = monthly_report_service
    app.state.user_service = user_service
    app.state.auth_token_service = auth_token_service
    app.state.password_reset_service = password_reset_service
    app.state.stripe_service = stripe_service

    logger.info("Copilote financier démarré — version %s", _VERSION)
    yield

    if tracer:
        tracer.shutdown()
    await db_pool.close()
    await rag_client.close()
    await redis_pool.aclose()


app = FastAPI(
    title="Copilote Financier IA",
    version=_VERSION,
    description="API d'analyse financière multi-skills basée sur Claude",
    lifespan=lifespan,
)

_api_key_env = os.environ.get("API_KEY", "")
_redis_url_env = os.environ.get("REDIS_URL", "redis://redis:6379/0")

_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _resolve_cors_origins() -> list[str]:
    """Origines CORS autorisées ; fail-fast en production si non configurées.

    Un `CORS_ORIGINS` vide en production retomberait sur localhost avec
    `allow_credentials=True` — origines de dev acceptées sur un déploiement réel.
    Le repli localhost n'est donc toléré qu'en dev/test ; sinon RuntimeError au boot.
    """
    raw = os.environ.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if origins:
        return origins
    if is_dev_environment():
        return list(_DEV_CORS_ORIGINS)
    raise RuntimeError(
        "CORS_ORIGINS est obligatoire hors développement. "
        "Définir CORS_ORIGINS (origines séparées par des virgules) ou APP_ENV=dev "
        "pour le développement local."
    )


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(annotations_router)
app.include_router(compare_router)
app.include_router(monthly_report_router)
app.include_router(screener_report_router)
app.include_router(ticker_report_router)
app.include_router(analyze_stream_router)
app.include_router(composite_history_router)
app.include_router(esg_history_router)
app.include_router(backtest_router)
app.include_router(billing_router)
app.include_router(evals_router)
app.include_router(export_router)
app.include_router(extract_router)
app.include_router(performance_router)
app.include_router(preferences_router)
app.include_router(jobs_router)
app.include_router(quota_router)
app.include_router(report_router)
app.include_router(screen_router)
app.include_router(semantic_search_router)
app.include_router(telemetry_router)
app.include_router(usage_router)
app.include_router(watchlist_router)
app.include_router(ws_metrics_router)

# Ordre inversé d'exécution : CSRF → BearerToken → RateLimit → TenantContext dans le
# pipeline. `add_middleware` empile en tête → ajouté EN PREMIER = couche la plus INTERNE,
# donc exécuté en dernier, après que BearerToken a résolu request.state.tenant_id.
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RateLimitMiddleware, redis_url=_redis_url_env)
app.add_middleware(BearerTokenMiddleware, api_key=_api_key_env, redis_url=_redis_url_env)
app.add_middleware(CSRFMiddleware)
_cors_origins = _resolve_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "Accept"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = log_internal_error(
        exc, logger, f"Erreur non gérée sur {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur interne", "correlation_id": correlation_id},
    )


@app.get("/healthz", summary="Vérification de santé du service")
async def healthz(request: Request) -> JSONResponse:
    """Vérifie le statut du service, de PostgreSQL et de Qdrant."""
    checks: dict[str, str] = {"status": "ok", "version": _VERSION}
    status_code = 200

    try:
        await request.app.state.db_pool.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        logger.exception("PostgreSQL indisponible lors du healthz")
        checks["postgres"] = "error"
        checks["status"] = "degraded"
        status_code = 503

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{request.app.state.qdrant_url}/healthz")
            checks["qdrant"] = "ok" if resp.status_code == 200 else "error"
            if resp.status_code != 200:
                checks["status"] = "degraded"
                status_code = 503
    except Exception:
        logger.exception("Qdrant indisponible lors du healthz")
        checks["qdrant"] = "error"
        checks["status"] = "degraded"
        status_code = 503

    return JSONResponse(content=checks, status_code=status_code)


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Lance le workflow company_analysis",
    description=(
        "Phase 3 : exécute graham_analysis, puis earnings_quality si earnings_ratios fournis, "
        "puis dorsey_moat si dorsey_ratios fournis, "
        "puis buffett_quality si buffett_ratios fournis, "
        "puis stock_valuation_triangulation si valuation_ratios fournis, "
        "puis investment_thesis_builder si thesis_ratios=true, "
        "puis munger_mental_models si munger_ratios=true (nécessite thesis_ratios=true), "
        "puis canadian_tax_considerations si tax_input fourni. "
        "Les ratios financiers doivent être fournis manuellement par l'utilisateur."
    ),
)
async def analyze(request: Request, body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Exécute le workflow company_analysis sur le ticker et les ratios fournis.
    Retourne une analyse complète selon les paramètres présents.
    """
    orchestrator: Orchestrator = request.app.state.orchestrator
    cache = getattr(request.app.state, "analysis_cache", None)
    observability = getattr(request.app.state, "observability", None)
    composite_history_service = getattr(request.app.state, "composite_history_service", None)
    esg_history_service = getattr(request.app.state, "esg_history_service", None)
    quota_service: QuotaService | None = getattr(request.app.state, "quota_service", None)

    # Borne dure : refuse AVANT tout travail si le quota mensuel est atteint (429).
    if quota_service is not None:
        try:
            await quota_service.check()
        except QuotaExceededError as err:
            raise quota_exceeded_http(err) from err
    try:
        response = await orchestrator.run_company_analysis(
            body, cache=cache, observability=observability,
            composite_history_service=composite_history_service,
            esg_history_service=esg_history_service,
        )
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de l'analyse de {body.ticker}"
        ) from exc
    # Un cache hit (Redis ou composite) ne consomme rien : cost_usd=0 → on n'incrémente pas
    # (cohérent avec le metering Sprint 166 qui n'émet rien pour cost_usd=0).
    if quota_service is not None and response.cost_usd > 0:
        await quota_service.increment()
    return response


def _parse_tags_param(tags: str | None) -> list[str] | None:
    """CSV `value,growth` → liste nettoyée ; None si absent, 422 si présent mais vide.

    Met en minuscules pour s'aligner sur la normalisation à la création (sinon le
    filtre `@>` sensible à la casse ne matcherait jamais un tag saisi en majuscules).
    """
    if tags is None:
        return None
    cleaned = [t.strip().lower() for t in tags.split(",") if t.strip()]
    if not cleaned:
        raise HTTPException(status_code=422, detail="tags : au moins un tag non vide requis")
    return cleaned


@app.get(
    "/history",
    response_model=HistoryResponse,
    summary="Historique des analyses par ticker ou recherche full-text",
)
async def history(
    request: Request,
    ticker: str | None = None,
    q: str | None = None,
    limit: int = 10,
    before: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    tags: str | None = None,
) -> HistoryResponse:
    """
    Retourne les analyses passées (max 50 par page).
    - `ticker`  : filtre exact sur le ticker (ex. BNS).
    - `q`       : recherche ILIKE sur ticker partiel, workflow et verdicts.
    - `from_dt` : borne inférieure ISO 8601 sur created_at (ex. 2026-01-01).
    - `to_dt`   : borne supérieure ISO 8601 sur created_at (ex. 2026-05-18).
    Au moins un des deux paramètres ticker ou q est obligatoire.
    `before` : cursor ISO 8601 pour la pagination (valeur de `next_before`).
    - `tags`  : filtre CSV (ex. `value,growth`) — analyses dont l'annotation porte TOUS ces tags.
    """
    if not ticker and not q:
        raise HTTPException(status_code=422, detail="ticker ou q est obligatoire")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="limit doit être entre 1 et 50")
    tags_parsed = _parse_tags_param(tags)

    before_dt: datetime | None = None
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(status_code=422, detail="before : format ISO 8601 requis")

    from_dt_parsed: datetime | None = None
    if from_dt:
        try:
            from_dt_parsed = datetime.fromisoformat(from_dt)
        except ValueError:
            raise HTTPException(status_code=422, detail="from_dt : format ISO 8601 requis (ex. 2026-01-01)")

    to_dt_parsed: datetime | None = None
    if to_dt:
        try:
            to_dt_parsed = datetime.fromisoformat(to_dt)
        except ValueError:
            raise HTTPException(status_code=422, detail="to_dt : format ISO 8601 requis (ex. 2026-05-18)")

    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_history(
        ticker=ticker,
        q=q,
        limit=limit,
        before=before_dt,
        from_dt=from_dt_parsed,
        to_dt=to_dt_parsed,
        tags=tags_parsed,
    )


@app.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Métriques agrégées sur la période",
)
async def metrics(
    request: Request,
    days: int = 30,
) -> MetricsResponse:
    """
    Retourne les métriques d'utilisation depuis analysis_history.
    - `days` : fenêtre de temps en jours (défaut 30, max 365)
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days doit être entre 1 et 365")
    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_metrics(days=days)


@app.get(
    "/metrics/skill-analyses",
    response_model=SkillAnalysesResponse,
    summary="Analyses ayant utilisé un skill donné (drill-down Sprint 112)",
)
async def metrics_skill_analyses(
    request: Request,
    skill: str = Query(..., min_length=1, max_length=100),
    days: int = 30,
) -> SkillAnalysesResponse:
    """
    Liste les analyses ayant utilisé `skill` sur la période (drill-down du camembert coût).
    - `skill` : identifiant du skill (ex: `graham_analysis`)
    - `days` : fenêtre de temps en jours (défaut 30, max 365)
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days doit être entre 1 et 365")
    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_skill_analyses(skill=skill, days=days)


@app.get(
    "/history-paged",
    response_model=PagedHistoryResponse,
    summary="Historique des analyses avec pagination offset/limit (Sprint 90)",
)
async def history_paged(
    request: Request,
    ticker: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 10,
    from_dt: str | None = None,
    to_dt: str | None = None,
    fast_count: bool = False,
    tags: str | None = None,
) -> PagedHistoryResponse:
    """
    Retourne les analyses passees avec pagination par numero de page.
    - `page`      : numero de page (>=1)
    - `page_size` : nombre d'entrees par page (1-50)
    - `ticker`    : filtre exact sur le ticker
    - `q`         : recherche ILIKE full-text
    - `from_dt`, `to_dt` : plage ISO 8601 sur created_at
    - `tags`      : filtre CSV (ex. `value,growth`) — analyses dont l'annotation porte TOUS ces tags
    """
    if not ticker and not q:
        raise HTTPException(status_code=422, detail="ticker ou q est obligatoire")
    if page < 1:
        raise HTTPException(status_code=422, detail="page doit etre >= 1")
    if page_size < 1 or page_size > 50:
        raise HTTPException(status_code=422, detail="page_size doit etre entre 1 et 50")
    tags_parsed = _parse_tags_param(tags)

    from_dt_parsed: datetime | None = None
    if from_dt:
        try:
            from_dt_parsed = datetime.fromisoformat(from_dt)
        except ValueError:
            raise HTTPException(status_code=422, detail="from_dt : format ISO 8601 requis")

    to_dt_parsed: datetime | None = None
    if to_dt:
        try:
            to_dt_parsed = datetime.fromisoformat(to_dt)
        except ValueError:
            raise HTTPException(status_code=422, detail="to_dt : format ISO 8601 requis")

    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_history_paged(
        ticker=ticker,
        q=q,
        page=page,
        page_size=page_size,
        from_dt=from_dt_parsed,
        to_dt=to_dt_parsed,
        fast_count=fast_count,
        tags=tags_parsed,
    )


@app.delete(
    "/history/{analysis_id}",
    status_code=204,
    summary="Supprimer une analyse (admin uniquement)",
)
async def delete_history(
    analysis_id: UUID,
    request: Request,
    _admin: _ApiKeyRecord | None = Depends(_require_admin),
) -> Response:
    """
    Supprime une analyse de l'historique et son annotation éventuelle.
    Retourne 204 si supprimée, 404 si introuvable.
    L'UUID invalide retourne 422 automatiquement via la validation FastAPI.
    """
    orchestrator: Orchestrator = request.app.state.orchestrator
    deleted = await orchestrator.delete_analysis(str(analysis_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return Response(status_code=204)


@app.get("/alerts", summary="Historique des alertes Celery (Sprint 99)")
async def get_alerts(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Retourne les N dernières alertes enregistrées par les workers Celery."""
    service = request.app.state.alert_history_service
    return {"alerts": await service.get_recent(limit)}
