"""Tests Sprint 95 — suppression d'analyses depuis l'historique."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.main import app as fastapi_app
from app.orchestrator.core import Orchestrator


def _make_mock_pool(execute_return: str = "DELETE 1") -> AsyncMock:
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value=execute_return)
    return pool


# ---------------------------------------------------------------------------
# Test 1 : delete_analysis retourne True pour un UUID existant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_analysis_retourne_true_si_uuid_existant():
    """delete_analysis() retourne True quand la DB confirme la suppression (DELETE 1)."""
    pool = _make_mock_pool(execute_return="DELETE 1")
    orchestrator = Orchestrator(
        db_pool=pool,
        graham_skill=AsyncMock(),
        earnings_skill=AsyncMock(),
    )

    analysis_id = str(uuid.uuid4())
    result = await orchestrator.delete_analysis(analysis_id)

    assert result is True
    # Vérifie que les deux DELETE ont bien été appelés (annotations + analysis_history)
    assert pool.execute.await_count == 2


# ---------------------------------------------------------------------------
# Test 2 : delete_analysis retourne False pour UUID inexistant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_analysis_retourne_false_si_uuid_inexistant():
    """delete_analysis() retourne False quand la DB ne trouve aucune ligne (DELETE 0)."""
    pool = _make_mock_pool(execute_return="DELETE 0")
    orchestrator = Orchestrator(
        db_pool=pool,
        graham_skill=AsyncMock(),
        earnings_skill=AsyncMock(),
    )

    result = await orchestrator.delete_analysis(str(uuid.uuid4()))

    assert result is False


# ---------------------------------------------------------------------------
# Test 3 : DELETE /history/{id} retourne 204 quand orchestrateur confirme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_history_endpoint_retourne_204(client):
    """DELETE /history/{id} retourne 204 quand l'orchestrateur confirme la suppression."""
    mock_orchestrator = AsyncMock(spec=Orchestrator)
    mock_orchestrator.delete_analysis = AsyncMock(return_value=True)
    fastapi_app.state.orchestrator = mock_orchestrator
    # bypass admin check en mode dev
    fastapi_app.state.api_key_service = None

    analysis_id = str(uuid.uuid4())
    resp = await client.delete(f"/history/{analysis_id}")

    assert resp.status_code == 204
    mock_orchestrator.delete_analysis.assert_awaited_once_with(analysis_id)
