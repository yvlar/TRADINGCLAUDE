"""Tests unitaires et d'intégration pour YahooFinanceExtractor et endpoints /extract, /analyze-auto."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.skills.tier1.yahoo_finance import (
    RATIOS_SOURCE,
    YahooFinanceExtractor,
    _compute_dividend_years,
    _compute_eps_growth,
    _compute_no_deficit_years,
    _finite_float,
    _resolve_ratio,
)
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

# ─── DataFrames mock pour extract_earnings_quality ─────────────────────────────

def _make_income_df() -> pd.DataFrame:
    """Compte de résultat fictif — 2 exercices, lignes = métriques, colonnes = années."""
    return pd.DataFrame({
        "2024": {
            "Total Revenue": 38_000_000_000.0,
            "Cost Of Revenue": 15_000_000_000.0,
            "Net Income": 10_000_000_000.0,
            "EBIT": 12_000_000_000.0,
        },
        "2023": {
            "Total Revenue": 36_000_000_000.0,
            "Cost Of Revenue": 14_500_000_000.0,
            "Net Income": 9_500_000_000.0,
            "EBIT": 11_500_000_000.0,
        },
    })


def _make_balance_df() -> pd.DataFrame:
    return pd.DataFrame({
        "2024": {
            "Total Assets": 1_000_000_000_000.0,
            "Accounts Receivable": 50_000_000_000.0,
            "Current Assets": 100_000_000_000.0,
            "Current Liabilities": 80_000_000_000.0,
            "Inventory": 5_000_000_000.0,
            "Long Term Debt": 200_000_000_000.0,
        },
        "2023": {
            "Total Assets": 950_000_000_000.0,
            "Accounts Receivable": 48_000_000_000.0,
            "Current Assets": 95_000_000_000.0,
            "Current Liabilities": 76_000_000_000.0,
            "Inventory": 4_800_000_000.0,
            "Long Term Debt": 195_000_000_000.0,
        },
    })


def _make_cashflow_df() -> pd.DataFrame:
    return pd.DataFrame({
        "2024": {
            "Operating Cash Flow": 12_000_000_000.0,
            "Depreciation And Amortization": 2_000_000_000.0,
        },
        "2023": {
            "Operating Cash Flow": 11_500_000_000.0,
            "Depreciation And Amortization": 1_900_000_000.0,
        },
    })


_MOCK_EARNINGS_DATA = {
    "income": _make_income_df(),
    "balance": _make_balance_df(),
    "cashflow": _make_cashflow_df(),
    "info": {"marketCap": 100_000_000_000},
}


# ─── Données mock ──────────────────────────────────────────────────────────────

_INFO_BNS_FINANCIER = {
    "currentPrice": 80.0,
    "regularMarketPrice": 80.0,
    "trailingPE": 11.0,
    "priceToBook": 1.3,
    "currentRatio": 1.5,
    "debtToEquity": 45.0,
    "bookValue": 61.5,
    "trailingEps": 7.25,
    "totalRevenue": 38_000_000_000,
    "sector": "Financial Services",
    "freeCashflow": 5_000_000_000,
    "returnOnEquity": 0.14,
    "profitMargins": 0.31,
    "dividendYield": 0.065,
    "sharesOutstanding": 1_200_000_000,
    "earningsGrowth": 0.04,
    "enterpriseToEbitda": 7.2,
}

_INFO_MSFT = {
    "currentPrice": 420.0,
    "regularMarketPrice": 420.0,
    "trailingPE": 34.2,
    "priceToBook": 12.1,
    "currentRatio": 1.34,
    "debtToEquity": 28.0,
    "bookValue": 35.0,
    "trailingEps": 12.28,
    "totalRevenue": 211_000_000_000,
    "sector": "Technology",
}


def _raw(info: dict) -> dict:
    """Construit le dict retourné par _fetch_info_and_history sans income ni dividends."""
    return {"info": info, "income": None, "dividends": None}


# ─── Tests unitaires — extract() ───────────────────────────────────────────────

class TestYahooFinanceExtract:
    @pytest.mark.asyncio
    async def test_graham_ratios_valide(self):
        """Données BNS complètes → GrahamRatios avec pe, pb, price, book_value, eps_ttm renseignés."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(_INFO_BNS_FINANCIER)):
            result = await extractor.extract("BNS")

        assert isinstance(result, GrahamRatios)
        assert result.pe == pytest.approx(11.0)
        assert result.pb == pytest.approx(1.3)
        assert result.price == pytest.approx(80.0)
        assert result.book_value == pytest.approx(61.5)
        assert result.eps_ttm == pytest.approx(7.25)

    @pytest.mark.asyncio
    async def test_current_ratio_none_pour_banque(self):
        """sector == Financial Services → current_ratio = None même si yfinance retourne une valeur."""
        extractor = YahooFinanceExtractor()
        info = {**_INFO_BNS_FINANCIER, "sector": "Financial Services", "currentRatio": 1.5}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.current_ratio is None

    @pytest.mark.asyncio
    async def test_ticker_inconnu_leve_404(self):
        """info = {} → HTTPException 404."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw({})):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract("ZZZZZ")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ticker_inconnu_prix_absent_leve_404(self):
        """info sans currentPrice et sans regularMarketPrice → HTTPException 404."""
        extractor = YahooFinanceExtractor()
        info_sans_prix = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                         if k not in ("currentPrice", "regularMarketPrice")}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info_sans_prix)):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract("BNS")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_debt_equity_divise_par_100(self):
        """yfinance retourne 45.0 (%) → debt_equity = 0.45 dans GrahamRatios."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(_INFO_BNS_FINANCIER)):
            result = await extractor.extract("BNS")
        assert result.debt_equity == pytest.approx(0.45)

    @pytest.mark.asyncio
    async def test_ratios_absents_donnent_none_pas_zero(self):
        """priceToBook / bookValue / debtToEquity absents → None (pas 0.0 trompeur)."""
        extractor = YahooFinanceExtractor()
        info = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                if k not in ("priceToBook", "bookValue", "debtToEquity")}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.pb is None
        assert result.book_value is None
        assert result.debt_equity is None

    @pytest.mark.asyncio
    async def test_pe_none_si_pe_et_eps_absents(self):
        """trailingPE et trailingEps absents → pe = None (pas 0.0)."""
        extractor = YahooFinanceExtractor()
        info = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                if k not in ("trailingPE", "trailingEps")}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.pe is None

    @pytest.mark.asyncio
    async def test_pb_zero_reel_conserve(self):
        """Un 0.0 réel de la source est conservé — seul l'absent devient None."""
        extractor = YahooFinanceExtractor()
        info = {**_INFO_BNS_FINANCIER, "priceToBook": 0.0}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.pb == 0.0

    @pytest.mark.asyncio
    async def test_pe_calcule_si_absent(self):
        """trailingPE absent mais price=80 et trailingEps=7.25 → pe ≈ 11.03."""
        extractor = YahooFinanceExtractor()
        info = {**_INFO_BNS_FINANCIER}
        del info["trailingPE"]
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.pe == pytest.approx(80.0 / 7.25, rel=0.01)

    @pytest.mark.asyncio
    async def test_extract_pose_source_et_date_recuperation(self):
        """extract() horodate les ratios (UTC, au moment de l'extraction) et pose la source littérale."""
        extractor = YahooFinanceExtractor()
        avant = datetime.now(timezone.utc)
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(_INFO_BNS_FINANCIER)):
            result = await extractor.extract("BNS")
        assert result.ratios_source == RATIOS_SOURCE
        assert result.ratios_fetched_at is not None
        assert result.ratios_fetched_at.tzinfo is not None
        assert result.ratios_fetched_at >= avant

    @pytest.mark.asyncio
    async def test_extract_provenance_cles_primaires(self):
        """Clés primaires présentes → provenance pointe la clé primaire pour pb/debt_equity/book_value."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(_INFO_BNS_FINANCIER)):
            result = await extractor.extract("BNS")
        assert result.ratios_provenance == {
            "pb": "priceToBook",
            "debt_equity": "debtToEquity",
            "book_value": "bookValue",
        }

    @pytest.mark.asyncio
    async def test_extract_provenance_repli_sur_cle_secondaire(self):
        """Clé primaire absente mais clé de repli présente → provenance expose la clé de repli effective."""
        extractor = YahooFinanceExtractor()
        info = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                if k not in ("priceToBook", "bookValue", "debtToEquity")}
        info = {
            **info,
            "priceToBookRatio": 1.4,
            "bookValuePerShare": 60.0,
            "debtToEquityRatio": 50.0,
        }
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.pb == pytest.approx(1.4)
        assert result.book_value == pytest.approx(60.0)
        assert result.debt_equity == pytest.approx(0.5)  # 50.0 % / 100
        assert result.ratios_provenance == {
            "pb": "priceToBookRatio",
            "debt_equity": "debtToEquityRatio",
            "book_value": "bookValuePerShare",
        }

    @pytest.mark.asyncio
    async def test_extract_provenance_none_si_aucun_ratio_replie(self):
        """Aucun ratio à repli résolu (ni primaire ni repli) → ratios_provenance = None (pas dict vide)."""
        extractor = YahooFinanceExtractor()
        info = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                if k not in ("priceToBook", "bookValue", "debtToEquity")}
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(info)):
            result = await extractor.extract("BNS")
        assert result.ratios_provenance is None

    @pytest.mark.asyncio
    async def test_timeout_gere(self):
        """asyncio.wait_for lève TimeoutError → HTTPException 504."""
        extractor = YahooFinanceExtractor(timeout_s=0.001)
        with patch(
            "app.skills.tier1.yahoo_finance.asyncio.wait_for",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract("SLOW")
        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_secteur_non_financier_current_ratio_present(self):
        """sector == Technology → current_ratio conservé."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info_and_history", return_value=_raw(_INFO_MSFT)):
            result = await extractor.extract("MSFT")
        assert result.current_ratio == pytest.approx(1.34)

    @pytest.mark.asyncio
    async def test_eps_growth_calcule_depuis_income(self):
        """income_stmt avec 2 ans → eps_growth_total calculé (non nul) + horizon réel exposé."""
        extractor = YahooFinanceExtractor()
        income = pd.DataFrame({
            "2024": {"Net Income": 12_000_000_000.0},
            "2022": {"Net Income": 8_000_000_000.0},
        })
        info = {**_INFO_BNS_FINANCIER, "sharesOutstanding": 1_000_000_000}
        raw = {"info": info, "income": income, "dividends": None}
        with patch.object(extractor, "_fetch_info_and_history", return_value=raw):
            result = await extractor.extract("BNS")
        # 12B/1B = 12 eps récent, 8B/1B = 8 eps ancien → growth = (12/8)-1 = 0.5 sur 1 intervalle
        assert result.eps_growth_total == pytest.approx(0.5)
        assert result.eps_growth_years == 1

    @pytest.mark.asyncio
    async def test_eps_growth_repli_sur_info_quand_income_absent(self):
        """income_stmt absent + info.earningsGrowth présent → repli tracé (horizon 1 an)."""
        extractor = YahooFinanceExtractor()
        info = {
            **_INFO_BNS_FINANCIER,
            "sharesOutstanding": 1_000_000_000,
            "earningsGrowth": 0.12,
        }
        raw = {"info": info, "income": None, "dividends": None}
        with patch.object(extractor, "_fetch_info_and_history", return_value=raw):
            result = await extractor.extract("BNS")
        assert result.eps_growth_total == pytest.approx(0.12)
        assert result.eps_growth_years == 1

    @pytest.mark.asyncio
    async def test_eps_growth_sans_income_ni_repli(self):
        """income absent ET info.earningsGrowth absent → 0.0 et horizon None (pas d'exception)."""
        extractor = YahooFinanceExtractor()
        info = {k: v for k, v in _INFO_BNS_FINANCIER.items() if k != "earningsGrowth"}
        info = {**info, "sharesOutstanding": 1_000_000_000}
        raw = {"info": info, "income": None, "dividends": None}
        with patch.object(extractor, "_fetch_info_and_history", return_value=raw):
            result = await extractor.extract("BNS")
        assert result.eps_growth_total == 0.0
        assert result.eps_growth_years is None

    @pytest.mark.asyncio
    async def test_dividend_years_compte_consecutif(self):
        """dividends avec 3 années consécutives → dividend_years = 3."""
        extractor = YahooFinanceExtractor()
        current_year = datetime.now().year
        idx = pd.DatetimeIndex([
            f"{current_year}-03-15", f"{current_year}-06-15",
            f"{current_year - 1}-03-15", f"{current_year - 2}-03-15",
        ])
        divs = pd.Series([1.0, 1.0, 1.0, 1.0], index=idx)
        raw = {"info": _INFO_BNS_FINANCIER, "income": None, "dividends": divs}
        with patch.object(extractor, "_fetch_info_and_history", return_value=raw):
            result = await extractor.extract("BNS")
        assert result.dividend_years == 3


# ─── Tests unitaires — extract_earnings_quality() ──────────────────────────────

class TestYahooFinanceExtractEarningsQuality:
    @pytest.mark.asyncio
    async def test_earnings_quality_valide(self):
        """DataFrames complets → EarningsQualityRatios valide avec tous les champs requis."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_earnings_data", return_value=_MOCK_EARNINGS_DATA):
            result = await extractor.extract_earnings_quality("BNS")

        assert isinstance(result, EarningsQualityRatios)
        assert result.sales_t == pytest.approx(38e9)
        assert result.sales_t1 == pytest.approx(36e9)
        assert result.cfo_t == pytest.approx(12e9)
        assert result.receivables_t == pytest.approx(50e9)
        assert result.total_assets_t == pytest.approx(1_000e9)
        assert result.current_assets_t == pytest.approx(100e9)
        assert result.current_liabilities_t == pytest.approx(80e9)

    @pytest.mark.asyncio
    async def test_earnings_quality_champ_obligatoire_manquant_retourne_none(self):
        """Si un champ requis est absent (ex: Net Income absent), retourne None."""
        extractor = YahooFinanceExtractor()
        income_incomplet = _make_income_df().drop(index="Net Income")
        data = {**_MOCK_EARNINGS_DATA, "income": income_incomplet}
        with patch.object(extractor, "_fetch_earnings_data", return_value=data):
            result = await extractor.extract_earnings_quality("BNS")
        assert result is None

    @pytest.mark.asyncio
    async def test_earnings_quality_une_seule_periode_retourne_none(self):
        """Si seulement 1 exercice disponible (pas de T-1), retourne None."""
        extractor = YahooFinanceExtractor()
        income_1col = _make_income_df()[["2024"]]
        data = {**_MOCK_EARNINGS_DATA, "income": income_1col}
        with patch.object(extractor, "_fetch_earnings_data", return_value=data):
            result = await extractor.extract_earnings_quality("BNS")
        assert result is None

    @pytest.mark.asyncio
    async def test_earnings_quality_timeout_retourne_none(self):
        """Timeout yfinance → retourne None sans lever d'exception."""
        extractor = YahooFinanceExtractor(timeout_s=0.001)
        with patch(
            "app.skills.tier1.yahoo_finance.asyncio.wait_for",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            result = await extractor.extract_earnings_quality("SLOW")
        assert result is None

    @pytest.mark.asyncio
    async def test_earnings_quality_current_liabilities_manquant_retourne_none(self):
        """current_liabilities requis — si absent retourne None."""
        extractor = YahooFinanceExtractor()
        balance_sans_cl = _make_balance_df().drop(index="Current Liabilities")
        data = {**_MOCK_EARNINGS_DATA, "balance": balance_sans_cl}
        with patch.object(extractor, "_fetch_earnings_data", return_value=data):
            result = await extractor.extract_earnings_quality("BNS")
        assert result is None

    @pytest.mark.asyncio
    async def test_earnings_quality_pose_source_et_date(self):
        """extract_earnings_quality horodate les ratios (UTC) et pose la source (Sprint 138)."""
        extractor = YahooFinanceExtractor()
        avant = datetime.now(timezone.utc)
        with patch.object(extractor, "_fetch_earnings_data", return_value=_MOCK_EARNINGS_DATA):
            result = await extractor.extract_earnings_quality("BNS")
        assert result is not None
        assert result.ratios_source == RATIOS_SOURCE
        assert result.ratios_fetched_at is not None
        assert result.ratios_fetched_at.tzinfo is not None
        assert result.ratios_fetched_at >= avant


# ─── Tests unitaires — extract_valuation() ─────────────────────────────────────

class TestYahooFinanceExtractValuation:
    @pytest.mark.asyncio
    async def test_retourne_valuation_ratios(self):
        """Données BNS → ValuationRatios avec price, pe, pb, eps_ttm renseignés."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
            result = await extractor.extract_valuation("BNS")

        assert isinstance(result, ValuationRatios)
        assert result.price == pytest.approx(80.0)
        assert result.pe == pytest.approx(11.0)
        assert result.pb == pytest.approx(1.3)
        assert result.eps_ttm == pytest.approx(7.25)

    @pytest.mark.asyncio
    async def test_ticker_inconnu_leve_404(self):
        """info = {} → HTTPException 404."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract_valuation("ZZZZZ")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_debt_equity_divise_par_100_valuation(self):
        """debtToEquity = 45.0 → debt_equity = 0.45 dans ValuationRatios."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
            result = await extractor.extract_valuation("BNS")
        assert result.debt_equity == pytest.approx(0.45)

    @pytest.mark.asyncio
    async def test_revenue_converti_en_milliards(self):
        """totalRevenue = 38e9 → revenue_bn = 38.0."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
            result = await extractor.extract_valuation("BNS")
        assert result.revenue_bn == pytest.approx(38.0)

    @pytest.mark.asyncio
    async def test_valuation_pose_source_et_date(self):
        """extract_valuation horodate les ratios (UTC) et pose la source (Sprint 138)."""
        extractor = YahooFinanceExtractor()
        avant = datetime.now(timezone.utc)
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
            result = await extractor.extract_valuation("BNS")
        assert result.ratios_source == RATIOS_SOURCE
        assert result.ratios_fetched_at is not None
        assert result.ratios_fetched_at.tzinfo is not None
        assert result.ratios_fetched_at >= avant


# ─── Tests d'intégration — endpoints /extract et /analyze-auto ─────────────────

def _make_mock_qdrant_response(status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    return mock_resp


@pytest.fixture
async def async_client_extract(analyze_response_msft):
    """Client ASGI pour tester /extract et /analyze-auto avec mocks injectés dans app.state."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis.return_value = analyze_response_msft

    mock_yahoo = AsyncMock(spec=YahooFinanceExtractor)
    mock_ratios = GrahamRatios(
        pe=11.0,
        pb=1.3,
        current_ratio=None,
        debt_equity=0.45,
        eps_growth_total=0.0,
        price=80.0,
        book_value=61.5,
    )
    mock_yahoo.extract.return_value = mock_ratios
    mock_yahoo.extract_earnings_quality.return_value = None

    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.get.return_value = _make_mock_qdrant_response(200)
    mock_qdrant_ctx = AsyncMock()
    mock_qdrant_ctx.__aenter__.return_value = mock_qdrant_client
    mock_qdrant_ctx.__aexit__.return_value = None

    mock_rag_client = AsyncMock()
    mock_rag_client.ensure_collection = AsyncMock()
    mock_rag_client.close = AsyncMock()

    with (
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
        patch("anthropic.AsyncAnthropic", return_value=MagicMock()),
        patch(
            "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
            return_value="prompt test",
        ),
        patch(
            "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
            return_value="prompt test",
        ),
        patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx),
        patch("app.api.main.RagClient", return_value=mock_rag_client),
    ):
        mock_pool.return_value = AsyncMock()
        mock_pool.return_value.close = AsyncMock()
        mock_pool.return_value.fetchval = AsyncMock(return_value=1)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            app.state.orchestrator = mock_orchestrator
            app.state.yahoo_extractor = mock_yahoo
            app.state.db_pool = mock_pool.return_value
            app.state.qdrant_url = "http://qdrant:6333"
            yield client


class TestExtractEndpoint:
    @pytest.mark.asyncio
    async def test_extract_endpoint_retourne_extract_response(self, async_client_extract):
        """GET /extract?ticker=BNS avec mock Yahoo → 200 + ExtractResponse {graham, earnings_quality}."""
        r = await async_client_extract.get("/extract?ticker=BNS")
        assert r.status_code == 200
        data = r.json()
        assert "graham" in data
        assert "earnings_quality" in data
        assert data["graham"]["pe"] == pytest.approx(11.0)
        assert data["graham"]["pb"] == pytest.approx(1.3)
        assert data["graham"]["price"] == pytest.approx(80.0)

    @pytest.mark.asyncio
    async def test_extract_endpoint_earnings_quality_null_par_defaut(self, async_client_extract):
        """earnings_quality = None quand extract_earnings_quality retourne None."""
        r = await async_client_extract.get("/extract?ticker=BNS")
        data = r.json()
        assert data["earnings_quality"] is None

    @pytest.mark.asyncio
    async def test_extract_endpoint_ticker_inconnu_retourne_404(self, async_client_extract):
        """GET /extract?ticker=ZZZZZ avec mock HTTPException 404 → 404."""
        app.state.yahoo_extractor.extract.side_effect = HTTPException(
            status_code=404, detail="Ticker inconnu"
        )
        r = await async_client_extract.get("/extract?ticker=ZZZZZ")
        assert r.status_code == 404
        # Remettre le mock en état normal
        app.state.yahoo_extractor.extract.side_effect = None
        app.state.yahoo_extractor.extract.return_value = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.0, price=80.0, book_value=61.5,
        )

    @pytest.mark.asyncio
    async def test_analyze_auto_workflow_complet(self, async_client_extract):
        """POST /analyze-auto?ticker=BNS → AnalyzeResponse avec skills_applied et cost_usd."""
        r = await async_client_extract.post("/analyze-auto?ticker=BNS")
        assert r.status_code == 200
        data = r.json()
        assert "graham" in data
        assert "skills_applied" in data
        assert data["cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_analyze_auto_ticker_inconnu_retourne_404(self, async_client_extract):
        """POST /analyze-auto?ticker=ZZZZZ → 404 propagé depuis l'extracteur."""
        app.state.yahoo_extractor.extract.side_effect = HTTPException(
            status_code=404, detail="Ticker inconnu"
        )
        r = await async_client_extract.post("/analyze-auto?ticker=ZZZZZ")
        assert r.status_code == 404
        # Remettre le mock en état normal
        app.state.yahoo_extractor.extract.side_effect = None
        app.state.yahoo_extractor.extract.return_value = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.0, price=80.0, book_value=61.5,
        )


# ─── Tests unitaires — helpers module-level ────────────────────────────────────

def _make_income_2cols(ni_recent: float, ni_oldest: float) -> pd.DataFrame:
    """DataFrame income_stmt minimal avec Net Income sur 2 années."""
    return pd.DataFrame({
        "2024": {"Net Income": ni_recent},
        "2022": {"Net Income": ni_oldest},
    })


class TestComputeEpsGrowth:
    def test_croissance_positive_avec_horizon(self):
        """net income 8B → 12B, 1B actions → growth = 0.50 sur 1 an (2 points = 1 intervalle)."""
        income = _make_income_2cols(12_000_000_000.0, 8_000_000_000.0)
        growth, years = _compute_eps_growth(income, 1_000_000_000)
        assert growth == pytest.approx(0.5)
        assert years == 1

    def test_quatre_points_horizon_trois_ans(self):
        """4 exercices annuels → horizon = 3 ans (N points couvrent N-1 années de croissance)."""
        income = pd.DataFrame({
            "2024": {"Net Income": 16_000_000_000.0},
            "2023": {"Net Income": 14_000_000_000.0},
            "2022": {"Net Income": 12_000_000_000.0},
            "2021": {"Net Income": 8_000_000_000.0},
        })
        growth, years = _compute_eps_growth(income, 1_000_000_000)
        assert growth == pytest.approx(1.0)  # (16/8) - 1
        assert years == 3

    def test_base_negative_retourne_zero_horizon_none(self):
        """BPA ancien négatif (déficit) → impossible de calculer, retourne (0.0, None)."""
        income = _make_income_2cols(10_000_000_000.0, -2_000_000_000.0)
        assert _compute_eps_growth(income, 1_000_000_000) == (0.0, None)

    def test_une_seule_periode_retourne_zero_horizon_none(self):
        """Une seule colonne → insuffisant pour calculer la croissance → (0.0, None)."""
        income = pd.DataFrame({"2024": {"Net Income": 10_000_000_000.0}})
        assert _compute_eps_growth(income, 1_000_000_000) == (0.0, None)

    def test_income_none_retourne_zero_horizon_none(self):
        """income = None → retourne (0.0, None) sans exception."""
        assert _compute_eps_growth(None, 1_000_000_000) == (0.0, None)


class TestComputeDividendYears:
    def test_trois_ans_consecutifs(self):
        """3 années consécutives → dividend_years = 3."""
        current_year = datetime.now().year
        idx = pd.DatetimeIndex([
            f"{current_year}-06-01",
            f"{current_year - 1}-06-01",
            f"{current_year - 2}-06-01",
        ])
        divs = pd.Series([1.0, 1.0, 1.0], index=idx)
        assert _compute_dividend_years(divs) == 3

    def test_gap_stoppe_le_compte(self):
        """Année manquante → compte s'arrête avant le gap."""
        current_year = datetime.now().year
        idx = pd.DatetimeIndex([
            f"{current_year}-06-01",
            # année current_year-1 manquante volontairement
            f"{current_year - 2}-06-01",
        ])
        divs = pd.Series([1.0, 1.0], index=idx)
        assert _compute_dividend_years(divs) == 1

    def test_serie_vide_retourne_zero(self):
        """Serie vide → 0 dividendes."""
        divs = pd.Series([], dtype=float)
        assert _compute_dividend_years(divs) == 0

    def test_none_retourne_none(self):
        """None → données indisponibles → retourne None."""
        assert _compute_dividend_years(None) is None


class TestComputeNoDeficitYears:
    def test_trois_sur_quatre_positifs(self):
        """3 années positives sur 4 disponibles → retourne 3."""
        income = pd.DataFrame({
            "2024": {"Net Income": 10e9},
            "2023": {"Net Income": -2e9},
            "2022": {"Net Income": 8e9},
            "2021": {"Net Income": 7e9},
        })
        assert _compute_no_deficit_years(income, 1_000_000_000) == 3

    def test_income_none_retourne_none(self):
        """income = None → retourne None."""
        assert _compute_no_deficit_years(None, 1_000_000_000) is None


class TestResolveRatio:
    def test_cle_primaire_presente(self):
        """Clé primaire présente → (valeur, clé_primaire), aucun repli."""
        info = {"priceToBook": 1.3}
        assert _resolve_ratio(info, "BNS", "priceToBook") == (1.3, "priceToBook")

    def test_repli_sur_cle_secondaire(self):
        """Primaire absente + clé de repli présente → (valeur_repli, clé_repli)."""
        info = {"bookValuePerShare": 42.0}
        assert _resolve_ratio(info, "BNS", "bookValue", "bookValuePerShare") == (
            42.0, "bookValuePerShare",
        )

    def test_aucune_source_retourne_none(self):
        """Primaire et replis absents → (None, None), jamais 0.0."""
        assert _resolve_ratio({}, "BNS", "priceToBook", "bookValuePerShare") == (None, None)

    def test_zero_reel_conserve(self):
        """Un 0.0 réel (présent dans la source) est retourné tel quel, pas traité comme absent."""
        assert _resolve_ratio({"priceToBook": 0.0}, "BNS", "priceToBook") == (0.0, "priceToBook")

    def test_valeur_non_finie_ignoree(self):
        """NaN/inf/non numérique sur la primaire → repli puis None — jamais propagé."""
        assert _resolve_ratio({"priceToBook": float("nan")}, "BNS", "priceToBook") == (None, None)
        assert _resolve_ratio({"priceToBook": "n/a"}, "BNS", "priceToBook") == (None, None)


class TestFiniteFloat:
    def test_nombre_fini(self):
        assert _finite_float(1.5) == 1.5

    def test_none_nan_inf_chaine(self):
        assert _finite_float(None) is None
        assert _finite_float(float("nan")) is None
        assert _finite_float(float("inf")) is None
        assert _finite_float("abc") is None

    def test_zero_conserve(self):
        """0.0 est un nombre fini valide — conservé, jamais converti en None."""
        assert _finite_float(0.0) == 0.0


class TestGrahamRatiosProvenance:
    def test_provenance_defaut_none(self):
        """ratios_provenance par défaut None — rétrocompat avec les analyses persistées avant le champ."""
        r = GrahamRatios(eps_growth_total=0.0, price=80.0)
        assert r.ratios_provenance is None

    def test_provenance_accepte_dict(self):
        """ratios_provenance accepte un dict[str, str] (clé yfinance par ratio)."""
        r = GrahamRatios(
            eps_growth_total=0.0, price=80.0,
            ratios_provenance={"pb": "priceToBook", "book_value": "bookValuePerShare"},
        )
        assert r.ratios_provenance == {"pb": "priceToBook", "book_value": "bookValuePerShare"}

    def test_provenance_exclue_de_la_cle_de_cache(self):
        """La provenance n'altère pas l'identité de cache (comme source/date — Sprint 134)."""
        from app.services.analysis_cache import AnalysisCacheService

        svc = AnalysisCacheService(None)  # _cache_key est pur — n'utilise pas le client redis
        base = dict(eps_growth_total=0.0, price=80.0, pe=11.0, pb=1.3, book_value=61.5)
        sans = GrahamRatios(**base)
        avec = GrahamRatios(**base, ratios_provenance={"pb": "priceToBook"})
        assert svc._cache_key("BNS", "value_graham", sans) == svc._cache_key(
            "BNS", "value_graham", avec
        )
