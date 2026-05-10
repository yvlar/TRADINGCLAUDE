"""Tests unitaires et d'intégration pour YahooFinanceExtractor et endpoints /extract, /analyze-auto."""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.skills.tier1.yahoo_finance import YahooFinanceExtractor
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


# ─── Tests unitaires — extract() ───────────────────────────────────────────────

class TestYahooFinanceExtract:
    @pytest.mark.asyncio
    async def test_graham_ratios_valide(self):
        """Données BNS complètes → GrahamRatios avec pe, pb, price, book_value, eps_ttm renseignés."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
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
        with patch.object(extractor, "_fetch_info", return_value=info):
            result = await extractor.extract("BNS")
        assert result.current_ratio is None

    @pytest.mark.asyncio
    async def test_ticker_inconnu_leve_404(self):
        """info = {} → HTTPException 404."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract("ZZZZZ")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ticker_inconnu_prix_absent_leve_404(self):
        """info sans currentPrice et sans regularMarketPrice → HTTPException 404."""
        extractor = YahooFinanceExtractor()
        info_sans_prix = {k: v for k, v in _INFO_BNS_FINANCIER.items()
                         if k not in ("currentPrice", "regularMarketPrice")}
        with patch.object(extractor, "_fetch_info", return_value=info_sans_prix):
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract("BNS")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_debt_equity_divise_par_100(self):
        """yfinance retourne 45.0 (%) → debt_equity = 0.45 dans GrahamRatios."""
        extractor = YahooFinanceExtractor()
        with patch.object(extractor, "_fetch_info", return_value=_INFO_BNS_FINANCIER):
            result = await extractor.extract("BNS")
        assert result.debt_equity == pytest.approx(0.45)

    @pytest.mark.asyncio
    async def test_pe_calcule_si_absent(self):
        """trailingPE absent mais price=80 et trailingEps=7.25 → pe ≈ 11.03."""
        extractor = YahooFinanceExtractor()
        info = {**_INFO_BNS_FINANCIER}
        del info["trailingPE"]
        with patch.object(extractor, "_fetch_info", return_value=info):
            result = await extractor.extract("BNS")
        assert result.pe == pytest.approx(80.0 / 7.25, rel=0.01)

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
        with patch.object(extractor, "_fetch_info", return_value=_INFO_MSFT):
            result = await extractor.extract("MSFT")
        assert result.current_ratio == pytest.approx(1.34)


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
        eps_growth_10y=0.0,
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
            eps_growth_10y=0.0, price=80.0, book_value=61.5,
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
            eps_growth_10y=0.0, price=80.0, book_value=61.5,
        )
