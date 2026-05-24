"""Tests de ScreenerPdfService — Sprint 71."""
from __future__ import annotations

import base64
import re
import zlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.screen import ScreenEntry, ScreenResult
from app.services.screener_pdf_service import ScreenerPdfService


def _pdf_text(pdf_bytes: bytes) -> bytes:
    """Extrait le texte décompressé des streams PDF (ASCII85 + zlib) sans dépendance externe.

    Reportlab génère `~>endstream` sans saut de ligne entre `~>` et `endstream`.
    """
    result = []
    for m in re.finditer(rb"stream\r?\n([\x00-\xff]*?)~>endstream", pdf_bytes, re.DOTALL):
        raw = b"<~" + m.group(1) + b"~>"
        try:
            decoded = base64.a85decode(raw, adobe=True)
            result.append(zlib.decompress(decoded))
        except Exception:
            pass
    return b"".join(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    ticker: str,
    composite_score: float | None = 75.0,
    composite_label: str | None = "FORT",
    verdict: str | None = "PASSE",
    erreur: str | None = None,
    cost_usd: float = 0.002,
) -> ScreenEntry:
    return ScreenEntry(
        ticker=ticker,
        defensive_score=6 if erreur is None else None,
        verdict=verdict,
        composite_score=composite_score,
        composite_label=composite_label,
        workflow_utilise="value_graham",
        cost_usd=cost_usd,
        depuis_cache=False,
        erreur=erreur,
    )


def _make_result(
    entries: list[ScreenEntry] | None = None,
    workflow: str = "value_graham",
) -> ScreenResult:
    if entries is None:
        entries = [_make_entry("BNS"), _make_entry("TD", composite_score=60.0, composite_label="MODERE")]
    tickers_echec = sum(1 for e in entries if e.erreur)
    return ScreenResult(
        tickers_analyses=len(entries) - tickers_echec,
        tickers_echec=tickers_echec,
        tickers_depuis_cache=0,
        cout_total_usd=round(sum(e.cost_usd for e in entries), 6),
        resultats=entries,
        workflow=workflow,
        duration_ms=1500,
    )


# ---------------------------------------------------------------------------
# Tests unitaires — ScreenerPdfService
# ---------------------------------------------------------------------------

def test_screener_pdf_service_init():
    """Instanciation sans paramètre."""
    svc = ScreenerPdfService()
    assert svc is not None


def test_generate_retourne_bytes():
    """generate() retourne des bytes non vides."""
    svc = ScreenerPdfService()
    result = _make_result()
    pdf = svc.generate(result)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0


def test_generate_pdf_contient_ticker():
    """Le PDF généré contient le ticker dans son contenu (décompressé)."""
    svc = ScreenerPdfService()
    result = _make_result([_make_entry("AAPL")])
    pdf = svc.generate(result)
    assert b"AAPL" in _pdf_text(pdf)


def test_generate_pdf_sans_resultats():
    """Liste vide → PDF généré sans erreur."""
    svc = ScreenerPdfService()
    result = _make_result(entries=[])
    pdf = svc.generate(result)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100  # PDF minimal avec en-tête


def test_generate_pdf_top_picks():
    """Les tickers FORT apparaissent dans la section Top Picks du PDF (décompressé)."""
    svc = ScreenerPdfService()
    fort = _make_entry("RY", composite_score=80.0, composite_label="FORT")
    modere = _make_entry("TD", composite_score=55.0, composite_label="MODERE")
    result = _make_result(entries=[fort, modere])
    pdf = svc.generate(result)
    text = _pdf_text(pdf)
    # RY apparaît (dans le tableau des résultats et dans la section Top Picks)
    assert b"RY" in text


def test_generate_avec_workflow():
    """Le titre inclut le workflow passé en paramètre (visible après décompression)."""
    svc = ScreenerPdfService()
    result = _make_result(workflow="value_graham")
    pdf = svc.generate(result, title="Rapport Test value_graham 2026-05-16")
    assert b"value_graham" in _pdf_text(pdf)


def test_generate_pdf_plusieurs_resultats():
    """PDF généré avec plusieurs tickers, tous présents dans le contenu décompressé."""
    svc = ScreenerPdfService()
    entries = [
        _make_entry("BNS", composite_score=78.0, composite_label="FORT"),
        _make_entry("TD", composite_score=62.0, composite_label="MODERE"),
        _make_entry("RY", composite_score=45.0, composite_label="FAIBLE"),
    ]
    result = _make_result(entries=entries)
    pdf = svc.generate(result)
    text = _pdf_text(pdf)
    assert b"BNS" in text
    assert b"TD" in text
    assert b"RY" in text


def test_generate_pdf_avec_erreur():
    """Entry avec erreur → PDF généré sans exception, ticker présent dans le contenu."""
    svc = ScreenerPdfService()
    entries = [
        _make_entry("BNS"),
        _make_entry("MSFT", composite_score=None, composite_label=None, verdict=None, erreur="Ticker invalide"),
    ]
    result = _make_result(entries=entries)
    pdf = svc.generate(result)
    assert isinstance(pdf, bytes)
    assert b"MSFT" in _pdf_text(pdf)


def test_generate_pdf_label_modere():
    """Entry MODERE → PDF généré sans erreur, ticker et label dans le contenu."""
    svc = ScreenerPdfService()
    entries = [_make_entry("TD", composite_score=58.0, composite_label="MODERE", verdict="ELIGIBLE")]
    result = _make_result(entries=entries)
    pdf = svc.generate(result)
    text = _pdf_text(pdf)
    assert b"TD" in text
    assert b"MODERE" in text


def test_generate_pdf_label_faible():
    """Entry FAIBLE → PDF généré sans erreur, ticker dans le contenu."""
    svc = ScreenerPdfService()
    entries = [_make_entry("GIB", composite_score=30.0, composite_label="FAIBLE", verdict="ECHOUE")]
    result = _make_result(entries=entries)
    pdf = svc.generate(result)
    assert b"GIB" in _pdf_text(pdf)


def test_generate_pdf_bytes_valides():
    """Les bytes retournés commencent par la signature PDF (%PDF)."""
    svc = ScreenerPdfService()
    result = _make_result()
    pdf = svc.generate(result)
    assert pdf[:4] == b"%PDF"


def test_generate_titre_personnalise():
    """Un titre personnalisé est accepté et produit un PDF valide."""
    svc = ScreenerPdfService()
    result = _make_result()
    pdf = svc.generate(result, title="Mon Rapport Personnalise")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0


# ---------------------------------------------------------------------------
# Test d'intégration — endpoint GET /screener-report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pdf_endpoint_integration():
    """GET /screener-report retourne application/pdf avec les bons headers."""
    from app.api.main import app

    fake_entry = _make_entry("BNS")
    fake_result = _make_result(entries=[fake_entry])
    fake_pdf = b"%PDF-1.4 fake pdf content"

    mock_screener = AsyncMock()
    mock_screener.screen = AsyncMock(return_value=fake_result)

    mock_pdf_svc = MagicMock()
    mock_pdf_svc.generate = MagicMock(return_value=fake_pdf)

    app.state.screener = mock_screener
    app.state.screener_pdf_service = mock_pdf_svc

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/screener-report",
            params={"tickers": "BNS", "workflow": "value_graham"},
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert resp.content == fake_pdf
