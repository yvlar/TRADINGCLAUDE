"""Tests unitaires pour Orchestrator._planned_skill_ids (event SSE `plan`)."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.skills.tier2.esg_simplified.schemas import EsgInput
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

_RATIOS = GrahamRatios(
    pe=11.0,
    pb=1.3,
    current_ratio=None,
    debt_equity=0.45,
    eps_growth_total=0.27,
    price=80.0,
    book_value=61.5,
)


def _orchestrator() -> Orchestrator:
    """Orchestrateur avec tous les skills présents (MagicMock) — seules les conditions comptent."""
    return Orchestrator(MagicMock(), MagicMock(), MagicMock(), *([MagicMock()] * 14))


def test_value_graham_ratios_seuls():
    """value_graham avec seulement les ratios Graham → uniquement graham_analysis."""
    req = AnalyzeRequest(ticker="BNS", ratios=_RATIOS, workflow="value_graham")
    assert _orchestrator()._planned_skill_ids(req) == ["graham_analysis"]


def test_value_graham_avec_thesis():
    """thesis_ratios activé → investment_thesis_builder planifié après graham."""
    req = AnalyzeRequest(
        ticker="BNS", ratios=_RATIOS, workflow="value_graham", thesis_ratios=True
    )
    assert _orchestrator()._planned_skill_ids(req) == [
        "graham_analysis",
        "investment_thesis_builder",
    ]


def test_munger_requiert_thesis():
    """munger n'est planifié que si thesis l'est aussi (dépendance d'exécution).

    Utilise compounder_buffett car munger n'appartient pas au workflow value_graham.
    """
    avec = AnalyzeRequest(
        ticker="BNS",
        ratios=_RATIOS,
        workflow="compounder_buffett",
        thesis_ratios=True,
        munger_ratios=True,
    )
    assert _orchestrator()._planned_skill_ids(avec) == [
        "graham_analysis",
        "investment_thesis_builder",
        "munger_mental_models",
    ]

    sans = AnalyzeRequest(
        ticker="BNS", ratios=_RATIOS, workflow="compounder_buffett", munger_ratios=True
    )
    planned = _orchestrator()._planned_skill_ids(sans)
    assert "munger_mental_models" not in planned
    assert "investment_thesis_builder" not in planned


def test_esg_non_filtre_par_workflow():
    """esg_simplified s'exécute dès que esg_input est fourni, même hors du workflow."""
    req = AnalyzeRequest(
        ticker="BNS",
        ratios=_RATIOS,
        workflow="value_graham",
        esg_input=EsgInput(ticker="BNS"),
    )
    assert _orchestrator()._planned_skill_ids(req) == ["graham_analysis", "esg_simplified"]


def test_workflow_inconnu_aucun_filtre():
    """Workflow inconnu → pas de filtre, tous les skills dont les données sont fournies."""
    req = AnalyzeRequest(
        ticker="BNS",
        ratios=_RATIOS,
        workflow="workflow_inexistant",
        thesis_ratios=True,
        esg_input=EsgInput(ticker="BNS"),
    )
    assert _orchestrator()._planned_skill_ids(req) == [
        "graham_analysis",
        "investment_thesis_builder",
        "esg_simplified",
    ]
