"""Tests du cache Redis des analyses — AnalysisCacheService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse
from app.services.analysis_cache import AnalysisCacheService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------

@pytest.fixture
def ratios_bns() -> GrahamRatios:
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
    )


@pytest.fixture
def ratios_bns_alt() -> GrahamRatios:
    """Ratios légèrement différents — même ticker, clé de cache distincte."""
    return GrahamRatios(
        pe=12.0,  # différent
        pb=1.3,
        current_ratio=None,
        debt_equity=0.45,
        eps_growth_10y=0.27,
        price=80.0,
        book_value=61.5,
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.keys = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def cache(mock_redis: AsyncMock) -> AnalysisCacheService:
    return AnalysisCacheService(redis_client=mock_redis, ttl_seconds=3600)


@pytest.fixture
def analyze_response_bns(ratios_bns: GrahamRatios) -> AnalyzeResponse:
    """AnalyzeResponse minimale valide pour BNS."""
    from tests.conftest import (
        _make_criteria_defensif,
        _make_criteria_entreprenant,
    )
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput

    graham = GrahamAnalysisOutput(
        ticker="BNS",
        profil_applique="DEFENSIF",
        defensive_score=6,
        enterprising_score=4,
        criteria_defensif=_make_criteria_defensif([True] * 6 + [False, False]),
        criteria_entreprenant=_make_criteria_entreprenant([True] * 4 + [False]),
        valeur_intrinseque_simple=88.0,
        valeur_intrinseque_ajustee=82.0,
        marge_securite=0.10,
        drapeaux_rouges=[],
        verdict="ACCEPTABLE",
        verdict_detail="BNS passe 6/8 critères défensifs.",
        recommandation_prochaine_etape=["dorsey_moat"],
        citations=[],
        cost_usd=0.003,
    )
    return AnalyzeResponse(
        analysis_id=str(uuid.uuid4()),
        ticker="BNS",
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=graham,
        cost_usd=0.003,
        created_at="2026-05-08T10:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Tests unitaires AnalysisCacheService
# ---------------------------------------------------------------------------

async def test_cache_get_absent(cache: AnalysisCacheService, ratios_bns: GrahamRatios):
    """Clé absente dans Redis → retourne None."""
    result = await cache.get("BNS", "value_graham", ratios_bns)
    assert result is None


async def test_cache_set_puis_get(
    mock_redis: AsyncMock,
    ratios_bns: GrahamRatios,
    analyze_response_bns: AnalyzeResponse,
):
    """set() puis get() retourne un AnalyzeResponse valide."""
    cache = AnalysisCacheService(redis_client=mock_redis, ttl_seconds=3600)

    # Simuler le set
    await cache.set("BNS", "value_graham", ratios_bns, analyze_response_bns)
    assert mock_redis.set.called

    # Simuler le get avec les données sérialisées
    serialized = analyze_response_bns.model_dump_json()
    mock_redis.get = AsyncMock(return_value=serialized)

    result = await cache.get("BNS", "value_graham", ratios_bns)
    assert result is not None
    assert result.ticker == "BNS"
    assert result.graham.defensive_score == 6


async def test_cache_key_deterministe(
    cache: AnalysisCacheService, ratios_bns: GrahamRatios
):
    """Même ticker + workflow + ratios → même clé à chaque appel."""
    key1 = cache._cache_key("BNS", "value_graham", ratios_bns)
    key2 = cache._cache_key("BNS", "value_graham", ratios_bns)
    assert key1 == key2
    assert key1.startswith("analysis:BNS:value_graham:")


async def test_cache_key_differente_si_ratios_diff(
    cache: AnalysisCacheService,
    ratios_bns: GrahamRatios,
    ratios_bns_alt: GrahamRatios,
):
    """pe=11 vs pe=12 → clés de cache différentes."""
    key1 = cache._cache_key("BNS", "value_graham", ratios_bns)
    key2 = cache._cache_key("BNS", "value_graham", ratios_bns_alt)
    assert key1 != key2


async def test_cache_ttl_transmis(
    mock_redis: AsyncMock,
    ratios_bns: GrahamRatios,
    analyze_response_bns: AnalyzeResponse,
):
    """AnalysisCacheService.set() transmet le TTL à Redis via le paramètre ex."""
    ttl = 7200
    cache = AnalysisCacheService(redis_client=mock_redis, ttl_seconds=ttl)
    await cache.set("BNS", "value_graham", ratios_bns, analyze_response_bns)
    call_kwargs = mock_redis.set.call_args
    assert call_kwargs.kwargs.get("ex") == ttl or (
        len(call_kwargs.args) > 2 and call_kwargs.args[2] == ttl
    )


async def test_cache_invalidate_ticker(mock_redis: AsyncMock, ratios_bns: GrahamRatios):
    """invalidate('BNS') supprime toutes les clés du ticker."""
    mock_redis.keys = AsyncMock(
        return_value=[
            "analysis:BNS:value_graham:abc123",
            "analysis:BNS:compounder_buffett:def456",
        ]
    )
    mock_redis.delete = AsyncMock(return_value=2)

    cache = AnalysisCacheService(redis_client=mock_redis, ttl_seconds=3600)
    count = await cache.invalidate("BNS")

    assert count == 2
    mock_redis.keys.assert_called_once()
    mock_redis.delete.assert_called_once()


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur + cache
# ---------------------------------------------------------------------------

async def test_orchestrator_utilise_cache_si_present(
    analyze_response_bns: AnalyzeResponse,
    ratios_bns: GrahamRatios,
):
    """Si cache.get retourne une réponse, l'orchestrateur ne fait aucun appel Claude."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=analyze_response_bns)

    mock_graham_skill = AsyncMock()
    mock_graham_skill.execute = AsyncMock()

    from app.orchestrator.core import Orchestrator, AnalyzeRequest
    from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill

    mock_earnings_skill = AsyncMock(spec=EarningsQualitySkill)
    mock_db = AsyncMock()

    orchestrator = Orchestrator(
        db_pool=mock_db,
        graham_skill=mock_graham_skill,
        earnings_skill=mock_earnings_skill,
    )

    request = AnalyzeRequest(ticker="BNS", ratios=ratios_bns, workflow="value_graham")
    result = await orchestrator.run_company_analysis(request, cache=mock_cache)

    # Aucun appel Claude — circuit court via cache
    mock_graham_skill.execute.assert_not_called()
    assert result.ticker == "BNS"
    assert result.cost_usd == 0.0  # coût remis à 0 pour les cache hits


async def test_orchestrator_bypass_cache_si_absent(
    ratios_bns: GrahamRatios,
    analyze_response_bns: AnalyzeResponse,
):
    """Avec cache=None, l'analyse normale s'exécute (graham_skill.execute est appelé)."""
    from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
    from app.skills.base import UsageDetail
    from app.orchestrator.core import Orchestrator, AnalyzeRequest
    from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
    import uuid

    graham_out = analyze_response_bns.graham
    usage = UsageDetail(
        tokens_input=100,
        tokens_output=50,
        tokens_cache_read=0,
        tokens_cache_creation=200,
        cost_usd=0.003,
        model="claude-sonnet-4-6",
    )

    mock_graham_skill = AsyncMock()
    mock_graham_skill.execute = AsyncMock(return_value=(graham_out, usage))

    mock_earnings_skill = AsyncMock(spec=EarningsQualitySkill)

    mock_db = AsyncMock()
    mock_db.fetchrow = AsyncMock(return_value={"id": uuid.uuid4()})

    orchestrator = Orchestrator(
        db_pool=mock_db,
        graham_skill=mock_graham_skill,
        earnings_skill=mock_earnings_skill,
    )

    request = AnalyzeRequest(ticker="BNS", ratios=ratios_bns, workflow="value_graham")
    result = await orchestrator.run_company_analysis(request, cache=None)

    # graham_skill.execute doit avoir été appelé
    mock_graham_skill.execute.assert_called_once()
    assert result.ticker == "BNS"
    assert result.cost_usd > 0
