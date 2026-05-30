from __future__ import annotations

import logging

from pydantic import BaseModel, Field, computed_field, model_validator

from app.skills.base import Citation
from app.utils.numeric_validation import FiniteFloatOrNone

_logger = logging.getLogger(__name__)


class GrahamRatios(BaseModel):
    """Ratios financiers fournis manuellement par l'utilisateur en Phase 0."""

    pe: float | None = Field(None, description="Price/Earnings ratio (cours / BPA). None si société déficitaire sans BPA publiable.")
    pb: float = Field(description="Price/Book ratio (cours / valeur comptable par action)")
    current_ratio: float | None = Field(None, description="Actif circulant / Passif circulant (None pour les banques)")
    debt_equity: float = Field(description="Dette totale / Capitaux propres")
    eps_growth_total: float = Field(
        description="Croissance totale du BPA sur l'horizon réellement disponible (voir eps_growth_years, souvent ~4 ans — PAS 10). Format fraction (0.85 = 85 % total sur la période)"
    )
    eps_growth_years: int | None = Field(
        None,
        description="Nombre d'années réellement couvertes par eps_growth_total. None si horizon inconnu (donnée absente ou repli de source).",
    )
    price: float = Field(description="Cours actuel de l'action")
    book_value: float = Field(description="Valeur comptable par action (book value per share)")
    eps_ttm: float | None = Field(None, description="BPA des 12 derniers mois. Calculé price/pe si absent.")
    revenue_bn: float | None = Field(None, description="Revenus annuels en milliards de la devise du titre")
    dividend_years: int | None = Field(None, description="Nombre d'années consécutives de dividendes versés")
    no_deficit_years: int | None = Field(None, description="Nombre d'années sans déficit sur les dernières années")

    @model_validator(mode="after")
    def valider_coherence_ratios(self) -> "GrahamRatios":
        """Détecte les incohérences financières — WARNING uniquement, jamais d'exception."""
        if self.pe is not None and self.pe < 0:
            _logger.warning(
                "GrahamRatios: P/E négatif (pe=%.2f) — déficit ou BPA négatif", self.pe
            )

        if self.pb < 0:
            _logger.warning(
                "GrahamRatios: P/B négatif (pb=%.2f) — valeur comptable négative (cas extrême)", self.pb
            )

        if self.eps_growth_total > 5.0:
            _logger.warning(
                "GrahamRatios: eps_growth_total=%.2f suspect (> 500%% de croissance sur la période)",
                self.eps_growth_total,
            )

        # Triangle pe / price / eps_ttm
        if (
            self.pe is not None
            and self.eps_ttm is not None
            and self.price is not None
            and self.eps_ttm != 0
            and abs(self.pe) > 0.01
        ):
            pe_calcule = self.price / self.eps_ttm
            ecart = abs(pe_calcule - self.pe) / abs(self.pe)
            if ecart > 0.50:
                _logger.warning(
                    "GrahamRatios: incohérence P/E forte — fourni=%.1f, calculé=%.1f (écart %.0f%%)",
                    self.pe, pe_calcule, ecart * 100,
                )
            elif ecart > 0.15:
                _logger.warning(
                    "GrahamRatios: incohérence P/E — fourni=%.1f, calculé=%.1f (écart %.0f%%)",
                    self.pe, pe_calcule, ecart * 100,
                )

        return self


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
    enterprising_score: int = Field(ge=0, le=5, description="Critères entrepreneuriaux satisfaits sur 5")
    criteria_defensif: list[GrahamCriterion] = Field(description="Les 8 critères défensifs évalués")
    criteria_entreprenant: list[GrahamCriterion] = Field(description="Les 5 critères entrepreneuriaux évalués")

    @computed_field
    @property
    def defensive_score(self) -> int:
        """Décompte déterministe des critères défensifs satisfaits — jamais via prompt."""
        return sum(1 for c in self.criteria_defensif if c.passe)
    valeur_intrinseque_simple: float | None = Field(
        None, description="V = BPA × (8.5 + 2g). Null si BPA incalculable."
    )
    valeur_intrinseque_ajustee: float | None = Field(
        None, description="V = BPA × (8.5 + 2g) × (4.4/Y). Null si BPA incalculable."
    )
    marge_securite: float | None = Field(
        None, description="(V_ajustée - prix) / V_ajustée. Positif = sous-évalué."
    )
    graham_number: FiniteFloatOrNone = Field(
        None,
        description="√(22.5 × BPA × valeur comptable) — calculé en Python (Sprint 128), jamais par le LLM. Null si BPA/BVPS ≤ 0 ou absent.",
    )
    drapeaux_rouges: list[str] = Field(description="Drapeaux rouges identifiés depuis les ratios")
    verdict: str = Field(description="REJETER | WATCHLIST | CANDIDAT_SOLIDE | EXEMPLAIRE")
    verdict_detail: str = Field(description="Explication narrative du verdict en 2-3 phrases")
    recommandation_prochaine_etape: list[str] = Field(
        description="Skills recommandés pour la suite de l'analyse"
    )
    citations: list[Citation] = Field(default_factory=list, description="Citations RAG — vide si OPENAI_API_KEY absente")
    cost_usd: float = Field(default=0.0, description="Coût API Claude de cet appel en USD")

    @computed_field
    @property
    def defensive_verdict(self) -> str:
        """
        Verdict de scoring pur dérivé du defensive_score — jamais via prompt.
        Seuils : PASSE ≥ 6, BORDERLINE 4-5, REJETER ≤ 3.
        Utilisé comme cible stable dans le golden dataset des evals.
        """
        if self.defensive_score >= 6:
            return "PASSE"
        if self.defensive_score >= 4:
            return "BORDERLINE"
        return "REJETER"

    @computed_field
    @property
    def confidence_score(self) -> float:
        """Fraction des critères Graham avec données réelles (valeur_observee != DONNÉES_MANQUANTES)."""
        all_criteria = self.criteria_defensif + self.criteria_entreprenant
        if not all_criteria:
            return 0.0
        evaluables = sum(1 for c in all_criteria if c.valeur_observee != "DONNÉES_MANQUANTES")
        return round(evaluables / len(all_criteria), 2)

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
