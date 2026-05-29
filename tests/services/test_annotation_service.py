"""Tests unitaires pour AnnotationService — mock pool asyncpg."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.annotation_service import AnnotationService


def _make_analysis_id() -> str:
    return str(uuid.uuid4())


def _make_row(analysis_id: str, note: str, tags: str = "[]") -> MagicMock:
    """Simule une Row asyncpg pour une annotation (tags = JSONB renvoyé en str)."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "annotation_id": str(uuid.uuid4()),
        "analysis_id": analysis_id,
        "note": note,
        "tags": tags,
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
async def test_upsert_persiste_et_normalise_les_tags(
    service: AnnotationService, mock_pool: AsyncMock
) -> None:
    """upsert normalise les tags (trim/minuscule/dédoublonnage) et les passe en JSONB."""
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(
        analysis_id, "Note", tags='["value", "growth"]'
    )

    annotation = await service.upsert(analysis_id, "Note", ["  Value ", "GROWTH", "value"])

    assert annotation.tags == ["value", "growth"]
    # 3e paramètre positionnel = JSONB normalisé (dédoublonné, minuscule)
    tags_param = mock_pool.fetchrow.call_args.args[3]
    assert tags_param == '["value", "growth"]'


@pytest.mark.asyncio
async def test_get_decode_tags_jsonb(service: AnnotationService, mock_pool: AsyncMock) -> None:
    """get décode le champ tags JSONB renvoyé en str par asyncpg."""
    analysis_id = _make_analysis_id()
    mock_pool.fetchrow.return_value = _make_row(analysis_id, "Note", tags='["dividende"]')

    annotation = await service.get(analysis_id)

    assert annotation is not None
    assert annotation.tags == ["dividende"]
