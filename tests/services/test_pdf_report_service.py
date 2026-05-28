"""Tests CI standard pour PdfReportService et GET /ticker-report/{ticker} — Sprint 63.

Aucun appel Claude réel. PdfReportService utilise reportlab (synchrone).
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.endpoints.ticker_report import _reconstruct_analyze_response
from app.api.main import app
from app.services.composite_history_service import CompositeHistoryPoint
from app.services.pdf_report_service import PdfReportService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

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


# ---------------------------------------------------------------------------
# Helpers — ligne analysis_history simulée
# ---------------------------------------------------------------------------


def _make_analysis_row(
    graham_output,
    *,
    ticker: str = "BNS",
    earnings_output=None,
    ratios: GrahamRatios | None = None,
    analysis_id: str | None = None,
    skill_corrompu: bool = False,
) -> dict:
    """Construit une ligne analysis_history (dict compatible asyncpg.Record indexable)."""
    result: dict = {"graham": graham_output.model_dump()}
    if earnings_output is not None:
        result["earnings_quality"] = earnings_output.model_dump()
    if skill_corrompu:
        result["dorsey_moat"] = {"champ_invalide": "data corrompue"}
    return {
        "id": analysis_id or str(uuid.uuid4()),
        "ticker": ticker,
        "workflow_name": "value_graham",
        "skills_used": json.dumps(list(result.keys())),
        "input_data": json.dumps(ratios.model_dump() if ratios is not None else {}),
        "result": json.dumps(result),
        "cost_usd": 0.0042,
        "created_at": datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
    }


# ---------------------------------------------------------------------------
# Tests : _reconstruct_analyze_response — unité
# ---------------------------------------------------------------------------


class TestReconstructAnalyzeResponse:

    def test_parse_multi_skills(self, graham_output_msft, earnings_output_msft):
        row = _make_analysis_row(
            graham_output_msft, ticker="MSFT", earnings_output=earnings_output_msft
        )
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.graham is not None
        assert result.earnings_quality is not None
        assert result.ticker == "MSFT"
        assert result.analysis_id == row["id"]

    def test_ignore_skill_corrompu(self, graham_output_msft, earnings_output_msft):
        """Un skill dont le JSON ne valide pas est ignoré, pas d'échec global."""
        row = _make_analysis_row(
            graham_output_msft,
            ticker="MSFT",
            earnings_output=earnings_output_msft,
            skill_corrompu=True,
        )
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.graham is not None
        assert result.earnings_quality is not None
        assert result.dorsey is None  # skill corrompu ignoré

    def test_result_illisible_retourne_none(self):
        row = {
            "id": str(uuid.uuid4()),
            "ticker": "BNS",
            "workflow_name": "value_graham",
            "skills_used": json.dumps([]),
            "input_data": json.dumps({}),
            "result": "{ ceci n'est pas du JSON valide",
            "cost_usd": 0.0,
            "created_at": datetime(2026, 5, 20, tzinfo=timezone.utc),
        }
        assert _reconstruct_analyze_response(row) is None


# ---------------------------------------------------------------------------
# Tests : GET /ticker-report/{ticker}?analysis_id=...
# ---------------------------------------------------------------------------


class TestTickerReportTargetedEndpoint:

    @pytest_asyncio.fixture
    async def targeted_client(self, client, graham_output_msft):
        """Client avec fetchrow simulant WHERE id=... AND ticker=BNS."""
        analysis_id = str(uuid.uuid4())
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_10y=0.27, price=80.0, book_value=61.5, eps_ttm=7.25,
        )
        row = _make_analysis_row(
            graham_output_msft, ticker="BNS", ratios=ratios, analysis_id=analysis_id
        )

        async def _fetchrow(query, *args):
            # Reproduit WHERE id = $1::uuid AND ticker = $2
            if "WHERE id =" in query and len(args) == 2:
                aid, tk = args
                if aid == analysis_id and tk == "BNS":
                    return row
            return None

        mock_history_svc = AsyncMock()
        mock_history_svc.get_history = AsyncMock(return_value=_make_history(3, ticker="BNS"))

        mock_pdf_svc = AsyncMock(spec=PdfReportService)
        mock_pdf_svc.generate_ticker_report = AsyncMock(return_value=b"%PDF-1.4 mock")

        app.state.composite_history_service = mock_history_svc
        app.state.pdf_report_service = mock_pdf_svc
        app.state.db_pool.fetchrow = AsyncMock(side_effect=_fetchrow)

        yield client, analysis_id, mock_pdf_svc

        for attr in ("composite_history_service", "pdf_report_service"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)

    @pytest.mark.asyncio
    async def test_analysis_id_valide_retourne_200_pdf(self, targeted_client):
        c, analysis_id, mock_pdf_svc = targeted_client
        resp = await c.get(f"/ticker-report/BNS?analysis_id={analysis_id}")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        # ratios + last_analysis propagés à la génération
        kwargs = mock_pdf_svc.generate_ticker_report.call_args.kwargs
        assert kwargs["ratios"] is not None
        assert kwargs["last_analysis"] is not None

    @pytest.mark.asyncio
    async def test_analysis_id_inconnu_retourne_404(self, targeted_client):
        c, _analysis_id, _ = targeted_client
        autre_id = str(uuid.uuid4())
        resp = await c.get(f"/ticker-report/BNS?analysis_id={autre_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_analysis_id_mismatch_ticker_retourne_404(self, targeted_client):
        c, analysis_id, _ = targeted_client
        resp = await c.get(f"/ticker-report/TD?analysis_id={analysis_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_analysis_id_malforme_retourne_404(self, targeted_client):
        c, _analysis_id, _ = targeted_client
        resp = await c.get("/ticker-report/BNS?analysis_id=pas-un-uuid")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests : enrichissement PDF (ratios, annotation, ESG, verdicts)
# ---------------------------------------------------------------------------


class TestPdfReportEnrichi:

    @pytest.mark.asyncio
    async def test_pdf_avec_ratios_annotation_esg(self, analyze_response_msft):
        svc = PdfReportService()
        ratios = GrahamRatios(
            pe=34.2, pb=12.1, current_ratio=1.34, debt_equity=0.28,
            eps_growth_10y=0.85, price=420.0, book_value=35.0, eps_ttm=11.2,
        )
        pdf = await svc.generate_ticker_report(
            ticker="MSFT",
            history=_make_history(3, ticker="MSFT"),
            last_analysis=analyze_response_msft,
            ratios=ratios,
            annotation="Surveiller la marge & le R&D <croissance>.",
            esg_score=8.0,
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 0

    @pytest.mark.asyncio
    async def test_pdf_enrichi_params_none_retrocompat(self, analyze_response_msft):
        """Sans les nouveaux paramètres, le PDF reste valide (rétrocompatibilité)."""
        svc = PdfReportService()
        pdf = await svc.generate_ticker_report(
            ticker="MSFT",
            history=_make_history(2, ticker="MSFT"),
            last_analysis=analyze_response_msft,
        )
        assert pdf[:4] == b"%PDF"
