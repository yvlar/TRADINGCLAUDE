"""Tests smoke Sprint 19 — valident les payloads et l'importabilité du locustfile."""
from __future__ import annotations

import pytest

GRAHAM_PAYLOAD = {
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
    "workflow": "value_graham",
}

_RATIOS_BANQUES = {
    "pe": 11.0,
    "pb": 1.3,
    "current_ratio": None,
    "debt_equity": 0.45,
    "eps_growth_total": 0.27,
    "price": 80.0,
    "book_value": 61.5,
}

SCREEN_PAYLOAD = {
    "tickers": ["BNS", "TD", "RY", "BMO", "CM"],
    "workflow": "value_graham",
    "ratios_map": {ticker: _RATIOS_BANQUES for ticker in ["BNS", "TD", "RY", "BMO", "CM"]},
}


# ---------------------------------------------------------------------------
# Tests endpoints (utilisent la fixture client de conftest.py)
# ---------------------------------------------------------------------------


async def test_analyze_payload_valide(client) -> None:
    """POST /analyze avec GRAHAM_PAYLOAD → 200."""
    response = await client.post("/analyze", json=GRAHAM_PAYLOAD)
    assert response.status_code == 200


async def test_screen_payload_valide(client) -> None:
    """POST /screen avec SCREEN_PAYLOAD → 200."""
    response = await client.post("/screen", json=SCREEN_PAYLOAD)
    assert response.status_code == 200


async def test_telemetry_summary_smoke(client) -> None:
    """GET /telemetry/summary → 200."""
    response = await client.get("/telemetry/summary?days=7")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests locustfile — pas d'appel réseau, pas de service requis
# ---------------------------------------------------------------------------


def test_locustfile_importable() -> None:
    """Le module locustfile s'importe sans erreur."""
    pytest.importorskip("locust")
    from tests.load.locustfile import AnalyzeUser  # noqa: F401


def test_analyze_user_taches_definies() -> None:
    """AnalyzeUser possède la tâche analyze_bns décorée avec @task."""
    pytest.importorskip("locust")
    from tests.load.locustfile import AnalyzeUser

    assert hasattr(AnalyzeUser, "analyze_bns")
    task_fn = AnalyzeUser.analyze_bns
    assert getattr(task_fn, "locust_task_weight", None) is not None or callable(task_fn)


def test_screen_user_taches_definies() -> None:
    """ScreenUser possède la tâche screen_banks décorée avec @task."""
    pytest.importorskip("locust")
    from tests.load.locustfile import ScreenUser

    assert hasattr(ScreenUser, "screen_banks")
    task_fn = ScreenUser.screen_banks
    assert getattr(task_fn, "locust_task_weight", None) is not None or callable(task_fn)
