"""Tests Sprint 24 — Alertes prix watchlist."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.price_alert_service import PriceAlertService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.workers.tasks import _execute_price_alert_check, _execute_watchlist_analysis


def _make_db_row(
    ticker: str = "BNS",
    last_intrinsic_value: Decimal | None = Decimal("80.00"),
    threshold: Decimal = Decimal("0.10"),
) -> dict:
    """Simule une ligne asyncpg avec les colonnes d'alerte prix."""
    return {
        "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        "ticker": ticker,
        "last_intrinsic_value": last_intrinsic_value,
        "price_alert_threshold_pct": threshold,
    }


def _make_graham_ratios(price: float = 80.0) -> GrahamRatios:
    return GrahamRatios(
        pe=11.0,
        pb=1.3,
        current_ratio=None,
        debt_equity=0.45,
        eps_growth_total=0.27,
        price=price,
        book_value=61.5,
    )


@pytest.mark.asyncio
async def test_price_alert_ecart_superieur_seuil():
    """Écart 12% > 10% → ticker présent dans la liste des alertes."""
    # prix = 89.60, intrinsèque = 80.00 → écart = |89.60-80|/80 = 0.12 ≥ 0.10
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [_make_db_row("BNS", Decimal("80.00"), Decimal("0.10"))]
    mock_pool.execute = AsyncMock()

    mock_yahoo = AsyncMock()
    mock_yahoo.extract.return_value = _make_graham_ratios(price=89.60)

    service = PriceAlertService()
    alerted = await service.check_price_alerts(mock_pool, mock_yahoo)

    assert "BNS" in alerted
    mock_pool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_price_alert_ecart_inferieur_seuil():
    """Écart 5% < 10% → pas d'alerte."""
    # prix = 84.00, intrinsèque = 80.00 → écart = 4/80 = 0.05 < 0.10
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [_make_db_row("BNS", Decimal("80.00"), Decimal("0.10"))]
    mock_pool.execute = AsyncMock()

    mock_yahoo = AsyncMock()
    mock_yahoo.extract.return_value = _make_graham_ratios(price=84.00)

    service = PriceAlertService()
    alerted = await service.check_price_alerts(mock_pool, mock_yahoo)

    assert alerted == []
    mock_pool.execute.assert_called_once()  # last_price_checked mis à jour quand même


@pytest.mark.asyncio
async def test_price_alert_sans_intrinsic_value():
    """Entrées sans last_intrinsic_value ignorées — filtre SQL WHERE IS NOT NULL."""
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = []  # aucune entrée avec valeur intrinsèque

    mock_yahoo = AsyncMock()

    service = PriceAlertService()
    alerted = await service.check_price_alerts(mock_pool, mock_yahoo)

    assert alerted == []
    mock_yahoo.extract.assert_not_called()
    mock_pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_price_alert_yahoo_indisponible():
    """Exception Yahoo Finance → loggué, pas de crash, ticker exclu des alertes."""
    from fastapi import HTTPException

    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [_make_db_row("BNS", Decimal("80.00"), Decimal("0.10"))]
    mock_pool.execute = AsyncMock()

    mock_yahoo = AsyncMock()
    mock_yahoo.extract.side_effect = HTTPException(
        status_code=504, detail="Timeout Yahoo Finance"
    )

    service = PriceAlertService()
    alerted = await service.check_price_alerts(mock_pool, mock_yahoo)

    assert alerted == []
    mock_pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_price_alert_celery_task_mock():
    """_execute_price_alert_check instancie PriceAlertService et appelle check_price_alerts."""
    with patch("app.workers.tasks.PriceAlertService") as MockService:
        mock_instance = AsyncMock()
        mock_instance.check_price_alerts.return_value = []
        MockService.return_value = mock_instance

        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_create_pool.return_value = mock_pool

            with patch("app.workers.tasks.YahooFinanceExtractor"):
                await _execute_price_alert_check()

    mock_instance.check_price_alerts.assert_called_once()


@pytest.mark.asyncio
async def test_price_alert_warning_loggue(caplog):
    """Écart > seuil → un WARNING est émis dans les logs avec 'ALERTE PRIX' et le ticker."""
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [_make_db_row("BNS", Decimal("80.00"), Decimal("0.10"))]
    mock_pool.execute = AsyncMock()

    mock_yahoo = AsyncMock()
    mock_yahoo.extract.return_value = _make_graham_ratios(price=89.60)  # écart 12%

    service = PriceAlertService()
    with caplog.at_level(logging.WARNING, logger="app.services.price_alert_service"):
        await service.check_price_alerts(mock_pool, mock_yahoo)

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("ALERTE PRIX" in msg and "BNS" in msg for msg in warnings)


@pytest.mark.asyncio
async def test_watchlist_update_intrinsic_after_analysis():
    """_execute_watchlist_analysis persiste last_intrinsic_value = graham.valeur_intrinseque_ajustee."""
    entry_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    mock_orchestrator = AsyncMock()
    mock_response = MagicMock()
    mock_graham = MagicMock()
    mock_graham.defensive_score = 6
    mock_graham.verdict = "ACCEPTABLE"
    mock_graham.valeur_intrinseque_ajustee = 85.50
    mock_response.graham = mock_graham
    mock_orchestrator.run_company_analysis.return_value = mock_response

    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [
        {
            "id": entry_id,
            "ticker": "BNS",
            "workflow": "value_graham",
            "ratios": None,
            "score_alerte_min": None,
        }
    ]
    mock_pool.execute = AsyncMock()
    mock_pool.close = AsyncMock()

    with patch("app.workers.tasks._build_orchestrator", return_value=(mock_orchestrator, mock_pool)):
        await _execute_watchlist_analysis()

    assert mock_pool.execute.call_count == 1
    call_positional = mock_pool.execute.call_args.args
    assert 85.50 in call_positional
