from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class ThesisContext(BaseModel):
    """Résumé thesis_builder passé en contexte au skill munger."""

    ticker: str
    verdict_final: str
    position_size_pct: float
    scenario_bull_probabilite: float
    scenario_base_probabilite: float
    scenario_bear_probabilite: float
    synthese_narrative: str
    kill_criteria: list[str]
    devils_advocate: str


class MungerInput(BaseModel):
    ticker: str
    thesis_context: ThesisContext


class BiaisCognitif(BaseModel):
    nom: str = Field(description="Nom du biais (ex: Commitment Bias, Overconfidence...)")
    description: str = Field(description="Comment ce biais se manifeste dans cette thèse")
    impact_sur_these: str = Field(description="MINEUR | MODERE | MAJEUR")


class MungerOutput(BaseModel):
    ticker: str
    biais_detectes: list[BiaisCognitif]
    inversion_analysis: str = Field(description="Réponse à : qu'est-ce qui ferait échouer cette thèse ?")
    lollapalooza_risk: bool = Field(description="Convergence de plusieurs biais amplificateurs")
    verdict_comportemental: str = Field(
        description="CONFIANCE_JUSTIFIEE | BIAIS_DETECTE | ALERTE_ROUGE"
    )
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_verdict(self) -> "MungerOutput":
        valid = {"CONFIANCE_JUSTIFIEE", "BIAIS_DETECTE", "ALERTE_ROUGE"}
        if self.verdict_comportemental not in valid:
            raise ValueError(f"verdict_comportemental invalide : {self.verdict_comportemental}")
        valid_impacts = {"MINEUR", "MODERE", "MAJEUR"}
        for b in self.biais_detectes:
            if b.impact_sur_these not in valid_impacts:
                raise ValueError(f"impact_sur_these invalide : {b.impact_sur_these}")
        return self
