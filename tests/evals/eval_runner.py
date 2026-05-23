"""
EvalRunner — Lance le golden dataset graham_analysis et calcule les métriques de drift.

Usage :
    pytest tests/evals/ -m evals -v --tb=short

    # Avec rapport JSON (nécessite pytest-json-report)
    pytest tests/evals/ -m evals --json-report --json-report-file=evals_report.json

IMPORTANT : Ce module fait des appels Claude RÉELS. Ne jamais inclure dans le CI standard.
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Résultat d'un cas de test individuel du golden dataset."""

    case_id: str
    passed: bool
    drift_fields: list[str]  # champs qui ont divergé du expected
    latency_ms: int
    cost_usd: float
    raw_output: dict[str, Any]


@dataclass
class EvalReport:
    """Rapport agrégé sur l'ensemble du golden dataset."""

    total: int
    passed: int
    results: list[EvalResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Taux de réussite — seuil Sprint 41 : ≥ 90 %."""
        return self.passed / self.total if self.total else 0.0

    @property
    def verdict_drift_rate(self) -> float:
        """
        Taux de verdicts incorrects sur le total.
        Seuil dur Sprint 41 : ≤ 2 %.
        Seuls les cas avec 'defensive_verdict' dans expected contribuent.
        """
        verdict_cases = [r for r in self.results if "defensive_verdict" in _get_expected(r)]
        if not verdict_cases:
            return 0.0
        wrong = sum(1 for r in verdict_cases if "defensive_verdict" in r.drift_fields)
        return wrong / len(verdict_cases)

    @property
    def score_drift_mean(self) -> float:
        """
        Écart moyen entre le score défensif réel et le score attendu (score_min).
        Objectif Sprint 41 : < 0.5 pts.
        """
        diffs = []
        for r in self.results:
            expected = _get_expected(r)
            if "defensive_score_min" in expected:
                actual_score = r.raw_output.get("graham", {}).get("defensive_score", 0)
                diffs.append(abs(actual_score - expected["defensive_score_min"]))
        return statistics.mean(diffs) if diffs else 0.0

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.results)

    @property
    def latency_p50_ms(self) -> float | None:
        latencies = [r.latency_ms for r in self.results]
        return statistics.median(latencies) if latencies else None

    def print_summary(self) -> None:
        """Affiche un résumé lisible dans la sortie pytest."""
        logger.info("=" * 60)
        logger.info("EVAL REPORT — graham_analysis golden dataset")
        logger.info("=" * 60)
        logger.info("Total cas          : %d", self.total)
        logger.info("Passés             : %d (%.1f %%)", self.passed, self.pass_rate * 100)
        logger.info("verdict_drift_rate : %.1f %% (seuil Sprint 41 : ≤ 2 %%)", self.verdict_drift_rate * 100)
        logger.info("score_drift_mean   : %.2f pts (objectif < 0.5)", self.score_drift_mean)
        logger.info("Coût total         : $%.4f USD", self.total_cost_usd)
        logger.info("Latence médiane    : %s ms", self.latency_p50_ms)
        logger.info("=" * 60)

        failed = [r for r in self.results if not r.passed]
        if failed:
            logger.info("CAS ÉCHOUÉS :")
            for r in failed:
                logger.info("  - %s | drift_fields=%s", r.case_id, r.drift_fields)


def _get_expected(result: EvalResult) -> dict[str, Any]:
    """Extrait le dict `expected` depuis raw_output (stocké lors de la construction)."""
    return result.raw_output.get("_expected", {})


class EvalRunner:
    """
    Lance le golden dataset complet et calcule les métriques de drift.

    Exemple d'utilisation programmatique (hors pytest) :
        runner = EvalRunner(base_url="http://localhost:8000", api_key="...")
        report = await runner.run_all()
        report.print_summary()
    """

    def __init__(self, base_url: str = "http://test", api_key: str = "") -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def run_case(
        self,
        client: Any,  # httpx.AsyncClient
        case: dict[str, Any],
    ) -> EvalResult:
        """Lance un cas de test et retourne EvalResult."""
        from tests.evals.fixtures import (
            load_graham_golden,  # noqa: F401 — import local intentionnel
        )

        t0 = time.perf_counter()
        response = await client.post(
            "/analyze",
            json={"ticker": case["ticker"], "ratios": case["ratios"]},
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if response.status_code != 200:
            return EvalResult(
                case_id=case["id"],
                passed=False,
                drift_fields=["http_status"],
                latency_ms=latency_ms,
                cost_usd=0.0,
                raw_output={"_expected": case.get("expected", {}), "http_status": response.status_code},
            )

        data = response.json()
        graham = data.get("graham", {})
        expected = case.get("expected", {})
        cost_usd = data.get("cost_usd", 0.0)

        drift_fields = self._compute_drift(graham, expected)
        passed = len(drift_fields) == 0

        raw_output: dict[str, Any] = {"graham": graham, "_expected": expected, "cost_usd": cost_usd}
        return EvalResult(
            case_id=case["id"],
            passed=passed,
            drift_fields=drift_fields,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            raw_output=raw_output,
        )

    def _compute_drift(self, actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
        """
        Retourne la liste des champs qui divergent de expected.
        Utilisé pour calculer verdict_drift_rate (seuil ≤ 2 % en Sprint 41).

        Formats expected supportés :
        - defensive_verdict : "PASSE" | "BORDERLINE" | "REJETER" (computed_field Décision 2)
        - defensive_score_range : [min, max] (format template)
        - defensive_score_min / defensive_score_max : ints séparés (format original sprint spec)
        - has_graham_number : bool
        - has_citations : bool
        """
        drifted: list[str] = []

        if "defensive_verdict" in expected:
            actual_verdict = actual.get("defensive_verdict", "")
            if actual_verdict != expected["defensive_verdict"]:
                drifted.append("defensive_verdict")

        if "defensive_score_range" in expected:
            score_range = expected["defensive_score_range"]
            actual_score = actual.get("defensive_score", 0)
            if not (score_range[0] <= actual_score <= score_range[1]):
                drifted.append("defensive_score_range")

        if "defensive_score_min" in expected:
            actual_score = actual.get("defensive_score", 0)
            if actual_score < expected["defensive_score_min"]:
                drifted.append("defensive_score_min")

        if "defensive_score_max" in expected:
            actual_score = actual.get("defensive_score", 0)
            if actual_score > expected["defensive_score_max"]:
                drifted.append("defensive_score_max")

        if "entrepreneurial_verdict" in expected:
            if actual.get("entrepreneurial_verdict") != expected["entrepreneurial_verdict"]:
                drifted.append("entrepreneurial_verdict")

        if "has_graham_number" in expected:
            has_number = (actual.get("valeur_intrinseque_ajustee") or 0) > 0
            if has_number != expected["has_graham_number"]:
                drifted.append("has_graham_number")

        if "has_citations" in expected:
            has_cit = len(actual.get("citations", [])) > 0
            if has_cit != expected["has_citations"]:
                drifted.append("has_citations")

        return drifted

    async def run_all(self, client: Any) -> EvalReport:
        """
        Lance tous les cas du golden dataset et retourne un EvalReport complet.
        `client` doit être un httpx.AsyncClient connecté à l'API.
        """
        from tests.evals.fixtures import load_graham_golden

        cases = load_graham_golden()
        results: list[EvalResult] = []
        for case in cases:
            result = await self.run_case(client, case)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            logger.info("[%s] %s — latency=%dms cost=$%.4f drift=%s",
                        status, result.case_id, result.latency_ms, result.cost_usd, result.drift_fields)

        passed = sum(1 for r in results if r.passed)
        report = EvalReport(total=len(cases), passed=passed, results=results)
        report.print_summary()
        return report
