"""Tests CI pour Sprint 65 — Cache composite_score automatique.

Couvre :
- CompositeHistoryService.get_recent() : aucun historique, trop ancien, récent
- run_company_analysis() : court-circuit cache chaud, exécution normale cache froid,
  exécution normale sans service, flags depuis_cache_composite
- stream_company_analysis() : event "cached" émis si cache chaud
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.services.composite_history_service import (
    CompositeHistoryPoint,
    CompositeHistoryService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool_with_fetchrow(fetchrow_return=None) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    pool.fetch = AsyncMock(return_value=[])
    pool.execute = AsyncMock(return_value="INSERT 1")
    return pool


def _make_point(
    ticker: str = "BNS",
    score: float = 72.5,
    label: str = "FORT",
    recorded_at: datetime | None = None,
) -> CompositeHistoryPoint:
    return CompositeHistoryPoint(
        id=str(uuid.uuid4()),
        ticker=ticker,
        score=score,
        label=label,
        workflow="value_graham",
        recorded_at=recorded_at or datetime.now(timezone.utc),
    )


def _make_minimal_orchestrator(pool=None) -> Orchestrator:
    """Orchestrateur avec uniquement les dépendances requises mockées."""
    if pool is None:
        pool = _make_pool_with_fetchrow(fetchrow_return={"id": uuid.uuid4()})
    graham_skill = MagicMock()
    earnings_skill = MagicMock()
    return Orchestrator(db_pool=pool, graham_skill=graham_skill, earnings_skill=earnings_skill)


# ---------------------------------------------------------------------------
# Tests 1-3 : CompositeHistoryService.get_recent()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recent_retourne_none_si_aucun_historique():
    """get_recent() doit retourner None si la DB ne retourne aucune ligne."""
    pool = _make_pool_with_fetchrow(fetchrow_return=None)
    service = CompositeHistoryService(db_pool=pool)

    result = await service.get_recent("BNS")

    assert result is None
    pool.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_retourne_none_si_db_retourne_none_filtre_par_age():
    """get_recent() renvoie None quand la requête SQL (filtrée sur l'âge) retourne None.

    La logique de filtre est dans le SQL — ici on simule que la DB ne retourne rien
    (ce qui se produirait si l'entrée la plus récente a plus de max_age_hours).
    """
    pool = _make_pool_with_fetchrow(fetchrow_return=None)
    service = CompositeHistoryService(db_pool=pool)

    result = await service.get_recent("BNS", max_age_hours=1)

    assert result is None
    # Vérifie que max_age_hours est passé comme "1" dans la requête
    call_args = pool.fetchrow.call_args
    assert call_args.args[2] == "1"


@pytest.mark.asyncio
async def test_get_recent_retourne_point_si_recent():
    """get_recent() doit retourner un CompositeHistoryPoint si la DB retourne une ligne."""
    now = datetime.now(timezone.utc)
    fake_row = {
        "id": uuid.uuid4(),
        "ticker": "BNS",
        "score": 72.5,
        "label": "FORT",
        "workflow": "value_graham",
        "recorded_at": now,
    }
    pool = _make_pool_with_fetchrow(fetchrow_return=fake_row)
    service = CompositeHistoryService(db_pool=pool)

    result = await service.get_recent("BNS")

    assert result is not None
    assert isinstance(result, CompositeHistoryPoint)
    assert result.ticker == "BNS"
    assert result.score == 72.5
    assert result.label == "FORT"
    assert result.recorded_at == now


@pytest.mark.asyncio
async def test_get_recent_max_age_hours_passe_correctement():
    """get_recent() doit transmettre max_age_hours converti en str à la requête SQL."""
    pool = _make_pool_with_fetchrow(fetchrow_return=None)
    service = CompositeHistoryService(db_pool=pool)

    await service.get_recent("BNS", max_age_hours=48)

    call_args = pool.fetchrow.call_args
    assert call_args.args[2] == "48"


# ---------------------------------------------------------------------------
# Tests 5-8 : run_company_analysis() — circuit court et exécution normale
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_company_analysis_court_circuite_si_cache_chaud():
    """run_company_analysis() doit retourner immédiatement si composite_score récent."""
    orchestrator = _make_minimal_orchestrator()
    mock_chs = AsyncMock(spec=CompositeHistoryService)
    mock_chs.get_recent.return_value = _make_point(score=72.5, label="FORT")

    request = AnalyzeRequest(ticker="BNS")
    response = await orchestrator.run_company_analysis(
        request, cache=None, composite_history_service=mock_chs
    )

    mock_chs.get_recent.assert_called_once_with("BNS")
    assert response.depuis_cache_composite is True
    assert response.composite_score is not None
    assert response.composite_score.score == 72.5
    assert response.composite_score.label == "FORT"
    assert response.skills_applied == []
    assert response.cost_usd == 0.0


@pytest.mark.asyncio
async def test_depuis_cache_composite_true_dans_reponse_cache():
    """La réponse cache chaud doit avoir depuis_cache_composite=True."""
    orchestrator = _make_minimal_orchestrator()
    mock_chs = AsyncMock(spec=CompositeHistoryService)
    mock_chs.get_recent.return_value = _make_point(score=55.0, label="MODÉRÉ")

    request = AnalyzeRequest(ticker="TD")
    response = await orchestrator.run_company_analysis(
        request, cache=None, composite_history_service=mock_chs
    )

    assert response.depuis_cache_composite is True
    assert response.analysis_id == "cached_composite"


@pytest.mark.asyncio
async def test_run_company_analysis_execute_normalement_si_cache_froid():
    """run_company_analysis() doit appeler les skills si get_recent() retourne None."""
    pool = _make_pool_with_fetchrow(fetchrow_return={"id": uuid.uuid4()})
    orchestrator = _make_minimal_orchestrator(pool=pool)
    mock_chs = AsyncMock(spec=CompositeHistoryService)
    mock_chs.get_recent.return_value = None  # cache froid
    mock_chs.record = AsyncMock()

    request = AnalyzeRequest(ticker="BNS")  # ratios=None → aucun skill appelé
    response = await orchestrator.run_company_analysis(
        request, cache=None, composite_history_service=mock_chs
    )

    mock_chs.get_recent.assert_called_once_with("BNS")
    assert response.depuis_cache_composite is False
    # L'analyse normale a eu lieu (persist a été appelé)
    pool.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_depuis_cache_composite_false_dans_reponse_normale():
    """La réponse d'une analyse normale doit avoir depuis_cache_composite=False."""
    pool = _make_pool_with_fetchrow(fetchrow_return={"id": uuid.uuid4()})
    orchestrator = _make_minimal_orchestrator(pool=pool)
    mock_chs = AsyncMock(spec=CompositeHistoryService)
    mock_chs.get_recent.return_value = None
    mock_chs.record = AsyncMock()

    request = AnalyzeRequest(ticker="RY")
    response = await orchestrator.run_company_analysis(
        request, cache=None, composite_history_service=mock_chs
    )

    assert response.depuis_cache_composite is False


@pytest.mark.asyncio
async def test_run_company_analysis_execute_normalement_si_service_absent():
    """run_company_analysis() doit fonctionner normalement si composite_history_service=None."""
    pool = _make_pool_with_fetchrow(fetchrow_return={"id": uuid.uuid4()})
    orchestrator = _make_minimal_orchestrator(pool=pool)

    request = AnalyzeRequest(ticker="BNS")
    response = await orchestrator.run_company_analysis(
        request, cache=None, composite_history_service=None
    )

    assert response.depuis_cache_composite is False
    pool.fetchrow.assert_called_once()


# ---------------------------------------------------------------------------
# Test 9 : stream_company_analysis() — event "cached" si cache chaud
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_company_analysis_emet_cached_si_cache_chaud():
    """stream_company_analysis() doit émettre un event 'cached' avec depuis_cache_composite=True."""
    orchestrator = _make_minimal_orchestrator()
    mock_chs = AsyncMock(spec=CompositeHistoryService)
    mock_chs.get_recent.return_value = _make_point(score=80.0, label="FORT")

    request = AnalyzeRequest(ticker="BNS")
    events = []
    async for event in orchestrator.stream_company_analysis(
        request, cache=None, composite_history_service=mock_chs
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0]["event"] == "cached"
    data = events[0]["data"]
    assert data["depuis_cache_composite"] is True
    assert data["composite_score"]["score"] == 80.0
    assert data["composite_score"]["label"] == "FORT"
