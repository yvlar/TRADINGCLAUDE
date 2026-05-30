"""Tests de l'export CSV/Excel -- Sprint 47."""
from __future__ import annotations

import csv
import io

import pytest

from app.api.endpoints.screen import ScreenEntry, ScreenResult
from app.services.export import export_to_csv, export_to_excel

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_screen_result(entries: list[ScreenEntry] | None = None) -> ScreenResult:
    """ScreenResult minimal pour les tests."""
    if entries is None:
        entries = [
            ScreenEntry(
                ticker="BNS",
                defensive_score=6,
                verdict="PASSE",
                composite_score=72.5,
                composite_label="FORT",
                workflow_utilise="value_graham",
                cost_usd=0.003,
                depuis_cache=False,
                erreur=None,
            ),
            ScreenEntry(
                ticker="TD",
                defensive_score=4,
                verdict="BORDERLINE",
                composite_score=48.0,
                composite_label="MODERE",
                workflow_utilise="value_graham",
                cost_usd=0.004,
                depuis_cache=False,
                erreur=None,
            ),
            ScreenEntry(
                ticker="FAIL",
                defensive_score=None,
                verdict=None,
                composite_score=None,
                composite_label=None,
                workflow_utilise="value_graham",
                cost_usd=0.0,
                depuis_cache=False,
                erreur="Timeout extraction",
            ),
        ]
    return ScreenResult(
        tickers_analyses=2,
        tickers_echec=1,
        tickers_depuis_cache=0,
        cout_total_usd=0.007,
        resultats=entries,
        workflow="value_graham",
        duration_ms=1234,
    )


# ---------------------------------------------------------------------------
# Tests export_to_csv
# ---------------------------------------------------------------------------

def test_csv_retourne_bytes():
    """export_to_csv retourne des bytes."""
    result = _make_screen_result()
    output = export_to_csv(result)
    assert isinstance(output, bytes)


def test_csv_decodable_utf8():
    """Le CSV est decodable en UTF-8."""
    result = _make_screen_result()
    output = export_to_csv(result)
    text = output.decode("utf-8-sig")
    assert len(text) > 0


def test_csv_contient_tous_les_tickers():
    """Le CSV contient une ligne par ticker."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    assert "BNS" in output
    assert "TD" in output
    assert "FAIL" in output


def test_csv_contient_composite_score():
    """Le CSV contient la colonne composite_score."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    assert "composite_score" in output
    assert "72.5" in output
    assert "FORT" in output


def test_csv_colonnes_header():
    """Le CSV contient tous les en-tetes attendus."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    # Sauter les lignes de commentaires (#) pour trouver l'en-tete
    lines = [l for l in output.splitlines() if l and not l.startswith("#")]
    reader = csv.reader(lines)
    header = next(reader)
    for col in ("ticker", "composite_score", "composite_label", "defensive_score", "verdict"):
        assert col in header, f"Colonne '{col}' absente du header"


def test_csv_erreur_ticker_affiche():
    """Les tickers en echec ont leur erreur dans la colonne erreur."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    assert "Timeout extraction" in output


def test_csv_metadonnees_workflow():
    """Le CSV contient les metadonnees workflow."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    assert "value_graham" in output


def test_csv_composite_score_vide_si_absent():
    """composite_score absent → champ vide dans le CSV."""
    result = _make_screen_result()
    output = export_to_csv(result).decode("utf-8-sig")
    # La ligne FAIL n'a pas de composite_score
    lines = output.splitlines()
    fail_line = next(l for l in lines if "FAIL" in l)
    parts = next(csv.reader([fail_line]))
    # composite_score est en colonne 2 (index 1)
    assert parts[1] == ""  # vide


# ---------------------------------------------------------------------------
# Tests export_to_excel
# ---------------------------------------------------------------------------

def test_excel_retourne_bytes():
    """export_to_excel retourne des bytes (format xlsx)."""
    pytest.importorskip("openpyxl")
    result = _make_screen_result()
    output = export_to_excel(result)
    assert isinstance(output, bytes)
    # Magic bytes xlsx = PK (zip)
    assert output[:2] == b"PK"


def test_excel_contient_tickers():
    """Le fichier Excel contient les tickers dans les cellules."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _make_screen_result()
    output = export_to_excel(result)

    wb = openpyxl.load_workbook(io.BytesIO(output))
    ws = wb.active
    all_values = [str(cell.value or "") for row in ws.iter_rows() for cell in row]
    assert "BNS" in all_values
    assert "TD" in all_values


def test_excel_contient_composite_score():
    """Le fichier Excel contient les valeurs composite_score."""
    openpyxl = pytest.importorskip("openpyxl")
    result = _make_screen_result()
    output = export_to_excel(result)

    wb = openpyxl.load_workbook(io.BytesIO(output))
    ws = wb.active
    all_values = [str(cell.value or "") for row in ws.iter_rows() for cell in row]
    assert "72.5" in all_values
    assert "FORT" in all_values


# ---------------------------------------------------------------------------
# Tests endpoint POST /export/screen
# ---------------------------------------------------------------------------

async def test_export_endpoint_csv_200(client):
    """POST /export/screen?format=csv -> 200 + Content-Type text/csv."""
    payload = {
        "tickers": ["MSFT"],
        "workflow": "value_graham",
        "ratios_map": {
            "MSFT": {
                "pe": 34.2, "pb": 12.1, "current_ratio": 1.34,
                "debt_equity": 0.28, "eps_growth_total": 0.85,
                "price": 420.0, "book_value": 35.0,
            }
        },
    }
    resp = await client.post("/export/screen?format=csv", json=payload)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_export_endpoint_csv_contenu(client):
    """Le CSV retourne contient les colonnes attendues."""
    payload = {
        "tickers": ["MSFT"],
        "workflow": "value_graham",
        "ratios_map": {
            "MSFT": {
                "pe": 34.2, "pb": 12.1, "current_ratio": 1.34,
                "debt_equity": 0.28, "eps_growth_total": 0.85,
                "price": 420.0, "book_value": 35.0,
            }
        },
    }
    resp = await client.post("/export/screen?format=csv", json=payload)
    text = resp.content.decode("utf-8-sig")
    assert "ticker" in text
    assert "composite_score" in text


async def test_export_endpoint_format_par_defaut_csv(client):
    """Sans ?format=, l'endpoint retourne du CSV par defaut."""
    payload = {
        "tickers": ["MSFT"],
        "workflow": "value_graham",
        "ratios_map": {
            "MSFT": {
                "pe": 34.2, "pb": 12.1, "current_ratio": 1.34,
                "debt_equity": 0.28, "eps_growth_total": 0.85,
                "price": 420.0, "book_value": 35.0,
            }
        },
    }
    resp = await client.post("/export/screen", json=payload)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


async def test_export_endpoint_tickers_vide_422(client):
    """POST /export/screen avec [] -> 422."""
    resp = await client.post("/export/screen", json={"tickers": []})
    assert resp.status_code == 422


async def test_export_endpoint_filename_contient_ticker(client):
    """Content-Disposition contient le ticker dans le nom de fichier."""
    payload = {
        "tickers": ["BNS"],
        "workflow": "value_graham",
        "ratios_map": {
            "BNS": {
                "pe": 11.0, "pb": 1.3, "current_ratio": None,
                "debt_equity": 0.45, "eps_growth_total": 0.27,
                "price": 80.0, "book_value": 61.5,
            }
        },
    }
    resp = await client.post("/export/screen?format=csv", json=payload)
    disposition = resp.headers.get("content-disposition", "")
    assert "BNS" in disposition
