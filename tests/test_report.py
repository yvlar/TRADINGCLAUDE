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
