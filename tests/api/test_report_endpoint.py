"""Tests d'intégration — endpoint /report scopé au tenant du demandeur (E4-S11).

`/report` n'est plus auth-exempté : ses deux routes exigent une session (cookie JWT) et
exécutent l'analyse / la lecture sous le tenant du demandeur (`tenant_scope`) — un rapport
ne reflète donc que les données de ce tenant (la RLS masque le reste). Ces tests prouvent,
sans PostgreSQL réel, le **threading du contexte** (le tenant courant au moment de l'appel
DB / de l'orchestrateur) et le **fail-closed** (401 sans session). La preuve d'isolation RLS
bout-en-bout vit dans `tests/integration/test_report_tenant_rls.py` (PG migré requis).
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.db.tenant_context import get_current_tenant

_TENANT_A = uuid.UUID("aaaaaaaa-0000-0000-0000-0000000000aa")
_ANALYSIS_ID = "11111111-2222-3333-4444-555555555555"
_COOKIE = {"access_token": "fake-jwt-access-token"}


@pytest.fixture
def _mock_auth_token_service():
    """auth_token_service mocké : décode le cookie en payload portant tenant_id = A."""
    mock = AsyncMock()
    mock.decode_access_token = MagicMock(
        return_value={
            "sub": str(uuid.uuid4()),
            "email": "a@test.com",
            "role": "reader",
            "tenant_id": str(_TENANT_A),
            "jti": str(uuid.uuid4()),
            "exp": 9_999_999_999,
        }
    )
    mock.is_jti_blacklisted.return_value = False
    return mock


def _history_row(graham_output) -> dict:
    """Ligne analysis_history reconstructible (graham obligatoire pour /report)."""
    return {
        "id": uuid.UUID(_ANALYSIS_ID),
        "ticker": "MSFT",
        "workflow_name": "value_graham",
        "skills_used": json.dumps(["graham_analysis"]),
        "input_data": None,
        "result": json.dumps({"graham": graham_output.model_dump(mode="json")}),
        "cost_usd": 0.0012,
        "created_at": "2026-06-08T10:00:00+00:00",
    }


@pytest_asyncio.fixture
async def report_client(client, _mock_auth_token_service):
    prev_auth = getattr(app.state, "auth_token_service", None)
    app.state.auth_token_service = _mock_auth_token_service
    try:
        yield client
    finally:
        app.state.auth_token_service = prev_auth


@pytest.mark.asyncio
async def test_get_report_sans_session_renvoie_401(report_client):
    """Lecture non authentifiée → 401 (plus de repli silencieux sur le tenant legacy)."""
    resp = await report_client.get(f"/report/{_ANALYSIS_ID}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_post_report_sans_session_renvoie_401(report_client):
    """Analyse non authentifiée → 401."""
    resp = await report_client.post("/report", json={"ticker": "MSFT"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_report_lecture_sous_tenant_du_demandeur_404_si_masque(report_client):
    """fetchrow s'exécute sous le tenant A ; ligne masquée par la RLS (None) → 404."""
    captured: list = []

    async def _fetchrow(*_args, **_kwargs):
        captured.append(get_current_tenant())
        return None

    app.state.db_pool.fetchrow = AsyncMock(side_effect=_fetchrow)

    resp = await report_client.get(f"/report/{_ANALYSIS_ID}", cookies=_COOKIE)

    assert resp.status_code == 404
    assert captured == [_TENANT_A]


@pytest.mark.asyncio
async def test_get_report_tenant_du_demandeur_renvoie_pdf(report_client, graham_output_msft):
    """Ligne visible sous A → 200 + PDF ; contexte tenant = A au moment du fetchrow."""
    captured: list = []
    row = _history_row(graham_output_msft)

    async def _fetchrow(*_args, **_kwargs):
        captured.append(get_current_tenant())
        return row

    app.state.db_pool.fetchrow = AsyncMock(side_effect=_fetchrow)

    resp = await report_client.get(f"/report/{_ANALYSIS_ID}", cookies=_COOKIE)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert captured == [_TENANT_A]


@pytest.mark.asyncio
async def test_post_report_execute_analyse_sous_tenant_du_demandeur(report_client):
    """POST /report exécute l'orchestrateur sous le tenant A (metering/écriture scopés)."""
    captured: list = []
    base_response = app.state.orchestrator.run_company_analysis.return_value

    async def _run(*_args, **_kwargs):
        captured.append(get_current_tenant())
        return base_response

    app.state.orchestrator.run_company_analysis = AsyncMock(side_effect=_run)

    resp = await report_client.post("/report", json={"ticker": "MSFT"}, cookies=_COOKIE)

    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"
    assert captured == [_TENANT_A]
