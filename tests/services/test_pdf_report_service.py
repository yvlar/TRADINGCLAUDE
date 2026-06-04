"""Tests CI standard pour PdfReportService et GET /ticker-report/{ticker} — Sprint 63.

Aucun appel Claude réel. PdfReportService utilise reportlab (synchrone).
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock

import pypdf
import pytest
import pytest_asyncio

from app.api.endpoints.ticker_report import (
    _extract_earnings_ratios,
    _extract_ratios,
    _extract_valuation_ratios,
    _reconstruct_analyze_response,
)
from app.api.main import app
from app.services.composite_history_service import CompositeHistoryPoint
from app.services.pdf_report_service import (
    PdfReportService,
    _build_ratios_rows,
    _build_ratios_source_rows,
)
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

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
# Tests : libellé honnête de la croissance BPA (Sprint 130)
# ---------------------------------------------------------------------------


class TestRatiosRowsLabel:
    def _ratios(self, **kwargs) -> GrahamRatios:
        base = dict(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
        )
        base.update(kwargs)
        return GrahamRatios(**base)

    def test_libelle_indique_horizon_reel(self):
        """eps_growth_years renseigné → libellé « sur N ans » (pas « 10 ans »)."""
        rows = _build_ratios_rows(self._ratios(eps_growth_years=4))
        labels = [label for label, _ in rows]
        assert "Croissance BPA sur 4 ans" in labels
        assert all("10 ans" not in label for label in labels)

    def test_libelle_horizon_inconnu(self):
        """eps_growth_years None → libellé « horizon n.d. » plutôt qu'un faux « 10 ans »."""
        rows = _build_ratios_rows(self._ratios(eps_growth_years=None))
        labels = [label for label, _ in rows]
        assert "Croissance BPA (horizon n.d.)" in labels

    def test_ligne_source_date_presente_quand_renseignee(self):
        """ratios_fetched_at + ratios_source présents → ligne « <source> · récupéré le AAAA-MM-JJ »."""
        r = self._ratios(
            ratios_source="Yahoo Finance",
            ratios_fetched_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        )
        rows = _build_ratios_rows(r)
        valeurs = {label: valeur for label, valeur in rows}
        assert "Source des ratios" in valeurs
        assert valeurs["Source des ratios"] == "Yahoo Finance · récupéré le 2026-05-30"

    def test_ligne_source_omise_quand_none(self):
        """Analyse ancienne (traçabilité None) → ligne source omise, pas de plantage ni date factice."""
        rows = _build_ratios_rows(self._ratios())
        labels = [label for label, _ in rows]
        assert "Source des ratios" not in labels


# ---------------------------------------------------------------------------
# Tests : _build_ratios_source_rows — source+date earnings/valuation (Sprint 145)
# ---------------------------------------------------------------------------


class TestRatiosSourceRows:
    """Une ligne n'est produite que si le ratio porte une source ou une date (parité Graham None)."""

    def _earnings_avec_source(
        self, ratios_earnings_msft: EarningsQualityRatios
    ) -> EarningsQualityRatios:
        return ratios_earnings_msft.model_copy(
            update={
                "ratios_source": "Yahoo Finance",
                "ratios_fetched_at": datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
            }
        )

    def test_ligne_earnings_rendue_quand_source_presente(self, ratios_earnings_msft):
        rows = _build_ratios_source_rows(self._earnings_avec_source(ratios_earnings_msft), None)
        valeurs = dict(rows)
        assert (
            valeurs["Source des ratios (Qualité bénéfices)"]
            == "Yahoo Finance · récupéré le 2026-05-30"
        )
        assert "Source des ratios (Valorisation)" not in valeurs

    def test_ligne_valuation_rendue_quand_source_presente(self):
        valuation = ValuationRatios(
            pe=34.2,
            ratios_source="Yahoo Finance",
            ratios_fetched_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        )
        rows = _build_ratios_source_rows(None, valuation)
        valeurs = dict(rows)
        assert (
            valeurs["Source des ratios (Valorisation)"]
            == "Yahoo Finance · récupéré le 2026-05-30"
        )
        assert "Source des ratios (Qualité bénéfices)" not in valeurs

    def test_les_deux_lignes_rendues(self, ratios_earnings_msft):
        """Earnings + valuation présents → deux lignes ; source sans date → libellé sans « récupéré le »."""
        valuation = ValuationRatios(ratios_source="SEDAR+", ratios_fetched_at=None)
        rows = _build_ratios_source_rows(
            self._earnings_avec_source(ratios_earnings_msft), valuation
        )
        valeurs = dict(rows)
        assert "Source des ratios (Qualité bénéfices)" in valeurs
        assert valeurs["Source des ratios (Valorisation)"] == "SEDAR+"

    def test_ratio_sans_source_ni_date_omis(self, ratios_earnings_msft):
        """Ratio présent mais traçabilité None → ligne omise (parité Graham None)."""
        valuation = ValuationRatios(pe=34.2)  # aucune source ni date
        rows = _build_ratios_source_rows(ratios_earnings_msft, valuation)
        assert rows == []

    def test_ratios_none_donne_liste_vide(self):
        assert _build_ratios_source_rows(None, None) == []


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
    earnings_ratios=None,
    valuation_ratios=None,
    analysis_id: str | None = None,
    skill_corrompu: bool = False,
) -> dict:
    """Construit une ligne analysis_history (dict compatible asyncpg.Record indexable)."""
    result: dict = {"graham": graham_output.model_dump()}
    if earnings_output is not None:
        result["earnings_quality"] = earnings_output.model_dump()
    if skill_corrompu:
        result["dorsey_moat"] = {"champ_invalide": "data corrompue"}
    input_payload: dict = ratios.model_dump(mode="json") if ratios is not None else {}
    if earnings_ratios is not None:
        input_payload["earnings_ratios"] = earnings_ratios.model_dump(mode="json")
    if valuation_ratios is not None:
        input_payload["valuation_ratios"] = valuation_ratios.model_dump(mode="json")
    return {
        "id": analysis_id or str(uuid.uuid4()),
        "ticker": ticker,
        "workflow_name": "value_graham",
        "skills_used": json.dumps(list(result.keys())),
        "input_data": json.dumps(input_payload),
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

    def test_tracabilite_reconstruite_depuis_input_data(self, graham_output_msft, ratios_msft):
        """Une analyse rechargée reconstruit la source+date des ratios depuis input_data."""
        ratios = ratios_msft.model_copy(
            update={
                "ratios_fetched_at": datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
                "ratios_source": "Yahoo Finance",
            }
        )
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios)
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.ratios_source == "Yahoo Finance"
        assert result.ratios_fetched_at is not None
        assert result.ratios_fetched_at.startswith("2026-05-20")

    def test_tracabilite_none_sans_horodatage(self, graham_output_msft, ratios_msft):
        """Analyse ancienne sans horodatage → champs None, pas de crash."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios_msft)
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.ratios_fetched_at is None
        assert result.ratios_source is None

    def test_input_data_corrompu_ne_fait_pas_crasher(self, graham_output_msft):
        """input_data illisible → traçabilité None sans propager d'exception."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT")
        row["input_data"] = "{ ceci n'est pas du JSON"
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.ratios_fetched_at is None
        assert result.ratios_source is None

    def test_tracabilite_earnings_valuation_reconstruite(
        self, graham_output_msft, ratios_msft, ratios_earnings_msft
    ):
        """Une analyse rechargée reconstruit la source+date earnings/valuation depuis input_data."""
        earnings = ratios_earnings_msft.model_copy(
            update={
                "ratios_fetched_at": datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
                "ratios_source": "Yahoo Finance",
            }
        )
        valuation = ValuationRatios(
            pe=34.2,
            ratios_fetched_at=datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
            ratios_source="Yahoo Finance",
        )
        row = _make_analysis_row(
            graham_output_msft,
            ticker="MSFT",
            ratios=ratios_msft,
            earnings_ratios=earnings,
            valuation_ratios=valuation,
        )
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.earnings_ratios_source == "Yahoo Finance"
        assert result.earnings_ratios_fetched_at is not None
        assert result.earnings_ratios_fetched_at.startswith("2026-05-20")
        assert result.valuation_ratios_source == "Yahoo Finance"
        assert result.valuation_ratios_fetched_at is not None
        assert result.valuation_ratios_fetched_at.startswith("2026-05-20")

    def test_tracabilite_earnings_valuation_none_ligne_plate(
        self, graham_output_msft, ratios_msft
    ):
        """Ancien input_data plat (Graham seul, sans sous-clés) → quatre champs None, pas de crash."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios_msft)
        result = _reconstruct_analyze_response(row)
        assert result is not None
        assert result.earnings_ratios_fetched_at is None
        assert result.earnings_ratios_source is None
        assert result.valuation_ratios_fetched_at is None
        assert result.valuation_ratios_source is None


# ---------------------------------------------------------------------------
# Tests : reconstruction earnings/valuation depuis input_data (sous-clés dédiées)
# ---------------------------------------------------------------------------


class TestExtractEarningsValuationRatios:

    def test_earnings_reconstruits_avec_tracabilite(
        self, graham_output_msft, ratios_msft, ratios_earnings_msft
    ):
        """Sous-clé earnings_ratios horodatée → reconstruction avec source+date."""
        earnings = ratios_earnings_msft.model_copy(
            update={
                "ratios_fetched_at": datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
                "ratios_source": "Yahoo Finance",
            }
        )
        row = _make_analysis_row(
            graham_output_msft, ticker="MSFT", ratios=ratios_msft, earnings_ratios=earnings
        )
        recon = _extract_earnings_ratios(row)
        assert recon is not None
        assert recon.ratios_source == "Yahoo Finance"
        assert recon.ratios_fetched_at is not None

    def test_valuation_reconstruits_avec_tracabilite(self, graham_output_msft, ratios_msft):
        """Sous-clé valuation_ratios horodatée → reconstruction avec source+date."""
        valuation = ValuationRatios(
            pe=34.2,
            ratios_fetched_at=datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
            ratios_source="Yahoo Finance",
        )
        row = _make_analysis_row(
            graham_output_msft, ticker="MSFT", ratios=ratios_msft, valuation_ratios=valuation
        )
        recon = _extract_valuation_ratios(row)
        assert recon is not None
        assert recon.ratios_source == "Yahoo Finance"
        assert recon.pe == 34.2

    def test_ligne_ancienne_sans_sous_cles_donne_none(self, graham_output_msft, ratios_msft):
        """Ancienne ligne plate (Graham seul) → earnings/valuation None, pas de crash."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios_msft)
        assert _extract_earnings_ratios(row) is None
        assert _extract_valuation_ratios(row) is None

    def test_input_data_illisible_donne_none(self, graham_output_msft, ratios_msft):
        """input_data corrompu → None, jamais d'exception."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios_msft)
        row["input_data"] = "{ pas du JSON valide"
        assert _extract_earnings_ratios(row) is None
        assert _extract_valuation_ratios(row) is None

    def test_sous_cle_malformee_donne_none(self, graham_output_msft, ratios_msft):
        """Sous-clé earnings_ratios non conforme au schéma → None, pas de crash."""
        row = _make_analysis_row(graham_output_msft, ticker="MSFT", ratios=ratios_msft)
        data = json.loads(row["input_data"])
        data["earnings_ratios"] = {"sales_t": "pas_un_nombre"}
        row["input_data"] = json.dumps(data)
        assert _extract_earnings_ratios(row) is None

    def test_graham_intact_malgre_sous_cles(
        self, graham_output_msft, ratios_msft, ratios_earnings_msft
    ):
        """Rétrocompat : _extract_ratios (Graham) reste correct quand input_data porte les sous-clés."""
        row = _make_analysis_row(
            graham_output_msft,
            ticker="MSFT",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
        )
        graham = _extract_ratios(row)
        assert graham is not None
        assert graham.price == 420.0


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
            eps_growth_total=0.27, price=80.0, book_value=61.5, eps_ttm=7.25,
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

    @pytest_asyncio.fixture
    async def targeted_client_with_subratios(
        self, client, graham_output_msft, ratios_earnings_msft
    ):
        """Comme targeted_client, mais input_data porte les sous-clés earnings/valuation horodatées."""
        analysis_id = str(uuid.uuid4())
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5, eps_ttm=7.25,
        )
        horodatage = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
        earnings = ratios_earnings_msft.model_copy(
            update={"ratios_source": "Yahoo Finance", "ratios_fetched_at": horodatage}
        )
        valuation = ValuationRatios(
            pe=34.2, ratios_source="Yahoo Finance", ratios_fetched_at=horodatage
        )
        row = _make_analysis_row(
            graham_output_msft, ticker="BNS", ratios=ratios,
            earnings_ratios=earnings, valuation_ratios=valuation, analysis_id=analysis_id,
        )

        async def _fetchrow(query, *args):
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
    async def test_sous_ratios_passes_au_service_pdf(self, targeted_client_with_subratios):
        """Les ratios earnings/valuation reconstruits sont passés au service PDF."""
        c, analysis_id, mock_pdf_svc = targeted_client_with_subratios
        resp = await c.get(f"/ticker-report/BNS?analysis_id={analysis_id}")
        assert resp.status_code == 200
        kwargs = mock_pdf_svc.generate_ticker_report.call_args.kwargs
        assert kwargs["earnings_ratios"] is not None
        assert kwargs["earnings_ratios"].ratios_source == "Yahoo Finance"
        assert kwargs["valuation_ratios"] is not None
        assert kwargs["valuation_ratios"].pe == 34.2

    @pytest.mark.asyncio
    async def test_ligne_ancienne_sans_sous_ratios_passe_none(self, targeted_client):
        """input_data ancien (Graham à plat, sans sous-clés) → earnings/valuation None, pas de crash."""
        c, analysis_id, mock_pdf_svc = targeted_client
        resp = await c.get(f"/ticker-report/BNS?analysis_id={analysis_id}")
        assert resp.status_code == 200
        kwargs = mock_pdf_svc.generate_ticker_report.call_args.kwargs
        assert kwargs["earnings_ratios"] is None
        assert kwargs["valuation_ratios"] is None


# ---------------------------------------------------------------------------
# Tests : enrichissement PDF (ratios, annotation, ESG, verdicts)
# ---------------------------------------------------------------------------


class TestPdfReportEnrichi:

    @pytest.mark.asyncio
    async def test_pdf_avec_ratios_annotation_esg(self, analyze_response_msft):
        svc = PdfReportService()
        ratios = GrahamRatios(
            pe=34.2, pb=12.1, current_ratio=1.34, debt_equity=0.28,
            eps_growth_total=0.85, price=420.0, book_value=35.0, eps_ttm=11.2,
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

    @pytest.mark.asyncio
    async def test_pdf_rend_ligne_source_earnings_valuation(
        self, analyze_response_msft, ratios_earnings_msft
    ):
        """Acceptation : la source+date earnings/valuation apparaît dans le texte du PDF rendu."""
        svc = PdfReportService()
        earnings = ratios_earnings_msft.model_copy(
            update={
                "ratios_source": "Yahoo Finance",
                "ratios_fetched_at": datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
            }
        )
        valuation = ValuationRatios(
            pe=34.2,
            ratios_source="Yahoo Finance",
            ratios_fetched_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        )
        pdf = await svc.generate_ticker_report(
            ticker="MSFT",
            history=_make_history(2, ticker="MSFT"),
            last_analysis=analyze_response_msft,
            earnings_ratios=earnings,
            valuation_ratios=valuation,
        )
        assert pdf[:4] == b"%PDF"
        texte = "".join(
            page.extract_text() for page in pypdf.PdfReader(BytesIO(pdf)).pages
        )
        # Sans param `ratios` Graham, les seules lignes « Source des ratios » sont les deux nouvelles.
        assert texte.count("Source des ratios") == 2
        assert "Valorisation" in texte
        assert "2026-05-30" in texte

    @pytest.mark.asyncio
    async def test_pdf_omet_source_complementaire_sans_tracabilite(self, analyze_response_msft):
        """earnings/valuation sans source/date → aucune ligne « Sources des ratios complémentaires »."""
        svc = PdfReportService()
        pdf = await svc.generate_ticker_report(
            ticker="MSFT",
            history=_make_history(2, ticker="MSFT"),
            last_analysis=analyze_response_msft,
            earnings_ratios=EarningsQualityRatios(
                sales_t=1.0, sales_t1=1.0, cogs_t=1.0, cogs_t1=1.0,
                net_income_t=1.0, cfo_t=1.0, receivables_t=1.0, receivables_t1=1.0,
                current_assets_t=1.0, current_liabilities_t=1.0,
                total_assets_t=1.0, total_assets_t1=1.0,
            ),
            valuation_ratios=ValuationRatios(pe=34.2),
        )
        assert pdf[:4] == b"%PDF"
        texte = "".join(
            page.extract_text() for page in pypdf.PdfReader(BytesIO(pdf)).pages
        )
        assert "Sources des ratios complémentaires" not in texte
