"""Tests Sprint 125 — filtre par tags d'annotation GET /history(-paged)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import (
    HistoryEntry,
    HistoryResponse,
    Orchestrator,
    PagedHistoryResponse,
)

_ENTRY_TAGGED = HistoryEntry(
    analysis_id="aaaaaaaa-0000-0000-0000-000000000001",
    ticker="BNS",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.004,
    defensive_score=7,
    graham_verdict="CANDIDAT_SOLIDE",
    earnings_verdict=None,
    tags=["value", "growth"],
    created_at="2026-05-01T12:00:00+00:00",
)


class TestHistoryTagsEndpoint:
    """Niveau endpoint — le paramètre CSV `tags` est parsé et transmis à l'orchestrateur."""

    @pytest.mark.asyncio
    async def test_tags_unique_forward_liste(self, client):
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[_ENTRY_TAGGED], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        r = await client.get("/history?ticker=BNS&tags=value")
        assert r.status_code == 200
        assert mock_get.call_args.kwargs["tags"] == ["value"]

    @pytest.mark.asyncio
    async def test_tags_multi_csv_forward_liste_de_deux(self, client):
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[_ENTRY_TAGGED], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        r = await client.get("/history?ticker=BNS&tags=value,growth")
        assert r.status_code == 200
        assert mock_get.call_args.kwargs["tags"] == ["value", "growth"]
        # les tags sont exposés dans la réponse pour l'affichage des chips
        assert r.json()["entries"][0]["tags"] == ["value", "growth"]

    @pytest.mark.asyncio
    async def test_tags_seul_sans_ticker_ni_q_autorise(self, client):
        """Un filtre tags seul (sans ticker ni q) doit être accepté."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[_ENTRY_TAGGED], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        r = await client.get("/history?tags=value")
        assert r.status_code == 200
        assert mock_get.call_args.kwargs["tags"] == ["value"]

    @pytest.mark.asyncio
    async def test_tags_vide_retourne_422(self, client):
        """Un paramètre tags présent mais sans tag non vide est malformé → 422."""
        r = await client.get("/history?ticker=BNS&tags=")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_tags_virgules_seules_retourne_422(self, client):
        r = await client.get("/history?ticker=BNS&tags=,,")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_paged_tags_forward(self, client):
        mock_get = AsyncMock(
            return_value=PagedHistoryResponse(
                ticker="BNS", q=None, entries=[_ENTRY_TAGGED],
                page=1, page_size=10, total_count=1, total_pages=1,
            )
        )
        app.state.orchestrator.get_history_paged = mock_get
        r = await client.get("/history-paged?tags=value,growth")
        assert r.status_code == 200
        assert mock_get.call_args.kwargs["tags"] == ["value", "growth"]


def _fake_row(tags_json: str | None) -> dict:
    """Simule une row du JOIN analysis_history ⨝ annotations (tags JSONB en str)."""
    return {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "ticker": "BNS",
        "workflow_name": "value_graham",
        "skills_used": '["graham_analysis"]',
        "cost_usd": 0.004,
        "result": '{"graham": {"defensive_score": 7, "verdict": "CANDIDAT_SOLIDE"}}',
        "created_at": datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        "annotation_tags": tags_json,
    }


class TestGetHistoryQuery:
    """Niveau requête — get_history sérialise les tags en JSONB et décode le résultat.

    Le filtrage `@>` lui-même s'exécute en SQL (non vérifiable hors Postgres) ; ce
    niveau vérifie que le paramètre jsonb est bien construit et que les tags joints
    sont décodés dans la réponse.
    """

    @pytest.mark.asyncio
    async def test_tags_param_serialise_en_jsonb_et_decode(self):
        orch = Orchestrator.__new__(Orchestrator)
        orch._db = AsyncMock()
        orch._db.fetch.return_value = [_fake_row('["value", "growth"]')]

        resp = await orch.get_history(ticker="BNS", tags=["value", "growth"])

        # 8e paramètre positionnel ($7) = tags sérialisés en JSON pour le cast ::jsonb
        assert orch._db.fetch.call_args.args[7] == '["value", "growth"]'
        assert resp.entries[0].tags == ["value", "growth"]

    @pytest.mark.asyncio
    async def test_sans_tags_passe_none(self):
        orch = Orchestrator.__new__(Orchestrator)
        orch._db = AsyncMock()
        orch._db.fetch.return_value = [_fake_row(None)]

        resp = await orch.get_history(ticker="BNS")

        assert orch._db.fetch.call_args.args[7] is None
        assert resp.entries[0].tags == []

    @pytest.mark.asyncio
    async def test_non_match_retourne_vide(self):
        orch = Orchestrator.__new__(Orchestrator)
        orch._db = AsyncMock()
        orch._db.fetch.return_value = []  # le filtre @> SQL n'a rien retourné

        resp = await orch.get_history(tags=["inexistant"])

        assert resp.entries == []
