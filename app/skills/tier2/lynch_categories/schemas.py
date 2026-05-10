from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class LynchRatios(BaseModel):
    pe: float
    eps_growth_5y: float
    revenue_growth_5y: float | None = None
    net_margin: float | None = None
    debt_equity: float | None = None
    fcf_yield: float | None = None
    dividend_yield: float | None = None
    capex_intensity: float | None = None


class LynchInput(BaseModel):
    ticker: str
    ratios: LynchRatios


class LynchOutput(BaseModel):
    ticker: str
    categorie: str = Field(description="SLOW_GROWER|STALWART|FAST_GROWER|CYCLICAL|TURNAROUND|ASSET_PLAY")
    peg_ratio: float | None = Field(description="pe / (eps_growth_5y * 100), null si eps_growth_5y <= 0")
    tenbagger_potential: bool = Field(description="FAST_GROWER avec PEG < 1.0")
    score_croissance: int = Field(description="Score de qualité de croissance 0-5")
    verdict: str = Field(description="EXCELLENT|BON|MOYEN|EVITER")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "LynchOutput":
        categories_valides = {"SLOW_GROWER", "STALWART", "FAST_GROWER", "CYCLICAL", "TURNAROUND", "ASSET_PLAY"}
        if self.categorie not in categories_valides:
            raise ValueError(f"categorie invalide : {self.categorie}")
        verdicts_valides = {"EXCELLENT", "BON", "MOYEN", "EVITER"}
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if not (0 <= self.score_croissance <= 5):
            raise ValueError(f"score_croissance hors plage [0,5] : {self.score_croissance}")
        if self.tenbagger_potential:
            if self.categorie != "FAST_GROWER":
                raise ValueError("tenbagger_potential=True nécessite categorie=FAST_GROWER")
            if self.peg_ratio is None or self.peg_ratio >= 1.0:
                raise ValueError("tenbagger_potential=True nécessite peg_ratio < 1.0")
        return self
