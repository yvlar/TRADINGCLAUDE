"""Découverte par catégorie — suggestions de qualité précalculées pour débutants.

Couche « précalculée » du design hybride (docs/design-decouverte-debutant.md) :
le rafraîchissement passe l'univers d'une catégorie au ScreenerService (analyses
cachées < 24h réutilisées), applique un gate qualité sector-aware puis persiste
les suggestions dans `discovery_suggestions` (table de référence globale, hors
RLS — mêmes listes pour tous les tenants). La lecture est instantanée et gratuite.

La phrase « pourquoi » et le badge de risque sont des templates déterministes —
aucun appel LLM dans ce service (décision §8.1 du design).
"""
from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg
from fastapi import HTTPException

from app.models.discovery import (
    CategorySummary,
    DiscoveryCategoryConfig,
    DiscoveryCategoryResponse,
    DiscoverySuggestion,
)

if TYPE_CHECKING:
    from app.services.screener import ScreenerService
    from app.skills.tier1.yahoo_finance import YahooFinanceExtractor

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "discovery_categories.json"

# Labels alignés sur composite_score.py ("FORT" ≥70, "MODÉRÉ" 45-69, "FAIBLE" <45).
_LABELS_QUALITE_OK = {"FORT", "MODÉRÉ"}


def load_categories(path: Path = _CONFIG_PATH) -> dict[str, DiscoveryCategoryConfig]:
    """Charge et valide les catégories depuis le JSON de config (id injecté depuis la clé)."""
    raw = _json.loads(path.read_text(encoding="utf-8"))
    return {
        cat_id: DiscoveryCategoryConfig(id=cat_id, **payload)
        for cat_id, payload in raw.items()
    }


def risk_badge(composite_label: str | None, niveau_risque_categorie: str) -> str:
    """Badge de risque déterministe (§4.4 du design) — jamais produit par un LLM."""
    if composite_label == "FAIBLE" or composite_label is None:
        return "élevé"
    if composite_label in _LABELS_QUALITE_OK and niveau_risque_categorie == "faible":
        return "faible"
    return "moyen"


def why_phrase(
    name: str,
    composite_label: str | None,
    composite_score: float | None,
    dividend_years: int | None,
) -> str:
    """Phrase « pourquoi » déterministe — factuelle, jamais impérative (§7 garde-fous)."""
    parts = [f"{name} : entreprise établie"]
    if composite_score is not None and composite_label is not None:
        parts.append(f"qualité {composite_label} ({composite_score:.0f}/100) selon nos filtres")
    if dividend_years is not None and dividend_years > 0:
        parts.append(f"dividende versé chaque année depuis au moins {dividend_years} ans")
    return ", ".join(parts) + "."


class DiscoveryService:
    """Lecture (instantanée) et rafraîchissement (batch) des suggestions par catégorie."""

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        screener: "ScreenerService | None" = None,
        extractor: "YahooFinanceExtractor | None" = None,
        categories: dict[str, DiscoveryCategoryConfig] | None = None,
    ) -> None:
        self._db = db_pool
        self._screener = screener
        self._extractor = extractor
        self._categories = categories if categories is not None else load_categories()

    # ------------------------------------------------------------------
    # Lecture — chemin requête (gratuit, instantané)
    # ------------------------------------------------------------------

    async def list_categories(self) -> list[CategorySummary]:
        """Métadonnées + compteur/fraîcheur par catégorie pour la grille de cartes."""
        counts: dict[str, tuple[int, datetime | None]] = {}
        rows = await self._db.fetch(
            "SELECT category, COUNT(*) AS nb, MAX(as_of) AS as_of "
            "FROM discovery_suggestions GROUP BY category"
        )
        for row in rows:
            counts[row["category"]] = (row["nb"], row["as_of"])

        summaries: list[CategorySummary] = []
        for cat in self._categories.values():
            nb, as_of = counts.get(cat.id, (0, None))
            summaries.append(
                CategorySummary(
                    id=cat.id,
                    titre=cat.titre,
                    emoji=cat.emoji,
                    description=cat.description,
                    niveau_risque=cat.niveau_risque,
                    nb_suggestions=nb,
                    as_of=as_of.isoformat() if as_of is not None else None,
                )
            )
        return summaries

    async def get_category(self, category_id: str) -> DiscoveryCategoryResponse:
        """Catégorie + suggestions persistées, triées par score décroissant. 404 si inconnue."""
        cat = self._categories.get(category_id)
        if cat is None:
            raise HTTPException(status_code=404, detail=f"Catégorie inconnue : {category_id}")

        rows = await self._db.fetch(
            "SELECT ticker, name, composite_score, composite_label, risk_badge, why, "
            "dividend_yield, dividend_years, pe, price, as_of "
            "FROM discovery_suggestions WHERE category = $1 "
            "ORDER BY composite_score DESC NULLS LAST, ticker",
            category_id,
        )
        suggestions = [
            DiscoverySuggestion(
                ticker=row["ticker"],
                name=row["name"],
                composite_score=row["composite_score"],
                composite_label=row["composite_label"],
                risk_badge=row["risk_badge"],
                why=row["why"],
                dividend_yield=row["dividend_yield"],
                dividend_years=row["dividend_years"],
                pe=row["pe"],
                price=row["price"],
                account_hint=cat.account_hint,
                as_of=row["as_of"].isoformat(),
            )
            for row in rows
        ]
        as_of = max((s.as_of for s in suggestions), default=None)
        return DiscoveryCategoryResponse(
            id=cat.id,
            titre=cat.titre,
            emoji=cat.emoji,
            description=cat.description,
            niveau_risque=cat.niveau_risque,
            account_hint=cat.account_hint,
            as_of=as_of,
            suggestions=suggestions,
        )

    # ------------------------------------------------------------------
    # Rafraîchissement — chemin batch (Celery beat, coût Claude assumé)
    # ------------------------------------------------------------------

    async def refresh_category(self, category_id: str) -> int:
        """Recalcule et remplace les suggestions d'une catégorie. Retourne le nombre persisté."""
        if self._screener is None or self._extractor is None:
            raise RuntimeError(
                "refresh_category requiert screener et extractor (chemin batch uniquement)"
            )
        cat = self._categories.get(category_id)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {category_id}")

        from app.api.endpoints.screen import ScreenRequest

        result = await self._screener.screen(
            ScreenRequest(
                tickers=[e.ticker for e in cat.univers],
                workflow=cat.workflow,
                max_parallel=3,
            )
        )
        names = {e.ticker: e.name for e in cat.univers}
        as_of = datetime.now(timezone.utc)

        suggestions: list[DiscoverySuggestion] = []
        for entry in result.resultats:
            if len(suggestions) >= cat.max_suggestions:
                break
            # Gate 1 — analyse réussie et qualité composite suffisante (§4.3 du design)
            if entry.erreur is not None:
                continue
            if entry.composite_score is None or entry.composite_score < cat.min_composite_score:
                continue
            if await self._earnings_verdict_rejete(entry.ticker):
                continue

            # Gate 2 — régularité du dividende + données d'affichage (best-effort par titre)
            try:
                graham_ratios = await self._extractor.extract(entry.ticker)
                valuation_ratios = await self._extractor.extract_valuation(entry.ticker)
            except Exception as exc:  # HTTPException 404/504 ou panne yfinance
                logger.warning(
                    "discovery : extraction impossible pour %s — exclu (%s)",
                    entry.ticker, exc,
                )
                continue
            dividend_years = graham_ratios.dividend_years
            if dividend_years is None or dividend_years < cat.min_dividend_years:
                continue

            name = names.get(entry.ticker, entry.ticker)
            suggestions.append(
                DiscoverySuggestion(
                    ticker=entry.ticker,
                    name=name,
                    composite_score=entry.composite_score,
                    composite_label=entry.composite_label,
                    risk_badge=risk_badge(entry.composite_label, cat.niveau_risque),
                    why=why_phrase(
                        name, entry.composite_label, entry.composite_score, dividend_years
                    ),
                    dividend_yield=valuation_ratios.dividend_yield,
                    dividend_years=dividend_years,
                    pe=graham_ratios.pe,
                    price=graham_ratios.price,
                    account_hint=cat.account_hint,
                    as_of=as_of.isoformat(),
                )
            )

        await self._replace_suggestions(category_id, suggestions, as_of)
        logger.info(
            "discovery : catégorie %s rafraîchie — %d suggestion(s) sur %d titre(s) screénés",
            category_id, len(suggestions), len(result.resultats),
        )
        return len(suggestions)

    async def refresh_all(self) -> dict[str, int]:
        """Rafraîchit toutes les catégories — best-effort, l'échec d'une n'avorte pas les autres."""
        counts: dict[str, int] = {}
        for category_id in self._categories:
            try:
                counts[category_id] = await self.refresh_category(category_id)
            except Exception:
                logger.exception("discovery : échec du rafraîchissement de %s", category_id)
                counts[category_id] = -1
        return counts

    async def _earnings_verdict_rejete(self, ticker: str) -> bool:
        """True si la dernière analyse porte earnings_quality.verdict=REJETER (§4.3).

        Best-effort : ligne absente ou JSON illisible → False (le composite_score,
        qui pondère déjà earnings_quality à 15 %, reste le gate principal).
        """
        try:
            row = await self._db.fetchrow(
                "SELECT result_json FROM analysis_history "
                "WHERE ticker = $1 ORDER BY created_at DESC LIMIT 1",
                ticker,
            )
            if row is None:
                return False
            payload = _json.loads(row["result_json"])
            earnings = payload.get("earnings_quality") or {}
            return earnings.get("verdict") == "REJETER"
        except Exception as exc:
            logger.warning("discovery : verdict earnings illisible pour %s (%s)", ticker, exc)
            return False

    async def _replace_suggestions(
        self,
        category_id: str,
        suggestions: list[DiscoverySuggestion],
        as_of: datetime,
    ) -> None:
        """Remplacement transactionnel — la catégorie n'est jamais visible à moitié vide."""
        async with self._db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM discovery_suggestions WHERE category = $1", category_id
                )
                await conn.executemany(
                    "INSERT INTO discovery_suggestions "
                    "(category, ticker, name, composite_score, composite_label, risk_badge, "
                    " why, dividend_yield, dividend_years, pe, price, as_of) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
                    [
                        (
                            category_id, s.ticker, s.name, s.composite_score,
                            s.composite_label, s.risk_badge, s.why, s.dividend_yield,
                            s.dividend_years, s.pe, s.price, as_of,
                        )
                        for s in suggestions
                    ],
                )
