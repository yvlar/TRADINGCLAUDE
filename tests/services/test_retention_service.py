"""Tests unitaires du RetentionService (E4-S6) — purge par plan, sans DB réelle.

La borne temporelle exacte (J-31 purgé / J-29 conservé) et l'isolation RLS de la purge sont
prouvées en intégration sous PG migré (`tests/integration/test_retention_purge_rls.py`). Ici on
verrouille : le périmètre des tables, la colonne d'horodatage par table, le binding de
`retention_days`, et le fail-safe (plan/borne absent → aucun DELETE).
"""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.services.retention_service import (
    _PURGEABLE_TABLES,
    RetentionService,
    _parse_delete_count,
)

_TENANT = UUID("00000000-0000-0000-0000-0000000000aa")
_FREE_ROW = {"plan": "free", "retention_days": 30}


def _service(*, plan_row: dict | None = _FREE_ROW, delete_status: str = "DELETE 0") -> tuple[RetentionService, AsyncMock]:
    """Fabrique un RetentionService avec db.fetchrow/execute mockés ; retourne (service, db)."""
    db = AsyncMock()
    db.fetchrow = AsyncMock(return_value=plan_row)
    db.execute = AsyncMock(return_value=delete_status)
    return RetentionService(db_pool=db), db


def test_perimetre_tables_purgees():
    """Le périmètre purgé est exactement les 4 tables historiques avec leur colonne d'horodatage."""
    assert _PURGEABLE_TABLES == (
        ("analysis_history", "created_at"),
        ("composite_score_history", "recorded_at"),
        ("esg_score_history", "recorded_at"),
        ("alert_history", "created_at"),
    )
    # usage_events (facturation), watchlist (état) et annotations (contenu utilisateur) sont exclus.
    tables = {t for t, _ in _PURGEABLE_TABLES}
    assert "usage_events" not in tables
    assert "watchlist" not in tables
    assert "annotations" not in tables


@pytest.mark.asyncio
async def test_resolve_plan_vers_retention():
    service, db = _service()
    resolved = await service._resolve_retention(_TENANT)
    assert resolved == ("free", 30)
    # Résolution en une seule requête (join tenants → plan_limits).
    assert db.fetchrow.await_count == 1


@pytest.mark.asyncio
async def test_purge_emet_un_delete_par_table_avec_borne_liee():
    """Chaque table purgée reçoit un DELETE scopé par sa colonne d'âge + retention_days lié en str."""
    service, db = _service(delete_status="DELETE 3")
    result = await service.purge_tenant(_TENANT)

    assert result is not None
    assert result.plan == "free"
    assert result.retention_days == 30
    # Un DELETE par table, dans l'ordre du périmètre.
    assert db.execute.await_count == len(_PURGEABLE_TABLES)
    for call, (table, ts_column) in zip(db.execute.await_args_list, _PURGEABLE_TABLES):
        sql, arg = call.args[0], call.args[1]
        assert f"DELETE FROM {table} " in sql
        assert f"WHERE {ts_column} < NOW() - ($1 || ' days')::interval" in sql
        # retention_days lié en str (patron interval de get_metrics/aggregate), jamais interpolé.
        assert arg == "30"
        assert "30" not in sql

    assert result.deleted_by_table == {t: 3 for t, _ in _PURGEABLE_TABLES}
    assert result.total_deleted == 3 * len(_PURGEABLE_TABLES)


@pytest.mark.asyncio
async def test_fail_safe_plan_absent_aucune_purge():
    """Tenant/plan introuvable (fetchrow None) → aucun DELETE (fail-safe)."""
    service, db = _service(plan_row=None)
    result = await service.purge_tenant(_TENANT)
    assert result is None
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fail_safe_retention_null_aucune_purge():
    """retention_days NULL → aucun DELETE (un plan mal configuré ne supprime rien)."""
    service, db = _service(plan_row={"plan": "broken", "retention_days": None})
    result = await service.purge_tenant(_TENANT)
    assert result is None
    db.execute.assert_not_awaited()


@pytest.mark.parametrize(
    ("status", "expected"),
    [("DELETE 0", 0), ("DELETE 7", 7), ("DELETE 142", 142), ("", 0), ("DELETE", 0)],
)
def test_parse_delete_count(status: str, expected: int):
    assert _parse_delete_count(status) == expected
