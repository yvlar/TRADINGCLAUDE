from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class DorseyRatios(BaseModel):
    roic: float | None = None
    roic_5y_avg: float | None = None
    gross_margin: float | None = None
    gross_margin_5y_avg: float | None = None
    operating_margin: float | None = None
    revenue_bn: float | None = None
    market_share_pct: float | None = None
    customer_retention_pct: float | None = None
    switching_cost_proxy: str | None = None
    brand_value_bn: float | None = None
    network_users_m: float | None = None
    cost_advantage_source: str | None = None


class EarningsContext(BaseModel):
    """Résumé earnings_quality passé en contexte (context enrichment)."""

    verdict: str
    z_score: float | None
    m_score: float | None
    f_score: int | None
    drapeaux_rouges: list[str]


class DorseyMoatInput(BaseModel):
    ticker: str
    ratios: DorseyRatios
    earnings_context: EarningsContext | None = None


class MoatSource(BaseModel):
    source: str  # "intangibles" | "switching_costs" | "network_effects" | "cost_advantages" | "efficient_scale"
    present: bool
    intensite: str  # "FORTE" | "MODÉRÉE" | "FAIBLE" | "ABSENTE"
    justification: str


class DorseyMoatOutput(BaseModel):
    ticker: str
    moat_type: str  # "WIDE" | "NARROW" | "NONE"
    sources_identifiees: list[MoatSource]  # exactement 5 éléments
    roic_durability: str  # "FORTE" | "MODÉRÉE" | "FAIBLE"
    verdict_detail: str
    drapeaux_rouges: list[str]
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0
    confidence_score: float = Field(
        default=0.0,
        description="Fraction des champs DorseyRatios fournis — calculé dans execute(), jamais via prompt.",
    )

    @model_validator(mode="after")
    def valider_sources(self) -> "DorseyMoatOutput":
        if len(self.sources_identifiees) != 5:
            raise ValueError(
                f"sources_identifiees : attendu 5, reçu {len(self.sources_identifiees)}"
            )
        valid_moat = {"WIDE", "NARROW", "NONE"}
        if self.moat_type not in valid_moat:
            raise ValueError(f"moat_type invalide : {self.moat_type}")
        valid_durability = {"FORTE", "MODÉRÉE", "FAIBLE"}
        if self.roic_durability not in valid_durability:
            raise ValueError(f"roic_durability invalide : {self.roic_durability}")
        return self
