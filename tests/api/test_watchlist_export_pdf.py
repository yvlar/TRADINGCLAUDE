"""Tests endpoint GET /watchlist/export.pdf — Sprint 76."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.services.watchlist_pdf_service import WatchlistPdfService


def _make_row(ticker: str = "BNS", score: float | None = 75.0) -> dict:
    return {
        "ticker": ticker,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "composite_alert_threshold": 15.0,
        "composite_score_latest": score,
        "composite_label_latest": "FORT" if score and score >= 70 else "MODERE",
        "derniere_analyse": datetime(2026, 5, 1, tzinfo=timezone.utc),
    }


_FAKE_PDF = b"%PDF-1.4 fake pdf content for watchlist"


@pytest.mark.asyncio
async def test_export_pdf_200():
    """GET /watchlist/export.pdf → 200 + application/pdf."""
    mock_svc = MagicMock(spec=WatchlistPdfService)
    mock_svc.generate_watchlist_pdf = AsyncMock(return_value=_FAKE_PDF)

    app.state.watchlist_pdf_service = mock_svc
    app.state.composite_history_service = MagicMock()
    app.state.db_pool = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/watchlist/export.pdf",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == _FAKE_PDF


@pytest.mark.asyncio
async def test_export_pdf_content_disposition():
    """GET /watchlist/export.pdf → Content-Disposition avec nom de fichier daté."""
    mock_svc = MagicMock(spec=WatchlistPdfService)
    mock_svc.generate_watchlist_pdf = AsyncMock(return_value=_FAKE_PDF)

    app.state.watchlist_pdf_service = mock_svc
    app.state.composite_history_service = MagicMock()
    app.state.db_pool = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/watchlist/export.pdf",
            headers={"Authorization": "Bearer test"},
        )

    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "watchlist-" in cd
    assert ".pdf" in cd


@pytest.mark.asyncio
async def test_export_pdf_404_watchlist_vide():
    """GET /watchlist/export.pdf → 404 si watchlist vide (ValueError levée)."""
    mock_svc = MagicMock(spec=WatchlistPdfService)
    mock_svc.generate_watchlist_pdf = AsyncMock(
        side_effect=ValueError("Watchlist vide")
    )

    app.state.watchlist_pdf_service = mock_svc
    app.state.composite_history_service = MagicMock()
    app.state.db_pool = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/watchlist/export.pdf",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_pdf_passe_pool_et_composite_service():
    """generate_watchlist_pdf reçoit pool et composite_history_service depuis app.state."""
    mock_svc = MagicMock(spec=WatchlistPdfService)
    mock_svc.generate_watchlist_pdf = AsyncMock(return_value=_FAKE_PDF)
    mock_pool = AsyncMock()
    mock_composite_svc = MagicMock()

    app.state.watchlist_pdf_service = mock_svc
    app.state.composite_history_service = mock_composite_svc
    app.state.db_pool = mock_pool

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get(
            "/watchlist/export.pdf",
            headers={"Authorization": "Bearer test"},
        )

    mock_svc.generate_watchlist_pdf.assert_called_once_with(
        pool=mock_pool,
        composite_history_service=mock_composite_svc,
    )


@pytest.mark.asyncio
async def test_export_pdf_bytes_valides():
    """Les bytes retournés commencent par la signature PDF (%PDF)."""
    fake_pdf = b"%PDF-1.4 real content"
    mock_svc = MagicMock(spec=WatchlistPdfService)
    mock_svc.generate_watchlist_pdf = AsyncMock(return_value=fake_pdf)

    app.state.watchlist_pdf_service = mock_svc
    app.state.composite_history_service = MagicMock()
    app.state.db_pool = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/watchlist/export.pdf",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.content[:4] == b"%PDF"
