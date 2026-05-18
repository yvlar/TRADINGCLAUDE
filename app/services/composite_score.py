from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WEIGHTS: dict[str, float] = {
    "graham": 0.20,
    "buffett": 0.20,
    "stock_valuation": 0.20,
    "dorsey_moat": 0.15,
    "earnings_quality": 0.15,
    "marks_cycles": 0.10,
}


@dataclass
class CompositeScore:
    score: float  # 0.0 à 100.0, arrondi 1 décimale
    label: str    # "FORT" ≥70, "MODÉRÉ" 45-69, "FAIBLE" <45
    skills_inclus: list[str]  # skills ayant contribué au score
    skills_exclus: list[str]  # skills absents ou confidence=0
    detail: dict[str, float]  # score brut par skill (avant pondération)


def _map_graham(verdict: str | None) -> float | None:
    mapping = {"PASSE": 1.0, "BORDERLINE": 0.5, "REJETER": 0.0}
    return mapping.get(verdict) if verdict else None


def _map_buffett(verdict: str | None) -> float | None:
    mapping = {
        "COMPOUNDER": 1.0,
        "QUALITÉ": 0.75,
        "QUALITE_CORRECTE": 0.75,  # valeur réelle du schéma
        "PASSABLE": 0.5,
        "REJETER": 0.0,
    }
    return mapping.get(verdict) if verdict else None


def _map_valuation(verdict: str | None) -> float | None:
    if verdict is None:
        return None
    v = verdict.upper()
    if "SOUS" in v:
        return 1.0
    if "JUSTE" in v:
        return 0.5
    if "SUR" in v:
        return 0.0
    return None


def _map_moat(moat_type: str | None) -> float | None:
    mapping = {"WIDE": 1.0, "NARROW": 0.5, "NONE": 0.0}
    return mapping.get(moat_type) if moat_type else None


def _map_earnings(verdict: str | None) -> float | None:
    mapping = {
        "FIABLE": 1.0,
        "AUCUN_SIGNAL": 1.0,  # valeur réelle du schéma
        "ATTENTION": 0.75,    # valeur réelle du schéma
        "SURVEILLER": 0.5,
        "WATCHLIST": 0.5,     # valeur réelle du schéma
        "REJETER": 0.0,
    }
    return mapping.get(verdict) if verdict else None


def _map_marks(signal: str | None) -> float | None:
    if signal is None:
        return None
    s = signal.upper()
    # Couvre "ACHETEUR AGRESSIF" (tests) et "ACHETER_AGRESSIF" / "ACHETER_PRUDEMMENT" (schéma réel)
    if "ACHETEUR" in s or "ACHETER" in s:
        return 1.0
    # Couvre "NEUTRE" (tests) et "ATTENDRE" (schéma réel)
    if "NEUTRE" in s or "ATTENDRE" in s:
        return 0.5
    return 0.0


def compute_composite_score(
    graham_verdict: str | None = None,
    graham_confidence: float = 0.0,
    buffett_verdict: str | None = None,
    buffett_confidence: float = 0.0,
    valuation_verdict: str | None = None,
    valuation_confidence: float = 0.0,
    moat_type: str | None = None,
    moat_confidence: float = 0.0,
    earnings_verdict: str | None = None,
    earnings_confidence: float = 0.0,
    marks_signal: str | None = None,
    marks_confidence: float = 1.0,  # marks_cycles n'a pas de confidence_score — défaut 1.0
) -> CompositeScore:
    """Calcule le score composite 0-100 depuis les verdicts des 6 skills pondérés."""
    raw_scores = {
        "graham": (_map_graham(graham_verdict), graham_confidence),
        "buffett": (_map_buffett(buffett_verdict), buffett_confidence),
        "stock_valuation": (_map_valuation(valuation_verdict), valuation_confidence),
        "dorsey_moat": (_map_moat(moat_type), moat_confidence),
        "earnings_quality": (_map_earnings(earnings_verdict), earnings_confidence),
        "marks_cycles": (_map_marks(marks_signal), marks_confidence),
    }

    numerateur = 0.0
    denominateur = 0.0
    skills_inclus: list[str] = []
    skills_exclus: list[str] = []
    detail: dict[str, float] = {}

    for skill_key, (raw, confidence) in raw_scores.items():
        poids = WEIGHTS[skill_key]
        if raw is None or confidence == 0.0:
            skills_exclus.append(skill_key)
            continue
        contribution = raw * poids * confidence
        numerateur += contribution
        denominateur += poids * confidence
        skills_inclus.append(skill_key)
        detail[skill_key] = round(raw, 4)

    if denominateur == 0.0:
        score = 0.0
    else:
        score = round((numerateur / denominateur) * 100, 1)

    if score >= 70:
        label = "FORT"
    elif score >= 45:
        label = "MODÉRÉ"
    else:
        label = "FAIBLE"

    return CompositeScore(
        score=score,
        label=label,
        skills_inclus=skills_inclus,
        skills_exclus=skills_exclus,
        detail=detail,
    )
