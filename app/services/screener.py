from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.services.analysis_cache import AnalysisCacheService
from app.skills.tier1.yahoo_finance import YahooFinanceExtractor

if TYPE_CHECKING:
    from app.api.endpoints.screen import ScreenEntry, ScreenRequest, ScreenResult

logger = logging.getLogger(__name__)

_TIMEOUT_TICKER_S: float = 30.0
_TIMEOUT_GLOBAL_S: float = 120.0


class ScreenerService:
    """
    Analyse une liste de tickers en parallèle (asyncio.Semaphore) et les classe par score.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        extractor: YahooFinanceExtractor,
        cache: AnalysisCacheService | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._extractor = extractor
        self._cache = cache

    async def screen(self, request: ScreenRequest) -> ScreenResult:
        from app.api.endpoints.screen import ScreenEntry, ScreenResult

        start = time.monotonic()
        # Déduplication silencieuse — préserve l'ordre d'insertion
        tickers = list(dict.fromkeys(request.tickers))

        semaphore = asyncio.Semaphore(request.max_parallel)
        tasks = [self._analyze_one(t, request, semaphore) for t in tickers]

        try:
            raw = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=_TIMEOUT_GLOBAL_S,
            )
        except asyncio.TimeoutError:
            raw = [asyncio.TimeoutError("Timeout global 120s")] * len(tickers)

        entries: list[ScreenEntry] = []
        for ticker, result in zip(tickers, raw):
            if isinstance(result, BaseException):
                entries.append(
                    ScreenEntry(
                        ticker=ticker,
                        defensive_score=None,
                        verdict=None,
                        workflow_utilise=request.workflow,
                        cost_usd=0.0,
                        depuis_cache=False,
                        erreur=str(result),
                    )
                )
            else:
                entries.append(result)

        # Tri : succès par score desc, échecs en bas, puis alphabétique
        def _sort_key(e: ScreenEntry) -> tuple[int, int, str]:
            if e.erreur is not None:
                return (1, 0, e.ticker)
            if e.defensive_score is None:
                return (0, 0, e.ticker)
            return (0, -e.defensive_score, e.ticker)

        entries.sort(key=_sort_key)

        tickers_echec = sum(1 for e in entries if e.erreur is not None)
        tickers_depuis_cache = sum(1 for e in entries if e.depuis_cache)
        cout_total = sum(e.cost_usd for e in entries)
        duration_ms = int((time.monotonic() - start) * 1000)

        return ScreenResult(
            tickers_analyses=len(entries) - tickers_echec,
            tickers_echec=tickers_echec,
            tickers_depuis_cache=tickers_depuis_cache,
            cout_total_usd=round(cout_total, 6),
            resultats=entries,
            workflow=request.workflow,
            duration_ms=duration_ms,
        )

    async def _analyze_one(
        self,
        ticker: str,
        request: ScreenRequest,
        semaphore: asyncio.Semaphore,
    ) -> ScreenEntry:
        from app.api.endpoints.screen import ScreenEntry

        async with semaphore:
            # 1. Obtenir les ratios (ratios_map prioritaire sur auto-extraction)
            if request.ratios_map and ticker in request.ratios_map:
                ratios = request.ratios_map[ticker]
            else:
                try:
                    ratios = await asyncio.wait_for(
                        self._extractor.extract(ticker),
                        timeout=_TIMEOUT_TICKER_S,
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError(
                        f"Timeout extraction {ticker} ({_TIMEOUT_TICKER_S:.0f}s)"
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Extraction échouée pour {ticker}: {exc}"
                    ) from exc

            # 2. Vérifier le cache
            if self._cache is not None:
                cached = await self._cache.get(ticker, request.workflow, ratios)
                if cached is not None:
                    logger.debug("Cache hit pour %s/%s", ticker, request.workflow)
                    return ScreenEntry(
                        ticker=ticker,
                        defensive_score=cached.graham.defensive_score,
                        verdict=cached.graham.verdict,
                        workflow_utilise=request.workflow,
                        cost_usd=0.0,
                        depuis_cache=True,
                        erreur=None,
                    )

            # 3. Analyser via l'orchestrateur
            analyze_request = AnalyzeRequest(
                ticker=ticker,
                ratios=ratios,
                workflow=request.workflow,
            )
            try:
                response = await asyncio.wait_for(
                    self._orchestrator.run_company_analysis(analyze_request),
                    timeout=_TIMEOUT_TICKER_S,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"Timeout analyse {ticker} ({_TIMEOUT_TICKER_S:.0f}s)"
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Analyse échouée pour {ticker}: {exc}"
                ) from exc

            # 4. Mettre en cache pour les prochains appels
            if self._cache is not None:
                await self._cache.set(ticker, request.workflow, ratios, response)

            return ScreenEntry(
                ticker=ticker,
                defensive_score=response.graham.defensive_score,
                verdict=response.graham.verdict,
                workflow_utilise=request.workflow,
                cost_usd=response.cost_usd,
                depuis_cache=False,
                erreur=None,
            )
