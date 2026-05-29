"""Tests Sprint 125 — filtre GET /history?tags= et /history-paged?tags= (annotations enrichies)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import HistoryResponse, Orchestrator, PagedHistoryResponse

# ---- Couche endpoint : orchestrateur mocké (parsing CSV + 422) ----


class TestHistoryTagsEndpoint:
    @pytest.mark.asyncio
    async def test_tags_csv_transmis_en_liste(self, client):
        """`?tags=value,growth` est transmis à l'orchestrateur comme liste nettoyée."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?ticker=BNS&tags=value, growth ")
        assert mock_get.call_args.kwargs["tags"] == ["value", "growth"]

    @pytest.mark.asyncio
    async def test_tags_mis_en_minuscules(self, client):
        """`?tags=Value,GROWTH` est normalisé en minuscules (alignement avec `@>`)."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?ticker=BNS&tags=Value,GROWTH")
        assert mock_get.call_args.kwargs["tags"] == ["value", "growth"]

    @pytest.mark.asyncio
    async def test_tags_absent_transmet_none(self, client):
        """Sans `?tags=`, l'orchestrateur reçoit tags=None (aucun filtre)."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?ticker=BNS")
        assert mock_get.call_args.kwargs["tags"] is None

    @pytest.mark.asyncio
    async def test_tags_vide_retourne_422(self, client):
        """`?tags=` vide est malformé → 422."""
        r = await client.get("/history?ticker=BNS&tags=")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_tags_seulement_virgules_retourne_422(self, client):
        """`?tags=,,` (aucun token valide) → 422."""
        r = await client.get("/history?ticker=BNS&tags=,,")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_paged_tags_transmis(self, client):
        """`/history-paged?tags=` est transmis à get_history_paged comme liste."""
        mock_get = AsyncMock(
            return_value=PagedHistoryResponse(
                ticker="BNS", q=None, entries=[], page=1, page_size=10,
                total_count=0, total_pages=1,
            )
        )
        app.state.orchestrator.get_history_paged = mock_get
        await client.get("/history-paged?ticker=BNS&tags=dividende")
        assert mock_get.call_args.kwargs["tags"] == ["dividende"]

    @pytest.mark.asyncio
    async def test_paged_tags_vide_retourne_422(self, client):
        """`/history-paged?tags=` vide → 422."""
        r = await client.get("/history-paged?ticker=BNS&tags=")
        assert r.status_code == 422


# ---- Couche requête : pool mocké (jointure annotations + opérateur @>) ----


def _mk_row(tags: list[str] | None) -> dict:
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "ticker": "BNS",
        "workflow_name": "value_graham",
        "skills_used": json.dumps(["graham_analysis"]),
        "cost_usd": 0.004,
        "result": json.dumps({"graham": {"defensive_score": 7, "verdict": "CANDIDAT_SOLIDE"}}),
        "created_at": datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        "tags": tags,
    }


@pytest.fixture
def orchestrator_db():
    """Construit un vrai Orchestrator (méthodes réelles) sur un pool asyncpg mocké.

    Le fixture `client` remplace `app.state.orchestrator` par un AsyncMock complet ; on
    instancie donc directement la classe pour exercer le vrai SQL de get_history.
    """
    mock_db = AsyncMock()
    orch = Orchestrator(db_pool=mock_db, graham_skill=AsyncMock(), earnings_skill=AsyncMock())
    return orch, mock_db


class TestGetHistoryTagsQuery:
    @pytest.mark.asyncio
    async def test_get_history_lie_les_tags_et_jointe_annotations(self, orchestrator_db):
        """get_history lie les tags ($7::text[]), joint annotations, et renvoie les tags."""
        orch, mock_db = orchestrator_db
        mock_db.fetch.return_value = [_mk_row(["value", "growth"])]

        resp = await orch.get_history(ticker="BNS", tags=["value", "growth"])

        sql, *args = mock_db.fetch.call_args.args
        assert "LEFT JOIN annotations" in sql
        assert "a.tags @> $7::text[]" in sql
        assert args[-1] == ["value", "growth"]
        assert resp.entries[0].tags == ["value", "growth"]

    @pytest.mark.asyncio
    async def test_get_history_sans_tags_passe_none(self, orchestrator_db):
        """Sans tags, le 7e paramètre lié est None (le filtre `@>` est neutralisé)."""
        orch, mock_db = orchestrator_db
        mock_db.fetch.return_value = [_mk_row(None)]

        resp = await orch.get_history(ticker="BNS")

        assert mock_db.fetch.call_args.args[-1] is None
        # tags NULL côté DB (analyse sans annotation) → liste vide
        assert resp.entries[0].tags == []

    @pytest.mark.asyncio
    async def test_get_history_paged_lie_les_tags(self, orchestrator_db):
        """get_history_paged lie les tags dans la requête de lignes et de comptage."""
        orch, mock_db = orchestrator_db
        mock_db.fetch.return_value = [_mk_row(["value"])]
        mock_db.fetchval.return_value = 1

        resp = await orch.get_history_paged(ticker="BNS", tags=["value"])

        fetch_sql, *fetch_args = mock_db.fetch.call_args.args
        assert "a.tags @> $7::text[]" in fetch_sql
        assert fetch_args[-1] == ["value"]
        count_sql, *count_args = mock_db.fetchval.call_args.args
        assert "a.tags @> $5::text[]" in count_sql
        assert count_args[-1] == ["value"]
        assert resp.entries[0].tags == ["value"]
