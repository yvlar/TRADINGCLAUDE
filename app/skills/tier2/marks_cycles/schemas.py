from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class MarksRatios(BaseModel):
    pe_market: float | None = None
    vix: float | None = None
    credit_spreads_bps: float | None = None
    insider_net_buying: float | None = None
    bullish_sentiment_pct: float | None = None


class MarksInput(BaseModel):
    market_context: str
    marks_ratios: MarksRatios


class MarksOutput(BaseModel):
    position_cycle: str = Field(
        description="PESSIMISME_EXCESSIF|PESSIMISME|NEUTRE|OPTIMISME|EUPHORIE"
    )
    pendule_score: int = Field(description="Score du pendule -5 à +5, négatif = opportunité contrariante")
    second_level_insight: str
    recommandation_timing: str = Field(
        description="ACHETER_AGRESSIF|ACHETER_PRUDEMMENT|ATTENDRE|REDUIRE|VENDRE"
    )
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "MarksOutput":
        positions_valides = {
            "PESSIMISME_EXCESSIF",
            "PESSIMISME",
            "NEUTRE",
            "OPTIMISME",
            "EUPHORIE",
        }
        if self.position_cycle not in positions_valides:
            raise ValueError(f"position_cycle invalide : {self.position_cycle}")
        timings_valides = {
            "ACHETER_AGRESSIF",
            "ACHETER_PRUDEMMENT",
            "ATTENDRE",
            "REDUIRE",
            "VENDRE",
        }
        if self.recommandation_timing not in timings_valides:
            raise ValueError(f"recommandation_timing invalide : {self.recommandation_timing}")
        if not (-5 <= self.pendule_score <= 5):
            raise ValueError(
                f"pendule_score hors plage [-5, 5] : {self.pendule_score}"
            )
        return self
