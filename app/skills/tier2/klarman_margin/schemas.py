from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class KlarmanRatios(BaseModel):
    price: float
    nav_per_share: float | None = None
    liquidation_value: float | None = None
    debt_equity: float | None = None
    revenue_bn: float | None = None
    catalyst: str | None = None


class KlarmanInput(BaseModel):
    ticker: str
    situation_type: str
    klarman_ratios: KlarmanRatios


class KlarmanOutput(BaseModel):
    ticker: str
    situation_type_qualifie: str = Field(
        description="NET_NET|ACTIFS_CACHES|DISTRESSED|SPECIAL_SITUATION|VALEUR_CLASSIQUE"
    )
    marge_securite_score: int = Field(ge=0, le=10, description="Score 0-10")
    preservation_capital_score: int = Field(ge=0, le=10, description="Score 0-10")
    discount_to_intrinsic: float | None = None
    verdict: str = Field(description="OPPORTUNITE_FORTE|OPPORTUNITE_MODEREE|ATTENDRE|PASSER")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "KlarmanOutput":
        types_valides = {"NET_NET", "ACTIFS_CACHES", "DISTRESSED", "SPECIAL_SITUATION", "VALEUR_CLASSIQUE"}
        if self.situation_type_qualifie not in types_valides:
            raise ValueError(f"situation_type_qualifie invalide : {self.situation_type_qualifie}")
        verdicts_valides = {"OPPORTUNITE_FORTE", "OPPORTUNITE_MODEREE", "ATTENDRE", "PASSER"}
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if not (0 <= self.marge_securite_score <= 10):
            raise ValueError(f"marge_securite_score hors plage [0,10] : {self.marge_securite_score}")
        if not (0 <= self.preservation_capital_score <= 10):
            raise ValueError(
                f"preservation_capital_score hors plage [0,10] : {self.preservation_capital_score}"
            )
        return self
