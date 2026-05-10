from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation
from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
from app.skills.tier2.earnings_quality.schemas import EarningsQualityOutput
from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
from app.skills.tier2.stock_valuation.schemas import StockValuationOutput


class AllSkillContexts(BaseModel):
    """Contextes de tous les skills précédents, passés en entrée du thesis_builder."""

    graham: GrahamAnalysisOutput | None = None
    earnings_quality: EarningsQualityOutput | None = None
    dorsey: DorseyMoatOutput | None = None
    buffett: BuffettQualityOutput | None = None
    valuation: StockValuationOutput | None = None


class ThesisBuilderInput(BaseModel):
    ticker: str
    all_contexts: AllSkillContexts


class ThesisScenario(BaseModel):
    probabilite: float = Field(ge=0.0, le=1.0, description="Probabilité (fraction : 0.35 = 35%)")
    rendement_cible: float = Field(description="Rendement attendu en fraction (0.25 = +25%)")
    hypotheses: list[str] = Field(description="Hypothèses clés du scénario (2-4 éléments)")


class ThesisBuilderOutput(BaseModel):
    ticker: str
    scenario_bull: ThesisScenario
    scenario_base: ThesisScenario
    scenario_bear: ThesisScenario
    kill_criteria: list[str] = Field(description="Conditions qui invalident la thèse (3-5 éléments)")
    devils_advocate: str = Field(description="Argument le plus fort contre la thèse")
    position_size_pct: float = Field(ge=0.0, le=10.0, description="Allocation en % du portefeuille")
    verdict_final: str = Field(description="ACHETER | ACCUMULER | CONSERVER | VENDRE")
    synthese_narrative: str = Field(description="Thèse formelle 3-5 paragraphes")
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_probabilites(self) -> "ThesisBuilderOutput":
        total = (
            self.scenario_bull.probabilite
            + self.scenario_base.probabilite
            + self.scenario_bear.probabilite
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Les probabilités bull + base + bear doivent sommer à 1.0, reçu {total:.3f}"
            )
        valid_verdicts = {"ACHETER", "ACCUMULER", "CONSERVER", "VENDRE"}
        if self.verdict_final not in valid_verdicts:
            raise ValueError(f"verdict_final invalide : {self.verdict_final}")
        return self
