"""Service dashboard evals -- gestion historique et metadonnees (Sprint 51)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import redis.asyncio as aioredis

from app.models.evals import EvalRunRecord, EvalSkillInfo, EvalsSummary

logger = logging.getLogger(__name__)

_EVALS_DIR = Path(__file__).parent.parent.parent / "tests" / "evals" / "fixtures"

_SKILL_CATALOGUE: list[dict] = [
    {"skill_id": "graham_analysis", "nb_cas": 20, "modele": "claude-sonnet-4-6", "fixture": "graham_golden.json"},
    {"skill_id": "earnings_quality", "nb_cas": 20, "modele": "claude-haiku-4-5-20251001", "fixture": "earnings_golden.json"},
    {"skill_id": "dorsey_moat", "nb_cas": 15, "modele": "claude-sonnet-4-6", "fixture": "dorsey_golden.json"},
    {"skill_id": "buffett_quality", "nb_cas": 15, "modele": "claude-sonnet-4-6", "fixture": "buffett_golden.json"},
    {"skill_id": "damodaran_narrative", "nb_cas": 15, "modele": "claude-sonnet-4-6", "fixture": "damodaran_golden.json"},
]

_REDIS_KEY_PREFIX = "evals"
_HISTORY_MAX_ENTRIES = 30
_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 jours


class EvalsDashboardService:
    """Lit les metadonnees evals depuis le disque et persiste l'historique dans Redis."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def get_summary(self) -> EvalsSummary:
        """Retourne les metadonnees statiques + derniere execution pour chaque skill."""
        skills: list[EvalSkillInfo] = []

        for entry in _SKILL_CATALOGUE:
            skill_id = entry["skill_id"]
            last_run = await self._get_last_run(skill_id)

            skills.append(EvalSkillInfo(
                skill_id=skill_id,
                nb_cas=entry["nb_cas"],
                modele_utilise=entry["modele"],
                last_run_at=last_run.run_at if last_run else None,
                last_concordance_pct=last_run.concordance_pct if last_run else None,
                last_nb_cas_testes=last_run.nb_cas_testes if last_run else None,
            ))

        return EvalsSummary(
            skills=skills,
            total_cas=sum(e["nb_cas"] for e in _SKILL_CATALOGUE),
            total_skills=len(_SKILL_CATALOGUE),
        )

    async def record_run(self, record: EvalRunRecord) -> None:
        """Enregistre le resultat d'une execution eval dans Redis."""
        if record.run_at is None:
            record = record.model_copy(update={"run_at": datetime.now(tz=timezone.utc)})

        key = f"{_REDIS_KEY_PREFIX}:{record.skill_id}:history"
        payload = json.dumps({
            "skill_id": record.skill_id,
            "concordance_pct": record.concordance_pct,
            "nb_cas_testes": record.nb_cas_testes,
            "modele": record.modele,
            "notes": record.notes,
            "run_at": record.run_at.isoformat(),
        })

        await self._redis.lpush(key, payload)
        await self._redis.ltrim(key, 0, _HISTORY_MAX_ENTRIES - 1)
        await self._redis.expire(key, _TTL_SECONDS)

        logger.info(
            "Eval run enregistre : skill=%s concordance=%.1f%% modele=%s",
            record.skill_id, record.concordance_pct, record.modele,
        )

    async def get_history(self, skill_id: str) -> list[EvalRunRecord]:
        """Retourne l'historique des executions pour un skill (plus recent en premier)."""
        key = f"{_REDIS_KEY_PREFIX}:{skill_id}:history"
        raw_list = await self._redis.lrange(key, 0, _HISTORY_MAX_ENTRIES - 1)

        records: list[EvalRunRecord] = []
        for raw in raw_list:
            try:
                data = json.loads(raw)
                run_at = datetime.fromisoformat(data["run_at"]) if data.get("run_at") else None
                records.append(EvalRunRecord(
                    skill_id=data["skill_id"],
                    concordance_pct=data["concordance_pct"],
                    nb_cas_testes=data["nb_cas_testes"],
                    modele=data["modele"],
                    notes=data.get("notes"),
                    run_at=run_at,
                ))
            except Exception:
                logger.debug("Entree historique eval invalide ignoree")

        return records

    async def _get_last_run(self, skill_id: str) -> EvalRunRecord | None:
        """Retourne le dernier run enregistre pour un skill, ou None."""
        history = await self.get_history(skill_id)
        return history[0] if history else None
