"""Écritures métier rattachées au tenant (E3-S2) — défaut legacy + tenant explicite.

Chaque service d'écriture des 6 tables métier doit poser `tenant_id` à l'INSERT :
faute de tenant explicite (threading E3-S4 pas encore câblé), la ligne atterrit sur
le tenant « legacy ». Le binding est ajouté en DERNIER paramètre — on l'assert via
`args[-1]` pour rester robuste à l'ordre des autres colonnes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.tenant import LEGACY_TENANT_ID
from app.models.watchlist import WatchlistCreate
from app.services.alert_history_service import AlertHistoryService
from app.services.annotation_service import AnnotationService
from app.services.composite_history_service import CompositeHistoryService
from app.services.esg_history_service import EsgHistoryService
from app.services.watchlist_service import WatchlistService

_EXPLICIT_TENANT = uuid.uuid4()

# Les deux cas couverts pour chaque service : sans tenant → legacy, avec tenant → respecté.
_CASES = [
    pytest.param({}, LEGACY_TENANT_ID, id="defaut-legacy"),
    pytest.param({"tenant_id": _EXPLICIT_TENANT}, _EXPLICIT_TENANT, id="tenant-explicite"),
]


@pytest.mark.parametrize("kwargs,expected", _CASES)
async def test_composite_record_tenant(kwargs, expected):
    pool = AsyncMock()
    await CompositeHistoryService(pool).record(
        "BNS", 72.5, "FORT", "value_graham", **kwargs
    )
    assert pool.execute.await_args.args[-1] == expected


@pytest.mark.parametrize("kwargs,expected", _CASES)
async def test_esg_record_tenant(kwargs, expected):
    pool = AsyncMock()
    await EsgHistoryService(pool).record("RY", 11.5, **kwargs)
    assert pool.execute.await_args.args[-1] == expected


@pytest.mark.parametrize("kwargs,expected", _CASES)
async def test_alert_record_tenant(kwargs, expected):
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value={"id": 1})
    await AlertHistoryService(pool).record("BNS", "ESG", 3.5, 5.0, "msg", **kwargs)
    assert pool.fetchrow.await_args.args[-1] == expected


def _annotation_row() -> dict:
    return {
        "annotation_id": str(uuid.uuid4()),
        "analysis_id": str(uuid.uuid4()),
        "note": "n",
        "tags": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.mark.parametrize("kwargs,expected", _CASES)
async def test_annotation_upsert_tenant(kwargs, expected):
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_annotation_row())
    await AnnotationService(pool).upsert(str(uuid.uuid4()), "note", **kwargs)
    assert pool.fetchrow.await_args.args[-1] == expected


def _watchlist_row() -> dict:
    return {
        "id": uuid.uuid4(), "ticker": "BNS", "workflow": "value_graham",
        "ratios": None, "score_alerte_min": None,
        "created_at": datetime.now(timezone.utc), "last_analyzed_at": None,
        "last_score": None, "last_verdict": None, "last_intrinsic_value": None,
        "last_price_checked": None, "price_alert_threshold_pct": 0.10,
        "last_composite_score": None, "composite_alert_threshold": None,
        "esg_alert_threshold": None, "last_esg_score": None,
    }


@pytest.mark.parametrize("kwargs,expected", _CASES)
async def test_watchlist_add_entry_tenant(kwargs, expected):
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetchrow = AsyncMock(return_value=_watchlist_row())
    await WatchlistService(pool).add_entry(
        WatchlistCreate(ticker="bns", workflow="value_graham"), **kwargs
    )
    assert pool.fetchrow.await_args.args[-1] == expected


async def test_threading_contextvar_renseigne_le_tenant_sans_param_explicite():
    """E3-S4 : sans param explicite, l'écriture prend le tenant résolu de la requête (ContextVar)."""
    from tests.conftest import as_tenant

    tenant_requete = uuid.uuid4()
    pool = AsyncMock()
    with as_tenant(tenant_requete):
        await CompositeHistoryService(pool).record("BNS", 72.5, "FORT", "value_graham")
    assert pool.execute.await_args.args[-1] == tenant_requete
