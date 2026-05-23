"""Tests Sprint 59 — Export Excel watchlist (GET /watchlist/export.xlsx)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.endpoints.watchlist import _generate_watchlist_xlsx
from app.api.main import app as fastapi_app
from app.services.watchlist_service import WatchlistService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rows(n: int = 2) -> list[dict]:
    """Construit n lignes watchlist enrichies pour les tests."""
    tickers = ["BNS", "TD", "RY", "MSFT", "AAPL"]
    return [
        {
            "id": f"uuid-{i}",
            "ticker": tickers[i % len(tickers)],
            "created_at": datetime(2026, 5, 1 + i, tzinfo=timezone.utc),
            "composite_alert_threshold": 15.0,
            "composite_score_latest": 72.5 - i * 10,
            "composite_label_latest": "FORT" if i == 0 else "MODERE",
        }
        for i in range(n)
    ]


def _make_row_sans_score() -> dict:
    """Ligne watchlist sans composite_score (composite_score_latest=None)."""
    return {
        "id": "uuid-no-score",
        "ticker": "EMPTY",
        "created_at": datetime(2026, 5, 14, tzinfo=timezone.utc),
        "composite_alert_threshold": 15.0,
        "composite_score_latest": None,
        "composite_label_latest": None,
    }


# ---------------------------------------------------------------------------
# Tests unitaires — _generate_watchlist_xlsx()
# ---------------------------------------------------------------------------

def test_generate_retourne_bytes():
    """_generate_watchlist_xlsx retourne des bytes."""
    result = _generate_watchlist_xlsx([])
    assert isinstance(result, bytes)


def test_generate_magic_bytes_zip():
    """Le contenu xlsx commence par PK (archive zip)."""
    result = _generate_watchlist_xlsx([])
    assert result[:2] == b"PK"


def test_generate_feuille_watchlist():
    """Le fichier contient une feuille nommée 'Watchlist'."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _generate_watchlist_xlsx([])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    assert "Watchlist" in wb.sheetnames


def test_generate_entete_row1():
    """La ligne 1 contient les colonnes Ticker, Composite Score, Label."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _generate_watchlist_xlsx([])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    header_values = [cell.value for cell in ws[1]]
    assert "Ticker" in header_values
    assert "Composite Score" in header_values
    assert "Label" in header_values


def test_generate_vide_entete_seulement():
    """Watchlist vide → fichier xlsx valide avec seulement la ligne d'en-tête."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _generate_watchlist_xlsx([])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    assert ws.max_row == 1  # uniquement l'en-tête


def test_generate_deux_tickers_trois_lignes():
    """2 tickers → 3 lignes au total (1 en-tête + 2 données)."""
    openpyxl = pytest.importorskip("openpyxl")
    rows = _make_rows(2)
    result = _generate_watchlist_xlsx(rows)
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    assert ws.max_row == 3


def test_generate_contient_ticker_bns():
    """Le fichier contient le ticker BNS dans les cellules de données."""
    openpyxl = pytest.importorskip("openpyxl")
    rows = _make_rows(1)
    result = _generate_watchlist_xlsx(rows)
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    all_values = [cell.value for row in ws.iter_rows() for cell in row]
    assert "BNS" in all_values


def test_generate_composite_score_arrondi():
    """Le composite_score est arrondi à 1 décimale dans le fichier."""
    openpyxl = pytest.importorskip("openpyxl")
    rows = [
        {
            "id": "uuid-1",
            "ticker": "BNS",
            "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "composite_alert_threshold": 15.0,
            "composite_score_latest": 72.567,
            "composite_label_latest": "FORT",
        }
    ]
    result = _generate_watchlist_xlsx(rows)
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    # Colonne 4 = Composite Score (row 2 = première ligne de données)
    assert ws.cell(row=2, column=4).value == 72.6


def test_generate_score_absent_cellule_vide():
    """composite_score_latest=None → cellule Composite Score vide (None)."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _generate_watchlist_xlsx([_make_row_sans_score()])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    assert ws.cell(row=2, column=4).value is None


def test_generate_label_calcule_si_absent():
    """Si composite_label_latest est None, le label est calculé depuis le score."""
    openpyxl = pytest.importorskip("openpyxl")
    rows = [
        {
            "id": "uuid-1",
            "ticker": "TD",
            "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "composite_alert_threshold": 15.0,
            "composite_score_latest": 75.0,
            "composite_label_latest": None,  # absent → doit être calculé
        }
    ]
    result = _generate_watchlist_xlsx(rows)
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["Watchlist"]
    # Colonne 5 = Label
    assert ws.cell(row=2, column=5).value == "FORT"


# ---------------------------------------------------------------------------
# Tests endpoint GET /watchlist/export.xlsx
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def watchlist_xlsx_client(client):
    """Client avec WatchlistService mocké exposant get_all_with_composite()."""
    mock_service = AsyncMock(spec=WatchlistService)
    mock_service.get_all_with_composite.return_value = _make_rows(2)
    fastapi_app.state.watchlist_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_endpoint_export_xlsx_200(watchlist_xlsx_client):
    """GET /watchlist/export.xlsx retourne 200 avec Content-Type xlsx."""
    client, _ = watchlist_xlsx_client
    resp = await client.get("/watchlist/export.xlsx")
    assert resp.status_code == 200
    assert "openxmlformats" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_endpoint_export_xlsx_content_disposition(watchlist_xlsx_client):
    """GET /watchlist/export.xlsx retourne attachment; filename=watchlist.xlsx."""
    client, _ = watchlist_xlsx_client
    resp = await client.get("/watchlist/export.xlsx")
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "watchlist.xlsx" in disposition


@pytest.mark.asyncio
async def test_endpoint_export_xlsx_corps_lisible(watchlist_xlsx_client):
    """Le corps de la réponse est un xlsx valide lisible par openpyxl."""
    openpyxl = pytest.importorskip("openpyxl")
    client, _ = watchlist_xlsx_client
    resp = await client.get("/watchlist/export.xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert "Watchlist" in wb.sheetnames


@pytest.mark.asyncio
async def test_endpoint_export_xlsx_watchlist_vide(client):
    """Watchlist vide → xlsx valide avec seulement l'en-tête."""
    openpyxl = pytest.importorskip("openpyxl")
    mock_service = AsyncMock(spec=WatchlistService)
    mock_service.get_all_with_composite.return_value = []
    fastapi_app.state.watchlist_service = mock_service

    resp = await client.get("/watchlist/export.xlsx")
    assert resp.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb["Watchlist"]
    assert ws.max_row == 1


@pytest.mark.asyncio
async def test_endpoint_export_xlsx_deux_tickers(watchlist_xlsx_client):
    """Watchlist avec 2 tickers → 3 lignes dans le xlsx (1 en-tête + 2 données)."""
    openpyxl = pytest.importorskip("openpyxl")
    client, _ = watchlist_xlsx_client
    resp = await client.get("/watchlist/export.xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb["Watchlist"]
    assert ws.max_row == 3
