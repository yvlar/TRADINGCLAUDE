from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class DamodararRatios(BaseModel):
    revenue_bn: float
    revenue_growth_5y: float
    net_margin: float
    roic: float
    tam_bn: float | None = None
    market_share_pct: float | None = None
    sector: str | None = None


class DamodararInput(BaseModel):
    ticker: str
    narrative_text: str
    damodaran_ratios: DamodararRatios


class DamodararOutput(BaseModel):
    ticker: str
    test_coherence: str = Field(description="POSSIBLE|PLAUSIBLE|PROBABLE|INCOHERENT")
    erp_implied: float | None = Field(description="ERP implicite estimé")
    narrative_strength: int = Field(description="Score de solidité de la narrative 0-10")
    divergences_detectees: list[str] = Field(default_factory=list)
    verdict: str = Field(description="NARRATIVE_FORTE|NARRATIVE_ACCEPTABLE|NARRATIVE_FAIBLE|NARRATIVE_INCOHERENTE")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "DamodararOutput":
        coherences_valides = {"POSSIBLE", "PLAUSIBLE", "PROBABLE", "INCOHERENT"}
        if self.test_coherence not in coherences_valides:
            raise ValueError(f"test_coherence invalide : {self.test_coherence}")
        verdicts_valides = {
            "NARRATIVE_FORTE",
            "NARRATIVE_ACCEPTABLE",
            "NARRATIVE_FAIBLE",
            "NARRATIVE_INCOHERENTE",
        }
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if not (0 <= self.narrative_strength <= 10):
            raise ValueError(
                f"narrative_strength hors plage [0,10] : {self.narrative_strength}"
            )
        return self
