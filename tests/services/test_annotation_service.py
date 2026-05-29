"""Tests unitaires pour AnnotationService — mock pool asyncpg."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.annotation_service import AnnotationService


def _make_analysis_id() -> str:
    return str(uuid.uuid4())


def _make_row(analysis_id: str, note: str, tags: list[str] | None = None) -> MagicMock:
    """Simule une Row asyncpg pour une annotation."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "annotation_id": str(uuid.uuid4()),
        "analysis_id": analysis_id,
        "note": note,
        "tags": tags if tags is not None else [],
        "created_at": datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    }[key]
    return row


@pytest.fixture
def mock_pool() -> AsyncMock:
    pool = AsyncMock()
    return pool


@pytest.fixture
def service(mock_pool: AsyncMock) -> AnnotationService:
    return AnnotationService(db_pool=mock_pool)


@pytest.mark.asyncio
async def test_upsert_crée_annotation(service: AnnotationService, mock_pool: AsyncMock) -> None:
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Note de test")

    annotation = await service.upsert(analysis_id, "Note de test")

    assert annotation.note == "Note de test"
    assert annotation.analysis_id == analysis_id
    mock_pool.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_met_à_jour_si_existant(service: AnnotationService, mock_pool: AsyncMock) -> None:
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Note mise à jour")

    annotation = await service.upsert(analysis_id, "Note mise à jour")

    assert annotation.note == "Note mise à jour"


@pytest.mark.asyncio
async def test_get_retourne_annotation_existante(service: AnnotationService, mock_pool: AsyncMock) -> None:
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Ma note")

    annotation = await service.get(analysis_id)

    assert annotation is not None
    assert annotation.note == "Ma note"
    assert annotation.analysis_id == analysis_id


@pytest.mark.asyncio
async def test_get_retourne_none_si_absent(service: AnnotationService, mock_pool: AsyncMock) -> None:
    mock_pool.fetchrow.return_value = None

    annotation = await service.get(_make_analysis_id())

    assert annotation is None


@pytest.mark.asyncio
async def test_get_retourne_none_si_exception(service: AnnotationService, mock_pool: AsyncMock) -> None:
    mock_pool.fetchrow.side_effect = Exception("DB indisponible")

    annotation = await service.get(_make_analysis_id())

    assert annotation is None


@pytest.mark.asyncio
async def test_upsert_persiste_les_tags(service: AnnotationService, mock_pool: AsyncMock) -> None:
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Note", ["value", "growth"])

    annotation = await service.upsert(analysis_id, "Note", ["value", "growth"])

    assert annotation.tags == ["value", "growth"]
    # fetchrow(query, analysis_id, note, tags) → les tags sont le 3e paramètre lié
    assert mock_pool.fetchrow.call_args.args[3] == ["value", "growth"]


@pytest.mark.asyncio
async def test_get_retourne_les_tags(service: AnnotationService, mock_pool: AsyncMock) -> None:
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Note", ["dividende"])

    annotation = await service.get(analysis_id)

    assert annotation is not None
    assert annotation.tags == ["dividende"]
