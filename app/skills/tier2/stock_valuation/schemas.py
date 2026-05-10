from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class ValuationRatios(BaseModel):
    price: float | None = None
    eps_ttm: float | None = None
    eps_growth_5y: float | None = None
    eps_growth_10y: float | None = None
    book_value: float | None = None
    revenue_bn: float | None = None
    revenue_growth_5y: float | None = None
    free_cash_flow_bn: float | None = None
    roic: float | None = None
    roe: float | None = None
    net_margin: float | None = None
    debt_equity: float | None = None
    pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    dividend_yield: float | None = None
    shares_outstanding_m: float | None = None
    sector: str | None = None
    wacc: float | None = None
    terminal_growth_rate: float | None = None


class GrahamContext(BaseModel):
    """Résumé graham_analysis passé en contexte."""

    verdict: str
    defensive_score: int
    marge_securite: float | None
    valeur_intrinseque_simple: float | None


class EarningsContext(BaseModel):
    """Résumé earnings_quality passé en contexte."""

    verdict: str
    z_score: float | None
    f_score: int | None


class DorseyContext(BaseModel):
    """Résumé dorsey_moat passé en contexte."""

    moat_type: str
    roic_durability: str


class BuffettContext(BaseModel):
    """Résumé buffett_quality passé en contexte."""

    quality_score: int
    verdict: str
    owner_earnings: float | None


class StockValuationInput(BaseModel):
    ticker: str
    ratios: ValuationRatios
    graham_context: GrahamContext | None = None
    earnings_context: EarningsContext | None = None
    dorsey_context: DorseyContext | None = None
    buffett_context: BuffettContext | None = None


class ValuationMethod(BaseModel):
    methode: str  # "dcf" | "comparables" | "sectoriel"
    valeur: float | None
    hypotheses: str


class SensitivityMatrix(BaseModel):
    wacc_range: list[float]
    growth_range: list[float]
    values: list[list[float]]


class StockValuationOutput(BaseModel):
    ticker: str
    methodes: list[ValuationMethod]  # exactement 3 éléments
    fourchette_basse: float
    fourchette_centrale: float
    fourchette_haute: float
    marge_securite_composite: float
    matrice_sensibilite: SensitivityMatrix
    verdict: str  # "SOUS_EVALUE" | "JUSTE_VALEUR" | "SUREVALUE"
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @model_validator(mode="after")
    def valider_output(self) -> "StockValuationOutput":
        if len(self.methodes) != 3:
            raise ValueError(f"methodes : attendu 3, reçu {len(self.methodes)}")
        valid_verdicts = {"SOUS_EVALUE", "JUSTE_VALEUR", "SUREVALUE"}
        if self.verdict not in valid_verdicts:
            raise ValueError(f"verdict invalide : {self.verdict}")
        if self.fourchette_basse > self.fourchette_centrale:
            raise ValueError("fourchette_basse doit être ≤ fourchette_centrale")
        if self.fourchette_centrale > self.fourchette_haute:
            raise ValueError("fourchette_centrale doit être ≤ fourchette_haute")
        n_wacc = len(self.matrice_sensibilite.wacc_range)
        n_growth = len(self.matrice_sensibilite.growth_range)
        if len(self.matrice_sensibilite.values) != n_wacc:
            raise ValueError("matrice_sensibilite.values : lignes != len(wacc_range)")
        for row in self.matrice_sensibilite.values:
            if len(row) != n_growth:
                raise ValueError("matrice_sensibilite.values : colonnes != len(growth_range)")
        return self
