"""Tests Sprint 83 — colonnes ESG dans l'export Excel watchlist."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import openpyxl
import pytest

from app.api.endpoints.watchlist import _esg_verdict, _generate_watchlist_xlsx


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
    )
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests unitaires sur _esg_verdict()
# ---------------------------------------------------------------------------

def test_esg_verdict_none():
    assert _esg_verdict(None) == "N/A"


def test_esg_verdict_fort():
    assert _esg_verdict(10.0) == "ESG_FORT"
    assert _esg_verdict(15.0) == "ESG_FORT"
    assert _esg_verdict(10.1) == "ESG_FORT"


def test_esg_verdict_modere():
    assert _esg_verdict(7.5) == "ESG_MODERE"
    assert _esg_verdict(5.0) == "ESG_MODERE"
    assert _esg_verdict(9.9) == "ESG_MODERE"


def test_esg_verdict_faible():
    assert _esg_verdict(0.0) == "ESG_FAIBLE"
    assert _esg_verdict(4.9) == "ESG_FAIBLE"


# ---------------------------------------------------------------------------
# Tests sur _generate_watchlist_xlsx()
# ---------------------------------------------------------------------------

def test_xlsx_headers_contiennent_esg():
    rows = [_make_row()]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    assert "Score ESG" in headers
    assert "Verdict ESG" in headers


def test_xlsx_esg_score_rempli():
    rows = [_make_row(ticker="BNS", last_esg_score=7.5)]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    data = lignes[1]
    idx_score = headers.index("Score ESG")
    idx_verdict = headers.index("Verdict ESG")
    assert data[idx_score] == 7.5
    assert data[idx_verdict] == "ESG_MODERE"


def test_xlsx_esg_score_absent():
    rows = [_make_row(ticker="TD", last_esg_score=None)]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    data = lignes[1]
    idx_score = headers.index("Score ESG")
    idx_verdict = headers.index("Verdict ESG")
    assert data[idx_score] is None
    assert data[idx_verdict] == "N/A"


def test_xlsx_retrocompatibilite_sept_premieres_colonnes():
    """Les 7 colonnes historiques restent en positions 0-6 (ordre immuable)."""
    rows = [_make_row(ticker="RY", last_esg_score=12.0)]
    content = _generate_watchlist_xlsx(rows)
    lignes = _parse_xlsx(content)
    headers = lignes[0]
    assert headers[0] == "Ticker"
    assert headers[1] == "Nom"
    assert headers[2] == "Date ajout"
    assert headers[3] == "Composite Score"
    assert headers[4] == "Label"
    assert headers[5] == "Alerte"
    assert headers[6] == "Notes"
    assert headers[7] == "Score ESG"
    assert headers[8] == "Verdict ESG"
