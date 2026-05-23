"""Tests CI standard pour EvalDriftService et GET /telemetry/eval-drift — Sprint 61.

Aucun appel Claude réel. _check_case() est patché pour contrôler la concordance.
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.api.main import app
from app.services.eval_drift_service import EvalDriftResult, EvalDriftService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis(stored: str | None = None) -> AsyncMock:
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=stored)
    redis.aclose = AsyncMock(return_value=None)
    return redis


def _make_result(dataset: str = "graham", concordance: float = 0.9, alert: bool = False) -> EvalDriftResult:
    return EvalDriftResult(
        dataset=dataset,
        concordance_rate=concordance,
        threshold=0.85,
        alert=alert,
        cases_total=20,
        cases_pass=int(concordance * 20),
        recorded_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests : EvalDriftResult schema
# ---------------------------------------------------------------------------


class TestEvalDriftResultSchema:

    def test_schema_valide_champs_requis(self):
        result = _make_result()
        assert result.dataset == "graham"
        assert 0.0 <= result.concordance_rate <= 1.0
        assert isinstance(result.alert, bool)
        assert result.cases_total >= 0
        assert result.cases_pass <= result.cases_total

    def test_alert_true_si_concordance_sous_seuil(self):
        result = EvalDriftResult(
            dataset="dorsey",
            concordance_rate=0.70,
            threshold=0.85,
            alert=True,
            cases_total=15,
            cases_pass=10,
            recorded_at=datetime.now(timezone.utc),
        )
        assert result.alert is True
        assert result.concordance_rate < result.threshold

    def test_alert_false_si_concordance_au_dessus_seuil(self):
        result = EvalDriftResult(
            dataset="buffett",
            concordance_rate=0.95,
            threshold=0.85,
            alert=False,
            cases_total=15,
            cases_pass=14,
            recorded_at=datetime.now(timezone.utc),
        )
        assert result.alert is False

    def test_serialisation_json_roundtrip(self):
        result = _make_result("earnings", concordance=0.88)
        json_str = result.model_dump_json()
        restored = EvalDriftResult.model_validate_json(json_str)
        assert restored.dataset == result.dataset
        assert restored.concordance_rate == result.concordance_rate


# ---------------------------------------------------------------------------
# Tests : record_result() — persiste dans Redis mocké
# ---------------------------------------------------------------------------


class TestRecordResult:

    @pytest.mark.asyncio
    async def test_record_result_appelle_redis_set(self):
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis)
        result = _make_result()
        await svc.record_result(result)
        redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_result_cle_correcte(self):
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis)
        result = _make_result("dorsey")
        await svc.record_result(result)
        call_args = redis.set.call_args
        assert "eval_drift:dorsey" in str(call_args)

    @pytest.mark.asyncio
    async def test_record_result_ttl_30_jours(self):
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis)
        await svc.record_result(_make_result())
        call_kwargs = redis.set.call_args.kwargs
        assert call_kwargs.get("ex") == 60 * 60 * 24 * 30


# ---------------------------------------------------------------------------
# Tests : get_last_result()
# ---------------------------------------------------------------------------


class TestGetLastResult:

    @pytest.mark.asyncio
    async def test_retourne_none_si_absent(self):
        redis = _make_redis(stored=None)
        svc = EvalDriftService(redis_client=redis)
        result = await svc.get_last_result("graham")
        assert result is None

    @pytest.mark.asyncio
    async def test_retourne_le_bon_resultat_si_present(self):
        expected = _make_result("buffett", concordance=0.93)
        redis = _make_redis(stored=expected.model_dump_json())
        svc = EvalDriftService(redis_client=redis)
        result = await svc.get_last_result("buffett")
        assert result is not None
        assert result.dataset == "buffett"
        assert result.concordance_rate == pytest.approx(0.93, abs=0.01)

    @pytest.mark.asyncio
    async def test_retourne_none_si_json_invalide(self):
        redis = _make_redis(stored="invalid json {{{")
        svc = EvalDriftService(redis_client=redis)
        result = await svc.get_last_result("graham")
        assert result is None


# ---------------------------------------------------------------------------
# Tests : run_eval() — _check_case patché, aucun appel Claude
# ---------------------------------------------------------------------------


class TestRunEval:

    @pytest.mark.asyncio
    async def test_run_eval_alert_true_si_concordance_sous_seuil(self):
        """Tous les cas échouent → concordance=0 < seuil=0.85 → alert=True."""
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis, threshold=0.85)

        fake_cases = [{"id": f"cas_{i}", "ticker": "TST"} for i in range(5)]
        with patch.object(svc, "_load_cases", return_value=fake_cases):
            with patch.object(svc, "_check_case", return_value=False):
                result = await svc.run_eval("graham")

        assert result.alert is True
        assert result.concordance_rate == 0.0
        assert result.cases_total == 5
        assert result.cases_pass == 0

    @pytest.mark.asyncio
    async def test_run_eval_alert_false_si_concordance_au_dessus_seuil(self):
        """Tous les cas réussissent → concordance=1.0 ≥ seuil → alert=False."""
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis, threshold=0.85)

        fake_cases = [{"id": f"cas_{i}", "ticker": "TST"} for i in range(10)]
        with patch.object(svc, "_load_cases", return_value=fake_cases):
            with patch.object(svc, "_check_case", return_value=True):
                result = await svc.run_eval("graham")

        assert result.alert is False
        assert result.concordance_rate == pytest.approx(1.0)
        assert result.cases_pass == 10

    @pytest.mark.asyncio
    async def test_run_eval_concordance_partielle(self):
        """7/10 cas réussissent → concordance=0.70 < seuil=0.85 → alert=True."""
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis, threshold=0.85)

        fake_cases = [{"id": f"cas_{i}", "ticker": "TST"} for i in range(10)]
        side_effects = [True] * 7 + [False] * 3
        with patch.object(svc, "_load_cases", return_value=fake_cases):
            with patch.object(svc, "_check_case", side_effect=side_effects):
                result = await svc.run_eval("graham")

        assert result.concordance_rate == pytest.approx(0.70)
        assert result.alert is True
        assert result.cases_pass == 7

    @pytest.mark.asyncio
    async def test_run_eval_dataset_invalide_leve_valueerror(self):
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis)
        with pytest.raises(ValueError, match="non supporté"):
            await svc.run_eval("dataset_inexistant")

    @pytest.mark.asyncio
    async def test_run_eval_aucun_cas_retourne_alert_true(self):
        """Si le golden dataset est vide, concordance=0 et alert=True."""
        redis = _make_redis()
        svc = EvalDriftService(redis_client=redis, threshold=0.85)

        with patch.object(svc, "_load_cases", return_value=[]):
            result = await svc.run_eval("dorsey")

        assert result.alert is True
        assert result.cases_total == 0


# ---------------------------------------------------------------------------
# Tests : GET /telemetry/eval-drift
# ---------------------------------------------------------------------------


class TestEvalDriftEndpoint:

    @pytest_asyncio.fixture
    async def drift_client(self, client):
        """Client HTTP avec EvalDriftService mocké dans app.state."""
        mock_svc = AsyncMock(spec=EvalDriftService)
        mock_svc.get_last_result = AsyncMock(return_value=_make_result("graham"))
        app.state.eval_drift_service = mock_svc
        yield client
        if hasattr(app.state, "eval_drift_service"):
            del app.state.eval_drift_service

    @pytest.mark.asyncio
    async def test_get_eval_drift_sans_dataset_retourne_200(self, drift_client):
        resp = await drift_client.get("/telemetry/eval-drift")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_eval_drift_avec_dataset_valide_retourne_200(self, drift_client):
        resp = await drift_client.get("/telemetry/eval-drift?dataset=graham")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_eval_drift_avec_dataset_invalide_retourne_400(self, drift_client):
        resp = await drift_client.get("/telemetry/eval-drift?dataset=inexistant")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_eval_drift_sans_service_retourne_503(self, client):
        """Sans EvalDriftService dans app.state → 503."""
        if hasattr(app.state, "eval_drift_service"):
            del app.state.eval_drift_service
        resp = await client.get("/telemetry/eval-drift")
        assert resp.status_code == 503
