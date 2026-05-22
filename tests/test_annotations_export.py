"""Tests Sprint 85 — export CSV/Excel des annotations (GET /annotations/export.csv et export.xlsx)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.services.annotation_service import AnnotationService


def _make_row(ticker: str = "BNS.TO") -> dict:
    return {
        "annotation_id": str(uuid.uuid4()),
        "analysis_id": str(uuid.uuid4()),
        "ticker": ticker,
        "note": "Note de test",
        "created_at": datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    }


@pytest_asyncio.fixture
async def annotation_client(client):
    """Injecte un AnnotationService mocké dans l'état de l'application."""
    mock_service = AsyncMock(spec=AnnotationService)
    fastapi_app.state.annotation_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_export_csv_appelle_get_all_with_ticker_et_retourne_ticker(annotation_client) -> None:
    """GET /annotations/export.csv appelle get_all_with_ticker() et inclut le ticker dans le CSV."""
    client, mock_service = annotation_client
    row = _make_row("BNS.TO")
    mock_service.get_all_with_ticker.return_value = [row]

    resp = await client.get("/annotations/export.csv")

    assert resp.status_code == 200
    mock_service.get_all_with_ticker.assert_called_once()
    text = resp.content.decode("utf-8-sig")
    assert "BNS.TO" in text


@pytest.mark.asyncio
async def test_export_csv_200_content_type_et_colonnes(annotation_client) -> None:
    """GET /annotations/export.csv → 200 + media_type contient text/csv + header CSV correct."""
    client, mock_service = annotation_client
    mock_service.get_all_with_ticker.return_value = [_make_row()]

    resp = await client.get("/annotations/export.csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    first_line = resp.content.decode("utf-8-sig").splitlines()[0]
    assert "Ticker" in first_line
    assert "Note" in first_line
    assert "Analysis ID" in first_line


@pytest.mark.asyncio
async def test_export_xlsx_200_content_type(annotation_client) -> None:
    """GET /annotations/export.xlsx → 200 + media_type xlsx."""
    client, mock_service = annotation_client
    mock_service.get_all_with_ticker.return_value = [_make_row()]

    resp = await client.get("/annotations/export.xlsx")

    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
