from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.skills.base import Citation

_logger = logging.getLogger(__name__)


class EsgInput(BaseModel):
    """Input du skill esg_simplified — données proxy extraites de Yahoo Finance ou fournies manuellement."""

    ticker: str = Field(description="Symbole boursier (ex: BNS.TO, MSFT)")
    sector: str | None = Field(None, description="Secteur Yahoo Finance (ex: 'Financial Services', 'Technology')")
    revenue_bn: float | None = Field(None, description="Revenus annuels en milliards")
    roe: float | None = Field(None, description="Return on Equity (fraction : 0.15 = 15%)")
    debt_equity: float | None = Field(None, description="Dette totale / Capitaux propres")
    dividend_years: int | None = Field(None, description="Nombre d'années consécutives de dividendes versés")
    eps_growth_10y: float | None = Field(
        None, description="Croissance totale BPA sur 10 ans (fraction : 0.85 = 85%)"
    )


class EsgCritere(BaseModel):
    """Évaluation d'un critère ESG individuel avec proxy financier explicite."""

    dimension: Literal["E", "S", "G"] = Field(description="Dimension ESG : Environnement, Social ou Gouvernance")
    nom: str = Field(description="Nom court du critère (ex: 'Efficience du capital')")
    passe: bool = Field(description="True si le critère proxy est satisfait")
    observation: str = Field(
        description="Constat factuel basé sur les données disponibles (1-2 phrases)"
    )
    proxy_utilise: str = Field(
        description="Donnée financière servant de proxy ESG (ex: 'debt_equity', 'roe', 'dividend_years')"
    )


class EsgOutput(BaseModel):
    """Résultat complet du skill esg_simplified produit par Claude via Tool Use."""

    ticker: str
    esg_score: int = Field(ge=0, le=15, description="Score ESG global : somme des 15 critères passés (0-15)")
    e_score: int = Field(ge=0, le=5, description="Score Environnement : 0-5 critères passés")
    s_score: int = Field(ge=0, le=5, description="Score Social : 0-5 critères passés")
    g_score: int = Field(ge=0, le=5, description="Score Gouvernance : 0-5 critères passés")
    criteres: list[EsgCritere] = Field(description="Exactement 15 critères ESG évalués (5E + 5S + 5G)")
    verdict: Literal["ESG_FORT", "ESG_MODERE", "ESG_FAIBLE"] = Field(
        description="ESG_FORT si score>=10, ESG_MODERE si 5-9, ESG_FAIBLE si <=4"
    )
    verdict_detail: str = Field(description="Explication narrative du verdict en 2-3 phrases")
    limites: list[str] = Field(
        description="Limites importantes de l'analyse — proxy imparfait, données manquantes, secteur atypique"
    )
    citations: list[Citation] = Field(default_factory=list, description="Citations RAG — vide si OPENAI_API_KEY absente")
    cost_usd: float = Field(default=0.0, description="Coût API Claude de cet appel en USD")

    @model_validator(mode="after")
    def valider_criteres(self) -> "EsgOutput":
        if len(self.criteres) != 15:
            raise ValueError(
                f"criteres : attendu exactement 15 critères (5E+5S+5G), reçu {len(self.criteres)}"
            )
        e_count = sum(1 for c in self.criteres if c.dimension == "E")
        s_count = sum(1 for c in self.criteres if c.dimension == "S")
        g_count = sum(1 for c in self.criteres if c.dimension == "G")
        if e_count != 5:
            raise ValueError(f"Attendu 5 critères E, reçu {e_count}")
        if s_count != 5:
            raise ValueError(f"Attendu 5 critères S, reçu {s_count}")
        if g_count != 5:
            raise ValueError(f"Attendu 5 critères G, reçu {g_count}")

        computed_e = sum(1 for c in self.criteres if c.dimension == "E" and c.passe)
        computed_s = sum(1 for c in self.criteres if c.dimension == "S" and c.passe)
        computed_g = sum(1 for c in self.criteres if c.dimension == "G" and c.passe)
        if self.e_score != computed_e:
            _logger.warning(
                "EsgOutput: e_score=%d != calculé=%d — correction automatique",
                self.e_score, computed_e,
            )
            object.__setattr__(self, "e_score", computed_e)
        if self.s_score != computed_s:
            _logger.warning(
                "EsgOutput: s_score=%d != calculé=%d — correction automatique",
                self.s_score, computed_s,
            )
            object.__setattr__(self, "s_score", computed_s)
        if self.g_score != computed_g:
            _logger.warning(
                "EsgOutput: g_score=%d != calculé=%d — correction automatique",
                self.g_score, computed_g,
            )
            object.__setattr__(self, "g_score", computed_g)

        computed_total = computed_e + computed_s + computed_g
        if self.esg_score != computed_total:
            _logger.warning(
                "EsgOutput: esg_score=%d != calculé=%d — correction automatique",
                self.esg_score, computed_total,
            )
            object.__setattr__(self, "esg_score", computed_total)

        return self
