"""Service de détection de drift des evals IA — Sprint 61.

Compare le taux de concordance d'un golden dataset contre un seuil configurable
et alerte si le modèle Claude régresse après une mise à jour.

Clé Redis : eval_drift:{dataset} (TTL 30 jours)
Seuil par défaut : EVAL_DRIFT_THRESHOLD (défaut 0.85)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "evals" / "fixtures"

SUPPORTED_DATASETS = frozenset({"graham", "earnings", "dorsey", "buffett", "damodaran"})

_REDIS_KEY_PREFIX = "eval_drift"
_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 jours


class EvalDriftResult(BaseModel):
    dataset: str
    concordance_rate: float  # 0.0–1.0
    threshold: float
    alert: bool  # True si concordance_rate < threshold
    cases_total: int
    cases_pass: int
    recorded_at: datetime


class EvalDriftService:
    """
    Exécute un golden dataset contre l'API et détecte les dérives de qualité IA.
    Stocke les résultats dans Redis pour consultation via GET /telemetry/eval-drift.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        *,
        api_url: str | None = None,
        threshold: float | None = None,
    ) -> None:
        self._redis = redis_client
        self._api_url = api_url or os.environ.get("EVAL_API_URL", "http://localhost:8000")
        self._threshold = (
            threshold
            if threshold is not None
            else float(os.environ.get("EVAL_DRIFT_THRESHOLD", "0.85"))
        )

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    async def run_eval(self, dataset: str) -> EvalDriftResult:
        """
        Exécute tous les cas du golden dataset contre l'API et retourne EvalDriftResult.
        Dans les tests CI, _check_case est patchable pour éviter tout appel Claude.
        """
        if dataset not in SUPPORTED_DATASETS:
            raise ValueError(
                f"Dataset {dataset!r} non supporté. Valides: {sorted(SUPPORTED_DATASETS)}"
            )

        cases = self._load_cases(dataset)
        if not cases:
            logger.warning("Aucun cas chargé pour le dataset %s", dataset)
            return EvalDriftResult(
                dataset=dataset,
                concordance_rate=0.0,
                threshold=self._threshold,
                alert=True,
                cases_total=0,
                cases_pass=0,
                recorded_at=datetime.now(timezone.utc),
            )

        pass_count = 0
        for case in cases:
            passed = await self._check_case(case, dataset)
            if passed:
                pass_count += 1
            logger.debug(
                "Eval %s — cas %s : %s",
                dataset,
                case.get("id", "?"),
                "PASS" if passed else "FAIL",
            )

        concordance = pass_count / len(cases)
        alert = concordance < self._threshold
        result = EvalDriftResult(
            dataset=dataset,
            concordance_rate=concordance,
            threshold=self._threshold,
            alert=alert,
            cases_total=len(cases),
            cases_pass=pass_count,
            recorded_at=datetime.now(timezone.utc),
        )
        logger.info(
            "Eval drift %s — concordance=%.1f%% seuil=%.1f%% alerte=%s",
            dataset,
            concordance * 100,
            self._threshold * 100,
            alert,
        )
        return result

    async def record_result(self, result: EvalDriftResult) -> None:
        """Persiste le résultat dans Redis avec TTL 30 jours."""
        key = f"{_REDIS_KEY_PREFIX}:{result.dataset}"
        await self._redis.set(key, result.model_dump_json(), ex=_TTL_SECONDS)
        logger.info(
            "Résultat eval drift enregistré : dataset=%s concordance=%.1f%%",
            result.dataset,
            result.concordance_rate * 100,
        )

    async def get_last_result(self, dataset: str) -> EvalDriftResult | None:
        """Retourne le dernier résultat depuis Redis, ou None si absent."""
        key = f"{_REDIS_KEY_PREFIX}:{dataset}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return EvalDriftResult.model_validate_json(raw)
        except Exception:
            logger.warning("Résultat eval drift invalide dans Redis pour %s", dataset)
            return None

    # ------------------------------------------------------------------
    # Méthodes internes (patchables dans les tests)
    # ------------------------------------------------------------------

    def _load_cases(self, dataset: str) -> list[dict[str, Any]]:
        """Charge le golden dataset depuis le disque."""
        path = _FIXTURES_DIR / f"{dataset}_golden.json"
        if not path.exists():
            logger.warning("Fixture introuvable : %s", path)
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Erreur de lecture du fixture %s", path)
            return []

    async def _check_case(self, case: dict[str, Any], dataset: str) -> bool:
        """
        Évalue un cas individuel contre l'API /analyze.
        Patchable dans les tests CI (unittest.mock.patch.object) pour éviter
        tout appel Claude réel.
        """
        try:
            import httpx

            ticker = case.get("ticker", "")
            ratios = case.get("inputs") or case.get("ratios") or {}
            payload: dict[str, Any] = {"ticker": ticker}
            if ratios:
                payload["ratios"] = ratios

            async with httpx.AsyncClient(base_url=self._api_url, timeout=60.0) as client:
                resp = await client.post("/analyze", json=payload)

            if resp.status_code != 200:
                logger.debug(
                    "Cas %s — HTTP %d pour %s",
                    case.get("id"), resp.status_code, ticker,
                )
                return False

            data = resp.json()
            expected = case.get("expected", {})
            return self._matches_expected(data, expected, dataset)

        except Exception:
            logger.exception("Erreur lors de l'évaluation du cas %s", case.get("id"))
            return False

    def _matches_expected(
        self,
        data: dict[str, Any],
        expected: dict[str, Any],
        dataset: str,
    ) -> bool:
        """Compare la réponse API aux valeurs attendues du golden dataset."""
        if dataset == "graham":
            graham = data.get("graham") or {}
            if "defensive_verdict" in expected:
                if graham.get("defensive_verdict") != expected["defensive_verdict"]:
                    return False
            if "defensive_score_range" in expected:
                lo, hi = expected["defensive_score_range"]
                if not (lo <= (graham.get("defensive_score") or 0) <= hi):
                    return False
            return True

        if dataset == "dorsey":
            dorsey = data.get("dorsey_moat") or {}
            if "moat_type_allowed" in expected:
                if dorsey.get("moat_type") not in expected["moat_type_allowed"]:
                    return False
            return True

        if dataset == "buffett":
            buffett = data.get("buffett_quality") or {}
            if "verdict_allowed" in expected:
                if buffett.get("verdict") not in expected["verdict_allowed"]:
                    return False
            return True

        if dataset == "damodaran":
            dam = data.get("damodaran_narrative") or {}
            if "verdict_allowed" in expected:
                if dam.get("verdict") not in expected["verdict_allowed"]:
                    return False
            return True

        if dataset == "earnings":
            eq = data.get("earnings_quality") or {}
            if "mscore_verdict_allowed" in expected:
                if eq.get("mscore_verdict") not in expected["mscore_verdict_allowed"]:
                    return False
            return True

        return False
