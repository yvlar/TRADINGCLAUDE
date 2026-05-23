"""Tests CI standard pour PdfReportService et GET /ticker-report/{ticker} — Sprint 63.

Aucun appel Claude réel. PdfReportService utilise reportlab (synchrone).
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.services.composite_history_service import CompositeHistoryPoint
from app.services.pdf_report_service import PdfReportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_history_point(
    ticker: str = "BNS",
    score: float = 75.0,
    label: str = "FORT",
    workflow: str = "value_graham",
    recorded_at: datetime | None = None,
) -> CompositeHistoryPoint:
    return CompositeHistoryPoint(
        id=str(uuid.uuid4()),
        ticker=ticker,
        score=score,
        label=label,
        workflow=workflow,
        recorded_at=recorded_at or datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc),
    )


def _make_history(n: int = 3, ticker: str = "BNS") -> list[CompositeHistoryPoint]:
    return [
        _make_history_point(
            ticker=ticker,
            score=float(60 + i * 5),
            label="FORT" if 60 + i * 5 >= 70 else "MODERE",
            recorded_at=datetime(2026, 5, i + 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests : PdfReportService — unité
# ---------------------------------------------------------------------------


class TestPdfReportService:

    def test_instantiation_sans_erreur(self):
        svc = PdfReportService()
        assert svc is not None

    @pytest.mark.asyncio
    async def test_generate_ticker_report_retourne_bytes_non_vides(self):
        svc = PdfReportService()
        history = _make_history(5)
        pdf = await svc.generate_ticker_report(ticker="BNS", history=history, last_analysis=None)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    @pytest.mark.asyncio
    async def test_generate_ticker_report_debut_pdf(self):
        """Les bytes retournés commencent par la signature PDF (%PDF-)."""
        svc = PdfReportService()
        history = _make_history(2)
        pdf = await svc.generate_ticker_report(ticker="BNS", history=history, last_analysis=None)
        assert pdf[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_generate_ticker_report_historique_vide_retourne_pdf_valide(self):
        svc = PdfReportService()
        pdf = await svc.generate_ticker_report(ticker="BNS", history=[], last_analysis=None)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0
        assert pdf[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_generate_ticker_report_last_analysis_none_retourne_pdf_valide(self):
        svc = PdfReportService()
        history = _make_history(3)
        pdf = await svc.generate_ticker_report(
            ticker="BNS", history=history, last_analysis=None
        )
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_generate_ticker_report_label_faible(self):
        """PDF valide même avec label FAIBLE (score bas)."""
        svc = PdfReportService()
        history = [_make_history_point(score=20.0, label="FAIBLE")]
        pdf = await svc.generate_ticker_report(ticker="TST", history=history, last_analysis=None)
        assert pdf[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_generate_ticker_report_label_modere(self):
        """PDF valide avec label MODERE."""
        svc = PdfReportService()
        history = [_make_history_point(score=55.0, label="MODERE")]
        pdf = await svc.generate_ticker_report(ticker="TST", history=history, last_analysis=None)
        assert pdf[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Tests : GET /ticker-report/{ticker}
# ---------------------------------------------------------------------------


class TestTickerReportEndpoint:

    @pytest_asyncio.fixture
    async def ticker_report_client(self, client):
        """Client HTTP avec composite_history_service et pdf_report_service mockés."""
        history = _make_history(5, ticker="BNS")

        mock_history_svc = AsyncMock()
        mock_history_svc.get_history = AsyncMock(return_value=history)

        mock_pdf_svc = AsyncMock(spec=PdfReportService)
        mock_pdf_svc.generate_ticker_report = AsyncMock(
            return_value=b"%PDF-1.4 mock content"
        )

        app.state.composite_history_service = mock_history_svc
        app.state.pdf_report_service = mock_pdf_svc
        # db_pool déjà mocké dans le client conftest — fetchrow retourne None par défaut
        app.state.db_pool.fetchrow = AsyncMock(return_value=None)

        yield client

        if hasattr(app.state, "composite_history_service"):
            del app.state.composite_history_service
        if hasattr(app.state, "pdf_report_service"):
            del app.state.pdf_report_service

    @pytest_asyncio.fixture
    async def ticker_report_client_empty(self, client):
        """Client HTTP avec composite_history_service retournant historique vide."""
        mock_history_svc = AsyncMock()
        mock_history_svc.get_history = AsyncMock(return_value=[])

        mock_pdf_svc = AsyncMock(spec=PdfReportService)

        app.state.composite_history_service = mock_history_svc
        app.state.pdf_report_service = mock_pdf_svc

        yield client

        if hasattr(app.state, "composite_history_service"):
            del app.state.composite_history_service
        if hasattr(app.state, "pdf_report_service"):
            del app.state.pdf_report_service

    @pytest.mark.asyncio
    async def test_get_ticker_report_retourne_200_avec_content_type_pdf(
        self, ticker_report_client
    ):
        resp = await ticker_report_client.get("/ticker-report/BNS")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_get_ticker_report_retourne_200_avec_header_content_disposition_correct(
        self, ticker_report_client
    ):
        resp = await ticker_report_client.get("/ticker-report/BNS")
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "BNS-report-" in cd
        assert ".pdf" in cd

    @pytest.mark.asyncio
    async def test_get_ticker_report_ticker_sans_donnees_retourne_404(
        self, ticker_report_client_empty
    ):
        resp = await ticker_report_client_empty.get("/ticker-report/ZZZZZ")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_ticker_report_days_hors_borne_retourne_422(
        self, ticker_report_client
    ):
        resp = await ticker_report_client.get("/ticker-report/BNS?days=0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_ticker_report_sans_pdf_service_retourne_503(self, client):
        """Sans PdfReportService dans app.state → 503."""
        mock_history_svc = AsyncMock()
        mock_history_svc.get_history = AsyncMock(return_value=_make_history(2))
        app.state.composite_history_service = mock_history_svc

        if hasattr(app.state, "pdf_report_service"):
            del app.state.pdf_report_service

        resp = await client.get("/ticker-report/BNS")
        assert resp.status_code == 503

        if hasattr(app.state, "composite_history_service"):
            del app.state.composite_history_service

    @pytest.mark.asyncio
    async def test_get_ticker_report_sans_history_service_retourne_503(self, client):
        """Sans CompositeHistoryService dans app.state → 503."""
        if hasattr(app.state, "composite_history_service"):
            del app.state.composite_history_service

        resp = await client.get("/ticker-report/BNS")
        assert resp.status_code == 503
