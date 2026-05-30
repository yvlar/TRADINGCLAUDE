"""Tests des endpoints /analyze-async et /jobs/{job_id} + tâche Celery run_full_analysis."""
from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.jobs import router as jobs_router

_BODY_BNS = {
    "ticker": "BNS",
    "ratios": {
        "pe": 11.0,
        "pb": 1.3,
        "current_ratio": None,
        "debt_equity": 0.45,
        "eps_growth_total": 0.27,
        "price": 80.0,
        "book_value": 61.5,
    },
}


def _make_jobs_app(mock_redis: AsyncMock) -> FastAPI:
    """Crée une app FastAPI minimale exposant uniquement les endpoints jobs."""
    app = FastAPI()
    app.state.redis_pool = mock_redis
    app.include_router(jobs_router)
    return app


@pytest.fixture
def mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.set = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    return r


class TestAnalyzeAsync:
    async def test_analyze_async_retourne_job_id(self, mock_redis: AsyncMock):
        with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
            mock_task.delay.return_value = None
            app = _make_jobs_app(mock_redis)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/analyze-async", json=_BODY_BNS)

        assert r.status_code == 200
        assert "job_id" in r.json()

    async def test_analyze_async_job_id_est_uuid_valide(self, mock_redis: AsyncMock):
        with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
            mock_task.delay.return_value = None
            app = _make_jobs_app(mock_redis)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/analyze-async", json=_BODY_BNS)

        job_id = r.json()["job_id"]
        parsed = uuid.UUID(job_id)
        assert str(parsed) == job_id

    async def test_analyze_async_stocke_pending_dans_redis(self, mock_redis: AsyncMock):
        with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
            mock_task.delay.return_value = None
            app = _make_jobs_app(mock_redis)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/analyze-async", json=_BODY_BNS)

        job_id = r.json()["job_id"]
        mock_redis.set.assert_any_call(f"job:{job_id}:status", "pending", ex=86400)

    async def test_analyze_async_appelle_celery_delay(self, mock_redis: AsyncMock):
        with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
            mock_task.delay.return_value = None
            app = _make_jobs_app(mock_redis)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                await c.post("/analyze-async", json=_BODY_BNS)

        mock_task.delay.assert_called_once()


class TestGetJob:
    async def test_get_job_status_pending(self, mock_redis: AsyncMock):
        mock_redis.get = AsyncMock(side_effect=lambda key: "pending" if "status" in key else None)
        app = _make_jobs_app(mock_redis)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/jobs/some-job-id")

        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    async def test_get_job_status_done_avec_result(self, mock_redis: AsyncMock):
        result_json = json.dumps({"ticker": "BNS", "analysis_id": "abc"})

        async def _get(key: str) -> str | None:
            if "status" in key:
                return "done"
            if "result" in key:
                return result_json
            return None

        mock_redis.get = AsyncMock(side_effect=_get)
        app = _make_jobs_app(mock_redis)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/jobs/some-job-id")

        data = r.json()
        assert data["status"] == "done"
        assert data["result"] == {"ticker": "BNS", "analysis_id": "abc"}

    async def test_get_job_status_failed_avec_error(self, mock_redis: AsyncMock):
        async def _get(key: str) -> str | None:
            if "status" in key:
                return "failed"
            if "error" in key:
                return "RuntimeError: connexion échouée"
            return None

        mock_redis.get = AsyncMock(side_effect=_get)
        app = _make_jobs_app(mock_redis)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/jobs/some-job-id")

        data = r.json()
        assert data["status"] == "failed"
        assert "error" in data
        assert data["error"] is not None

    async def test_get_job_inconnu_retourne_404(self, mock_redis: AsyncMock):
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_jobs_app(mock_redis)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/jobs/job-inexistant")

        assert r.status_code == 404


class TestRunFullAnalysisTask:
    def test_run_full_analysis_task_met_statut_running(self):
        mock_redis = MagicMock()
        result_dict: dict[str, Any] = {"ticker": "BNS", "analysis_id": "xyz"}

        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch("app.workers.tasks._execute_analysis", new_callable=AsyncMock, return_value=result_dict),
        ):
            from app.workers.tasks import run_full_analysis
            run_full_analysis.apply(args=["job-abc", {"ticker": "BNS"}])

        running_call = call("job:job-abc:status", "running", ex=86400)
        assert running_call in mock_redis.set.call_args_list

    def test_run_full_analysis_task_met_statut_done(self):
        mock_redis = MagicMock()
        result_dict: dict[str, Any] = {"ticker": "BNS", "analysis_id": "xyz"}

        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch("app.workers.tasks._execute_analysis", new_callable=AsyncMock, return_value=result_dict),
        ):
            from app.workers.tasks import run_full_analysis
            run_full_analysis.apply(args=["job-abc", {"ticker": "BNS"}])

        done_call = call("job:job-abc:status", "done", ex=86400)
        assert done_call in mock_redis.set.call_args_list

    def test_run_full_analysis_task_met_statut_failed_si_erreur(self):
        mock_redis = MagicMock()

        async def _raise(*args, **kwargs):
            raise RuntimeError("Erreur simulée")

        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch("app.workers.tasks._execute_analysis", side_effect=_raise),
        ):
            from app.workers.tasks import run_full_analysis
            # throw=False évite que l'exception de retry ne remonte dans le test
            run_full_analysis.apply(args=["job-err", {"ticker": "BNS"}], throw=False)

        failed_call = call("job:job-err:status", "failed", ex=86400)
        assert failed_call in mock_redis.set.call_args_list

    def test_run_full_analysis_task_expire_24h(self):
        mock_redis = MagicMock()
        result_dict: dict[str, Any] = {"ticker": "BNS", "analysis_id": "xyz"}

        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch("app.workers.tasks._execute_analysis", new_callable=AsyncMock, return_value=result_dict),
        ):
            from app.workers.tasks import run_full_analysis
            run_full_analysis.apply(args=["job-ttl", {"ticker": "BNS"}])

        for set_call in mock_redis.set.call_args_list:
            _, kwargs = set_call
            assert kwargs.get("ex") == 86400, f"TTL incorrect dans l'appel : {set_call}"
