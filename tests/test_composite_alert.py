"""Tests unitaires pour CompositeAlertService (Sprint 48)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.composite_alert import CompositeAlertResult, CompositeAlertService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeCompositeScore:
    score: float
    label: str = "MODERE"


@dataclass
class _FakeResponse:
    composite_score: _FakeCompositeScore | None


def _make_entry(
    ticker: str,
    last_composite_score: float | None,
    composite_alert_threshold: float = 15.0,
    ratios=None,
    workflow: str = "value_graham",
    entry_id: str = "abc-123",
):
    entry = MagicMock()
    entry.id = entry_id
    entry.ticker = ticker
    entry.last_composite_score = last_composite_score
    entry.composite_alert_threshold = composite_alert_threshold
    entry.ratios = ratios
    entry.workflow = workflow
    return entry


def _make_service(
    entries,
    new_score: float | None = 70.0,
    email_service=None,
    email_to: str | None = None,
):
    watchlist = AsyncMock()
    watchlist.list_entries = AsyncMock(return_value=entries)
    watchlist.update_composite_score = AsyncMock()

    orchestrator = AsyncMock()
    if new_score is not None:
        orchestrator.run_company_analysis = AsyncMock(
            return_value=_FakeResponse(_FakeCompositeScore(score=new_score))
        )
    else:
        orchestrator.run_company_analysis = AsyncMock(
            return_value=_FakeResponse(composite_score=None)
        )

    svc = CompositeAlertService(
        watchlist_service=watchlist,
        orchestrator=orchestrator,
        email_service=email_service,
        email_to=email_to,
    )
    return svc, watchlist, orchestrator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCheckCompositeAlerts:

    @pytest.mark.asyncio
    async def test_aucune_entree_avec_baseline_retourne_vide(self):
        entries = [
            _make_entry("AAPL", last_composite_score=None),
            _make_entry("MSFT", last_composite_score=None),
        ]
        svc, _, _ = _make_service(entries)
        resultats = await svc.check_composite_alerts()
        assert resultats == []

    @pytest.mark.asyncio
    async def test_score_stable_pas_alerte(self):
        # baseline 80, new_score 70 => chute 10 < seuil 15
        entries = [_make_entry("BNS", last_composite_score=80.0)]
        svc, watchlist, _ = _make_service(entries, new_score=70.0)

        resultats = await svc.check_composite_alerts()

        assert len(resultats) == 1
        r = resultats[0]
        assert r.ticker == "BNS"
        assert r.baseline == 80.0
        assert r.new_score == 70.0
        assert r.chute == pytest.approx(10.0)
        assert r.alerte_declenchee is False

    @pytest.mark.asyncio
    async def test_chute_superieure_au_seuil_declenche_alerte(self):
        # baseline 80, new_score 60 => chute 20 > seuil 15
        entries = [_make_entry("BNS", last_composite_score=80.0)]
        svc, _, _ = _make_service(entries, new_score=60.0)

        resultats = await svc.check_composite_alerts()

        assert len(resultats) == 1
        r = resultats[0]
        assert r.alerte_declenchee is True
        assert r.chute == pytest.approx(20.0)

    @pytest.mark.asyncio
    async def test_alerte_logue_warning(self, caplog):
        entries = [_make_entry("TSLA", last_composite_score=80.0)]
        svc, _, _ = _make_service(entries, new_score=60.0)

        with caplog.at_level(logging.WARNING, logger="app.services.composite_alert"):
            await svc.check_composite_alerts()

        assert any("TSLA" in r.message for r in caplog.records if r.levelno == logging.WARNING)

    @pytest.mark.asyncio
    async def test_update_composite_score_appele_avec_nouveau_score(self):
        entries = [_make_entry("TD", last_composite_score=75.0, entry_id="id-td")]
        svc, watchlist, _ = _make_service(entries, new_score=68.0)

        await svc.check_composite_alerts()

        watchlist.update_composite_score.assert_awaited_once_with("id-td", 68.0)

    @pytest.mark.asyncio
    async def test_composite_score_absent_saute_entree(self):
        entries = [_make_entry("GME", last_composite_score=70.0)]
        svc, watchlist, _ = _make_service(entries, new_score=None)

        resultats = await svc.check_composite_alerts()

        assert resultats == []
        watchlist.update_composite_score.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exception_sur_un_ticker_ne_bloque_pas_les_autres(self):
        entries = [
            _make_entry("ERR", last_composite_score=80.0, entry_id="id-err"),
            _make_entry("OK", last_composite_score=80.0, entry_id="id-ok"),
        ]
        watchlist = AsyncMock()
        watchlist.list_entries = AsyncMock(return_value=entries)
        watchlist.update_composite_score = AsyncMock()

        orchestrator = AsyncMock()
        # Premier ticker leve une exception, second retourne 70
        orchestrator.run_company_analysis = AsyncMock(
            side_effect=[RuntimeError("boom"), _FakeResponse(_FakeCompositeScore(70.0))]
        )

        svc = CompositeAlertService(watchlist_service=watchlist, orchestrator=orchestrator)
        resultats = await svc.check_composite_alerts()

        assert len(resultats) == 1
        assert resultats[0].ticker == "OK"

    @pytest.mark.asyncio
    async def test_seuil_personnalise_respecte(self):
        # seuil 5, chute 10 => alerte
        entries = [_make_entry("RY", last_composite_score=80.0, composite_alert_threshold=5.0)]
        svc, _, _ = _make_service(entries, new_score=70.0)

        resultats = await svc.check_composite_alerts()
        assert resultats[0].alerte_declenchee is True
        assert resultats[0].threshold == 5.0

    @pytest.mark.asyncio
    async def test_plusieurs_entrees_traitees(self):
        entries = [
            _make_entry("A", last_composite_score=80.0, entry_id="id-a"),
            _make_entry("B", last_composite_score=None, entry_id="id-b"),
            _make_entry("C", last_composite_score=70.0, entry_id="id-c"),
        ]
        watchlist = AsyncMock()
        watchlist.list_entries = AsyncMock(return_value=entries)
        watchlist.update_composite_score = AsyncMock()

        orchestrator = AsyncMock()
        orchestrator.run_company_analysis = AsyncMock(
            side_effect=[
                _FakeResponse(_FakeCompositeScore(75.0)),  # A: chute 5 => pas d'alerte
                _FakeResponse(_FakeCompositeScore(50.0)),  # C: chute 20 => alerte
            ]
        )

        svc = CompositeAlertService(watchlist_service=watchlist, orchestrator=orchestrator)
        resultats = await svc.check_composite_alerts()

        assert len(resultats) == 2
        assert resultats[0].ticker == "A"
        assert resultats[0].alerte_declenchee is False
        assert resultats[1].ticker == "C"
        assert resultats[1].alerte_declenchee is True


class TestSendAlertEmail:

    @pytest.mark.asyncio
    async def test_email_envoye_si_configure(self):
        email_svc = AsyncMock()
        email_svc.send_text = AsyncMock()

        entries = [_make_entry("AAPL", last_composite_score=80.0)]
        svc, _, _ = _make_service(
            entries, new_score=60.0, email_service=email_svc, email_to="test@example.com"
        )

        await svc.check_composite_alerts()

        email_svc.send_text.assert_awaited_once()
        call_kwargs = email_svc.send_text.call_args
        assert call_kwargs.kwargs["to"] == "test@example.com"
        assert "AAPL" in call_kwargs.kwargs["subject"]

    @pytest.mark.asyncio
    async def test_email_non_envoye_si_service_absent(self, caplog):
        entries = [_make_entry("AAPL", last_composite_score=80.0)]
        svc, _, _ = _make_service(entries, new_score=60.0, email_service=None, email_to=None)

        with caplog.at_level(logging.WARNING, logger="app.services.composite_alert"):
            await svc.check_composite_alerts()

        assert any("non configure" in r.message for r in caplog.records if r.levelno == logging.WARNING)

    @pytest.mark.asyncio
    async def test_email_non_envoye_si_destinataire_absent(self, caplog):
        email_svc = AsyncMock()
        entries = [_make_entry("BNS", last_composite_score=80.0)]
        svc, _, _ = _make_service(
            entries, new_score=60.0, email_service=email_svc, email_to=None
        )

        with caplog.at_level(logging.WARNING, logger="app.services.composite_alert"):
            await svc.check_composite_alerts()

        email_svc.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_echec_envoi_email_ne_bloque_pas_le_flux(self):
        email_svc = AsyncMock()
        email_svc.send_text = AsyncMock(side_effect=Exception("SMTP error"))

        entries = [_make_entry("TD", last_composite_score=80.0)]
        svc, watchlist, _ = _make_service(
            entries, new_score=60.0, email_service=email_svc, email_to="test@example.com"
        )

        resultats = await svc.check_composite_alerts()

        # Le resultat est quand meme retourne malgre l'echec email
        assert len(resultats) == 1
        assert resultats[0].alerte_declenchee is True
        # Et le score est quand meme mis a jour
        watchlist.update_composite_score.assert_awaited_once()
