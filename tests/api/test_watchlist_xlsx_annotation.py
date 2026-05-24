"""Tests Sprint 92 — colonne Annotation dans l'export Excel watchlist."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import openpyxl
import pytest

from app.api.endpoints.watchlist import _generate_watchlist_xlsx
from app.services.watchlist_service import WatchlistService


def _parse_xlsx(content: bytes) -> list[list]:
    """Retourne toutes les lignes (liste de listes de valeurs) depuis des bytes Excel."""
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active
    return [[cell.value for cell in row] for row in ws.iter_rows()]


def _make_row(**kwargs) -> dict:
    defaults = dict(
        id="1",
        ticker="BNS",
        created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        composite_alert_threshold=15.0,
        composite_score_latest=None,
        composite_label_latest=None,
        last_esg_score=None,
        esg_alert_threshold=5.0,
        derniere_annotation="",
    )
    defaults.update(kwargs)
    return defaults


@pytest.mark.asyncio
async def test_get_all_with_composite_sql_contient_derniere_annotation() -> None:
    """get_all_with_composite() transmet une requête SQL contenant 'derniere_annotation'."""
    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[])
    service = WatchlistService(mock_pool)

    await service.get_all_with_composite()

    mock_pool.fetch.assert_called_once()
    sql_query = mock_pool.fetch.call_args[0][0]
    assert "derniere_annotation" in sql_query


def test_xlsx_headers_contiennent_annotation() -> None:
    """L'en-tête du XLSX exporté contient la colonne 'Annotation'."""
    rows = [_make_row()]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    assert "Annotation" in headers


def test_xlsx_annotation_presente_et_absente() -> None:
    """La colonne Annotation est remplie si présente, chaîne vide si absente."""
    rows = [
        _make_row(ticker="BNS", derniere_annotation="Action surévaluée — attendre correction"),
        _make_row(ticker="TD", derniere_annotation=""),
    ]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    idx = headers.index("Annotation")

    assert lignes[1][idx] == "Action surévaluée — attendre correction"
    # openpyxl retourne None pour les cellules vides (string vide non persisté)
    assert lignes[2][idx] in (None, "")
