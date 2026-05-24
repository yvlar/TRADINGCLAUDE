"""Tests de WatchlistPdfService — Sprint 76."""
from __future__ import annotations

import base64
import re
import zlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.watchlist_pdf_service import WatchlistPdfService


def _pdf_text(pdf_bytes: bytes) -> bytes:
    """Extrait le texte décompressé des streams PDF (ASCII85 + zlib)."""
    result = []
    for m in re.finditer(rb"stream\r?\n([\x00-\xff]*?)~>endstream", pdf_bytes, re.DOTALL):
        raw = b"<~" + m.group(1) + b"~>"
        try:
            decoded = base64.a85decode(raw, adobe=True)
            result.append(zlib.decompress(decoded))
        except Exception:
            pass
    return b"".join(result)


def _make_pool(rows: list[dict]) -> AsyncMock:
    """Mock asyncpg.Pool retournant les lignes fournies."""
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=rows)
    return pool


def _make_row(
    ticker: str = "BNS",
    score: float | None = 75.0,
    label: str | None = "FORT",
    threshold: float = 15.0,
    derniere_analyse: datetime | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "composite_alert_threshold": threshold,
        "composite_score_latest": score,
        "composite_label_latest": label,
        "derniere_analyse": derniere_analyse or datetime(2026, 5, 1, tzinfo=timezone.utc),
    }


# ---------------------------------------------------------------------------
# Tests unitaires — WatchlistPdfService
# ---------------------------------------------------------------------------

def test_watchlist_pdf_service_init():
    """Instanciation sans paramètre."""
    svc = WatchlistPdfService()
    assert svc is not None


@pytest.mark.asyncio
async def test_generate_retourne_bytes():
    """generate_watchlist_pdf() retourne des bytes non vides."""
    svc = WatchlistPdfService()
    pool = _make_pool([_make_row("BNS"), _make_row("TD", score=60.0, label="MODERE")])
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0


@pytest.mark.asyncio
async def test_generate_pdf_signature_valide():
    """Les bytes retournés commencent par la signature PDF (%PDF)."""
    svc = WatchlistPdfService()
    pool = _make_pool([_make_row()])
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    assert pdf[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_generate_pdf_contient_ticker():
    """Le PDF généré contient le ticker dans son contenu décompressé."""
    svc = WatchlistPdfService()
    pool = _make_pool([_make_row("AAPL", score=80.0)])
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    assert b"AAPL" in _pdf_text(pdf)


@pytest.mark.asyncio
async def test_generate_pdf_watchlist_vide_leve_valueerror():
    """ValueError levée si la watchlist est vide."""
    svc = WatchlistPdfService()
    pool = _make_pool([])
    with pytest.raises(ValueError, match="Watchlist vide"):
        await svc.generate_watchlist_pdf(pool=pool)


@pytest.mark.asyncio
async def test_generate_pdf_plusieurs_tickers():
    """PDF généré avec plusieurs tickers — tous présents dans le contenu."""
    svc = WatchlistPdfService()
    rows = [
        _make_row("BNS", score=78.0, label="FORT"),
        _make_row("TD", score=55.0, label="MODERE"),
        _make_row("RY", score=30.0, label="FAIBLE"),
    ]
    pool = _make_pool(rows)
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    text = _pdf_text(pdf)
    assert b"BNS" in text
    assert b"TD" in text
    assert b"RY" in text


@pytest.mark.asyncio
async def test_generate_pdf_top_picks_fort():
    """Un ticker FORT apparaît dans la section Top Picks du PDF."""
    svc = WatchlistPdfService()
    rows = [
        _make_row("BNS", score=82.0, label="FORT"),
        _make_row("TD", score=50.0, label="MODERE"),
    ]
    pool = _make_pool(rows)
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    text = _pdf_text(pdf)
    assert b"BNS" in text
    assert b"FORT" in text


@pytest.mark.asyncio
async def test_generate_pdf_score_absent():
    """Ticker sans composite_score → PDF généré sans exception."""
    svc = WatchlistPdfService()
    pool = _make_pool([_make_row("GIB", score=None, label=None)])
    pdf = await svc.generate_watchlist_pdf(pool=pool)
    assert isinstance(pdf, bytes)
    assert b"GIB" in _pdf_text(pdf)
