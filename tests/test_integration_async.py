"""Tests d'intégration asynchrones — POST /analyze-async → poll /jobs/{id}."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.jobs import router as jobs_router

TICKER_TEST = "TEST"

_BODY_TEST = {
    "ticker": TICKER_TEST,
    "ratios": {
        "pe": 15.0,
        "pb": 1.5,
        "current_ratio": 2.0,
        "debt_equity": 0.30,
        "eps_growth_10y": 0.30,
        "price": 100.0,
        "book_value": 66.0,
    },
}


def _make_jobs_app(mock_redis: AsyncMock) -> FastAPI:
    """App FastAPI minimale avec uniquement les endpoints jobs."""
    mini_app = FastAPI()
    mini_app.state.redis_pool = mock_redis
    mini_app.include_router(jobs_router)
    return mini_app


@pytest.fixture
def mock_redis_jobs() -> AsyncMock:
    r = AsyncMock()
    r.set = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    return r


async def test_analyze_async_retourne_job_id(mock_redis_jobs: AsyncMock):
    with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
        mock_task.delay.return_value = None
        mini_app = _make_jobs_app(mock_redis_jobs)
        async with AsyncClient(
            transport=ASGITransport(app=mini_app), base_url="http://test"
        ) as c:
            r = await c.post("/analyze-async", json=_BODY_TEST)

    assert r.status_code == 200
    assert "job_id" in r.json()


async def test_analyze_async_job_id_est_uuid(mock_redis_jobs: AsyncMock):
    with patch("app.api.endpoints.jobs.run_full_analysis") as mock_task:
        mock_task.delay.return_value = None
        mini_app = _make_jobs_app(mock_redis_jobs)
        async with AsyncClient(
            transport=ASGITransport(app=mini_app), base_url="http://test"
        ) as c:
            r = await c.post("/analyze-async", json=_BODY_TEST)

    job_id = r.json()["job_id"]
    parsed = uuid.UUID(job_id)
    assert str(parsed) == job_id


async def test_job_inconnu_retourne_404(mock_redis_jobs: AsyncMock):
    mock_redis_jobs.get = AsyncMock(return_value=None)
    mini_app = _make_jobs_app(mock_redis_jobs)
    async with AsyncClient(
        transport=ASGITransport(app=mini_app), base_url="http://test"
    ) as c:
        r = await c.get(f"/jobs/{uuid.uuid4()}")

    assert r.status_code == 404


async def test_job_status_pending_apres_creation(mock_redis_jobs: AsyncMock):
    mock_redis_jobs.get = AsyncMock(
        side_effect=lambda key: "pending" if "status" in key else None
    )
    mini_app = _make_jobs_app(mock_redis_jobs)
    async with AsyncClient(
        transport=ASGITransport(app=mini_app), base_url="http://test"
    ) as c:
        r = await c.get("/jobs/some-job-id")

    assert r.status_code == 200
    assert r.json()["status"] in {"pending", "running"}


async def test_job_done_apres_completion(mock_redis_jobs: AsyncMock):
    result_payload = json.dumps({"ticker": TICKER_TEST, "analysis_id": str(uuid.uuid4())})

    async def _get(key: str) -> str | None:
        if "status" in key:
            return "done"
        if "result" in key:
            return result_payload
        return None

    mock_redis_jobs.get = AsyncMock(side_effect=_get)
    mini_app = _make_jobs_app(mock_redis_jobs)
    async with AsyncClient(
        transport=ASGITransport(app=mini_app), base_url="http://test"
    ) as c:
        r = await c.get("/jobs/completed-job-id")

    data = r.json()
    assert data["status"] == "done"
    assert data["result"] is not None


async def test_job_failed_contient_error(mock_redis_jobs: AsyncMock):
    async def _get(key: str) -> str | None:
        if "status" in key:
            return "failed"
        if "error" in key:
            return "RuntimeError: analyse échouée"
        return None

    mock_redis_jobs.get = AsyncMock(side_effect=_get)
    mini_app = _make_jobs_app(mock_redis_jobs)
    async with AsyncClient(
        transport=ASGITransport(app=mini_app), base_url="http://test"
    ) as c:
        r = await c.get("/jobs/failed-job-id")

    data = r.json()
    assert data["status"] == "failed"
    assert data["error"] is not None
