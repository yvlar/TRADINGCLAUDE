from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic
import asyncpg
import redis

from app.observability.langfuse_client import LangfuseTracer
from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.rag.service import RagService
from app.services.email_service import EmailService
from app.services.price_alert_service import PriceAlertService
from app.services.report import ReportService
from app.services.watchlist_service import WatchlistService
from app.skills.base import SkillConfig
from app.skills.tier1.yahoo_finance import YahooFinanceExtractor
from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
from app.skills.tier2.canadian_tax.skill import CanadianTaxSkill
from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill
from app.skills.tier2.munger_mental.skill import MungerMentalSkill
from app.skills.tier2.stock_valuation.skill import StockValuationSkill
from app.skills.tier2.thesis_builder.skill import ThesisBuilderSkill
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_JOB_TTL = 86400  # 24 heures


def _get_redis() -> redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return redis.from_url(url, decode_responses=True)


async def _build_orchestrator() -> tuple[Orchestrator, asyncpg.Pool]:
    """Crée un Orchestrator avec sa propre pool asyncpg — indépendant du serveur FastAPI."""
    api_key = os.environ["ANTHROPIC_API_KEY"]
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    qdrant_coll = os.environ.get("QDRANT_COLLECTION", "investment_knowledge")
    openai_key = os.environ.get("OPENAI_API_KEY")
    top_k = int(os.environ.get("RAG_TOP_K", "5"))

    db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
    client = anthropic.AsyncAnthropic(api_key=api_key)

    rag_client = RagClient(url=qdrant_url, collection=qdrant_coll)
    await rag_client.ensure_collection()

    rag_service: RagService | None = None
    if openai_key:
        embedder = EmbeddingClient(api_key=openai_key)
        rag_service = RagService(rag_client=rag_client, embedder=embedder)

    tracer: LangfuseTracer | None = None
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if lf_secret:
        tracer = LangfuseTracer(
            secret_key=lf_secret,
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )

    skill_config = SkillConfig(tracer=tracer)

    def _skill(cls):
        return cls(
            client=client,
            model=model,
            config=skill_config,
            rag_service=rag_service,
            top_k=top_k,
        )

    orchestrator = Orchestrator(
        db_pool=db_pool,
        graham_skill=_skill(GrahamAnalysisSkill),
        earnings_skill=_skill(EarningsQualitySkill),
        dorsey_skill=_skill(DorseyMoatSkill),
        buffett_skill=_skill(BuffettQualitySkill),
        valuation_skill=_skill(StockValuationSkill),
        thesis_skill=_skill(ThesisBuilderSkill),
        munger_skill=_skill(MungerMentalSkill),
        canadian_tax_skill=_skill(CanadianTaxSkill),
    )
    return orchestrator, db_pool


async def _execute_analysis(request_dict: dict[str, Any]) -> dict[str, Any]:
    """Exécute l'analyse complète et retourne un dict JSON-sérialisable."""
    orchestrator, db_pool = await _build_orchestrator()
    try:
        request = AnalyzeRequest.model_validate(request_dict)
        response = await orchestrator.run_company_analysis(request)
        return response.model_dump(mode="json")
    finally:
        await db_pool.close()


@celery_app.task(name="run_full_analysis", bind=True, max_retries=3)
def run_full_analysis(self, job_id: str, request_dict: dict[str, Any]) -> None:
    """
    Tâche Celery synchrone qui lance le workflow company_analysis.
    1. Statut Redis → "running"
    2. Orchestrator avec pool asyncpg dédié via asyncio.run()
    3. Résultat dans Redis (TTL 24h)
    4. Statut → "done" ou "failed" (avec retry si échec transitoire)
    """
    r = _get_redis()
    r.set(f"job:{job_id}:status", "running", ex=_JOB_TTL)
    logger.info("Job %s démarré", job_id)

    try:
        result = asyncio.run(_execute_analysis(request_dict))
        r.set(f"job:{job_id}:result", json.dumps(result), ex=_JOB_TTL)
        r.set(f"job:{job_id}:status", "done", ex=_JOB_TTL)
        logger.info("Job %s terminé avec succès", job_id)
    except Exception as exc:
        logger.exception("Erreur lors de l'analyse du job %s", job_id)
        r.set(f"job:{job_id}:error", str(exc), ex=_JOB_TTL)
        r.set(f"job:{job_id}:status", "failed", ex=_JOB_TTL)
        raise self.retry(exc=exc, countdown=30)


async def _execute_watchlist_analysis() -> None:
    """Itère sur toutes les entrées watchlist et déclenche une analyse pour chacune."""
    orchestrator, db_pool = await _build_orchestrator()
    try:
        rows = await db_pool.fetch(
            """
            SELECT id, ticker, workflow, ratios, score_alerte_min
            FROM watchlist
            ORDER BY created_at
            """
        )
        logger.info("Watchlist re-analyse hebdomadaire — %d entrée(s)", len(rows))
        for row in rows:
            entry_id = str(row["id"])
            ticker = row["ticker"]
            workflow = row["workflow"]
            score_alerte_min = row["score_alerte_min"]
            try:
                ratios_raw = row["ratios"]
                ratios: GrahamRatios | None = None
                if ratios_raw:
                    ratios = GrahamRatios.model_validate(
                        json.loads(ratios_raw) if isinstance(ratios_raw, str) else ratios_raw
                    )
                request = AnalyzeRequest(ticker=ticker, workflow=workflow, ratios=ratios)
                response = await orchestrator.run_company_analysis(request)
                last_score = response.graham.defensive_score if response.graham else None
                last_verdict = response.graham.verdict if response.graham else None
                last_intrinsic = (
                    response.graham.valeur_intrinseque_ajustee if response.graham else None
                )
                await db_pool.execute(
                    """
                    UPDATE watchlist
                    SET last_analyzed_at = NOW(), last_score = $2, last_verdict = $3,
                        last_intrinsic_value = $4
                    WHERE id = $1::uuid
                    """,
                    entry_id,
                    last_score,
                    last_verdict,
                    last_intrinsic,
                )
                if (
                    score_alerte_min is not None
                    and last_score is not None
                    and last_score < score_alerte_min
                ):
                    logger.warning(
                        "ALERTE watchlist — %s : score %d < seuil %d (verdict: %s)",
                        ticker, last_score, score_alerte_min, last_verdict,
                    )
                else:
                    logger.info("Watchlist — %s analysé : score=%s, verdict=%s", ticker, last_score, last_verdict)
            except Exception:
                logger.exception("Erreur lors de la re-analyse watchlist pour %s", ticker)
    finally:
        await db_pool.close()


@celery_app.task(name="run_watchlist_analysis", bind=True)
def run_watchlist_analysis(self) -> None:
    """
    Tâche Celery — re-analyse hebdomadaire de toutes les entrées watchlist.
    Planifiée chaque dimanche à 07h00 UTC via Celery beat.
    """
    logger.info("Début re-analyse hebdomadaire watchlist")
    asyncio.run(_execute_watchlist_analysis())
    logger.info("Fin re-analyse hebdomadaire watchlist")


async def _execute_price_alert_check() -> list[str]:
    """
    Vérifie les alertes prix pour toutes les entrées watchlist avec valeur intrinsèque connue.
    Déclenche une re-analyse Celery pour chaque ticker dont l'écart dépasse le seuil.
    """
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
    yahoo_extractor = YahooFinanceExtractor()
    service = PriceAlertService()
    try:
        alerted = await service.check_price_alerts(db_pool, yahoo_extractor)
        if alerted:
            r = _get_redis()
            for ticker in alerted:
                rows = await db_pool.fetch(
                    "SELECT id, workflow, ratios FROM watchlist WHERE ticker = $1",
                    ticker,
                )
                for row in rows:
                    job_id = str(uuid.uuid4())
                    ratios: GrahamRatios | None = None
                    ratios_raw = row["ratios"]
                    if ratios_raw:
                        ratios = GrahamRatios.model_validate(
                            json.loads(ratios_raw)
                            if isinstance(ratios_raw, str)
                            else ratios_raw
                        )
                    request = AnalyzeRequest(
                        ticker=ticker,
                        workflow=row["workflow"],
                        ratios=ratios,
                    )
                    r.set(f"job:{job_id}:status", "pending", ex=_JOB_TTL)
                    run_full_analysis.delay(job_id, request.model_dump(mode="json"))
                    logger.info(
                        "Re-analyse déclenchée — ticker=%s, job=%s (alerte prix)",
                        ticker,
                        job_id,
                    )
        return alerted
    finally:
        await db_pool.close()


@celery_app.task(name="run_price_alert_check", bind=True)
def run_price_alert_check(self) -> None:
    """
    Tâche Celery — vérification quotidienne des alertes prix watchlist.
    Planifiée chaque jour à 08h00 UTC via Celery beat.
    """
    logger.info("Début vérification quotidienne alertes prix watchlist")
    alerted = asyncio.run(_execute_price_alert_check())
    logger.info(
        "Fin vérification alertes prix — %d alerte(s) déclenchée(s)", len(alerted)
    )


async def _execute_weekly_watchlist_report() -> None:
    """
    Génère un rapport PDF récapitulatif de la watchlist et l'envoie par email.
    1. Charge toutes les entrées watchlist depuis PostgreSQL
    2. Si vide → log INFO et return
    3. Génère un PDF via ReportService
    4. Envoie via EmailService vers REPORT_EMAIL_TO
    5. Log INFO avec le nombre de positions
    """
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
    try:
        wl_service = WatchlistService(db_pool)
        entries = await wl_service.list_entries()

        if not entries:
            logger.info("Rapport hebdomadaire ignoré — watchlist vide")
            return

        report_service = ReportService()
        pdf_bytes = report_service.generate_watchlist_summary_pdf(entries)

        email_service = EmailService()
        to = os.environ.get("REPORT_EMAIL_TO", "")
        if not to:
            logger.warning("REPORT_EMAIL_TO non configuré — rapport PDF non envoyé")
            return

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sent = await email_service.send_report(
            subject=f"Rapport watchlist hebdomadaire — {len(entries)} position(s) — {date_str}",
            body_text=(
                f"Bonjour,\n\n"
                f"Voici le rapport hebdomadaire de votre watchlist : {len(entries)} position(s) analysées.\n\n"
                f"Date : {date_str}\n"
                f"Copilote Financier IA"
            ),
            pdf_bytes=pdf_bytes,
            filename=f"watchlist-{date_str}.pdf",
            to=to,
        )
        if sent:
            logger.info("Rapport watchlist hebdomadaire envoyé — %d position(s)", len(entries))
        else:
            logger.warning("Rapport watchlist hebdomadaire non envoyé (échec EmailService)")
    finally:
        await db_pool.close()


@celery_app.task(name="run_weekly_watchlist_report", bind=True)
def run_weekly_watchlist_report(self) -> None:
    """
    Tâche Celery — rapport PDF hebdomadaire de la watchlist par email.
    Planifiée chaque dimanche à 09h00 UTC via Celery beat (après 07h00 + 08h00).
    """
    logger.info("Début rapport hebdomadaire watchlist")
    asyncio.run(_execute_weekly_watchlist_report())
    logger.info("Fin rapport hebdomadaire watchlist")
