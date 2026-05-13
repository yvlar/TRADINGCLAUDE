from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class BuffettRatios(BaseModel):
    roe: float | None = None
    roe_5y_avg: float | None = None
    roic: float | None = None
    roic_5y_avg: float | None = None
    net_margin: float | None = None
    net_margin_5y_avg: float | None = None
    revenue_growth_5y: float | None = None
    eps_growth_5y: float | None = None
    debt_equity: float | None = None
    free_cash_flow_bn: float | None = None
    capex_bn: float | None = None
    maintenance_capex_bn: float | None = None
    depreciation_bn: float | None = None
    eps_ttm: float | None = None
    revenue_bn: float | None = None
    pe: float | None = None
    price: float | None = None
    management_quality_proxy: str | None = None
    business_understandability: str | None = None


class DorseyContext(BaseModel):
    """Résumé dorsey_moat passé en contexte (context enrichment)."""

    moat_type: str
    sources: list[str]
    roic_durability: str


class BuffettQualityInput(BaseModel):
    ticker: str
    ratios: BuffettRatios
    dorsey_context: DorseyContext | None = None


class BuffettFiltre(BaseModel):
    filtre: str
    passe: bool
    score: int
    justification: str


class BuffettQualityOutput(BaseModel):
    ticker: str
    filtres: list[BuffettFiltre]
    owner_earnings: float | None
    quality_score: int
    verdict: str
    verdict_detail: str
    drapeaux_rouges: list[str]
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0
    confidence_score: float = Field(
        default=0.0,
        description="Fraction des champs BuffettRatios fournis — calculé dans execute(), jamais via prompt.",
    )

    @model_validator(mode="after")
    def valider_output(self) -> "BuffettQualityOutput":
        if len(self.filtres) != 4:
            raise ValueError(
                f"filtres : attendu 4, reçu {len(self.filtres)}"
            )
        valid_verdicts = {"COMPOUNDER", "QUALITE_CORRECTE", "REJETER"}
        if self.verdict not in valid_verdicts:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if not (0 <= self.quality_score <= 4):
            raise ValueError(f"quality_score hors plage [0,4] : {self.quality_score}")
        return self
