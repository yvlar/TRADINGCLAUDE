"""Modeles Pydantic pour le dashboard evals (Sprint 51)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EvalSkillInfo(BaseModel):
    """Metadonnees statiques + dynamiques pour un skill evalue."""

    skill_id: str
    nb_cas: int
    modele_utilise: str
    last_run_at: datetime | None = None
    last_concordance_pct: float | None = None
    last_nb_cas_testes: int | None = None


class EvalsSummary(BaseModel):
    """Resume de toutes les evals disponibles."""

    skills: list[EvalSkillInfo]
    total_cas: int = 0
    total_skills: int = 0


class EvalRunRecord(BaseModel):
    """Resultat d'une execution eval a persister."""

    skill_id: str
    concordance_pct: float = Field(ge=0.0, le=100.0)
    nb_cas_testes: int = Field(ge=0)
    modele: str
    notes: str | None = None
    run_at: datetime | None = None
