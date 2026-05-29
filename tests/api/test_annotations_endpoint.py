"""Tests Sprint 78 — endpoints POST /annotations et GET /annotations/{analysis_id}."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.annotation import Annotation
from app.services.annotation_service import AnnotationService


def _make_annotation(
    analysis_id: str, note: str = "Note de test", tags: list[str] | None = None
) -> Annotation:
    return Annotation(
        annotation_id=str(uuid.uuid4()),
        analysis_id=analysis_id,
        note=note,
        tags=tags or [],
        created_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest_asyncio.fixture
async def annotation_client(client):
    """Injecte un AnnotationService mocké dans l'état de l'application."""
    mock_service = AsyncMock(spec=AnnotationService)
    fastapi_app.state.annotation_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_post_annotations_crée_201(annotation_client) -> None:
    """POST /annotations → 201 avec l'annotation créée."""
    client, mock_service = annotation_client
    analysis_id = str(uuid.uuid4())
    annotation = _make_annotation(analysis_id, "Note ACHAT BNS")
    mock_service.upsert.return_value = annotation

    resp = await client.post(
        "/annotations",
        json={"analysis_id": analysis_id, "note": "Note ACHAT BNS"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["analysis_id"] == analysis_id
    assert data["note"] == "Note ACHAT BNS"
    mock_service.upsert.assert_called_once_with(analysis_id, "Note ACHAT BNS", [])


@pytest.mark.asyncio
async def test_post_annotations_avec_tags_round_trip(annotation_client) -> None:
    """POST /annotations avec tags → 201 ; tags normalisés transmis au service et renvoyés."""
    client, mock_service = annotation_client
    analysis_id = str(uuid.uuid4())
    annotation = _make_annotation(analysis_id, "Note", tags=["value", "growth"])
    mock_service.upsert.return_value = annotation

    resp = await client.post(
        "/annotations",
        json={"analysis_id": analysis_id, "note": "Note", "tags": ["  Value ", "GROWTH", "value"]},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["tags"] == ["value", "growth"]
    # tags normalisés (trim/minuscule/dédoublonnage) côté modèle avant d'atteindre le service
    mock_service.upsert.assert_called_once_with(analysis_id, "Note", ["value", "growth"])


@pytest.mark.asyncio
async def test_post_annotations_note_vide_422(annotation_client) -> None:
    """POST /annotations avec note vide → 422 validation error."""
    client, _ = annotation_client
    analysis_id = str(uuid.uuid4())

    resp = await client.post(
        "/annotations",
        json={"analysis_id": analysis_id, "note": ""},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_annotation_existante_200(annotation_client) -> None:
    """GET /annotations/{analysis_id} → 200 si annotation présente."""
    client, mock_service = annotation_client
    analysis_id = str(uuid.uuid4())
    mock_service.get.return_value = _make_annotation(analysis_id, "Note existante")

    resp = await client.get(f"/annotations/{analysis_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == analysis_id
    assert data["note"] == "Note existante"


@pytest.mark.asyncio
async def test_get_annotation_absente_404(annotation_client) -> None:
    """GET /annotations/{analysis_id} → 404 si aucune annotation."""
    client, mock_service = annotation_client
    mock_service.get.return_value = None

    resp = await client.get(f"/annotations/{uuid.uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_annotations_idempotent_upsert(annotation_client) -> None:
    """POST /annotations deux fois sur le même analysis_id → 201 les deux fois (upsert)."""
    client, mock_service = annotation_client
    analysis_id = str(uuid.uuid4())
    mock_service.upsert.return_value = _make_annotation(analysis_id, "Note modifiée")

    for note in ["Note initiale", "Note modifiée"]:
        resp = await client.post(
            "/annotations",
            json={"analysis_id": analysis_id, "note": note},
        )
        assert resp.status_code == 201

    assert mock_service.upsert.call_count == 2
