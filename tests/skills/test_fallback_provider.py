"""Tests unitaires pour FallbackDataProvider (repli transparent primaire → secondaire — E5-S2)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier1.fallback_provider import FallbackDataProvider
from app.skills.tier2.graham_analysis.schemas import GrahamRatios


def _ratios(source: str) -> GrahamRatios:
    return GrahamRatios(
        eps_growth_total=0.0,
        price=100.0,
        ratios_fetched_at=datetime.now(timezone.utc),
        ratios_source=source,
    )


def _provider() -> AsyncMock:
    """Faux fournisseur respectant l'interface (méthodes async mockées)."""
    return AsyncMock(spec=FinancialDataProvider)


def test_fallback_implements_provider_protocol() -> None:
    assert isinstance(FallbackDataProvider(_provider(), _provider()), FinancialDataProvider)


@pytest.mark.asyncio
async def test_extract_primaire_ok_secondaire_ignore() -> None:
    """Primaire répond → secondaire jamais appelé."""
    primary, secondary = _provider(), _provider()
    primary.extract.return_value = _ratios("primaire")
    fb = FallbackDataProvider(primary, secondary)

    result = await fb.extract("AAPL")

    assert result.ratios_source == "primaire"
    secondary.extract.assert_not_called()


@pytest.mark.asyncio
async def test_extract_repli_si_primaire_leve() -> None:
    """Primaire lève → bascule sur le secondaire."""
    primary, secondary = _provider(), _provider()
    primary.extract.side_effect = HTTPException(status_code=504, detail="Yahoo KO")
    secondary.extract.return_value = _ratios("secondaire")
    fb = FallbackDataProvider(primary, secondary)

    result = await fb.extract("AAPL")

    assert result.ratios_source == "secondaire"
    secondary.extract.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_deux_echecs_propage() -> None:
    """Les deux échouent → l'erreur du secondaire remonte."""
    primary, secondary = _provider(), _provider()
    primary.extract.side_effect = HTTPException(status_code=504, detail="primaire")
    secondary.extract.side_effect = HTTPException(status_code=404, detail="secondaire")
    fb = FallbackDataProvider(primary, secondary)

    with pytest.raises(HTTPException) as exc:
        await fb.extract("ZZZZ")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_price_repli_si_primaire_none() -> None:
    """get_price : primaire None → secondaire utilisé."""
    primary, secondary = _provider(), _provider()
    primary.get_price.return_value = None
    secondary.get_price.return_value = 42.0
    fb = FallbackDataProvider(primary, secondary)

    assert await fb.get_price("AAPL") == 42.0


@pytest.mark.asyncio
async def test_earnings_quality_repli_si_primaire_none() -> None:
    """earnings_quality : primaire None → secondaire interrogé."""
    primary, secondary = _provider(), _provider()
    primary.extract_earnings_quality.return_value = None
    secondary.extract_earnings_quality.return_value = None
    fb = FallbackDataProvider(primary, secondary)

    assert await fb.extract_earnings_quality("AAPL") is None
    secondary.extract_earnings_quality.assert_awaited_once()
