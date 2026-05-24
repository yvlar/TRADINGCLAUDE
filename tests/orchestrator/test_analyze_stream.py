"""Tests d'intégration pour POST /analyze-stream (SSE)."""
from __future__ import annotations

import json
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.orchestrator.core import AnalyzeResponse
from app.services.observability import CacheStats, CostSummary, LatencyStats, ObservabilityService
from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
from tests.conftest import (
    _SKILL_PROMPT_PATCHES,
    _make_criteria_defensif,
    _make_criteria_entreprenant,
)

_RATIOS = {
    "pe": 11.0,
    "pb": 1.3,
    "current_ratio": None,
    "debt_equity": 0.45,
    "eps_growth_10y": 0.27,
    "price": 80.0,
    "book_value": 61.5,
}

_PAYLOAD = {"ticker": "BNS", "ratios": _RATIOS, "workflow": "value_graham"}


def _parse_sse(text: str) -> list[dict]:
    """Parse un corps SSE texte en liste d'events {type, data}."""
    events: list[dict] = []
    current_event = ""
    for line in text.splitlines():
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append({"type": current_event, "data": data})
            except json.JSONDecodeError:
                pass
    return events


def _make_graham_output() -> GrahamAnalysisOutput:
    return GrahamAnalysisOutput(
        ticker="BNS",
        profil_applique="DEFENSIF",
        defensive_score=5,
        enterprising_score=3,
        criteria_defensif=_make_criteria_defensif([True] * 5 + [False] * 3),
        criteria_entreprenant=_make_criteria_entreprenant([True] * 3 + [False] * 2),
        valeur_intrinseque_simple=95.0,
        valeur_intrinseque_ajustee=87.5,
        marge_securite=0.093,
        drapeaux_rouges=[],
        verdict="CANDIDAT_SOLIDE",
        verdict_detail="BNS passe 5/8 critères défensifs.",
        recommandation_prochaine_etape=["earnings_quality"],
        citations=[],
        cost_usd=0.001,
    )


def _make_analyze_response(graham: GrahamAnalysisOutput) -> AnalyzeResponse:
    import uuid
    return AnalyzeResponse(
        analysis_id=str(uuid.uuid4()),
        ticker="BNS",
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=graham,
        earnings_quality=None,
        cost_usd=0.001,
        created_at="2026-05-10T00:00:00+00:00",
    )


@pytest_asyncio.fixture
async def stream_client():
    """Client HTTP avec orchestrateur mocké pour /analyze-stream."""
    graham = _make_graham_output()
    response = _make_analyze_response(graham)

    async def _mock_stream(*_args, **_kwargs):
        yield {"event": "skill_start", "data": {"skill_id": "graham_analysis"}}
        yield {
            "event": "skill_result",
            "data": {"skill_id": "graham_analysis", "result": graham.model_dump()},
        }
        yield {"event": "complete", "data": response.model_dump()}

    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis.return_value = response
    mock_orchestrator.stream_company_analysis = MagicMock(side_effect=_mock_stream)

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

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.delete = AsyncMock(return_value=0)

    mock_obs = AsyncMock(spec=ObservabilityService)
    mock_obs.get_cost_summary.return_value = CostSummary(
        cost_total_usd=0.0, cost_par_jour=[], analyses_count=0
    )
    mock_obs.get_cache_stats.return_value = CacheStats(
        hits=0, misses=0, hit_ratio=0.0, keys_count=0
    )
    mock_obs.get_latency_p95.return_value = LatencyStats(
        skill_id=None, p50_ms=None, p95_ms=None, p99_ms=None, sample_count=0
    )
    mock_obs.check_cost_alert.return_value = False

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
            patch("app.api.main.aioredis.from_url", return_value=mock_redis)
        )
        for prompt_path in _SKILL_PROMPT_PATCHES:
            stack.enter_context(patch(prompt_path, return_value="prompt de test"))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            app.state.orchestrator = mock_orchestrator
            app.state.db_pool = mock_pool.return_value
            app.state.qdrant_url = "http://qdrant:6333"
            app.state.redis_pool = mock_redis
            app.state.analysis_cache = AsyncMock()
            app.state.observability = mock_obs
            yield c


@pytest.mark.asyncio
async def test_stream_content_type_sse(stream_client):
    """POST /analyze-stream → Content-Type: text/event-stream."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_stream_contient_skill_start(stream_client):
    """POST /analyze-stream → event skill_start présent."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "skill_start" in types


@pytest.mark.asyncio
async def test_stream_skill_start_contient_skill_id(stream_client):
    """L'event skill_start contient le champ skill_id."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    start = next(e for e in events if e["type"] == "skill_start")
    assert "skill_id" in start["data"]
    assert start["data"]["skill_id"] == "graham_analysis"


@pytest.mark.asyncio
async def test_stream_skill_result_contient_result(stream_client):
    """L'event skill_result contient skill_id et result."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    result_evt = next(e for e in events if e["type"] == "skill_result")
    assert "skill_id" in result_evt["data"]
    assert "result" in result_evt["data"]
    assert result_evt["data"]["skill_id"] == "graham_analysis"


@pytest.mark.asyncio
async def test_stream_complete_contient_analyze_response(stream_client):
    """L'event complete contient une AnalyzeResponse valide."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    complete = next(e for e in events if e["type"] == "complete")
    data = complete["data"]
    assert "analysis_id" in data
    assert data["ticker"] == "BNS"
    assert "cost_usd" in data
    assert "skills_applied" in data


@pytest.mark.asyncio
async def test_stream_ordre_events(stream_client):
    """Les events arrivent dans l'ordre : skill_start → skill_result → complete."""
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert types.index("skill_start") < types.index("skill_result")
    assert types.index("skill_result") < types.index("complete")


@pytest.mark.asyncio
async def test_stream_cache_hit_retourne_cached(stream_client):
    """Si le cache retourne un résultat, l'event cached est émis (pas de skill_start)."""
    graham = _make_graham_output()
    cached_response = _make_analyze_response(graham)

    async def _cached_stream(*_args, **_kwargs):
        yield {"event": "cached", "data": cached_response.model_dump()}

    app.state.orchestrator.stream_company_analysis = MagicMock(
        side_effect=_cached_stream
    )
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "cached" in types
    assert "skill_start" not in types


@pytest.mark.asyncio
async def test_stream_erreur_skill_retourne_event_error(stream_client):
    """Si le générateur lève une exception, un event error est émis."""
    async def _failing_stream(*_args, **_kwargs):
        yield {"event": "skill_start", "data": {"skill_id": "graham_analysis"}}
        raise RuntimeError("Claude indisponible")
        yield  # rendre la fonction un générateur

    app.state.orchestrator.stream_company_analysis = MagicMock(
        side_effect=_failing_stream
    )
    r = await stream_client.post("/analyze-stream", json=_PAYLOAD)
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "error" in types
    error_evt = next(e for e in events if e["type"] == "error")
    assert "message" in error_evt["data"]
