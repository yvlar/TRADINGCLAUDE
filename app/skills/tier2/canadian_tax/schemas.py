from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class CanadianTaxInput(BaseModel):
    ticker: str
    position_size_pct: float = Field(ge=0.0, le=10.0)
    verdict_final: str = Field(description="Verdict du thesis_builder : ACHETER|ACCUMULER|CONSERVER|VENDRE")
    province: str = Field(default="QC", description="Province canadienne (QC, ON, BC, AB...)")
    dividende_canadien: bool = False
    dividende_us: bool = False
    est_reit: bool = False
    est_action_croissance: bool = True

    @model_validator(mode="after")
    def valider_province(self) -> "CanadianTaxInput":
        provinces_valides = {"QC", "ON", "BC", "AB", "SK", "MB", "NB", "NS", "PE", "NL"}
        if self.province not in provinces_valides:
            raise ValueError(f"province invalide : {self.province}")
        return self


class CanadianTaxOutput(BaseModel):
    ticker: str
    compte_recommande: str = Field(description="CELI | REER | CELIAPP | NON_ENREGISTRE")
    justification_fiscale: str
    impact_retenue_us: str | None = Field(None, description="Retenue à la source US si applicable")
    strategie_smith_manoeuvre: bool = Field(description="Smith Manœuvre applicable si marge HELOC disponible")
    taux_inclusion_gain_capital: float = Field(description="0.50 = 50% inclusion pour particulier QC/CA")
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_compte(self) -> "CanadianTaxOutput":
        valid = {"CELI", "REER", "CELIAPP", "NON_ENREGISTRE"}
        if self.compte_recommande not in valid:
            raise ValueError(f"compte_recommande invalide : {self.compte_recommande}")
        return self
