from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class GreenblattRatios(BaseModel):
    ebit: float
    enterprise_value: float
    net_working_capital: float
    net_fixed_assets: float
    sector: str | None = None

    @model_validator(mode="after")
    def valider_ratios(self) -> "GreenblattRatios":
        if self.enterprise_value <= 0:
            raise ValueError("enterprise_value doit être > 0 pour calculer l'Earnings Yield")
        capital_investi = self.net_working_capital + self.net_fixed_assets
        if capital_investi <= 0:
            raise ValueError("(net_working_capital + net_fixed_assets) doit être > 0 pour calculer le ROC")
        return self


class GreenblattInput(BaseModel):
    ticker: str
    greenblatt_ratios: GreenblattRatios


class GreenblattOutput(BaseModel):
    ticker: str
    roc: float = Field(description="EBIT / (NWC + NFA)")
    earnings_yield: float = Field(description="EBIT / EV")
    verdict: str = Field(description="TOP_DECILE|BON|MOYEN|EVITER")
    situations_speciales: list[str] = Field(default_factory=list)
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "GreenblattOutput":
        verdicts_valides = {"TOP_DECILE", "BON", "MOYEN", "EVITER"}
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        return self
