from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class FisherAnswer(BaseModel):
    point: int = Field(ge=1, le=15)
    score: int = Field(ge=0, le=2)
    commentaire: str


class FisherInput(BaseModel):
    ticker: str
    fisher_answers: list[FisherAnswer] = Field(min_length=15, max_length=15)
    contexte_qualitatif: str | None = None


class FisherPoint(BaseModel):
    point: int = Field(ge=1, le=15)
    titre: str
    score: int = Field(ge=0, le=2)
    commentaire: str


class FisherOutput(BaseModel):
    ticker: str
    fisher_score: int = Field(ge=0, le=30, description="Somme des 15 scores (0-30)")
    points_evalues: list[FisherPoint] = Field(description="Exactement 15 éléments")
    management_quality: str = Field(description="EXCEPTIONNEL|BON|ADEQUAT|MEDIOCRE")
    verdict: str = Field(description="ACHAT_FORT|ACHAT|CONSERVER|EVITER")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "FisherOutput":
        if len(self.points_evalues) != 15:
            raise ValueError(
                f"points_evalues doit contenir exactement 15 éléments, got {len(self.points_evalues)}"
            )
        if not (0 <= self.fisher_score <= 30):
            raise ValueError(f"fisher_score hors plage [0,30] : {self.fisher_score}")
        mq_valides = {"EXCEPTIONNEL", "BON", "ADEQUAT", "MEDIOCRE"}
        if self.management_quality not in mq_valides:
            raise ValueError(f"management_quality invalide : {self.management_quality}")
        verdicts_valides = {"ACHAT_FORT", "ACHAT", "CONSERVER", "EVITER"}
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        return self
