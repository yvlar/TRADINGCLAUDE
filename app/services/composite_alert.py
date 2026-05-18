"""
Service de surveillance des alertes composite_score pour la watchlist.

Detecte les chutes de composite_score > seuil (defaut 15 pts) vs la baseline
enregistree dans last_composite_score. Envoie un email si configure.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 15.0


@dataclass
class CompositeAlertResult:
    """Resultat de la verification d'alertes pour un ticker."""

    ticker: str
    baseline: float
    new_score: float
    chute: float
    threshold: float
    alerte_declenchee: bool


class CompositeAlertService:
    """
    Verifie si le composite_score d'un ticker a chute de plus du seuil
    par rapport au score de reference (last_composite_score).
    """

    def __init__(
        self,
        watchlist_service: Any,
        orchestrator: Any,
        email_service: Any | None = None,
        email_to: str | None = None,
    ) -> None:
        self._watchlist = watchlist_service
        self._orchestrator = orchestrator
        self._email = email_service
        self._email_to = email_to

    async def check_composite_alerts(self) -> list[CompositeAlertResult]:
        """
        Pour chaque entree watchlist avec last_composite_score :
        1. Relancer l'analyse via orchestrator
        2. Comparer composite_score vs baseline
        3. Si chute > seuil -> logguer WARNING + email si configure
        4. Mettre a jour last_composite_score dans la DB
        Retourne la liste des resultats (alertes declenchees ou non).
        """
        from app.orchestrator.core import AnalyzeRequest

        entries = await self._watchlist.list_entries()
        alertes_declenchees = [e for e in entries if e.last_composite_score is not None]

        logger.info(
            "Verification alertes composite -- %d entree(s) avec baseline",
            len(alertes_declenchees),
        )

        resultats: list[CompositeAlertResult] = []

        for entry in alertes_declenchees:
            baseline = entry.last_composite_score
            threshold = entry.composite_alert_threshold

            try:
                req = AnalyzeRequest(
                    ticker=entry.ticker,
                    ratios=entry.ratios,
                    workflow=entry.workflow,
                )
                response = await self._orchestrator.run_company_analysis(req)
                cs = response.composite_score

                if cs is None:
                    logger.warning(
                        "composite_score absent pour %s -- impossible de verifier l'alerte",
                        entry.ticker,
                    )
                    continue

                new_score = cs.score
                chute = baseline - new_score
                alerte = chute > threshold

                if alerte:
                    logger.warning(
                        "ALERTE COMPOSITE [%s] : score %.1f -> %.1f (chute=%.1f > seuil=%.1f)",
                        entry.ticker, baseline, new_score, chute, threshold,
                    )
                    await self._send_alert_email(entry.ticker, baseline, new_score, chute, threshold)
                else:
                    logger.debug(
                        "Composite stable [%s] : %.1f -> %.1f (chute=%.1f)",
                        entry.ticker, baseline, new_score, chute,
                    )

                await self._watchlist.update_composite_score(entry.id, new_score)

                resultats.append(CompositeAlertResult(
                    ticker=entry.ticker,
                    baseline=baseline,
                    new_score=new_score,
                    chute=chute,
                    threshold=threshold,
                    alerte_declenchee=alerte,
                ))

            except Exception:
                logger.exception("Erreur lors de la verification de %s", entry.ticker)

        return resultats

    async def _send_alert_email(
        self,
        ticker: str,
        baseline: float,
        new_score: float,
        chute: float,
        threshold: float,
    ) -> None:
        """Envoie un email d'alerte si le service email est configure."""
        if self._email is None or not self._email_to:
            logger.warning(
                "Email non configure -- alerte composite [%s] non envoyee", ticker
            )
            return

        sujet = f"[TradingClaude] Alerte composite : {ticker} -%.1f pts" % chute
        corps = (
            f"Le score composite de {ticker} a chute de {chute:.1f} points "
            f"(seuil : {threshold:.1f} pts).\n\n"
            f"Baseline : {baseline:.1f}\n"
            f"Nouveau score : {new_score:.1f}\n\n"
            f"Action requise : relancer une analyse complete et reviser la these d'investissement."
        )

        try:
            await self._email.send_text(
                to=self._email_to,
                subject=sujet,
                body=corps,
            )
            logger.info("Email alerte composite envoye pour %s", ticker)
        except Exception:
            logger.exception("Echec envoi email alerte pour %s", ticker)
