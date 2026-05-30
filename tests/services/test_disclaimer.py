"""Tests Sprint 129 — bloc d'avertissement réglementaire dans les rapports PDF.

CI standard : pytest -m "not e2e and not evals". Aucun appel Claude réel.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from reportlab.platypus import Paragraph

from app.api.endpoints.screen import ScreenEntry, ScreenResult
from app.services.disclaimer import DISCLAIMER_TEXT, build_disclaimer_flowables
from app.services.pdf_report_service import PdfReportService
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.watchlist_pdf_service import WatchlistPdfService
from tests.services.test_pdf_report_service import _make_history


def _story_contient_disclaimer(story: list) -> bool:
    """Vrai si un Paragraph du story porte le texte d'avertissement."""
    return any(
        isinstance(flowable, Paragraph) and DISCLAIMER_TEXT in flowable.getPlainText()
        for flowable in story
    )


def _patch_build_capture(captured: dict[str, list]):
    """Patche SimpleDocTemplate.build pour capturer le story sans rendre le PDF."""

    def _capture(self, story, *args, **kwargs):  # noqa: ANN001
        captured["story"] = story

    return patch("reportlab.platypus.SimpleDocTemplate.build", _capture)


class TestBuildDisclaimerFlowables:
    def test_contient_un_paragraph_avec_le_texte(self):
        flowables = build_disclaimer_flowables()
        assert _story_contient_disclaimer(flowables)


class TestDisclaimerDansRapportTicker:
    @pytest.mark.asyncio
    async def test_story_du_ticker_report_contient_le_disclaimer(self):
        """Le story passé à doc.build contient le bloc d'avertissement."""
        captured: dict[str, list] = {}
        with _patch_build_capture(captured):
            await PdfReportService().generate_ticker_report(
                ticker="BNS", history=_make_history(3), last_analysis=None
            )
        assert _story_contient_disclaimer(captured["story"])


class TestDisclaimerDansAutresRapports:
    def test_story_du_screener_contient_le_disclaimer(self):
        captured: dict[str, list] = {}
        result = ScreenResult(
            tickers_analyses=1,
            tickers_echec=0,
            tickers_depuis_cache=0,
            cout_total_usd=0.0,
            resultats=[
                ScreenEntry(
                    ticker="BNS",
                    defensive_score=6,
                    verdict="PASSE",
                    composite_score=75.0,
                    composite_label="FORT",
                    workflow_utilise="value_graham",
                    cost_usd=0.0,
                    depuis_cache=False,
                    erreur=None,
                )
            ],
            workflow="value_graham",
            duration_ms=0,
        )
        with _patch_build_capture(captured):
            ScreenerPdfService().generate(result, title="Screener")
        assert _story_contient_disclaimer(captured["story"])

    @pytest.mark.asyncio
    async def test_story_de_la_watchlist_contient_le_disclaimer(self):
        captured: dict[str, list] = {}
        row = {
            "ticker": "BNS",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "composite_alert_threshold": 15.0,
            "composite_score_latest": 75.0,
            "composite_label_latest": "FORT",
            "derniere_analyse": datetime(2026, 5, 1, tzinfo=timezone.utc),
        }
        pool = AsyncMock()
        pool.fetch = AsyncMock(return_value=[row])
        with _patch_build_capture(captured):
            await WatchlistPdfService().generate_watchlist_pdf(pool=pool)
        assert _story_contient_disclaimer(captured["story"])
