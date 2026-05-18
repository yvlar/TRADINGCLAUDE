"""Fixtures partagées entre tous les modules de test."""
from __future__ import annotations

import os
import uuid
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.screen import ScreenEntry, ScreenResult
from app.api.main import app
from app.services.observability import CacheStats, CostSummary, DailyCost, LatencyStats, ObservabilityService
from app.orchestrator.core import (
    AnalyzeRequest,
    AnalyzeResponse,
    HistoryResponse,
    MetricsResponse,
)
from app.rag.service import RagService
from app.skills.base import Citation
from app.skills.tier2.earnings_quality.schemas import (
    CScoreDetail,
    CScoreSignal,
    EarningsQualityInput,
    EarningsQualityOutput,
    EarningsQualityRatios,
    FScoreCriterion,
    FScoreDetail,
    GrahamContext,
    MScoreDetail,
    SloanDetail,
    ZScoreDetail,
)
from app.skills.tier2.graham_analysis.schemas import (
    GrahamAnalysisOutput,
    GrahamCriterion,
    GrahamRatios,
)
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill


def _make_criteria_defensif(scores: list[bool] | None = None) -> list[GrahamCriterion]:
    """Construit exactement 8 GrahamCriterion pour les tests."""
    noms = [
        "Taille suffisante",
        "Solidité financière",
        "Stabilité des bénéfices",
        "Historique de dividendes",
        "Croissance des bénéfices",
        "P/E modéré",
        "P/B modéré",
        "Règle combinée P/E × P/B",
    ]
    if scores is None:
        scores = [False] * 8
    return [
        GrahamCriterion(
            numero=i + 1,
            nom=noms[i],
            passe=scores[i],
            valeur_observee="test",
            seuil="seuil Graham",
            commentaire="commentaire de test",
        )
        for i in range(8)
    ]


def _make_criteria_entreprenant(scores: list[bool] | None = None) -> list[GrahamCriterion]:
    """Construit exactement 5 GrahamCriterion entreprenant pour les tests."""
    noms = [
        "Solidité financière (assouplie)",
        "Stabilité (5 ans)",
        "Dividende quelconque",
        "Croissance positive (5 ans)",
        "Prix vs actifs tangibles",
    ]
    if scores is None:
        scores = [False] * 5
    return [
        GrahamCriterion(
            numero=i + 1,
            nom=noms[i],
            passe=scores[i],
            valeur_observee="test",
            seuil="seuil entreprenant",
            commentaire="commentaire de test",
        )
        for i in range(5)
    ]


def _make_f_criteria(scores: list[bool]) -> list[FScoreCriterion]:
    """Génère exactement 9 FScoreCriterion."""
    noms = [
        "ROA > 0",
        "CFO > 0",
        "ROA en hausse",
        "CFO > bénéfice net",
        "Désendettement",
        "Current ratio en hausse",
        "Pas d'émission d'actions",
        "Marge brute en hausse",
        "Asset turnover en hausse",
    ]
    return [
        FScoreCriterion(nom=noms[i], passe=scores[i], detail="test")
        for i in range(9)
    ]


def _make_c_signaux(present: list[bool]) -> list[CScoreSignal]:
    """Génère exactement 6 CScoreSignal."""
    noms = [
        "Divergence NI-CFO",
        "DSO en hausse",
        "DIO en hausse",
        "Autres actifs courants",
        "Dépréciation réduite",
        "Émission d'actions",
    ]
    return [
        CScoreSignal(nom=noms[i], present=present[i], detail="test")
        for i in range(6)
    ]


@pytest.fixture
def ratios_msft() -> GrahamRatios:
    """Ratios MSFT — action de croissance qui échoue les critères Graham."""
    return GrahamRatios(
        pe=34.2,
        pb=12.1,
        current_ratio=1.34,
        debt_equity=0.28,
        eps_growth_10y=0.85,
        price=420.0,
        book_value=35.0,
    )


@pytest.fixture
def ratios_bns() -> GrahamRatios:
    """Ratios BNS — banque canadienne, current_ratio None, candidat Graham solide."""
    return GrahamRatios(
        pe=11.0,
        pb=1.3,
        current_ratio=None,
        debt_equity=0.45,
        eps_growth_10y=0.27,
        price=80.0,
        book_value=61.5,
        eps_ttm=7.25,
        revenue_bn=38.0,
        dividend_years=190,
        no_deficit_years=10,
    )


@pytest.fixture
def ratios_earnings_msft() -> EarningsQualityRatios:
    """Ratios états financiers MSFT pour le skill earnings_quality."""
    return EarningsQualityRatios(
        sales_t=211_915_000_000,
        sales_t1=198_270_000_000,
        cogs_t=74_114_000_000,
        cogs_t1=65_863_000_000,
        net_income_t=72_361_000_000,
        cfo_t=87_582_000_000,
        ebit_t=88_523_000_000,
        receivables_t=48_688_000_000,
        receivables_t1=44_261_000_000,
        current_assets_t=184_257_000_000,
        current_liabilities_t=95_082_000_000,
        total_assets_t=512_163_000_000,
        total_assets_t1=484_275_000_000,
        retained_earnings_t=118_848_000_000,
        total_liabilities_t=205_753_000_000,
        market_cap_t=3_100_000_000_000,
        book_equity_t=206_223_000_000,
        ltd_t=49_800_000_000,
        sga_t=24_456_000_000,
        sga_t1=22_759_000_000,
        depreciation_t=13_900_000_000,
        depreciation_t1=12_900_000_000,
    )


@pytest.fixture
def graham_output_msft() -> GrahamAnalysisOutput:
    """GrahamAnalysisOutput valide pour MSFT — verdict REJETER."""
    return GrahamAnalysisOutput(
        ticker="MSFT",
        profil_applique="LES_DEUX",
        defensive_score=2,
        enterprising_score=2,
        criteria_defensif=_make_criteria_defensif(
            [False, False, True, False, True, False, False, False]
        ),
        criteria_entreprenant=_make_criteria_entreprenant(
            [False, True, False, True, False]
        ),
        valeur_intrinseque_simple=245.70,
        valeur_intrinseque_ajustee=216.22,
        marge_securite=-0.9437,
        drapeaux_rouges=[
            "P/E élevé (34.2 > 25) : prime de croissance importante",
            "P/B très élevé (12.1 > 5) : déconnexion sévère de la valeur comptable",
        ],
        verdict="REJETER",
        verdict_detail=(
            "MSFT ne passe que 2/8 critères défensifs. "
            "P/E et P/B très supérieurs aux seuils Graham. "
            "L'entreprise mérite une évaluation via buffett-quality-investing."
        ),
        recommandation_prochaine_etape=[
            "buffett-quality-investing",
            "damodaran-narrative-and-numbers",
        ],
        citations=[],
        cost_usd=0.002341,
    )


@pytest.fixture
def earnings_output_msft() -> EarningsQualityOutput:
    """EarningsQualityOutput valide pour MSFT — verdict AUCUN_SIGNAL."""
    return EarningsQualityOutput(
        ticker="MSFT",
        is_financial=False,
        m_score=MScoreDetail(
            dsri=None,
            gmi=None,
            aqi=None,
            sgi=1.07,
            depi=None,
            sgai=None,
            tata=-0.028,
            lvgi=None,
            m_score=None,
            interpretation="DONNÉES_MANQUANTES",
        ),
        z_score=ZScoreDetail(
            variante="Z_original",
            z_score=4.12,
            interpretation="zone_sure",
        ),
        f_score=FScoreDetail(
            criteria=_make_f_criteria([True] * 8 + [False]),
            f_score=8,
            interpretation="forte_qualite",
        ),
        c_score=CScoreDetail(
            signaux=_make_c_signaux([False] * 6),
            c_score=0,
            interpretation="propre",
        ),
        sloan=SloanDetail(accrual_ratio=-0.029, interpretation="qualite_elevee"),
        drapeaux_rouges=[],
        verdict="AUCUN_SIGNAL",
        verdict_detail="Aucun signal de manipulation ou de détresse.",
        recommandation_prochaine_etape=["dorsey_moat", "buffett_quality"],
    )


@pytest.fixture
def analyze_response_msft(graham_output_msft: GrahamAnalysisOutput) -> AnalyzeResponse:
    """AnalyzeResponse complète pour MSFT utilisée dans les tests API."""
    return AnalyzeResponse(
        analysis_id=str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000")),
        ticker="MSFT",
        workflow="company_analysis",
        skills_applied=["graham_analysis"],
        graham=graham_output_msft,
        earnings_quality=None,
        cost_usd=0.002341,
        created_at="2026-05-07T14:32:00+00:00",
    )


@pytest.fixture
def mock_usage_no_cache() -> SimpleNamespace:
    """Objet usage Anthropic simulé — premier appel, pas de cache hit."""
    return SimpleNamespace(
        input_tokens=1000,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=1500,
    )


@pytest.fixture
def mock_usage_cache_hit() -> SimpleNamespace:
    """Objet usage Anthropic simulé — cache hit sur le system prompt."""
    return SimpleNamespace(
        input_tokens=50,
        output_tokens=200,
        cache_read_input_tokens=1500,
        cache_creation_input_tokens=0,
    )


@pytest.fixture
def mock_rag_service() -> RagService:
    """RagService mocké retournant une citation de test."""
    service = AsyncMock(spec=RagService)
    service.search.return_value = [
        Citation(
            source="graham-stock-screening/references/graham-defensif.md",
            extrait="## Les 8 critères\nL'investisseur défensif applique 8 critères stricts.",
            score=0.91,
        )
    ]
    return service


@pytest.fixture
def mock_rag_service_vide() -> RagService:
    """RagService mocké retournant une liste vide (RAG désactivé)."""
    service = AsyncMock(spec=RagService)
    service.search.return_value = []
    return service


@pytest.fixture
def skill_avec_mock_client(graham_output_msft: GrahamAnalysisOutput) -> GrahamAnalysisSkill:
    """Skill dont le client Anthropic est entièrement mocké, sans RAG."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = graham_output_msft.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=1500,
    )

    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_response

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    return GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", rag_service=None)


@pytest.fixture
def skill_avec_mock_client_et_rag(
    graham_output_msft: GrahamAnalysisOutput,
    mock_rag_service: RagService,
) -> GrahamAnalysisSkill:
    """Skill dont le client Anthropic et le RagService sont mockés."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = graham_output_msft.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=1500,
    )

    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_response

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    return GrahamAnalysisSkill(
        client=mock_client,
        model="claude-sonnet-4-6",
        rag_service=mock_rag_service,
    )


# ---------------------------------------------------------------------------
# Fixtures Sprint 13 — client d'intégration + mock Claude
# ---------------------------------------------------------------------------

_SKILL_PROMPT_PATCHES = [
    "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
    "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
    "app.skills.tier2.dorsey_moat.skill.DorseyMoatSkill._load_system_prompt",
    "app.skills.tier2.buffett_quality.skill.BuffettQualitySkill._load_system_prompt",
    "app.skills.tier2.stock_valuation.skill.StockValuationSkill._load_system_prompt",
    "app.skills.tier2.thesis_builder.skill.ThesisBuilderSkill._load_system_prompt",
    "app.skills.tier2.munger_mental.skill.MungerMentalSkill._load_system_prompt",
    "app.skills.tier2.canadian_tax.skill.CanadianTaxSkill._load_system_prompt",
    "app.skills.tier2.lynch_categories.skill.LynchCategoriesSkill._load_system_prompt",
    "app.skills.tier2.fisher_scuttlebutt.skill.FisherScuttlebuttSkill._load_system_prompt",
    "app.skills.tier2.klarman_margin.skill.KlarmanMarginSkill._load_system_prompt",
    "app.skills.tier2.greenblatt.skill.GreenblattSkill._load_system_prompt",
    "app.skills.tier2.damodaran_narrative.skill.DamodararNarrativeSkill._load_system_prompt",
    "app.skills.tier2.marks_cycles.skill.MarksCyclesSkill._load_system_prompt",
    "app.skills.tier2.pabrai_dhandho.skill.PabraiDhandhoSkill._load_system_prompt",
]


@pytest_asyncio.fixture
async def client(analyze_response_msft: AnalyzeResponse):
    """Client HTTP sans infrastructure réelle — orchestrateur et dépendances mockés."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis.return_value = analyze_response_msft
    mock_orchestrator.get_history.return_value = HistoryResponse(
        ticker="TEST", entries=[], next_before=None
    )
    mock_orchestrator.get_metrics.return_value = MetricsResponse(
        period_days=30,
        total_analyses=0,
        total_cost_usd=0.0,
        avg_cost_per_analysis=0.0,
        cache_hit_ratio_avg=0.0,
        top_tickers=[],
        skills_usage={},
    )

    mock_rag_client = AsyncMock()
    mock_rag_client.ensure_collection = AsyncMock()
    mock_rag_client.close = AsyncMock()

    mock_qdrant_resp = MagicMock()
    mock_qdrant_resp.status_code = 200
    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.get.return_value = mock_qdrant_resp
    mock_qdrant_ctx = AsyncMock()
    mock_qdrant_ctx.__aenter__.return_value = mock_qdrant_client
    mock_qdrant_ctx.__aexit__.return_value = None

    mock_redis_pool = AsyncMock()
    mock_redis_pool.incr = AsyncMock(return_value=1)
    mock_redis_pool.expire = AsyncMock(return_value=True)
    mock_redis_pool.get = AsyncMock(return_value=None)
    mock_redis_pool.set = AsyncMock(return_value=True)
    mock_redis_pool.aclose = AsyncMock()
    mock_redis_pool.keys = AsyncMock(return_value=[])
    mock_redis_pool.delete = AsyncMock(return_value=0)
    mock_redis_pool.lpush = AsyncMock(return_value=1)
    mock_redis_pool.ltrim = AsyncMock(return_value=True)
    mock_redis_pool.lrange = AsyncMock(return_value=[])

    mock_yahoo = AsyncMock()
    mock_yahoo.extract = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Ticker inconnu")
    )

    mock_analysis_cache = AsyncMock()
    mock_analysis_cache.get = AsyncMock(return_value=None)
    mock_analysis_cache.set = AsyncMock(return_value=None)
    mock_analysis_cache.invalidate = AsyncMock(return_value=0)

    mock_screener = AsyncMock()
    mock_screener.screen = AsyncMock(
        return_value=ScreenResult(
            tickers_analyses=1,
            tickers_echec=0,
            tickers_depuis_cache=0,
            cout_total_usd=0.002341,
            resultats=[
                ScreenEntry(
                    ticker="MSFT",
                    defensive_score=2,
                    verdict="REJETER",
                    workflow_utilise="value_graham",
                    cost_usd=0.002341,
                    depuis_cache=False,
                    erreur=None,
                )
            ],
            workflow="value_graham",
            duration_ms=1234,
        )
    )

    env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, env_vars))
        mock_pool = stack.enter_context(
            patch("asyncpg.create_pool", new_callable=AsyncMock)
        )
        mock_pool.return_value = AsyncMock()
        mock_pool.return_value.close = AsyncMock()
        mock_pool.return_value.fetchval = AsyncMock(return_value=1)
        stack.enter_context(
            patch("anthropic.AsyncAnthropic", return_value=MagicMock())
        )
        stack.enter_context(
            patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx)
        )
        stack.enter_context(
            patch("app.api.main.RagClient", return_value=mock_rag_client)
        )
        stack.enter_context(
            patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool)
        )
        for prompt_path in _SKILL_PROMPT_PATCHES:
            stack.enter_context(patch(prompt_path, return_value="prompt de test"))

            mock_obs = AsyncMock(spec=ObservabilityService)
        mock_obs.get_cost_summary.return_value = CostSummary(
            cost_total_usd=0.0,
            cost_par_jour=[],
            analyses_count=0,
        )
        mock_obs.get_cache_stats.return_value = CacheStats(
            hits=0, misses=0, hit_ratio=0.0, keys_count=0
        )
        mock_obs.get_latency_p95.return_value = LatencyStats(
            skill_id=None, p50_ms=None, p95_ms=None, p99_ms=None, sample_count=0
        )
        mock_obs.check_cost_alert.return_value = False

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            app.state.orchestrator = mock_orchestrator
            app.state.db_pool = mock_pool.return_value
            app.state.qdrant_url = "http://qdrant:6333"
            app.state.redis_pool = mock_redis_pool
            app.state.yahoo_extractor = mock_yahoo
            app.state.analysis_cache = mock_analysis_cache
            app.state.screener = mock_screener
            app.state.observability = mock_obs
            yield c


@pytest.fixture
def mock_claude_graham(graham_output_msft: GrahamAnalysisOutput):
    """Patch anthropic.AsyncAnthropic → messages.create retourne un GrahamAnalysisOutput via tool_use."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = graham_output_msft.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=200,
    )
    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_response
    mock_client_instance = MagicMock()
    mock_client_instance.messages = mock_messages

    with patch("anthropic.AsyncAnthropic", return_value=mock_client_instance):
        yield mock_client_instance


@pytest_asyncio.fixture
async def db_cleanup(client):
    """Nettoyage post-test — no-op avec orchestrateur mocké (pas de vraie DB)."""
    yield


# ---------------------------------------------------------------------------
# Fixtures Sprint 18 — ObservabilityService avec FakeRedis dédié
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_obs_redis():
    """FakeRedis dédié à ObservabilityService — namespace séparé des autres mocks."""
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def obs_service(mock_obs_redis):
    """ObservabilityService avec FakeRedis et sans Langfuse."""
    return ObservabilityService(redis_client=mock_obs_redis, langfuse_client=None)
