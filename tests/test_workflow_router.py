"""Tests Sprint 21 — WorkflowRouter + WebSocket /ws/metrics."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.orchestrator.router import WorkflowRouter

# ---------------------------------------------------------------------------
# Tests WorkflowRouter — pure unit, 0 appel réseau
# ---------------------------------------------------------------------------


def test_workflow_value_graham_steps():
    """value_graham : 5 étapes, graham en premier et non-optionnel."""
    router = WorkflowRouter()
    steps = router.route("value_graham")
    assert len(steps) == 5
    ids = [s.skill_id for s in steps]
    assert ids[0] == "graham_analysis"
    assert not steps[0].optional  # graham est obligatoire
    assert "earnings_quality" in ids
    assert "stock_valuation_triangulation" in ids
    assert "investment_thesis_builder" in ids
    assert "canadian_tax_considerations" in ids


def test_workflow_compounder_buffett_steps():
    """compounder_buffett : 10 étapes avec tous les skills prévus."""
    router = WorkflowRouter()
    steps = router.route("compounder_buffett")
    assert len(steps) == 10
    ids = [s.skill_id for s in steps]
    assert "graham_analysis" in ids
    assert "earnings_quality" in ids
    assert "dorsey_moat" in ids
    assert "buffett_quality" in ids
    assert "fisher_scuttlebutt" in ids
    assert "stock_valuation_triangulation" in ids
    assert "investment_thesis_builder" in ids
    assert "munger_mental_models" in ids
    assert "marks_cycles_risk" in ids
    assert "canadian_tax_considerations" in ids


def test_workflow_fast_grower_lynch_steps():
    """fast_grower_lynch : 6 étapes, lynch présent, graham absent."""
    router = WorkflowRouter()
    steps = router.route("fast_grower_lynch")
    assert len(steps) == 6
    ids = [s.skill_id for s in steps]
    assert "lynch_categories" in ids
    assert "graham_analysis" not in ids
    assert "damodaran_narrative" in ids
    assert "stock_valuation_triangulation" in ids
    assert "investment_thesis_builder" in ids
    assert "munger_mental_models" in ids
    assert "canadian_tax_considerations" in ids


def test_workflow_special_situation_steps():
    """special_situation : 4 étapes, klarman et greenblatt présents."""
    router = WorkflowRouter()
    steps = router.route("special_situation")
    assert len(steps) == 4
    ids = [s.skill_id for s in steps]
    assert "klarman_margin" in ids
    assert "greenblatt_magic_formula" in ids
    assert "graham_analysis" in ids
    assert "investment_thesis_builder" in ids
    assert "canadian_tax_considerations" not in ids


def test_workflow_distressed_pabrai_steps():
    """distressed_pabrai : 5 étapes, pabrai en première position."""
    router = WorkflowRouter()
    steps = router.route("distressed_pabrai")
    assert len(steps) == 5
    assert steps[0].skill_id == "pabrai_dhandho"
    ids = [s.skill_id for s in steps]
    assert "klarman_margin" in ids
    assert "earnings_quality" in ids
    assert "investment_thesis_builder" in ids
    assert "canadian_tax_considerations" in ids


def test_workflow_inconnu_raise_value_error():
    """Un workflow inconnu lève ValueError avec le nom du workflow."""
    router = WorkflowRouter()
    with pytest.raises(ValueError, match="Workflow inconnu"):
        router.route("foo")
    with pytest.raises(ValueError, match="Workflow inconnu"):
        router.route("company_analysis")


def test_orchestrator_workflow_non_defaut():
    """Pour fast_grower_lynch, graham_analysis est absent et lynch_categories présent."""
    router = WorkflowRouter()
    steps = router.route("fast_grower_lynch")
    ids = [s.skill_id for s in steps]
    assert "graham_analysis" not in ids
    assert "lynch_categories" in ids
    # Vérifie aussi que les skills d'analyse graham ne « contaminent » pas ce workflow
    assert "dorsey_moat" not in ids
    assert "buffett_quality" not in ids


# ---------------------------------------------------------------------------
# Tests WebSocket /ws/metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ws_metrics_payload_structure():
    """_build_metrics_payload retourne un dict avec tous les champs requis."""
    from app.api.endpoints.ws_metrics import _build_metrics_payload

    mock_redis = AsyncMock()
    mock_redis.keys.return_value = []
    mock_redis.get.return_value = None

    mock_state = SimpleNamespace(redis_pool=mock_redis)
    payload = await _build_metrics_payload(mock_state)

    assert "jobs_en_cours" in payload
    assert "jobs_echoues_1h" in payload
    assert "cout_total_1h_usd" in payload
    assert "cache_hit_ratio" in payload
    assert "analyses_24h" in payload
    assert "timestamp" in payload

    assert isinstance(payload["jobs_en_cours"], int)
    assert isinstance(payload["jobs_echoues_1h"], int)
    assert isinstance(payload["cout_total_1h_usd"], float)
    assert 0.0 <= payload["cache_hit_ratio"] <= 1.0
    assert isinstance(payload["analyses_24h"], int)
    assert "T" in payload["timestamp"] and "Z" in payload["timestamp"]


@pytest.mark.asyncio
async def test_ws_metrics_connect_disconnect():
    """ws_metrics se ferme proprement quand le client se déconnecte (WebSocketDisconnect)."""
    from fastapi import WebSocketDisconnect

    from app.api.endpoints.ws_metrics import ws_metrics

    mock_redis = AsyncMock()
    mock_redis.keys.return_value = []
    mock_redis.get.return_value = None

    mock_ws = AsyncMock()
    mock_ws.app = SimpleNamespace(state=SimpleNamespace(redis_pool=mock_redis))
    # Simule une déconnexion immédiate dès le premier send_text
    mock_ws.send_text.side_effect = WebSocketDisconnect(code=1000)

    # Ne doit pas propager d'exception
    await ws_metrics(mock_ws)

    mock_ws.accept.assert_called_once()
    mock_ws.send_text.assert_called_once()
    # close() ne doit PAS être appelé pour une déconnexion normale
    mock_ws.close.assert_not_called()
