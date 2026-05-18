"""Tests unitaires pour BacktestService et le endpoint /backtest/composite (Sprint 50)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.backtest import BacktestRequest, BacktestResult, BucketResult
from app.services.backtest import BacktestService, _classify_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analysis_row(
    composite_score: float | None,
    created_at_date: date | None = None,
    price_at_analysis: float | None = 100.0,
):
    if created_at_date is None:
        created_at_date = date(2024, 3, 1)
    row = MagicMock()
    result_data = {}
    if composite_score is not None:
        result_data["composite_score"] = {"score": composite_score, "label": "FORT"}
    row.__getitem__ = lambda self, key: {
        "result": json.dumps(result_data),
        "created_at": MagicMock(date=lambda: created_at_date),
        "price_at_analysis": price_at_analysis,
    }[key]
    return row


def _make_service(
    score_rows: dict,  # ticker -> (composite_score, date, price)
    current_prices: dict | None = None,
    benchmark_return: float = 0.12,
):
    db_pool = AsyncMock()

    async def fake_fetchrow(query, ticker, start_date):
        entry = score_rows.get(ticker)
        if entry is None:
            return None
        composite_score, analyse_date, price = entry
        row = MagicMock()
        result_data = {}
        if composite_score is not None:
            result_data["composite_score"] = {"score": composite_score, "label": "FORT"}
        row.__getitem__ = lambda self, key: {
            "result": json.dumps(result_data),
            "created_at": MagicMock(date=lambda: analyse_date),
            "price_at_analysis": price,
        }[key]
        return row

    db_pool.fetchrow = fake_fetchrow

    svc = BacktestService(db_pool=db_pool)

    def fake_fetch_current_price(ticker):
        if current_prices:
            return current_prices.get(ticker)
        return 120.0

    def fake_benchmark_return(benchmark, start_date):
        return benchmark_return

    def fake_max_drawdown(ticker, entry_date):
        return -0.05

    return svc, fake_fetch_current_price, fake_benchmark_return, fake_max_drawdown


# ---------------------------------------------------------------------------
# Tests : classifieur
# ---------------------------------------------------------------------------


class TestClassifyScore:

    def test_fort(self):
        assert _classify_score(75.0) == "FORT"

    def test_fort_exactement_seuil(self):
        assert _classify_score(70.0) == "FORT"

    def test_modere(self):
        assert _classify_score(55.0) == "MODERE"

    def test_modere_exactement_seuil(self):
        assert _classify_score(40.0) == "MODERE"

    def test_faible(self):
        assert _classify_score(25.0) == "FAIBLE"

    def test_none_donne_no_signal(self):
        assert _classify_score(None) == "NO_SIGNAL"


# ---------------------------------------------------------------------------
# Tests : modeles Pydantic
# ---------------------------------------------------------------------------


class TestBacktestRequest:

    def test_trop_de_tickers_leve_erreur(self):
        with pytest.raises(Exception):
            BacktestRequest(tickers=[f"T{i}" for i in range(31)], start_date=date(2024, 1, 1))

    def test_start_date_futur_leve_erreur(self):
        with pytest.raises(Exception):
            BacktestRequest(tickers=["AAPL"], start_date=date.today() + timedelta(days=1))

    def test_start_date_trop_ancienne_leve_erreur(self):
        with pytest.raises(Exception):
            BacktestRequest(tickers=["AAPL"], start_date=date(2022, 12, 31))

    def test_requete_valide(self):
        req = BacktestRequest(tickers=["AAPL", "MSFT"], start_date=date(2024, 1, 1))
        assert req.benchmark == "SPY"
        assert len(req.tickers) == 2


# ---------------------------------------------------------------------------
# Tests : service
# ---------------------------------------------------------------------------


class TestBacktestService:

    @pytest.mark.asyncio
    async def test_ticker_sans_historique_va_dans_no_signal(self):
        svc, fake_price, fake_bench, fake_dd = _make_service(score_rows={})

        with (
            patch("app.services.backtest._fetch_current_price", fake_price),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["AAPL"], date(2024, 1, 1))

        no_signal = next(b for b in result.buckets if b.label == "NO_SIGNAL")
        assert "AAPL" in no_signal.tickers

    @pytest.mark.asyncio
    async def test_score_fort_va_dans_bucket_fort(self):
        scores = {"BNS": (80.0, date(2024, 3, 1), 100.0)}
        svc, fake_price, fake_bench, fake_dd = _make_service(scores, current_prices={"BNS": 120.0})

        with (
            patch("app.services.backtest._fetch_current_price", fake_price),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 100.0),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["BNS"], date(2024, 1, 1))

        fort = next(b for b in result.buckets if b.label == "FORT")
        assert "BNS" in fort.tickers

    @pytest.mark.asyncio
    async def test_score_modere_va_dans_bucket_modere(self):
        scores = {"TD": (55.0, date(2024, 3, 1), 80.0)}
        svc, fake_price, fake_bench, fake_dd = _make_service(scores, current_prices={"TD": 88.0})

        with (
            patch("app.services.backtest._fetch_current_price", fake_price),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 80.0),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["TD"], date(2024, 1, 1))

        modere = next(b for b in result.buckets if b.label == "MODERE")
        assert "TD" in modere.tickers

    @pytest.mark.asyncio
    async def test_score_faible_va_dans_bucket_faible(self):
        scores = {"GME": (20.0, date(2024, 3, 1), 15.0)}
        svc, fake_price, fake_bench, fake_dd = _make_service(scores, current_prices={"GME": 12.0})

        with (
            patch("app.services.backtest._fetch_current_price", fake_price),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 15.0),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["GME"], date(2024, 1, 1))

        faible = next(b for b in result.buckets if b.label == "FAIBLE")
        assert "GME" in faible.tickers

    @pytest.mark.asyncio
    async def test_rendement_calcule_correctement(self):
        # Prix entree 100, prix actuel 120 => rendement 20%
        scores = {"AAPL": (80.0, date(2024, 3, 1), 100.0)}
        svc, _, fake_bench, fake_dd = _make_service(scores, current_prices={"AAPL": 120.0})

        with (
            patch("app.services.backtest._fetch_current_price", lambda t: 120.0),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 100.0),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["AAPL"], date(2024, 1, 1))

        fort = next(b for b in result.buckets if b.label == "FORT")
        assert fort.rendement_moyen == pytest.approx(0.20, abs=0.001)

    @pytest.mark.asyncio
    async def test_signal_alpha_calcule(self):
        # FORT rendement 20%, benchmark 12% => alpha 8%
        scores = {"AAPL": (80.0, date(2024, 3, 1), 100.0)}
        svc, _, fake_bench, fake_dd = _make_service(
            scores,
            current_prices={"AAPL": 120.0},
            benchmark_return=0.12,
        )

        with (
            patch("app.services.backtest._fetch_current_price", lambda t: 120.0),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 100.0),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["AAPL"], date(2024, 1, 1))

        assert result.signal_alpha == pytest.approx(0.08, abs=0.001)

    @pytest.mark.asyncio
    async def test_erreur_yfinance_met_ticker_dans_erreurs(self):
        scores = {"ERR": (80.0, date(2024, 3, 1), None)}
        svc, _, fake_bench, _ = _make_service(scores)

        def boom(_ticker, *args):
            raise RuntimeError("network error")

        with (
            patch("app.services.backtest._fetch_current_price", boom),
            patch("app.services.backtest._fetch_price_at_date", boom),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", lambda t, d: None),
        ):
            result = await svc.run_backtest(["ERR"], date(2024, 1, 1))

        assert "ERR" in result.erreurs

    @pytest.mark.asyncio
    async def test_4_buckets_toujours_presents(self):
        svc, fake_price, fake_bench, fake_dd = _make_service(score_rows={})

        with (
            patch("app.services.backtest._fetch_current_price", fake_price),
            patch.object(BacktestService, "_fetch_benchmark_return", staticmethod(fake_bench)),
            patch("app.services.backtest._compute_max_drawdown", fake_dd),
        ):
            result = await svc.run_backtest(["AAPL", "MSFT"], date(2024, 1, 1))

        labels = [b.label for b in result.buckets]
        assert "FORT" in labels
        assert "MODERE" in labels
        assert "FAIBLE" in labels
        assert "NO_SIGNAL" in labels


# ---------------------------------------------------------------------------
# Tests : endpoint
# ---------------------------------------------------------------------------


class TestBacktestEndpoint:

    @pytest.mark.asyncio
    async def test_endpoint_200_retourne_backtest_result(self, client):
        with (
            patch("app.services.backtest._fetch_current_price", lambda t: 120.0),
            patch("app.services.backtest._fetch_price_at_date", lambda t, d: 100.0),
            patch.object(
                BacktestService,
                "_fetch_benchmark_return",
                staticmethod(lambda b, s: 0.10),
            ),
            patch("app.services.backtest._compute_max_drawdown", lambda t, d: -0.05),
            patch.object(
                BacktestService,
                "_get_first_score_after",
                AsyncMock(return_value=None),
            ),
        ):
            resp = await client.get(
                "/backtest/composite",
                params={"tickers": "BNS,TD", "start_date": "2024-01-01"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "buckets" in data
        assert len(data["buckets"]) == 4

    @pytest.mark.asyncio
    async def test_endpoint_trop_tickers_retourne_400(self, client):
        tickers = ",".join([f"T{i}" for i in range(31)])
        resp = await client.get(
            "/backtest/composite",
            params={"tickers": tickers, "start_date": "2024-01-01"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_endpoint_date_futur_retourne_400(self, client):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        resp = await client.get(
            "/backtest/composite",
            params={"tickers": "BNS", "start_date": tomorrow},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_endpoint_aucun_ticker_retourne_400(self, client):
        resp = await client.get(
            "/backtest/composite",
            params={"tickers": "   ,  ", "start_date": "2024-01-01"},
        )
        assert resp.status_code == 400
