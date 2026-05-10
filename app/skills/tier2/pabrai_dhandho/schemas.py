from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class PabraiRatios(BaseModel):
    price: float
    intrinsic_value_low: float
    intrinsic_value_high: float
    downside_pct: float
    upside_pct: float
    debt_equity: float
    fcf_yield: float
    business_quality_score: int = Field(ge=0, le=10)


class PabraiInput(BaseModel):
    ticker: str
    pabrai_ratios: PabraiRatios
    cloning_source: str | None = None


class DhandhoPrincipe(BaseModel):
    nom: str
    satisfait: bool
    commentaire: str


class PabraiOutput(BaseModel):
    ticker: str
    principes_dhandho: list[DhandhoPrincipe] = Field(description="Exactement 9 éléments")
    heads_i_win_score: int = Field(description="Score 0-9 (nombre de principes satisfaits)")
    asymetrie: float = Field(description="upside / abs(downside), >= 0")
    kelly_fractionnel: float | None = Field(description="Kelly / 4, ou null si non calculable")
    verdict: str = Field(description="DHANDHO_FORT|DHANDHO_MOYEN|PAS_DHANDHO")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "PabraiOutput":
        if len(self.principes_dhandho) != 9:
            raise ValueError(
                f"principes_dhandho doit contenir exactement 9 éléments, "
                f"reçu {len(self.principes_dhandho)}"
            )
        verdicts_valides = {"DHANDHO_FORT", "DHANDHO_MOYEN", "PAS_DHANDHO"}
        if self.verdict not in verdicts_valides:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if self.asymetrie < 0:
            raise ValueError(f"asymetrie doit être >= 0, reçu {self.asymetrie}")
        if not (0 <= self.heads_i_win_score <= 9):
            raise ValueError(
                f"heads_i_win_score hors plage [0,9] : {self.heads_i_win_score}"
            )
        return self
