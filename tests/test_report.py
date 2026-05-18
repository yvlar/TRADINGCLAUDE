"""Tests Sprint 20 — ReportService + endpoint /report."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from app.orchestrator.core import AnalyzeResponse
from app.services.report import ReportService


# ---------------------------------------------------------------------------
# Helpers — construction d'AnalyzeResponse de test
# ---------------------------------------------------------------------------


def _make_minimal_response(graham_output) -> AnalyzeResponse:
    """AnalyzeResponse minimale : seulement graham, pas de skills optionnels."""
    return AnalyzeResponse(
        analysis_id=str(uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")),
        ticker="BNS",
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=graham_output,
        cost_usd=0.0012,
        created_at="2026-05-09T10:00:00+00:00",
    )


def _make_full_response(graham_output, earnings_output) -> AnalyzeResponse:
    """AnalyzeResponse avec graham + earnings — les autres sont None."""
    return AnalyzeResponse(
        analysis_id=str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")),
        ticker="MSFT",
        workflow="value_graham",
        skills_applied=["graham_analysis", "earnings_quality"],
        graham=graham_output,
        earnings_quality=earnings_output,
        cost_usd=0.0034,
        created_at="2026-05-09T11:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Tests unitaires — ReportService (pas d'appel réseau, pas de DB)
# ---------------------------------------------------------------------------


def test_generate_pdf_retourne_bytes(graham_output_msft):
    """generate_pdf() retourne un objet bytes non vide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_commence_par_pdf_header(graham_output_msft):
    """Le PDF généré commence bien par le magic number %PDF."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert result[:4] == b"%PDF"


def test_generate_pdf_graham_seulement(graham_output_msft):
    """AnalyzeResponse sans skills optionnels → PDF valide non vide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_pdf_avec_earnings(graham_output_msft, earnings_output_msft):
    """AnalyzeResponse avec graham + earnings → PDF valide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_full_response(graham_output_msft, earnings_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_save_pdf_cree_fichier(tmp_path, graham_output_msft):
    """save_pdf() crée un fichier .pdf sur le disque."""
    service = ReportService(output_dir=str(tmp_path))
    response = _make_minimal_response(graham_output_msft)

    path = service.save_pdf(response)

    assert path.exists()
    assert path.suffix == ".pdf"
    assert path.stat().st_size > 0


def test_save_pdf_nom_correct(tmp_path, graham_output_msft):
    """save_pdf() nomme le fichier {ticker}-{analysis_id[:8]}.pdf."""
    service = ReportService(output_dir=str(tmp_path))
    response = _make_minimal_response(graham_output_msft)

    path = service.save_pdf(response)

    expected_name = f"{response.ticker}-{response.analysis_id[:8]}.pdf"
    assert path.name == expected_name


# ---------------------------------------------------------------------------
# Tests endpoint — client mocké de conftest.py
# ---------------------------------------------------------------------------


async def test_post_report_200(client) -> None:
    """POST /report avec payload valide → 200 + Content-Type application/pdf."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            "pe": 11.0,
            "pb": 1.3,
            "current_ratio": None,
            "debt_equity": 0.45,
            "eps_growth_10y": 0.27,
            "price": 80.0,
            "book_value": 61.5,
        },
        "workflow": "value_graham",
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")


async def test_post_report_content_disposition(client) -> None:
    """POST /report → header Content-Disposition présent avec filename .pdf."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            "pe": 11.0,
            "pb": 1.3,
            "current_ratio": None,
            "debt_equity": 0.45,
            "eps_growth_10y": 0.27,
            "price": 80.0,
            "book_value": 61.5,
        },
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 200
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert ".pdf" in disposition


async def test_post_report_ratios_invalides_422(client) -> None:
    """POST /report sans le champ pb obligatoire → 422 Unprocessable Entity."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            # pb manquant — doit déclencher une erreur de validation Pydantic
            # Note : pe est maintenant optionnel (Sprint 36 — pe: float | None)
            "pe": 11.0,
            "debt_equity": 0.45,
            "eps_growth_10y": 0.27,
            "price": 80.0,
            "book_value": 61.5,
        },
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 422


async def test_get_report_analysis_inconnu_404(client) -> None:
    """GET /report/{uuid-inexistant} → 404 Not Found."""
    from unittest.mock import AsyncMock
    from app.api.main import app

    # fetchrow retourne None pour simuler un analysis_id introuvable en DB
    app.state.db_pool.fetchrow = AsyncMock(return_value=None)

    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await client.get(f"/report/{fake_id}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests Sprint 53 — generate_watchlist_summary_pdf() avec composite_score
# ---------------------------------------------------------------------------


def _make_watchlist_entry(**kwargs):
    """Crée une WatchlistEntry minimale pour les tests PDF watchlist."""
    from datetime import datetime, timezone

    from app.models.watchlist import WatchlistEntry

    defaults = {
        "id": str(uuid.uuid4()),
        "ticker": "BNS",
        "created_at": datetime.now(timezone.utc),
        "last_composite_score": None,
        "composite_alert_threshold": 15.0,
        "last_score": None,
        "last_verdict": None,
        "last_intrinsic_value": None,
        "last_price_checked": None,
        "price_alert_threshold_pct": 0.10,
    }
    defaults.update(kwargs)
    return WatchlistEntry(**defaults)


def test_pdf_contient_composite_score():
    """PDF watchlist valide + _composite_label retourne FORT pour score >= 70."""
    from app.services.report import _composite_label

    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(ticker="RY", last_composite_score=75.0)

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert _composite_label(75.0) == "FORT"
    assert _composite_label(55.0) == "MODERE"
    assert _composite_label(30.0) == "FAIBLE"
    assert _composite_label(None) == "—"


def test_pdf_gere_composite_score_none():
    """Le PDF watchlist se génère sans erreur quand last_composite_score est None."""
    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(ticker="TD", last_composite_score=None)

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 0


def test_pdf_alerte_active_marquee():
    """_composite_alerte retourne OUI quand score < threshold, NON sinon."""
    from app.services.report import _composite_alerte

    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(
        ticker="XIU",
        last_composite_score=10.0,
        composite_alert_threshold=15.0,
    )

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    # Vérification de la logique d'alerte
    assert _composite_alerte(10.0, 15.0) == "OUI"   # score < threshold → alerte
    assert _composite_alerte(20.0, 15.0) == "NON"   # score >= threshold → pas d'alerte
    assert _composite_alerte(None, 15.0) == "—"      # score absent → neutre
