"""Tests Sprint 99 — AlertHistoryService (aucun appel DB reel — asyncpg mocke)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.alert_history_service import AlertHistoryService


def _make_row(
    id_: int = 1,
    ticker: str = "BNS",
    type_: str = "ESG_DEGRADATION",
    valeur: float | None = 3.5,
    seuil: float | None = 5.0,
    message: str | None = "test",
    created_at: datetime | None = None,
) -> dict:
    """Simule une ligne asyncpg.Record sous forme de dict."""
    return {
        "id": id_,
        "ticker": ticker,
        "type": type_,
        "valeur": valeur,
        "seuil": seuil,
        "message": message,
        "created_at": created_at or datetime.now(timezone.utc),
    }


def _make_mock_pool(
    fetchrow_return=None,
    fetch_return=None,
) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=fetchrow_return or {"id": 1})
    pool.fetch = AsyncMock(return_value=fetch_return or [])
    return pool


# ---------------------------------------------------------------------------
# Test 1 : record() passe les bons parametres SQL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_sql_params_corrects():
    """record() doit appeler pool.fetchrow avec ticker, type, valeur, seuil, message."""
    pool = _make_mock_pool(fetchrow_return={"id": 42})
    service = AlertHistoryService(db_pool=pool)

    alert_id = await service.record(
        ticker="BNS",
        type="ESG_DEGRADATION",
        valeur=3.5,
        seuil=5.0,
        message="Score ESG dégradé",
    )

    pool.fetchrow.assert_awaited_once()
    call_args = pool.fetchrow.await_args
    # [0]=SQL, [1]=ticker, [2]=type, [3]=valeur, [4]=seuil, [5]=message
    assert call_args.args[1] == "BNS"
    assert call_args.args[2] == "ESG_DEGRADATION"
    assert call_args.args[3] == pytest.approx(3.5)
    assert call_args.args[4] == pytest.approx(5.0)
    assert call_args.args[5] == "Score ESG dégradé"
    assert alert_id == 42


# ---------------------------------------------------------------------------
# Test 2 : get_recent() tri DESC + respect limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recent_tri_desc_et_limit():
    """get_recent() doit passer limit a la DB et retourner les alertes dans l'ordre recu."""
    rows = [
        _make_row(id_=3, created_at=datetime(2026, 5, 23, 10, tzinfo=timezone.utc)),
        _make_row(id_=2, created_at=datetime(2026, 5, 22, 10, tzinfo=timezone.utc)),
        _make_row(id_=1, created_at=datetime(2026, 5, 21, 10, tzinfo=timezone.utc)),
    ]
    pool = _make_mock_pool(fetch_return=rows)
    service = AlertHistoryService(db_pool=pool)

    result = await service.get_recent(limit=10)

    pool.fetch.assert_awaited_once()
    # Verifie que limit=10 est passe comme parametre
    assert pool.fetch.await_args.args[1] == 10
    assert len(result) == 3
    assert result[0]["id"] == 3
    assert result[1]["id"] == 2
    assert result[2]["id"] == 1


# ---------------------------------------------------------------------------
# Test 3 : endpoint GET /alerts?limit=2 retourne 200 + liste
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_alerts_endpoint_200(client):
    """GET /alerts?limit=2 doit retourner 200 et une liste d'alertes."""
    from app.api.main import app

    mock_svc = AsyncMock()
    mock_svc.get_recent = AsyncMock(
        return_value=[
            {
                "id": 1,
                "ticker": "BNS",
                "type": "ESG_DEGRADATION",
                "valeur": 3.5,
                "seuil": 5.0,
                "message": "test",
                "created_at": "2026-05-23T10:00:00+00:00",
            },
            {
                "id": 2,
                "ticker": "TD",
                "type": "SCREENER_FORT",
                "valeur": 75.0,
                "seuil": 70.0,
                "message": None,
                "created_at": "2026-05-23T09:00:00+00:00",
            },
        ]
    )
    app.state.alert_history_service = mock_svc

    resp = await client.get("/alerts?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert len(data["alerts"]) == 2
    assert data["alerts"][0]["ticker"] == "BNS"
    assert data["alerts"][1]["type"] == "SCREENER_FORT"
    mock_svc.get_recent.assert_awaited_once_with(2)
