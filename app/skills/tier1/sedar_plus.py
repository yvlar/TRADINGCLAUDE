from __future__ import annotations

import logging

import httpx

from app.skills.tier2.graham_analysis.schemas import GrahamRatios

logger = logging.getLogger(__name__)

_SEDAR_SEARCH_URL = "https://www.sedarplus.ca/csa-party/parties/party/search"


class SedarPlusExtractor:
    """
    Extrait les ratios depuis SEDAR+ (sedarplus.ca) pour les titres TSX.
    Best-effort : retourne None si le ticker n'est pas sur TSX ou si la requête échoue.
    Timeout 10s. Ne lève jamais d'exception — retourne None en cas d'erreur.
    """

    def __init__(self, timeout_s: float = 10.0) -> None:
        self._timeout_s = timeout_s

    def _is_tsx_ticker(self, ticker: str) -> bool:
        """
        Heuristique : ticker TSX se termine par .TO ou .V.
        Retourne False pour les tickers purement US (MSFT, AAPL, etc.).
        """
        upper = ticker.upper()
        return upper.endswith(".TO") or upper.endswith(".V")

    async def extract(self, ticker: str) -> GrahamRatios | None:
        """
        Retourne GrahamRatios si le ticker est sur TSX et les données disponibles.
        Retourne None (pas d'exception) si TSX non détecté ou source indisponible.
        SEDAR+ est un dépôt de documents — les ratios structurés ne sont pas disponibles
        via leur API publique. Cette méthode est best-effort pour usage futur.
        """
        if not self._is_tsx_ticker(ticker):
            return None

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                clean_ticker = ticker.upper().replace(".TO", "").replace(".V", "")
                resp = await client.get(
                    _SEDAR_SEARCH_URL,
                    params={"searchText": clean_ticker},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "SEDAR+ HTTP %d pour %s", resp.status_code, ticker
                    )
                    return None
                # SEDAR+ retourne des métadonnées de dépôts, pas des ratios financiers.
                return None
        except Exception:
            logger.warning("Erreur SEDAR+ pour %s", ticker, exc_info=True)
            return None
