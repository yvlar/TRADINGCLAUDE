"""Tests endpoint GET /monthly-report — Sprint 81."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.services.monthly_report_service import MonthlyReportService
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.watchlist_pdf_service import WatchlistPdfService

_FAKE_WATCHLIST_PDF = b"%PDF-1.4 fake monthly watchlist"
_FAKE_SCREENER_PDF = b"%PDF-1.4 fake monthly screener"


def _setup_state(watchlist_pdf: bytes = _FAKE_WATCHLIST_PDF, empty: bool = False) -> None:
    """Configure app.state avec les services mockés pour les tests endpoint."""
    mock_monthly = MagicMock(spec=MonthlyReportService)
    if empty:
        mock_monthly.generate = AsyncMock(
            side_effect=ValueError("Watchlist vide — aucun ticker à inclure dans le rapport")
        )
    else:
        mock_monthly.generate = AsyncMock(return_value=(watchlist_pdf, _FAKE_SCREENER_PDF))

    app.state.monthly_report_service = mock_monthly
    app.state.db_pool = AsyncMock()
    app.state.watchlist_pdf_service = MagicMock(spec=WatchlistPdfService)
    app.state.screener_pdf_service = MagicMock(spec=ScreenerPdfService)


@pytest.mark.asyncio
async def test_monthly_report_200():
    """GET /monthly-report → 200 avec contenu PDF."""
    _setup_state()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/monthly-report",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code == 200
    assert resp.content == _FAKE_WATCHLIST_PDF


@pytest.mark.asyncio
async def test_monthly_report_media_type():
    """GET /monthly-report → Content-Type application/pdf."""
    _setup_state()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/monthly-report",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_monthly_report_content_disposition():
    """GET /monthly-report → Content-Disposition avec nom de fichier daté."""
    _setup_state()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/monthly-report",
            headers={"Authorization": "Bearer test"},
        )

    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "rapport-mensuel-" in cd
    assert ".pdf" in cd


@pytest.mark.asyncio
async def test_monthly_report_404_watchlist_vide():
    """GET /monthly-report → 404 si la watchlist est vide (ValueError propagée)."""
    _setup_state(empty=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/monthly-report",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code == 404
