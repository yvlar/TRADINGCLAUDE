"""Tests des endpoints FastAPI — /healthz, /analyze et /history avec orchestrateur mocké."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import _VERSION, app
from app.orchestrator.core import HistoryEntry, HistoryResponse


def _make_mock_qdrant_response(status_code: int = 200) -> MagicMock:
    """Crée un mock de réponse httpx avec le status_code donné."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    return mock_resp


def _make_mock_rag_client() -> AsyncMock:
    """Crée un RagClient mocké qui ne touche pas Qdrant."""
    mock = AsyncMock()
    mock.ensure_collection = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
async def async_client(analyze_response_msft):
    """
    Client HTTP pour tester l'API.
    Patche les dépendances du lifespan (asyncpg, Anthropic, RagClient, lecture des fichiers)
    puis injecte un orchestrateur mocké dans app.state.
    """
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis.return_value = analyze_response_msft

    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.get.return_value = _make_mock_qdrant_response(200)
    mock_qdrant_ctx = AsyncMock()
    mock_qdrant_ctx.__aenter__.return_value = mock_qdrant_client
    mock_qdrant_ctx.__aexit__.return_value = None

    mock_rag_client = _make_mock_rag_client()

    env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}

    mock_redis_pool = AsyncMock()
    mock_redis_pool.incr = AsyncMock(return_value=1)   # sous le seuil → rate limit inactif
    mock_redis_pool.expire = AsyncMock(return_value=True)
    mock_redis_pool.get = AsyncMock(return_value=None)
    mock_redis_pool.set = AsyncMock(return_value=True)
    mock_redis_pool.aclose = AsyncMock()

    with (
        patch.dict(os.environ, env_vars),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
        patch("anthropic.AsyncAnthropic", return_value=MagicMock()),
        patch(
            "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
            return_value="System prompt Graham de test.",
        ),
        patch(
            "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
            return_value="System prompt earnings quality de test.",
        ),
        patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx),
        patch("app.api.main.RagClient", return_value=mock_rag_client),
        patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool),
    ):
        mock_pool.return_value = AsyncMock()
        mock_pool.return_value.close = AsyncMock()
        mock_pool.return_value.fetchval = AsyncMock(return_value=1)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            app.state.orchestrator = mock_orchestrator
            app.state.db_pool = mock_pool.return_value
            app.state.qdrant_url = "http://qdrant:6333"
            app.state.redis_pool = mock_redis_pool
            yield client


BODY_MSFT = {
    "ticker": "MSFT",
    "ratios": {
        "pe": 34.2,
        "pb": 12.1,
        "current_ratio": 1.34,
        "debt_equity": 0.28,
        "eps_growth_total": 0.85,
        "price": 420.0,
        "book_value": 35.0,
    },
}


class TestHealthz:
    @pytest.mark.asyncio
    async def test_status_200(self, async_client):
        r = await async_client.get("/healthz")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_status_ok(self, async_client):
        r = await async_client.get("/healthz")
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_version_presente(self, async_client):
        r = await async_client.get("/healthz")
        assert r.json()["version"] == _VERSION

    @pytest.mark.asyncio
    async def test_version_est_courante(self, async_client):
        r = await async_client.get("/healthz")
        assert r.json()["version"] == _VERSION

    @pytest.mark.asyncio
    async def test_postgres_ok_dans_reponse(self, async_client):
        r = await async_client.get("/healthz")
        assert r.json()["postgres"] == "ok"

    @pytest.mark.asyncio
    async def test_qdrant_ok_dans_reponse(self, async_client):
        r = await async_client.get("/healthz")
        assert r.json()["qdrant"] == "ok"

    @pytest.mark.asyncio
    async def test_healthz_postgres_indisponible_retourne_503(self, analyze_response_msft):
        """Si db_pool.fetchval lève une exception, /healthz retourne 503."""
        mock_qdrant_client = AsyncMock()
        mock_qdrant_client.get.return_value = _make_mock_qdrant_response(200)
        mock_qdrant_ctx = AsyncMock()
        mock_qdrant_ctx.__aenter__.return_value = mock_qdrant_client
        mock_qdrant_ctx.__aexit__.return_value = None

        mock_rag_client = _make_mock_rag_client()

        mock_redis_pool = AsyncMock()
        mock_redis_pool.incr = AsyncMock(return_value=1)
        mock_redis_pool.expire = AsyncMock(return_value=True)
        mock_redis_pool.get = AsyncMock(return_value=None)
        mock_redis_pool.set = AsyncMock(return_value=True)
        mock_redis_pool.aclose = AsyncMock()

        env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}
        with (
            patch.dict(os.environ, env_vars),
            patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("anthropic.AsyncAnthropic", return_value=MagicMock()),
            patch(
                "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
                return_value="prompt de test",
            ),
            patch(
                "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
                return_value="prompt earnings test",
            ),
            patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx),
            patch("app.api.main.RagClient", return_value=mock_rag_client),
            patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool),
        ):
            mock_pool.return_value = AsyncMock()
            mock_pool.return_value.close = AsyncMock()
            mock_pool.return_value.fetchval = AsyncMock(
                side_effect=Exception("connexion refusée")
            )

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                app.state.db_pool = mock_pool.return_value
                app.state.qdrant_url = "http://qdrant:6333"
                app.state.redis_pool = mock_redis_pool
                r = await client.get("/healthz")

        assert r.status_code == 503
        assert r.json()["postgres"] == "error"


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_body_valide_retourne_200(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_reponse_contient_ticker(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["ticker"] == "MSFT"

    @pytest.mark.asyncio
    async def test_reponse_contient_workflow(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["workflow"] == "company_analysis"

    @pytest.mark.asyncio
    async def test_skills_applied_contient_graham(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["skills_applied"] == ["graham_analysis"]

    @pytest.mark.asyncio
    async def test_reponse_contient_analysis_id(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert "analysis_id" in r.json()
        assert len(r.json()["analysis_id"]) == 36

    @pytest.mark.asyncio
    async def test_cost_usd_non_nul(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["cost_usd"] > 0.0

    @pytest.mark.asyncio
    async def test_graham_present_dans_reponse(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert "graham" in r.json()

    @pytest.mark.asyncio
    async def test_earnings_quality_null_sans_earnings_ratios(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["earnings_quality"] is None

    @pytest.mark.asyncio
    async def test_graham_citations_vides(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert r.json()["graham"]["citations"] == []

    @pytest.mark.asyncio
    async def test_graham_8_criteres_defensifs(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert len(r.json()["graham"]["criteria_defensif"]) == 8

    @pytest.mark.asyncio
    async def test_graham_5_criteres_entrepreneuriaux(self, async_client):
        r = await async_client.post("/analyze", json=BODY_MSFT)
        assert len(r.json()["graham"]["criteria_entreprenant"]) == 5

    @pytest.mark.asyncio
    async def test_body_sans_price_retourne_422(self, async_client):
        # pe/pb/debt_equity/book_value optionnels (pb depuis Sprint 135) ; price reste requis
        body_invalide = {
            "ticker": "MSFT",
            "ratios": {
                "pe": 34.2, "pb": 12.1, "current_ratio": 1.34, "debt_equity": 0.28,
                "eps_growth_total": 0.85, "book_value": 35.0,
            },
        }
        r = await async_client.post("/analyze", json=body_invalide)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_body_sans_ticker_retourne_422(self, async_client):
        body_invalide = {"ratios": BODY_MSFT["ratios"]}
        r = await async_client.post("/analyze", json=body_invalide)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_body_vide_retourne_422(self, async_client):
        r = await async_client.post("/analyze", json={})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_current_ratio_null_accepte(self, async_client):
        """current_ratio peut être null (banques) — le body doit passer la validation."""
        body_bns = {
            "ticker": "BNS",
            "ratios": {
                "pe": 11.0, "pb": 1.3, "current_ratio": None,
                "debt_equity": 0.45, "eps_growth_total": 0.27,
                "price": 80.0, "book_value": 61.5,
            },
        }
        r = await async_client.post("/analyze", json=body_bns)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_orchestrateur_appele_une_fois(self, async_client):
        await async_client.post("/analyze", json=BODY_MSFT)
        app.state.orchestrator.run_company_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_erreur_orchestrateur_retourne_500(self, analyze_response_msft):
        """Si l'orchestrateur lève une exception, l'API retourne 500."""
        mock_orchestrator_erreur = AsyncMock()
        mock_orchestrator_erreur.run_company_analysis.side_effect = RuntimeError(
            "Erreur simulée"
        )

        mock_qdrant_client = AsyncMock()
        mock_qdrant_client.get.return_value = _make_mock_qdrant_response(200)
        mock_qdrant_ctx = AsyncMock()
        mock_qdrant_ctx.__aenter__.return_value = mock_qdrant_client
        mock_qdrant_ctx.__aexit__.return_value = None

        mock_rag_client = _make_mock_rag_client()

        mock_redis_pool = AsyncMock()
        mock_redis_pool.incr = AsyncMock(return_value=1)
        mock_redis_pool.expire = AsyncMock(return_value=True)
        mock_redis_pool.get = AsyncMock(return_value=None)
        mock_redis_pool.set = AsyncMock(return_value=True)
        mock_redis_pool.aclose = AsyncMock()

        env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}
        with (
            patch.dict(os.environ, env_vars),
            patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("anthropic.AsyncAnthropic", return_value=MagicMock()),
            patch(
                "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
                return_value="prompt de test",
            ),
            patch(
                "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
                return_value="prompt earnings test",
            ),
            patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx),
            patch("app.api.main.RagClient", return_value=mock_rag_client),
            patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool),
        ):
            mock_pool.return_value = AsyncMock()
            mock_pool.return_value.close = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                app.state.orchestrator = mock_orchestrator_erreur
                app.state.redis_pool = mock_redis_pool
                r = await client.post("/analyze", json=BODY_MSFT)

        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_endpoint_inexistant_retourne_404(self, async_client):
        r = await async_client.get("/inexistant")
        assert r.status_code == 404


class TestHistory:
    @pytest.mark.asyncio
    async def test_history_ticker_existant_retourne_200(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        r = await async_client.get("/history?ticker=BNS")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_history_sans_ticker_retourne_422(self, async_client):
        r = await async_client.get("/history")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_limit_superieur_50_retourne_422(self, async_client):
        r = await async_client.get("/history?ticker=BNS&limit=100")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_limit_zero_retourne_422(self, async_client):
        r = await async_client.get("/history?ticker=BNS&limit=0")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_before_invalide_retourne_422(self, async_client):
        r = await async_client.get("/history?ticker=BNS&before=pas-une-date")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_retourne_entries(self, async_client):
        entry = HistoryEntry(
            analysis_id="550e8400-e29b-41d4-a716-446655440000",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            cost_usd=0.0042,
            defensive_score=5,
            graham_verdict="CANDIDAT_SOLIDE",
            earnings_verdict=None,
            created_at="2026-05-07T14:00:00+00:00",
        )
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(
                ticker="BNS", entries=[entry], next_before=None
            )
        )
        r = await async_client.get("/history?ticker=BNS")
        data = r.json()
        assert data["ticker"] == "BNS"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["graham_verdict"] == "CANDIDAT_SOLIDE"

    @pytest.mark.asyncio
    async def test_history_entries_vides(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        r = await async_client.get("/history?ticker=BNS")
        data = r.json()
        assert data["entries"] == []
        assert data["next_before"] is None

    @pytest.mark.asyncio
    async def test_history_next_before_present_si_page_suivante(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(
                ticker="BNS",
                entries=[],
                next_before="2026-05-01T00:00:00+00:00",
            )
        )
        r = await async_client.get("/history?ticker=BNS")
        assert r.json()["next_before"] == "2026-05-01T00:00:00+00:00"

    @pytest.mark.asyncio
    async def test_history_ticker_dans_reponse(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="MSFT", entries=[], next_before=None)
        )
        r = await async_client.get("/history?ticker=MSFT")
        assert r.json()["ticker"] == "MSFT"

    @pytest.mark.asyncio
    async def test_history_earnings_verdict_none_si_skill_absent(self, async_client):
        entry = HistoryEntry(
            analysis_id="uuid-1",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            cost_usd=0.002,
            defensive_score=6,
            graham_verdict="CANDIDAT_SOLIDE",
            earnings_verdict=None,
            created_at="2026-05-07T10:00:00+00:00",
        )
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[entry], next_before=None)
        )
        r = await async_client.get("/history?ticker=BNS")
        assert r.json()["entries"][0]["earnings_verdict"] is None


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_retourne_200(self, async_client):
        from app.orchestrator.core import MetricsResponse
        app.state.orchestrator.get_metrics = AsyncMock(
            return_value=MetricsResponse(
                period_days=30,
                total_analyses=5,
                total_cost_usd=0.012,
                avg_cost_per_analysis=0.0024,
                cache_hit_ratio_avg=0.82,
                top_tickers=[],
                skills_usage={"graham_analysis": 5},
            )
        )
        r = await async_client.get("/metrics")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_champs_presents(self, async_client):
        from app.orchestrator.core import MetricsResponse
        app.state.orchestrator.get_metrics = AsyncMock(
            return_value=MetricsResponse(
                period_days=30,
                total_analyses=10,
                total_cost_usd=0.05,
                avg_cost_per_analysis=0.005,
                cache_hit_ratio_avg=0.75,
                top_tickers=[],
                skills_usage={},
            )
        )
        r = await async_client.get("/metrics")
        data = r.json()
        for field in (
            "period_days",
            "total_analyses",
            "total_cost_usd",
            "cache_hit_ratio_avg",
            "top_tickers",
            "skills_usage",
        ):
            assert field in data

    @pytest.mark.asyncio
    async def test_metrics_days_trop_grand_retourne_422(self, async_client):
        r = await async_client.get("/metrics?days=400")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_metrics_days_zero_retourne_422(self, async_client):
        r = await async_client.get("/metrics?days=0")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_version_courante(self, async_client):
        """Version courante vérifiée dynamiquement."""
        r = await async_client.get("/healthz")
        assert r.json()["version"] == _VERSION
