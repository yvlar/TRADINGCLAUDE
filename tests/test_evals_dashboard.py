"""Tests unitaires pour EvalsDashboardService et les endpoints /evals (Sprint 51)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.evals import EvalRunRecord, EvalSkillInfo, EvalsSummary
from app.services.evals_dashboard import EvalsDashboardService, _SKILL_CATALOGUE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redis(history: list[str] | None = None):
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=history or [])
    redis.lpush = AsyncMock(return_value=1)
    redis.ltrim = AsyncMock(return_value=True)
    redis.expire = AsyncMock(return_value=True)
    return redis


def _make_record(skill_id: str = "graham_analysis", concordance: float = 90.0) -> EvalRunRecord:
    return EvalRunRecord(
        skill_id=skill_id,
        concordance_pct=concordance,
        nb_cas_testes=20,
        modele="claude-sonnet-4-6",
        notes="test run",
        run_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc),
    )


def _serialize_record(record: EvalRunRecord) -> str:
    return json.dumps({
        "skill_id": record.skill_id,
        "concordance_pct": record.concordance_pct,
        "nb_cas_testes": record.nb_cas_testes,
        "modele": record.modele,
        "notes": record.notes,
        "run_at": record.run_at.isoformat() if record.run_at else None,
    })


# ---------------------------------------------------------------------------
# Tests : service
# ---------------------------------------------------------------------------


class TestEvalsDashboardService:

    @pytest.mark.asyncio
    async def test_summary_retourne_5_skills(self):
        redis = _make_redis()
        svc = EvalsDashboardService(redis_client=redis)
        summary = await svc.get_summary()
        assert summary.total_skills == 5
        assert len(summary.skills) == 5

    @pytest.mark.asyncio
    async def test_summary_total_cas_85(self):
        redis = _make_redis()
        svc = EvalsDashboardService(redis_client=redis)
        summary = await svc.get_summary()
        assert summary.total_cas == 85  # 20+20+15+15+15

    @pytest.mark.asyncio
    async def test_summary_sans_historique_last_run_none(self):
        redis = _make_redis(history=[])
        svc = EvalsDashboardService(redis_client=redis)
        summary = await svc.get_summary()
        for skill in summary.skills:
            assert skill.last_run_at is None
            assert skill.last_concordance_pct is None

    @pytest.mark.asyncio
    async def test_summary_avec_historique_retourne_derniere_execution(self):
        record = _make_record("graham_analysis", concordance=95.0)
        redis = _make_redis(history=[_serialize_record(record)])
        svc = EvalsDashboardService(redis_client=redis)
        summary = await svc.get_summary()
        graham = next(s for s in summary.skills if s.skill_id == "graham_analysis")
        assert graham.last_concordance_pct == 95.0
        assert graham.last_nb_cas_testes == 20

    @pytest.mark.asyncio
    async def test_record_run_appelle_lpush_redis(self):
        redis = _make_redis()
        svc = EvalsDashboardService(redis_client=redis)
        record = _make_record()
        await svc.record_run(record)
        redis.lpush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_run_ajoute_timestamp_si_absent(self):
        redis = _make_redis()
        svc = EvalsDashboardService(redis_client=redis)
        record = EvalRunRecord(
            skill_id="graham_analysis",
            concordance_pct=80.0,
            nb_cas_testes=18,
            modele="claude-sonnet-4-6",
        )
        # Ne doit pas lever d'exception
        await svc.record_run(record)
        redis.lpush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_history_retourne_liste_ordonnee(self):
        r1 = _make_record("earnings_quality", 88.0)
        r2 = _make_record("earnings_quality", 75.0)
        redis = _make_redis(history=[_serialize_record(r1), _serialize_record(r2)])
        svc = EvalsDashboardService(redis_client=redis)
        history = await svc.get_history("earnings_quality")
        assert len(history) == 2
        assert history[0].concordance_pct == 88.0
        assert history[1].concordance_pct == 75.0

    @pytest.mark.asyncio
    async def test_get_history_ignore_entrees_invalides(self):
        redis = _make_redis(history=["invalid json {{{", _serialize_record(_make_record())])
        svc = EvalsDashboardService(redis_client=redis)
        history = await svc.get_history("graham_analysis")
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_get_history_vide_si_pas_de_runs(self):
        redis = _make_redis(history=[])
        svc = EvalsDashboardService(redis_client=redis)
        history = await svc.get_history("dorsey_moat")
        assert history == []

    @pytest.mark.asyncio
    async def test_skills_catalogue_contient_bons_modeles(self):
        haiku_skills = {"earnings_quality", "greenblatt", "lynch_categories"}
        for entry in _SKILL_CATALOGUE:
            if entry["skill_id"] in haiku_skills:
                assert "haiku" in entry["modele"].lower(), (
                    f"{entry['skill_id']} devrait utiliser Haiku"
                )


# ---------------------------------------------------------------------------
# Tests : endpoints
# ---------------------------------------------------------------------------


class TestEvalsEndpoints:

    @pytest.mark.asyncio
    async def test_evals_summary_retourne_200(self, client):
        resp = await client.get("/evals/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        assert data["total_skills"] == 5
        assert data["total_cas"] == 85

    @pytest.mark.asyncio
    async def test_evals_record_skill_invalide_retourne_400(self, client):
        payload = {
            "skill_id": "skill_inexistant",
            "concordance_pct": 90.0,
            "nb_cas_testes": 20,
            "modele": "claude-sonnet-4-6",
        }
        resp = await client.post("/evals/record", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_evals_record_skill_valide_retourne_201(self, client):
        payload = {
            "skill_id": "graham_analysis",
            "concordance_pct": 90.0,
            "nb_cas_testes": 20,
            "modele": "claude-sonnet-4-6",
            "notes": "run de test",
        }
        resp = await client.post("/evals/record", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["skill_id"] == "graham_analysis"

    @pytest.mark.asyncio
    async def test_evals_history_skill_invalide_retourne_400(self, client):
        resp = await client.get("/evals/history", params={"skill_id": "inexistant"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_evals_history_skill_valide_retourne_200(self, client):
        resp = await client.get("/evals/history", params={"skill_id": "dorsey_moat"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
