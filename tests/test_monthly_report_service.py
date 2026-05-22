"""Tests de MonthlyReportService — Sprint 81."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.monthly_report_service import MonthlyReportService
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.watchlist_pdf_service import WatchlistPdfService

_FAKE_WATCHLIST_PDF = b"%PDF-1.4 fake watchlist content"
_FAKE_SCREENER_PDF = b"%PDF-1.4 fake screener content"


def _make_pool(fort_rows: list[dict] | None = None) -> AsyncMock:
    """Mock asyncpg.Pool — retourne les lignes FORT depuis composite_score_history."""
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=fort_rows or [])
    return pool


def _make_watchlist_svc(pdf: bytes = _FAKE_WATCHLIST_PDF) -> MagicMock:
    svc = MagicMock(spec=WatchlistPdfService)
    svc.generate_watchlist_pdf = AsyncMock(return_value=pdf)
    return svc


def _make_screener_svc(pdf: bytes = _FAKE_SCREENER_PDF) -> MagicMock:
    svc = MagicMock(spec=ScreenerPdfService)
    svc.generate = MagicMock(return_value=pdf)
    return svc


def _make_fort_row(ticker: str = "BNS", score: float = 78.0) -> dict:
    return {"ticker": ticker, "score": score, "label": "FORT"}


# ---------------------------------------------------------------------------
# Tests unitaires — MonthlyReportService
# ---------------------------------------------------------------------------

def test_monthly_report_service_init():
    """Instanciation sans paramètre."""
    svc = MonthlyReportService()
    assert svc is not None


@pytest.mark.asyncio
async def test_generate_returns_tuple_of_bytes():
    """generate() avec 2 tickers (1 FORT) retourne un tuple (watchlist_pdf, screener_pdf)."""
    svc = MonthlyReportService()
    pool = _make_pool([_make_fort_row("BNS")])
    watchlist_svc = _make_watchlist_svc()
    screener_svc = _make_screener_svc()

    result = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
    )

    assert isinstance(result, tuple)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_generate_watchlist_pdf_valid():
    """Le premier élément du tuple est le PDF watchlist attendu."""
    svc = MonthlyReportService()
    pool = _make_pool([_make_fort_row("BNS")])
    watchlist_svc = _make_watchlist_svc(_FAKE_WATCHLIST_PDF)
    screener_svc = _make_screener_svc()

    watchlist_pdf, _ = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
    )

    assert watchlist_pdf == _FAKE_WATCHLIST_PDF
    assert watchlist_pdf[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_generate_screener_pdf_valid():
    """Le second élément du tuple est le PDF screener FORT attendu."""
    svc = MonthlyReportService()
    pool = _make_pool([_make_fort_row("BNS"), _make_fort_row("TD", 75.0)])
    watchlist_svc = _make_watchlist_svc()
    screener_svc = _make_screener_svc(_FAKE_SCREENER_PDF)

    _, screener_pdf = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
    )

    assert screener_pdf == _FAKE_SCREENER_PDF
    assert screener_pdf[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_generate_empty_watchlist_raises_valueerror():
    """ValueError propagée si la watchlist est vide (levée par WatchlistPdfService)."""
    svc = MonthlyReportService()
    pool = _make_pool([])
    watchlist_svc = MagicMock(spec=WatchlistPdfService)
    watchlist_svc.generate_watchlist_pdf = AsyncMock(
        side_effect=ValueError("Watchlist vide — aucun ticker à inclure dans le rapport")
    )
    screener_svc = _make_screener_svc()

    with pytest.raises(ValueError, match="Watchlist vide"):
        await svc.generate(
            db_pool=pool,
            watchlist_pdf_service=watchlist_svc,
            screener_pdf_service=screener_svc,
        )


@pytest.mark.asyncio
async def test_generate_no_fort_tickers_still_returns_screener_pdf():
    """Aucun ticker FORT → screener_pdf retourné quand même (ScreenResult vide)."""
    svc = MonthlyReportService()
    pool = _make_pool([])  # aucun ticker FORT
    watchlist_svc = _make_watchlist_svc()
    screener_svc = _make_screener_svc()

    watchlist_pdf, screener_pdf = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
    )

    assert isinstance(watchlist_pdf, bytes)
    assert isinstance(screener_pdf, bytes)
    # ScreenerPdfService.generate() doit avoir été appelé même sans tickers FORT
    screener_svc.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Tests Sprint 88 — section ESG dans le PDF mensuel
# ---------------------------------------------------------------------------

def _make_watchlist_service(esg_rows: list[dict]) -> MagicMock:
    """Mock WatchlistService dont get_all_with_composite() retourne les lignes ESG fournies."""
    from app.services.watchlist_service import WatchlistService

    svc = MagicMock(spec=WatchlistService)
    svc.get_all_with_composite = AsyncMock(return_value=esg_rows)
    return svc


def _real_watchlist_pdf_bytes() -> bytes:
    """Génère un VRAI PDF watchlist minimal via reportlab (parseable par pypdf)."""
    from io import BytesIO

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    doc.build([Paragraph("Rapport Watchlist (test)", styles["Title"])])
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_monthly_report_pdf_contient_esg_quand_score_present():
    """PDF retourné contient 'ESG' si au moins un ticker a un last_esg_score non-null."""
    svc = MonthlyReportService()
    pool = _make_pool([_make_fort_row("BNS")])
    watchlist_svc = _make_watchlist_svc(_real_watchlist_pdf_bytes())
    screener_svc = _make_screener_svc()
    watchlist_service = _make_watchlist_service([
        {"ticker": "BNS", "last_esg_score": 8.5, "esg_alert_threshold": 5.0},
        {"ticker": "TD", "last_esg_score": 12.0, "esg_alert_threshold": 5.0},
    ])

    watchlist_pdf, _ = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
        watchlist_service=watchlist_service,
    )

    assert watchlist_pdf[:4] == b"%PDF"
    # Section ESG insérée — vérification via extraction texte pypdf
    from io import BytesIO
    from pypdf import PdfReader

    text = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(watchlist_pdf)).pages)
    assert "ESG" in text


@pytest.mark.asyncio
async def test_monthly_report_pdf_sans_esg_quand_aucun_score():
    """PDF retourné ne contient PAS 'ESG' si tous les last_esg_score sont null."""
    svc = MonthlyReportService()
    pool = _make_pool([_make_fort_row("BNS")])
    watchlist_svc = _make_watchlist_svc(_real_watchlist_pdf_bytes())
    screener_svc = _make_screener_svc()
    watchlist_service = _make_watchlist_service([
        {"ticker": "BNS", "last_esg_score": None, "esg_alert_threshold": 5.0},
        {"ticker": "TD", "last_esg_score": None, "esg_alert_threshold": 5.0},
    ])

    watchlist_pdf, _ = await svc.generate(
        db_pool=pool,
        watchlist_pdf_service=watchlist_svc,
        screener_pdf_service=screener_svc,
        watchlist_service=watchlist_service,
    )

    # Aucune section ESG → bytes retournés identiques au PDF watchlist mocké
    assert watchlist_pdf == watchlist_svc.generate_watchlist_pdf.return_value


def test_esg_verdict_helper_importable():
    """Le helper esg_verdict est accessible depuis app.utils.esg_utils."""
    from app.utils.esg_utils import esg_verdict
    # Alias retro-compatible exposé depuis l'endpoint watchlist
    from app.api.endpoints.watchlist import _esg_verdict

    assert esg_verdict(12.0) == "ESG_FORT"
    assert esg_verdict(7.5) == "ESG_MODERE"
    assert esg_verdict(2.0) == "ESG_FAIBLE"
    assert esg_verdict(None) == "N/A"
    # L'alias historique doit pointer vers la même implémentation
    assert _esg_verdict is esg_verdict
