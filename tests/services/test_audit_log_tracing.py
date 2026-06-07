"""Tests d'intégration — les mutations métier émettent une entrée d'audit (E2-S3).

Vérifie le câblage des 3 sites de traçage (watchlist, annotation, clé API) et le
caractère best-effort : un échec d'audit n'avorte jamais la mutation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.watchlist import WatchlistCreate
from app.services.annotation_service import AnnotationService
from app.services.api_key_service import ApiKeyService
from app.services.audit_log_service import AuditLogService
from app.services.watchlist_service import WatchlistService

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def _watchlist_row(entry_id: uuid.UUID) -> dict:
    return {
        "id": entry_id, "ticker": "BNS", "workflow": "value_graham",
        "ratios": None, "score_alerte_min": None, "created_at": _NOW,
        "last_analyzed_at": None, "last_score": None, "last_verdict": None,
        "last_intrinsic_value": None, "last_price_checked": None,
        "price_alert_threshold_pct": 0.10, "last_composite_score": None,
        "composite_alert_threshold": None, "esg_alert_threshold": None,
        "last_esg_score": None,
    }


def _annotation_row(analysis_id: str) -> dict:
    return {
        "annotation_id": str(uuid.uuid4()), "analysis_id": analysis_id,
        "note": "Note", "tags": ["value"], "created_at": _NOW, "updated_at": _NOW,
    }


def _api_key_row(key_id: uuid.UUID) -> dict:
    return {
        "id": key_id, "name": "Marie", "role": "reader", "active": True,
        "created_at": _NOW, "last_used_at": None, "expires_at": None,
        "tenant_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
    }


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_entry_trace_audit():
    entry_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetchrow = AsyncMock(return_value=_watchlist_row(entry_id))
    audit = AsyncMock(spec=AuditLogService)
    service = WatchlistService(db_pool=pool, audit_log=audit)

    await service.add_entry(WatchlistCreate(ticker="bns", workflow="value_graham"))

    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == "watchlist.create"
    assert audit.record.call_args.kwargs["cible_id"] == str(entry_id)


@pytest.mark.asyncio
async def test_delete_entry_trace_audit():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="DELETE 1")
    audit = AsyncMock(spec=AuditLogService)
    service = WatchlistService(db_pool=pool, audit_log=audit)

    assert await service.delete_entry("entry-1") is True
    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == "watchlist.delete"


@pytest.mark.asyncio
async def test_delete_entry_absent_ne_trace_pas():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="DELETE 0")
    audit = AsyncMock(spec=AuditLogService)
    service = WatchlistService(db_pool=pool, audit_log=audit)

    assert await service.delete_entry("inconnu") is False
    audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_entry_best_effort_si_audit_echoue():
    """L'échec de l'audit ne doit pas faire échouer l'ajout watchlist."""
    entry_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetchrow = AsyncMock(return_value=_watchlist_row(entry_id))
    audit = AsyncMock(spec=AuditLogService)
    audit.record.side_effect = Exception("audit DB down")
    service = WatchlistService(db_pool=pool, audit_log=audit)

    result = await service.add_entry(WatchlistCreate(ticker="bns", workflow="value_graham"))
    assert result.ticker == "BNS"


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_trace_audit():
    analysis_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_annotation_row(analysis_id))
    audit = AsyncMock(spec=AuditLogService)
    service = AnnotationService(db_pool=pool, audit_log=audit)

    await service.upsert(analysis_id, "Note", ["value"])

    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == "annotation.upsert"
    assert audit.record.call_args.kwargs["cible_id"] == analysis_id


@pytest.mark.asyncio
async def test_upsert_best_effort_si_audit_echoue():
    analysis_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_annotation_row(analysis_id))
    audit = AsyncMock(spec=AuditLogService)
    audit.record.side_effect = Exception("audit DB down")
    service = AnnotationService(db_pool=pool, audit_log=audit)

    annotation = await service.upsert(analysis_id, "Note", ["value"])
    assert annotation.note == "Note"


# ---------------------------------------------------------------------------
# Clé API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_key_trace_audit():
    key_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_api_key_row(key_id))
    audit = AsyncMock(spec=AuditLogService)
    service = ApiKeyService(db_pool=pool, audit_log=audit)

    await service.create_key(name="Marie", role="reader")

    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == "api_key.create"
    assert audit.record.call_args.kwargs["cible_id"] == str(key_id)


@pytest.mark.asyncio
async def test_revoke_key_trace_audit():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="UPDATE 1")
    audit = AsyncMock(spec=AuditLogService)
    service = ApiKeyService(db_pool=pool, audit_log=audit)
    key_id = uuid.uuid4()

    assert await service.revoke_key(key_id) is True
    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == "api_key.revoke"


@pytest.mark.asyncio
async def test_revoke_key_absente_ne_trace_pas():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="UPDATE 0")
    audit = AsyncMock(spec=AuditLogService)
    service = ApiKeyService(db_pool=pool, audit_log=audit)

    assert await service.revoke_key(uuid.uuid4()) is False
    audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_key_best_effort_si_audit_echoue():
    key_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_api_key_row(key_id))
    audit = AsyncMock(spec=AuditLogService)
    audit.record.side_effect = Exception("audit DB down")
    service = ApiKeyService(db_pool=pool, audit_log=audit)

    token, record = await service.create_key(name="Marie", role="reader")
    assert isinstance(token, str) and record.name == "Marie"
