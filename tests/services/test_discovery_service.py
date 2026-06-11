"""Tests du service de découverte par catégorie — config, gates, badge, refresh, lecture."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.endpoints.screen import ScreenEntry, ScreenResult
from app.models.discovery import DiscoveryCategoryConfig, UniverseEntry
from app.services.discovery_service import (
    DiscoveryService,
    load_categories,
    risk_badge,
    why_phrase,
)
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_category(**overrides) -> DiscoveryCategoryConfig:
    base = dict(
        id="solides_stables",
        titre="Solides et stables",
        emoji="🟢",
        description="Entreprises établies.",
        niveau_risque="faible",
        workflow="value_graham",
        min_composite_score=45.0,
        min_dividend_years=5,
        max_suggestions=8,
        account_hint="CELI ou non enregistré.",
        univers=[
            UniverseEntry(ticker="RY.TO", name="Banque Royale du Canada"),
            UniverseEntry(ticker="TD.TO", name="Banque TD"),
            UniverseEntry(ticker="BCE.TO", name="BCE (Bell Canada)"),
        ],
    )
    base.update(overrides)
    return DiscoveryCategoryConfig(**base)


def _entry(ticker: str, score: float | None, label: str | None, erreur: str | None = None) -> ScreenEntry:
    return ScreenEntry(
        ticker=ticker,
        defensive_score=5,
        verdict="PASSE",
        composite_score=score,
        composite_label=label,
        workflow_utilise="value_graham",
        cost_usd=0.01,
        depuis_cache=True,
        erreur=erreur,
    )


def _screen_result(entries: list[ScreenEntry]) -> ScreenResult:
    return ScreenResult(
        tickers_analyses=len([e for e in entries if e.erreur is None]),
        tickers_echec=len([e for e in entries if e.erreur is not None]),
        tickers_depuis_cache=0,
        cout_total_usd=0.05,
        resultats=entries,
        workflow="value_graham",
        duration_ms=1000,
    )


def _graham_ratios(dividend_years: int | None = 10) -> GrahamRatios:
    return GrahamRatios(
        price=82.40, pe=11.2, eps_growth_total=0.25, dividend_years=dividend_years
    )


def _valuation_ratios() -> ValuationRatios:
    return ValuationRatios(price=82.40, dividend_yield=0.041)


def _mock_db(fetch_rows: list | None = None, fetchrow_result=None) -> MagicMock:
    """Pool asyncpg mocké — fetch/fetchrow directs + acquire() pour la transaction d'écriture."""
    conn = AsyncMock()
    tx = AsyncMock()
    tx.__aenter__ = AsyncMock(return_value=None)
    tx.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=tx)

    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=fetch_rows or [])
    pool.fetchrow = AsyncMock(return_value=fetchrow_result)
    pool.acquire = MagicMock(return_value=acquire_cm)
    pool._conn = conn  # accès direct pour les assertions de tests
    return pool


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestLoadCategories:
    def test_config_reelle_se_charge(self):
        cats = load_categories()
        assert "solides_stables" in cats

    def test_categorie_pilote_univers_borne_screener(self):
        # ScreenRequest plafonne à 20 tickers — l'univers d'une catégorie doit tenir dessous
        cats = load_categories()
        for cat in cats.values():
            assert len(cat.univers) <= 20

    def test_tickers_tsx_suffixe_to(self):
        # donnees-financieres.md : les tickers TSX exigent le suffixe .TO
        cats = load_categories()
        for entry in cats["solides_stables"].univers:
            assert entry.ticker.endswith(".TO")

    def test_id_injecte_depuis_la_cle(self):
        cats = load_categories()
        assert cats["solides_stables"].id == "solides_stables"


# ---------------------------------------------------------------------------
# Fonctions pures — badge et phrase
# ---------------------------------------------------------------------------


class TestRiskBadge:
    def test_fort_categorie_defensive(self):
        assert risk_badge("FORT", "faible") == "faible"

    def test_modere_categorie_defensive(self):
        assert risk_badge("MODÉRÉ", "faible") == "faible"

    def test_fort_categorie_non_defensive(self):
        assert risk_badge("FORT", "moyen") == "moyen"

    def test_faible_donne_eleve(self):
        assert risk_badge("FAIBLE", "faible") == "élevé"

    def test_label_none_donne_eleve(self):
        assert risk_badge(None, "faible") == "élevé"


class TestWhyPhrase:
    def test_phrase_complete(self):
        phrase = why_phrase("Banque Royale du Canada", "FORT", 78.0, 10)
        assert "Banque Royale du Canada" in phrase
        assert "FORT (78/100)" in phrase
        assert "10 ans" in phrase

    def test_sans_dividende(self):
        phrase = why_phrase("Test", "MODÉRÉ", 50.0, None)
        assert "dividende" not in phrase

    def test_jamais_imperative(self):
        # garde-fou §7 : aucune formulation d'ordre d'achat
        phrase = why_phrase("Test", "FORT", 78.0, 10)
        assert "achète" not in phrase.lower()
        assert "achetez" not in phrase.lower()


# ---------------------------------------------------------------------------
# Rafraîchissement — gates et persistance
# ---------------------------------------------------------------------------


class TestRefreshCategory:
    def _make_service(self, entries: list[ScreenEntry], dividend_years: int | None = 10):
        pool = _mock_db()
        screener = AsyncMock()
        screener.screen = AsyncMock(return_value=_screen_result(entries))
        extractor = AsyncMock()
        extractor.extract = AsyncMock(return_value=_graham_ratios(dividend_years))
        extractor.extract_valuation = AsyncMock(return_value=_valuation_ratios())
        service = DiscoveryService(
            db_pool=pool,
            screener=screener,
            extractor=extractor,
            categories={"solides_stables": _make_category()},
        )
        return service, pool

    @pytest.mark.asyncio
    async def test_gate_composite_filtre_les_faibles(self):
        entries = [
            _entry("RY.TO", 78.0, "FORT"),
            _entry("TD.TO", 30.0, "FAIBLE"),  # sous min_composite_score=45 → exclu
        ]
        service, pool = self._make_service(entries)
        count = await service.refresh_category("solides_stables")
        assert count == 1
        inserted = pool._conn.executemany.call_args.args[1]
        assert [row[1] for row in inserted] == ["RY.TO"]

    @pytest.mark.asyncio
    async def test_gate_erreur_exclut(self):
        entries = [
            _entry("RY.TO", 78.0, "FORT"),
            _entry("TD.TO", None, None, erreur="Timeout"),
        ]
        service, _ = self._make_service(entries)
        assert await service.refresh_category("solides_stables") == 1

    @pytest.mark.asyncio
    async def test_gate_dividende_insuffisant_exclut(self):
        entries = [_entry("RY.TO", 78.0, "FORT")]
        service, _ = self._make_service(entries, dividend_years=2)  # < min 5
        assert await service.refresh_category("solides_stables") == 0

    @pytest.mark.asyncio
    async def test_gate_dividende_inconnu_exclut(self):
        # design §4.3 : données manquantes → on ne suggère pas à un débutant
        entries = [_entry("RY.TO", 78.0, "FORT")]
        service, _ = self._make_service(entries, dividend_years=None)
        assert await service.refresh_category("solides_stables") == 0

    @pytest.mark.asyncio
    async def test_gate_earnings_rejeter_exclut(self):
        entries = [_entry("RY.TO", 78.0, "FORT")]
        service, pool = self._make_service(entries)
        pool.fetchrow = AsyncMock(
            return_value={"result_json": '{"earnings_quality": {"verdict": "REJETER"}}'}
        )
        assert await service.refresh_category("solides_stables") == 0

    @pytest.mark.asyncio
    async def test_earnings_illisible_n_exclut_pas(self):
        # best-effort : JSON corrompu → le gate composite reste le filet principal
        entries = [_entry("RY.TO", 78.0, "FORT")]
        service, pool = self._make_service(entries)
        pool.fetchrow = AsyncMock(return_value={"result_json": "pas du json"})
        assert await service.refresh_category("solides_stables") == 1

    @pytest.mark.asyncio
    async def test_extraction_en_echec_exclut_le_titre(self):
        entries = [_entry("RY.TO", 78.0, "FORT"), _entry("TD.TO", 70.0, "FORT")]
        service, _ = self._make_service(entries)
        service._extractor.extract = AsyncMock(
            side_effect=[Exception("yfinance down"), _graham_ratios(10)]
        )
        assert await service.refresh_category("solides_stables") == 1

    @pytest.mark.asyncio
    async def test_plafond_max_suggestions(self):
        entries = [_entry(f"T{i}.TO", 80.0 - i, "FORT") for i in range(5)]
        service, _ = self._make_service(entries)
        service._categories["solides_stables"] = _make_category(max_suggestions=2)
        assert await service.refresh_category("solides_stables") == 2

    @pytest.mark.asyncio
    async def test_suggestion_persistee_complete(self):
        entries = [_entry("RY.TO", 78.0, "FORT")]
        service, pool = self._make_service(entries)
        await service.refresh_category("solides_stables")
        pool._conn.execute.assert_awaited_once()  # DELETE de la catégorie
        (category, ticker, name, score, label, badge, why, *_rest) = (
            pool._conn.executemany.call_args.args[1][0]
        )
        assert (category, ticker) == ("solides_stables", "RY.TO")
        assert name == "Banque Royale du Canada"
        assert (score, label, badge) == (78.0, "FORT", "faible")
        assert "Banque Royale du Canada" in why

    @pytest.mark.asyncio
    async def test_categorie_inconnue_leve_valueerror(self):
        service, _ = self._make_service([])
        with pytest.raises(ValueError, match="inconnue"):
            await service.refresh_category("inexistante")

    @pytest.mark.asyncio
    async def test_refresh_sans_screener_leve_runtimeerror(self):
        service = DiscoveryService(
            db_pool=_mock_db(), categories={"solides_stables": _make_category()}
        )
        with pytest.raises(RuntimeError, match="screener"):
            await service.refresh_category("solides_stables")

    @pytest.mark.asyncio
    async def test_refresh_all_best_effort(self):
        # l'échec d'une catégorie (-1) n'avorte pas les autres
        service, _ = self._make_service([_entry("RY.TO", 78.0, "FORT")])
        service._categories["cassee"] = _make_category(id="cassee")
        service._screener.screen = AsyncMock(
            side_effect=[_screen_result([_entry("RY.TO", 78.0, "FORT")]), Exception("boom")]
        )
        counts = await service.refresh_all()
        assert counts["solides_stables"] == 1
        assert counts["cassee"] == -1


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


class TestLecture:
    _AS_OF = datetime(2026, 6, 11, 6, 0, tzinfo=timezone.utc)

    def _row(self, ticker: str = "RY.TO", score: float = 78.0) -> dict:
        return {
            "ticker": ticker,
            "name": "Banque Royale du Canada",
            "composite_score": score,
            "composite_label": "FORT",
            "risk_badge": "faible",
            "why": "Banque Royale du Canada : entreprise établie.",
            "dividend_yield": 0.041,
            "dividend_years": 10,
            "pe": 11.2,
            "price": 82.40,
            "as_of": self._AS_OF,
        }

    @pytest.mark.asyncio
    async def test_get_category_retourne_suggestions(self):
        pool = _mock_db(fetch_rows=[self._row()])
        service = DiscoveryService(
            db_pool=pool, categories={"solides_stables": _make_category()}
        )
        resp = await service.get_category("solides_stables")
        assert resp.id == "solides_stables"
        assert len(resp.suggestions) == 1
        s = resp.suggestions[0]
        assert s.ticker == "RY.TO"
        assert s.account_hint == "CELI ou non enregistré."
        assert resp.as_of == self._AS_OF.isoformat()

    @pytest.mark.asyncio
    async def test_get_category_vide_liste_vide(self):
        pool = _mock_db(fetch_rows=[])
        service = DiscoveryService(
            db_pool=pool, categories={"solides_stables": _make_category()}
        )
        resp = await service.get_category("solides_stables")
        assert resp.suggestions == []
        assert resp.as_of is None

    @pytest.mark.asyncio
    async def test_get_category_inconnue_404(self):
        service = DiscoveryService(
            db_pool=_mock_db(), categories={"solides_stables": _make_category()}
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.get_category("inexistante")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_categories_avec_compteurs(self):
        pool = _mock_db(
            fetch_rows=[{"category": "solides_stables", "nb": 8, "as_of": self._AS_OF}]
        )
        service = DiscoveryService(
            db_pool=pool, categories={"solides_stables": _make_category()}
        )
        cats = await service.list_categories()
        assert len(cats) == 1
        assert cats[0].nb_suggestions == 8
        assert cats[0].as_of == self._AS_OF.isoformat()

    @pytest.mark.asyncio
    async def test_list_categories_sans_donnees(self):
        pool = _mock_db(fetch_rows=[])
        service = DiscoveryService(
            db_pool=pool, categories={"solides_stables": _make_category()}
        )
        cats = await service.list_categories()
        assert cats[0].nb_suggestions == 0
        assert cats[0].as_of is None
