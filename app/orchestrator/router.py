from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkillStep:
    skill_id: str
    optional: bool = False


# Séquences de skills par workflow (section 3.3 de l'architecture)
WORKFLOWS: dict[str, list[SkillStep]] = {
    "value_graham": [
        SkillStep("graham_analysis"),
        SkillStep("earnings_quality", optional=True),
        SkillStep("stock_valuation_triangulation", optional=True),
        SkillStep("investment_thesis_builder", optional=True),
        SkillStep("canadian_tax_considerations", optional=True),
    ],
    "compounder_buffett": [
        SkillStep("graham_analysis"),
        SkillStep("earnings_quality", optional=True),
        SkillStep("dorsey_moat", optional=True),
        SkillStep("buffett_quality", optional=True),
        SkillStep("fisher_scuttlebutt", optional=True),
        SkillStep("stock_valuation_triangulation", optional=True),
        SkillStep("investment_thesis_builder", optional=True),
        SkillStep("munger_mental_models", optional=True),
        SkillStep("marks_cycles_risk", optional=True),
        SkillStep("canadian_tax_considerations", optional=True),
    ],
    "fast_grower_lynch": [
        SkillStep("lynch_categories"),
        SkillStep("damodaran_narrative", optional=True),
        SkillStep("stock_valuation_triangulation", optional=True),
        SkillStep("investment_thesis_builder", optional=True),
        SkillStep("munger_mental_models", optional=True),
        SkillStep("canadian_tax_considerations", optional=True),
    ],
    "special_situation": [
        SkillStep("graham_analysis"),
        SkillStep("klarman_margin", optional=True),
        SkillStep("greenblatt_magic_formula", optional=True),
        SkillStep("investment_thesis_builder", optional=True),
    ],
    "distressed_pabrai": [
        SkillStep("pabrai_dhandho"),
        SkillStep("klarman_margin", optional=True),
        SkillStep("earnings_quality", optional=True),
        SkillStep("investment_thesis_builder", optional=True),
        SkillStep("canadian_tax_considerations", optional=True),
    ],
}


class WorkflowRouter:
    """Dispatch vers la séquence de skills appropriée selon le workflow demandé."""

    def route(self, workflow: str) -> list[SkillStep]:
        """
        Retourne la liste ordonnée des SkillStep pour le workflow donné.
        Lève ValueError si le workflow est inconnu.
        """
        if workflow not in WORKFLOWS:
            raise ValueError(f"Workflow inconnu: {workflow}")
        return WORKFLOWS[workflow]
