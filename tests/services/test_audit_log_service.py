"""Tests unitaires AuditLogService — journal d'audit append-only (E2-S3).

asyncpg mocké via AsyncMock — aucune DB réelle (validation runtime = job CI migrations).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.audit_log_service import (
    AuditLogService,
    record_audit_safe,
)

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def _make_row(
    *,
    action: str = "watchlist.create",
    cible_type: str = "watchlist",
    cible_id: str | None = "abc",
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    metadata: str | dict = "{}",
    created_at: datetime = _NOW,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "cible_type": cible_type,
        "cible_id": cible_id,
        "metadata": metadata,
        "created_at": created_at,
    }


class TestRecord:

    @pytest.mark.asyncio
    async def test_record_insere_et_retourne_entree(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = AuditLogService(db_pool=pool)

        entry = await svc.record(
            action="watchlist.create",
            cible_type="watchlist",
            cible_id="abc",
            metadata={"ticker": "BNS"},
        )

        assert entry.action == "watchlist.create"
        assert entry.cible_type == "watchlist"
        pool.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_serialise_metadata_en_json(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = AuditLogService(db_pool=pool)

        await svc.record(
            action="api_key.create",
            cible_type="api_key",
            cible_id="id-1",
            metadata={"name": "Yves", "role": "admin"},
        )

        # query=args[0], tenant=1, user=2, action=3, cible_type=4, cible_id=5, metadata=6
        meta_param = pool.fetchrow.call_args.args[6]
        assert json.loads(meta_param) == {"name": "Yves", "role": "admin"}

    @pytest.mark.asyncio
    async def test_record_metadata_none_devient_objet_vide(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = AuditLogService(db_pool=pool)

        await svc.record(action="watchlist.delete", cible_type="watchlist", cible_id="x")

        assert pool.fetchrow.call_args.args[6] == "{}"

    @pytest.mark.asyncio
    async def test_record_convertit_ids_en_str(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = AuditLogService(db_pool=pool)
        uid = uuid.uuid4()
        tid = uuid.uuid4()

        await svc.record(
            action="watchlist.create",
            cible_type="watchlist",
            cible_id="x",
            user_id=uid,
            tenant_id=tid,
        )

        assert pool.fetchrow.call_args.args[1] == str(tid)
        assert pool.fetchrow.call_args.args[2] == str(uid)

    @pytest.mark.asyncio
    async def test_record_parse_metadata_str_jsonb(self):
        """asyncpg renvoie le JSONB en texte — _row_to_entry doit le désérialiser."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(
            return_value=_make_row(metadata=json.dumps({"ticker": "TD"}))
        )
        svc = AuditLogService(db_pool=pool)

        entry = await svc.record(action="watchlist.create", cible_type="watchlist", cible_id="x")

        assert entry.metadata == {"ticker": "TD"}


class TestListRecent:

    @pytest.mark.asyncio
    async def test_list_recent_retourne_entrees(self):
        rows = [
            _make_row(action="watchlist.create", created_at=_NOW),
            _make_row(action="api_key.revoke", created_at=_NOW),
        ]
        pool = AsyncMock()
        pool.fetch = AsyncMock(return_value=rows)
        svc = AuditLogService(db_pool=pool)

        entries = await svc.list_recent(limit=10)

        assert len(entries) == 2
        # La limite est passée comme paramètre lié, pas interpolée.
        assert pool.fetch.call_args.args[1] == 10

    @pytest.mark.asyncio
    async def test_list_recent_ordonne_par_created_at_desc(self):
        """Le tri DESC est garanti par la requête (ORDER BY created_at DESC)."""
        pool = AsyncMock()
        pool.fetch = AsyncMock(return_value=[])
        svc = AuditLogService(db_pool=pool)

        await svc.list_recent()

        query = pool.fetch.call_args.args[0]
        assert "ORDER BY created_at DESC" in query


class TestAppendOnly:

    def test_service_n_expose_aucune_mutation(self):
        """Append-only : ni update ni delete exposés (contrat Loi 25)."""
        methods = {m for m in dir(AuditLogService) if not m.startswith("_")}
        assert methods == {"record", "list_recent"}


class TestRecordAuditSafe:

    @pytest.mark.asyncio
    async def test_safe_noop_si_audit_none(self):
        # Ne doit pas lever même sans service (best-effort, audit désactivé).
        await record_audit_safe(None, "watchlist.create", "watchlist", "x")

    @pytest.mark.asyncio
    async def test_safe_delegue_a_record(self):
        audit = AsyncMock(spec=AuditLogService)
        await record_audit_safe(
            audit, "watchlist.create", "watchlist", "x", metadata={"ticker": "BNS"}
        )
        audit.record.assert_awaited_once_with(
            action="watchlist.create",
            cible_type="watchlist",
            cible_id="x",
            metadata={"ticker": "BNS"},
        )

    @pytest.mark.asyncio
    async def test_safe_avale_exception(self):
        """Une panne d'audit ne doit jamais remonter à l'appelant."""
        audit = AsyncMock(spec=AuditLogService)
        audit.record.side_effect = Exception("DB audit indisponible")
        # Aucune exception attendue.
        await record_audit_safe(audit, "watchlist.delete", "watchlist", "x")
