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

from app.db.tenant_context import apply_tenant_context
from app.observability.langfuse_client import LangfuseTracer
from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.rag.service import RagService
from app.services.alert_history_service import AlertHistoryService
from app.services.composite_alert import CompositeAlertService
from app.services.email_service import EmailService
from app.services.price_alert_service import PriceAlertService
from app.services.report import ReportService
from app.services.screener import ScreenerService
from app.services.slack_service import SlackService
from app.services.watchlist_service import WatchlistService
from app.services.webhook_service import WebhookService
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


def _score_label(score: float) -> str:
    """Convertit un composite_score en label textuel."""
    if score >= 70:
        return "Fort"
    if score >= 50:
        return "Modéré"
    return "Faible"


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

    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
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

    # Pas de `usage_event_service` ici : les analyses planifiées (screener/alertes) tournent
    # sous le tenant legacy (le threading tenant→worker relève d'un sprint E4 ultérieur) ;
    # les facturer au legacy serait du bruit. Le metering reste donc scopé au chemin requête.
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
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
    yahoo_extractor = YahooFinanceExtractor()
    service = PriceAlertService()
    webhook_service = WebhookService()
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

                # Notification webhook après re-déclenchement des analyses
                price_row = await db_pool.fetchrow(
                    """SELECT last_price_checked, price_alert_threshold_pct
                       FROM watchlist WHERE ticker = $1""",
                    ticker,
                )
                if price_row:
                    await webhook_service.send_price_alert(
                        ticker=ticker,
                        prix=float(price_row["last_price_checked"] or 0.0),
                        seuil=float(price_row["price_alert_threshold_pct"] or 0.10),
                        direction="divergence",
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
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
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
        else:
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

        # Notification webhook résumé hebdomadaire
        alertes_webhook = [
            {"ticker": e.ticker, "score": e.last_score}
            for e in entries
            if e.score_alerte_min is not None
            and e.last_score is not None
            and e.last_score < e.score_alerte_min
        ]
        webhook_service = WebhookService()
        await webhook_service.send_watchlist_summary(
            nb_positions=len(entries),
            alertes=alertes_webhook,
        )
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


async def _execute_composite_alert_check() -> list[str]:
    """
    Verifie les alertes composite_score pour toutes les entrees watchlist avec baseline.
    Relance l'analyse via l'orchestrateur, compare vs la baseline, envoie un email si derive.
    Retourne la liste des tickers qui ont declenche une alerte.
    """
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
    try:
        orchestrator, _ = await _build_orchestrator()
        watchlist_service = WatchlistService(db_pool)

        email_service: EmailService | None = None
        email_to = os.environ.get("REPORT_EMAIL_TO")
        smtp_host = os.environ.get("SMTP_HOST")
        if email_to and smtp_host:
            email_service = EmailService()

        alert_service = CompositeAlertService(
            watchlist_service=watchlist_service,
            orchestrator=orchestrator,
            email_service=email_service,
            email_to=email_to,
        )

        resultats = await alert_service.check_composite_alerts()
        alertes = [r.ticker for r in resultats if r.alerte_declenchee]

        # Notifications webhook pour chaque alerte composite déclenchée
        webhook_service = WebhookService()
        for r in resultats:
            if r.alerte_declenchee:
                await webhook_service.send_composite_alert(
                    ticker=r.ticker,
                    score=r.new_score,
                    label=_score_label(r.new_score),
                )

        return alertes
    finally:
        await db_pool.close()


async def _execute_eval_drift_check(dataset: str) -> dict:
    """Lance EvalDriftService.run_eval() et persist le résultat dans Redis."""
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    import redis.asyncio as aioredis

    from app.services.eval_drift_service import EvalDriftService

    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        svc = EvalDriftService(redis_client=redis_client)
        result = await svc.run_eval(dataset)
        await svc.record_result(result)
        return result.model_dump(mode="json")
    finally:
        await redis_client.aclose()


@celery_app.task(name="run_eval_drift_check", bind=True)
def run_eval_drift_check(self, dataset: str = "graham") -> dict:
    """
    Tâche Celery — exécute le golden dataset et enregistre le résultat dans Redis.
    Déclenchable manuellement ou en cron pour détecter les régressions de qualité IA.
    """
    logger.info("Début eval drift check — dataset=%s", dataset)
    result = asyncio.run(_execute_eval_drift_check(dataset))
    logger.info(
        "Fin eval drift check — dataset=%s concordance=%.1f%% alerte=%s",
        dataset,
        result.get("concordance_rate", 0.0) * 100,
        result.get("alert"),
    )
    return result


@celery_app.task(name="run_composite_alert_check", bind=True)
def run_composite_alert_check(self) -> None:
    """
    Tache Celery -- verification quotidienne des alertes composite_score watchlist.
    Planifiee chaque jour a 10h00 UTC via Celery beat.
    """
    logger.info("Debut verification quotidienne alertes composite watchlist")
    alertes = asyncio.run(_execute_composite_alert_check())
    logger.info(
        "Fin verification alertes composite -- %d alerte(s) declenchee(s)", len(alertes)
    )


async def _execute_scheduled_screener() -> dict:
    """Screene tous les tickers watchlist et envoie les opportunités FORT par webhook."""
    from app.api.endpoints.screen import ScreenRequest

    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
    orch_pool: asyncpg.Pool | None = None
    try:
        wl_service = WatchlistService(db_pool)
        entries = await wl_service.list_entries()

        if not entries:
            logger.info("Screener planifié ignoré — watchlist vide")
            return {"nb_tickers_screenes": 0, "nb_opportunites": 0, "tickers_fort": []}

        tickers = [e.ticker for e in entries]
        logger.info("Screener planifié — %d ticker(s) à analyser", len(tickers))

        orchestrator, orch_pool = await _build_orchestrator()
        extractor = YahooFinanceExtractor()
        screener = ScreenerService(orchestrator=orchestrator, extractor=extractor)

        all_screen_entries = []
        for i in range(0, len(tickers), 20):
            batch = tickers[i : i + 20]
            try:
                req = ScreenRequest(tickers=batch, min_composite_score=70)
                result = await screener.screen(req)
                all_screen_entries.extend(result.resultats)
            except Exception:
                logger.exception("Erreur screener pour le batch %s", batch)

        fort_entries = [
            e
            for e in all_screen_entries
            if e.erreur is None
            and (
                e.composite_label == "FORT"
                or (e.defensive_score is not None and e.defensive_score >= 5)
            )
        ]
        tickers_fort = [e.ticker for e in fort_entries]

        from types import SimpleNamespace

        # SimpleNamespace évite la validation Pydantic sur des entrées hétérogènes
        nb_echec = sum(1 for e in all_screen_entries if getattr(e, "erreur", None))
        screen_result = SimpleNamespace(
            tickers_analyses=len(all_screen_entries) - nb_echec,
            tickers_echec=nb_echec,
            tickers_depuis_cache=sum(1 for e in all_screen_entries if getattr(e, "depuis_cache", False)),
            cout_total_usd=0.0,
            resultats=all_screen_entries,
            workflow="value_graham",
            duration_ms=0,
        )

        webhook_service = WebhookService()
        alert_history_service = AlertHistoryService(db_pool)
        if tickers_fort:
            await webhook_service.send_screener_report(
                nb_tickers_screenes=len(tickers),
                tickers_fort=tickers_fort,
            )
            logger.info(
                "Screener planifié — %d opportunité(s) FORT notifiée(s) par webhook JSON",
                len(tickers_fort),
            )
            for e in fort_entries:
                try:
                    await alert_history_service.record(
                        ticker=e.ticker,
                        type="SCREENER_FORT",
                        valeur=float(e.composite_score) if e.composite_score is not None else None,
                        seuil=70.0,
                        message=f"Screener hebdomadaire — composite_label={e.composite_label}",
                    )
                except Exception:
                    logger.warning(
                        "Impossible d'enregistrer l'alerte screener FORT dans alert_history pour %s",
                        e.ticker,
                    )

        # Envoi du rapport PDF en plus du JSON (optionnel — no-op si WEBHOOK_URL absent)
        await webhook_service.send_screener_pdf_report(screen_result)

        # Alertes ESG — vérification des scores ESG stockés vs seuils par entrée watchlist
        nb_alertes_esg = 0
        for entry in entries:
            if (
                entry.last_esg_score is not None
                and entry.last_esg_score < entry.esg_alert_threshold
            ):
                sent = await webhook_service.send_esg_alert(
                    ticker=entry.ticker,
                    esg_score=entry.last_esg_score,
                    threshold=entry.esg_alert_threshold,
                )
                if sent:
                    nb_alertes_esg += 1
                    logger.warning(
                        "Alerte ESG — %s : score %.1f < seuil %.1f",
                        entry.ticker, entry.last_esg_score, entry.esg_alert_threshold,
                    )
        if nb_alertes_esg:
            logger.info("Screener planifié — %d alerte(s) ESG envoyée(s)", nb_alertes_esg)

        if not tickers_fort:
            logger.info("Screener planifié — aucune opportunité FORT identifiée")

        # Résumé Slack (no-op si SLACK_WEBHOOK_URL absent)
        slack_service = SlackService()
        await slack_service.send_screener_summary(
            nb_analyses=len(tickers),
            nb_fort=len(tickers_fort),
            cout_usd=screen_result.cout_total_usd,
        )

        return {
            "nb_tickers_screenes": len(tickers),
            "nb_opportunites": len(tickers_fort),
            "tickers_fort": tickers_fort,
        }
    finally:
        await db_pool.close()
        if orch_pool is not None:
            await orch_pool.close()


async def _execute_monthly_report() -> None:
    """Génère le rapport PDF mensuel et l'envoie par webhook et/ou Slack."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    slack_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url and not slack_url:
        logger.info("WEBHOOK_URL et SLACK_WEBHOOK_URL absents — rapport mensuel ignoré")
        return

    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
    try:
        from app.services.monthly_report_service import MonthlyReportService
        from app.services.screener_pdf_service import ScreenerPdfService
        from app.services.watchlist_pdf_service import WatchlistPdfService
        from app.services.watchlist_service import WatchlistService

        monthly_service = MonthlyReportService()
        watchlist_pdf_service = WatchlistPdfService()
        screener_pdf_service = ScreenerPdfService()
        watchlist_service = WatchlistService(db_pool)

        try:
            watchlist_pdf, screener_pdf = await monthly_service.generate(
                db_pool=db_pool,
                watchlist_pdf_service=watchlist_pdf_service,
                screener_pdf_service=screener_pdf_service,
                watchlist_service=watchlist_service,
            )
        except ValueError:
            logger.info("Rapport mensuel ignoré — watchlist vide")
            return

        webhook_service = WebhookService()
        sent = await webhook_service.send_monthly_report(watchlist_pdf, screener_pdf)
        if sent:
            logger.info("Rapport mensuel envoyé par webhook")
        else:
            logger.warning("Rapport mensuel non envoyé (échec WebhookService)")

        # Résumé Slack (no-op si SLACK_WEBHOOK_URL absent)
        slack_service = SlackService()
        nb_positions = int(await db_pool.fetchval("SELECT COUNT(*) FROM watchlist") or 0)
        await slack_service.send_monthly_report_summary(nb_positions=nb_positions, nb_fort=0)
    finally:
        await db_pool.close()


@celery_app.task(name="run_monthly_report", bind=True)
def run_monthly_report(self) -> None:
    """
    Tâche Celery — rapport PDF mensuel consolidé watchlist + screener FORT.
    Planifiée le 1er du mois à 08h00 UTC via Celery beat.
    No-op si WEBHOOK_URL absent.
    """
    logger.info("Début rapport mensuel automatisé")
    asyncio.run(_execute_monthly_report())
    logger.info("Fin rapport mensuel automatisé")


async def _execute_esg_degradation_check() -> int:
    """Vérifie la dégradation ESG pour toutes les entrées watchlist et envoie les alertes."""
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote"
    )
    db_pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=3, setup=apply_tenant_context
    )
    try:
        from app.services.esg_history_service import EsgHistoryService

        watchlist_service = WatchlistService(db_pool)
        esg_history_service = EsgHistoryService(db_pool)
        alert_history_service = AlertHistoryService(db_pool)
        webhook_service = WebhookService()
        slack_service = SlackService()
        entries = await watchlist_service.list_entries()
        nb_alertes = 0

        for entry in entries:
            if entry.last_esg_score is None:
                continue
            try:
                previous_score = await esg_history_service.get_latest_previous(entry.ticker)
                if WatchlistService.check_esg_degradation(entry, previous_score):
                    await webhook_service.send_esg_alert(
                        ticker=entry.ticker,
                        esg_score=entry.last_esg_score,
                        threshold=entry.esg_alert_threshold,
                    )
                    await slack_service.send_esg_alert(
                        ticker=entry.ticker,
                        score=entry.last_esg_score,
                        threshold=entry.esg_alert_threshold,
                    )
                    nb_alertes += 1
                    logger.warning(
                        "Alerte dégradation ESG — %s : score actuel %.1f, précédent %.1f, seuil %.1f",
                        entry.ticker,
                        entry.last_esg_score,
                        previous_score,
                        entry.esg_alert_threshold,
                    )
                    try:
                        await alert_history_service.record(
                            ticker=entry.ticker,
                            type="ESG_DEGRADATION",
                            valeur=entry.last_esg_score,
                            seuil=entry.esg_alert_threshold,
                            message=(
                                f"Score ESG passé de {previous_score:.1f} à {entry.last_esg_score:.1f}"
                                if previous_score is not None
                                else f"Score ESG {entry.last_esg_score:.1f} sous le seuil {entry.esg_alert_threshold:.1f}"
                            ),
                        )
                    except Exception:
                        logger.warning(
                            "Impossible d'enregistrer l'alerte ESG dans alert_history pour %s",
                            entry.ticker,
                        )
            except Exception:
                logger.exception("Erreur vérification dégradation ESG pour %s", entry.ticker)

        return nb_alertes
    finally:
        await db_pool.close()


@celery_app.task(name="run_esg_degradation_check", bind=True)
def run_esg_degradation_check(self) -> dict:
    """
    Tâche Celery — vérification hebdomadaire des dégradations ESG watchlist.
    Planifiée chaque dimanche à 12h00 UTC (après le screener 11h00 UTC).
    """
    logger.info("Début vérification dégradation ESG watchlist")
    nb_alertes = asyncio.run(_execute_esg_degradation_check())
    logger.info(
        "Fin vérification dégradation ESG — %d alerte(s) déclenchée(s)", nb_alertes
    )
    return {"nb_alertes": nb_alertes}


@celery_app.task(name="run_scheduled_screener", bind=True)
def run_scheduled_screener(self) -> dict:
    """
    Tâche Celery — screener hebdomadaire de la watchlist complète.
    Filtre les opportunités FORT (composite_label="FORT" ou defensive_score >= 5)
    et envoie un rapport via webhook. Planifiée chaque dimanche à 11h00 UTC.
    """
    logger.info("Début screener planifié hebdomadaire")
    result = asyncio.run(_execute_scheduled_screener())
    logger.info(
        "Fin screener planifié — %d ticker(s) analysé(s), %d opportunité(s) FORT",
        result.get("nb_tickers_screenes", 0),
        result.get("nb_opportunites", 0),
    )
    return result
