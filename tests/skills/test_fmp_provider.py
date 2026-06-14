"""Tests unitaires pour FmpProvider (fournisseur REST de repli — E5-S2)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier1.fmp_provider import RATIOS_SOURCE, FmpProvider


def _fake_async_client_cls(routes: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Mock de httpx.AsyncClient routant chaque GET vers un payload par sous-chaîne d'URL."""

    def _get(url: str, params: dict[str, Any] | None = None) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        payload = next((v for k, v in routes.items() if k in url), [])
        resp.json = MagicMock(return_value=payload)
        return resp

    client = AsyncMock()
    client.get = AsyncMock(side_effect=_get)
    cls = MagicMock()
    cls.return_value.__aenter__ = AsyncMock(return_value=client)
    cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return cls


_QUOTE = {"price": 150.0, "eps": 6.0, "pe": 25.0, "sharesOutstanding": 1_000_000_000}
_PROFILE = {"sector": "Technology"}
_RATIOS = {
    "peRatioTTM": 24.5,
    "priceToBookRatioTTM": 12.0,
    "returnOnEquityTTM": 0.45,
    "netProfitMarginTTM": 0.36,
    "currentRatioTTM": 1.8,
    "debtEquityRatioTTM": 0.4,
    "dividendYieldTTM": 0.008,
    "enterpriseValueMultipleTTM": 18.0,
}
_METRICS = {
    "bookValuePerShareTTM": 12.5,
    "revenuePerShareTTM": 24.0,
    "freeCashFlowPerShareTTM": 5.0,
    "roicTTM": 0.30,
    "netIncomePerShareTTM": 6.0,
}

_ROUTES = {"quote/": [_QUOTE], "profile/": [_PROFILE], "ratios-ttm/": [_RATIOS], "key-metrics-ttm/": [_METRICS]}


def test_fmp_implements_provider_protocol() -> None:
    """FmpProvider satisfait l'interface FinancialDataProvider."""
    assert isinstance(FmpProvider(api_key="k"), FinancialDataProvider)


@pytest.mark.asyncio
async def test_extract_ok() -> None:
    """extract peuple GrahamRatios depuis quote + ratios + key-metrics."""
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls(_ROUTES)):
        ratios = await provider.extract("AAPL")
    assert ratios.price == 150.0
    assert ratios.pe == 25.0
    assert ratios.pb == 12.0
    assert ratios.current_ratio == 1.8
    assert ratios.debt_equity == 0.4
    assert ratios.eps_ttm == 6.0
    assert ratios.book_value == 12.5
    assert ratios.revenue_bn == pytest.approx(24.0)  # 24.0 × 1e9 actions / 1e9
    assert ratios.eps_growth_total == 0.0  # historique non reconstruit
    assert ratios.eps_growth_years is None
    assert ratios.ratios_source == RATIOS_SOURCE
    assert ratios.ratios_fetched_at is not None


@pytest.mark.asyncio
async def test_extract_secteur_financier_current_ratio_none() -> None:
    """current_ratio = None pour un titre du secteur financier."""
    routes = {**_ROUTES, "profile/": [{"sector": "Financial Services"}]}
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls(routes)):
        ratios = await provider.extract("BNS.TO")
    assert ratios.current_ratio is None


@pytest.mark.asyncio
async def test_extract_404_si_quote_vide() -> None:
    """Quote vide → HTTPException 404."""
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls({"quote/": []})):
        with pytest.raises(HTTPException) as exc:
            await provider.extract("ZZZZ")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_extract_valuation_ok() -> None:
    """extract_valuation peuple ValuationRatios (roic, roe, ev_ebitda, fcf)."""
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls(_ROUTES)):
        val = await provider.extract_valuation("AAPL")
    assert val.price == 150.0
    assert val.roic == 0.30
    assert val.roe == 0.45
    assert val.net_margin == 0.36
    assert val.ev_ebitda == 18.0
    assert val.free_cash_flow_bn == pytest.approx(5.0)
    assert val.shares_outstanding_m == pytest.approx(1000.0)
    assert val.sector == "Technology"
    assert val.ratios_source == RATIOS_SOURCE


@pytest.mark.asyncio
async def test_get_price_ok() -> None:
    """get_price retourne le cours du quote."""
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls(_ROUTES)):
        price = await provider.get_price("AAPL")
    assert price == 150.0


@pytest.mark.asyncio
async def test_get_price_none_sur_erreur() -> None:
    """get_price retourne None sur HTTP non-200 — ne lève jamais."""
    provider = FmpProvider(api_key="k")
    with patch("app.skills.tier1.fmp_provider.httpx.AsyncClient", _fake_async_client_cls(_ROUTES, status_code=500)):
        price = await provider.get_price("AAPL")
    assert price is None


@pytest.mark.asyncio
async def test_extract_earnings_quality_none() -> None:
    """extract_earnings_quality non couvert → None (repli garde la primaire)."""
    provider = FmpProvider(api_key="k")
    assert await provider.extract_earnings_quality("AAPL") is None


@pytest.mark.asyncio
async def test_cle_absente_leve_503() -> None:
    """Sans FMP_API_KEY, extract lève 503 (fournisseur indisponible)."""
    provider = FmpProvider(api_key="")
    with pytest.raises(HTTPException) as exc:
        await provider.extract("AAPL")
    assert exc.value.status_code == 503
