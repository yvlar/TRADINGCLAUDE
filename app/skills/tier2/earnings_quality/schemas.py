from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator

from app.skills.base import Citation
from app.utils.numeric_validation import FiniteFloatOrNone, valider_borne_plausible

# Bornes de plausibilité larges — au-delà, la valeur est invraisemblable et trahit une sortie LLM erronée.
# Altman Z réel ~[-5, 15] ; Beneish M réel ~[-5, 2] (cf. .claude/skills/earnings-quality-fraud-detection/references/).
_Z_SCORE_BORNE = 50.0
_M_SCORE_BORNE = 20.0


class EarningsQualityRatios(BaseModel):
    """
    Données des états financiers sur deux exercices (T = courant, t1 = exercice précédent).
    Toutes les valeurs monétaires dans la devise du titre (pas normalisées).
    """

    # Compte de résultat
    sales_t: float
    sales_t1: float
    cogs_t: float
    cogs_t1: float
    net_income_t: float
    cfo_t: float
    ebit_t: float | None = None
    sga_t: float | None = None
    sga_t1: float | None = None
    depreciation_t: float | None = None
    depreciation_t1: float | None = None

    # Bilan T
    receivables_t: float
    current_assets_t: float
    current_liabilities_t: float
    total_assets_t: float
    inventory_t: float | None = None
    ppe_net_t: float | None = None
    ppe_gross_t: float | None = None
    ltd_t: float | None = None
    retained_earnings_t: float | None = None
    total_liabilities_t: float | None = None
    market_cap_t: float | None = None
    book_equity_t: float | None = None

    # Bilan T-1
    receivables_t1: float
    total_assets_t1: float
    current_assets_t1: float | None = None
    current_liabilities_t1: float | None = None
    inventory_t1: float | None = None
    ppe_net_t1: float | None = None
    ppe_gross_t1: float | None = None
    ltd_t1: float | None = None

    # Capital
    shares_issued_net: bool | None = None


class GrahamContext(BaseModel):
    """Résumé du verdict Graham passé en contexte à earnings_quality (context enrichment)."""

    verdict: str
    defensive_score: int
    marge_securite: float | None
    drapeaux_rouges: list[str]


class EarningsQualityInput(BaseModel):
    """Input du skill earnings_quality."""

    ticker: str
    ratios: EarningsQualityRatios
    graham_context: GrahamContext | None = None


class MScoreDetail(BaseModel):
    dsri: FiniteFloatOrNone
    gmi: FiniteFloatOrNone
    aqi: FiniteFloatOrNone
    sgi: FiniteFloatOrNone
    depi: FiniteFloatOrNone
    sgai: FiniteFloatOrNone
    tata: FiniteFloatOrNone
    lvgi: FiniteFloatOrNone
    m_score: FiniteFloatOrNone
    interpretation: str

    @model_validator(mode="after")
    def valider_plausibilite(self) -> "MScoreDetail":
        valider_borne_plausible(self.m_score, _M_SCORE_BORNE, "m_score")
        return self


class ZScoreDetail(BaseModel):
    variante: str
    z_score: FiniteFloatOrNone
    interpretation: str

    @model_validator(mode="after")
    def valider_plausibilite(self) -> "ZScoreDetail":
        valider_borne_plausible(self.z_score, _Z_SCORE_BORNE, "z_score")
        return self


class FScoreCriterion(BaseModel):
    nom: str
    passe: bool
    detail: str


class FScoreDetail(BaseModel):
    criteria: list[FScoreCriterion]
    f_score: int = Field(ge=0, le=9)
    interpretation: str


class CScoreSignal(BaseModel):
    nom: str
    present: bool
    detail: str


class CScoreDetail(BaseModel):
    signaux: list[CScoreSignal]
    c_score: int = Field(ge=0, le=6)
    interpretation: str


class SloanDetail(BaseModel):
    accrual_ratio: FiniteFloatOrNone
    interpretation: str


class EarningsQualityOutput(BaseModel):
    ticker: str
    is_financial: bool = Field(False, description="Banque/assureur — certains scores inapplicables")
    m_score: MScoreDetail
    z_score: ZScoreDetail
    f_score: FScoreDetail
    c_score: CScoreDetail
    sloan: SloanDetail
    drapeaux_rouges: list[str]
    verdict: str = Field(description="AUCUN_SIGNAL | ATTENTION | WATCHLIST | REJETER")
    verdict_detail: str
    recommandation_prochaine_etape: list[str]
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = 0.0

    @computed_field
    @property
    def confidence_score(self) -> float:
        """Fraction des 5 cadres analytiques calculables (score non-None)."""
        cadres = [
            self.m_score.m_score is not None,
            self.z_score.z_score is not None,
            True,  # f_score : toujours calculable (int ge=0 le=9)
            True,  # c_score : toujours calculable (int ge=0 le=6)
            self.sloan.accrual_ratio is not None,
        ]
        return round(sum(1 for c in cadres if c) / len(cadres), 2)

    @model_validator(mode="after")
    def valider_comptes_cadres(self) -> "EarningsQualityOutput":
        if len(self.f_score.criteria) != 9:
            raise ValueError(
                f"f_score.criteria : attendu 9, reçu {len(self.f_score.criteria)}"
            )
        if len(self.c_score.signaux) != 6:
            raise ValueError(
                f"c_score.signaux : attendu 6, reçu {len(self.c_score.signaux)}"
            )
        if self.verdict not in {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}:
            raise ValueError(f"verdict invalide : {self.verdict}")
        return self
