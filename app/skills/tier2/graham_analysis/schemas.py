from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation


class GrahamRatios(BaseModel):
    """Ratios financiers fournis manuellement par l'utilisateur en Phase 0."""

    pe: float = Field(description="Price/Earnings ratio (cours / BPA)")
    pb: float = Field(description="Price/Book ratio (cours / valeur comptable par action)")
    current_ratio: float | None = Field(None, description="Actif circulant / Passif circulant (None pour les banques)")
    debt_equity: float = Field(description="Dette totale / Capitaux propres")
    eps_growth_10y: float = Field(
        description="Croissance totale du BPA sur 10 ans, format fraction (0.85 = 85 % total)"
    )
    price: float = Field(description="Cours actuel de l'action")
    book_value: float = Field(description="Valeur comptable par action (book value per share)")
    eps_ttm: float | None = Field(None, description="BPA des 12 derniers mois. Calculé price/pe si absent.")
    revenue_bn: float | None = Field(None, description="Revenus annuels en milliards de la devise du titre")
    dividend_years: int | None = Field(None, description="Nombre d'années consécutives de dividendes versés")
    no_deficit_years: int | None = Field(None, description="Nombre d'années sans déficit sur les dernières années")


class GrahamAnalysisInput(BaseModel):
    """Input du skill graham_analysis — correspond au body du POST /analyze."""

    ticker: str = Field(description="Symbole boursier (ex: MSFT, BNS.TO)")
    ratios: GrahamRatios


class GrahamCriterion(BaseModel):
    """Évaluation d'un critère Graham individuel."""

    numero: int = Field(description="Numéro du critère (1-8 pour défensif, 1-5 pour entreprenant)")
    nom: str = Field(description="Nom court du critère")
    passe: bool = Field(description="True si le critère est satisfait")
    valeur_observee: str = Field(description="Valeur constatée depuis les ratios, ou DONNÉES_MANQUANTES")
    seuil: str = Field(description="Seuil Graham applicable")
    commentaire: str = Field(description="Explication concise du résultat")


class GrahamAnalysisOutput(BaseModel):
    """Résultat complet du skill graham_analysis produit par Claude (section 11.2)."""

    ticker: str
    profil_applique: str = Field(description="Toujours LES_DEUX en Phase 0")
    defensive_score: int = Field(ge=0, le=8, description="Critères défensifs satisfaits sur 8")
    enterprising_score: int = Field(ge=0, le=5, description="Critères entrepreneuriaux satisfaits sur 5")
    criteria_defensif: list[GrahamCriterion] = Field(description="Les 8 critères défensifs évalués")
    criteria_entreprenant: list[GrahamCriterion] = Field(description="Les 5 critères entrepreneuriaux évalués")
    valeur_intrinseque_simple: float | None = Field(
        None, description="V = BPA × (8.5 + 2g). Null si BPA incalculable."
    )
    valeur_intrinseque_ajustee: float | None = Field(
        None, description="V = BPA × (8.5 + 2g) × (4.4/Y). Null si BPA incalculable."
    )
    marge_securite: float | None = Field(
        None, description="(V_ajustée - prix) / V_ajustée. Positif = sous-évalué."
    )
    drapeaux_rouges: list[str] = Field(description="Drapeaux rouges identifiés depuis les ratios")
    verdict: str = Field(description="REJETER | WATCHLIST | CANDIDAT_SOLIDE | EXEMPLAIRE")
    verdict_detail: str = Field(description="Explication narrative du verdict en 2-3 phrases")
    recommandation_prochaine_etape: list[str] = Field(
        description="Skills recommandés pour la suite de l'analyse"
    )
    citations: list[Citation] = Field(default_factory=list, description="Citations RAG — vide si OPENAI_API_KEY absente")
    cost_usd: float = Field(default=0.0, description="Coût API Claude de cet appel en USD")

    @model_validator(mode="after")
    def valider_comptes_criteres(self) -> "GrahamAnalysisOutput":
        if len(self.criteria_defensif) != 8:
            raise ValueError(
                f"criteria_defensif : attendu 8 critères, reçu {len(self.criteria_defensif)}"
            )
        if len(self.criteria_entreprenant) != 5:
            raise ValueError(
                f"criteria_entreprenant : attendu 5 critères, reçu {len(self.criteria_entreprenant)}"
            )
        return self
