from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class WebhookService:
    """Envoie des notifications via webhook HTTP compatible Slack/Discord/n8n."""

    def __init__(self) -> None:
        self._url: str | None = os.environ.get("WEBHOOK_URL") or None
        self._secret: str | None = os.environ.get("WEBHOOK_SECRET") or None
        self._nb_erreurs: int = 0
        self._derniere_notification: datetime | None = None
        # import tardif pour éviter la circularité de dépendances au niveau module
        from app.services.slack_service import SlackService
        self._slack = SlackService()

    @property
    def url_configuree(self) -> bool:
        return bool(self._url)

    @property
    def nb_erreurs(self) -> int:
        return self._nb_erreurs

    @property
    def derniere_notification(self) -> datetime | None:
        return self._derniere_notification

    async def _post(self, payload: dict) -> bool:
        """Envoie le payload JSON via HTTP POST avec 1 retry sur erreur réseau."""
        if not self._url:
            return False

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-Webhook-Secret"] = self._secret

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self._url, json=payload, headers=headers)
                    resp.raise_for_status()
                self._derniere_notification = datetime.now(timezone.utc)
                logger.info(
                    "Webhook envoyé — type=%s ticker=%s status=%d",
                    payload.get("type"),
                    payload.get("ticker", "—"),
                    resp.status_code,
                )
                return True
            except httpx.RequestError as exc:
                logger.warning(
                    "Erreur réseau webhook (essai %d/2) — %s", attempt + 1, exc
                )
                if attempt == 1:
                    self._nb_erreurs += 1
                    logger.error("Webhook échoué après retry — %s", exc)
                    return False
            except httpx.HTTPStatusError as exc:
                self._nb_erreurs += 1
                logger.error(
                    "Webhook HTTP erreur %d — %s", exc.response.status_code, exc
                )
                return False
            except Exception:
                self._nb_erreurs += 1
                logger.exception("Erreur inattendue lors de l'envoi du webhook")
                return False
        return False

    async def send_price_alert(
        self, ticker: str, prix: float, seuil: float, direction: str
    ) -> bool:
        """Envoie une alerte prix via webhook. Retourne True si succès."""
        payload = {
            "text": (
                f"ALERTE PRIX — {ticker} : prix {prix:.2f} "
                f"(seuil écart {seuil * 100:.1f}%, direction={direction})"
            ),
            "ticker": ticker,
            "type": "price",
            "prix": prix,
            "seuil": seuil,
            "direction": direction,
        }
        return await self._post(payload)

    async def send_composite_alert(
        self, ticker: str, score: float, label: str
    ) -> bool:
        """Envoie une alerte composite_score via webhook."""
        payload = {
            "text": f"ALERTE COMPOSITE — {ticker} : score {score:.1f} ({label})",
            "ticker": ticker,
            "type": "composite",
            "score": score,
            "label": label,
        }
        return await self._post(payload)

    async def send_watchlist_summary(
        self, nb_positions: int, alertes: list[dict]
    ) -> bool:
        """Envoie un résumé hebdomadaire de la watchlist."""
        nb_alertes = len(alertes)
        payload = {
            "text": (
                f"Rapport hebdomadaire watchlist : {nb_positions} position(s), "
                f"{nb_alertes} alerte(s)"
            ),
            "type": "summary",
            "nb_positions": nb_positions,
            "alertes": alertes,
        }
        return await self._post(payload)

    async def send_esg_alert(self, ticker: str, esg_score: float, threshold: float) -> bool:
        """Envoie une alerte webhook si esg_score < threshold. Retourne False si WEBHOOK_URL absent."""
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "type": "esg_alert",
            "ticker": ticker,
            "esg_score": esg_score,
            "threshold": threshold,
            "timestamp": timestamp,
        }
        webhook_result = await self._post(payload)
        # Notification Slack en complément (no-op si SLACK_WEBHOOK_URL absent)
        await self._slack.send_esg_alert(ticker=ticker, score=esg_score, threshold=threshold)
        return webhook_result

    async def send_screener_report(
        self, nb_tickers_screenes: int, tickers_fort: list[str]
    ) -> bool:
        """Envoie le rapport de screener hebdomadaire avec les opportunités FORT."""
        nb_opportunites = len(tickers_fort)
        payload = {
            "text": (
                f"Screener hebdomadaire — {nb_opportunites} opportunité(s) FORT "
                f"sur {nb_tickers_screenes} ticker(s) analysé(s) : {', '.join(tickers_fort)}"
            ),
            "type": "screener",
            "nb_tickers_screenes": nb_tickers_screenes,
            "nb_opportunites": nb_opportunites,
            "tickers_fort": tickers_fort,
        }
        return await self._post(payload)

    async def send_monthly_report(
        self, watchlist_pdf: bytes, screener_pdf: bytes
    ) -> bool:
        """Envoie les deux PDFs du rapport mensuel via webhook multipart."""
        if not self._url:
            return False

        headers: dict[str, str] = {}
        if self._secret:
            headers["X-Webhook-Secret"] = self._secret

        date_str = datetime.now(timezone.utc).strftime("%Y-%m")

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        self._url,
                        headers=headers,
                        files=[
                            ("file", (f"watchlist-{date_str}.pdf", watchlist_pdf, "application/pdf")),
                            ("file", (f"screener-fort-{date_str}.pdf", screener_pdf, "application/pdf")),
                        ],
                    )
                    resp.raise_for_status()
                self._derniere_notification = datetime.now(timezone.utc)
                logger.info("Webhook rapport mensuel envoyé — %s", date_str)
                return True
            except httpx.RequestError as exc:
                logger.warning(
                    "Erreur réseau webhook mensuel (essai %d/2) — %s", attempt + 1, exc
                )
                if attempt == 1:
                    self._nb_erreurs += 1
                    logger.error("Webhook mensuel échoué après retry — %s", exc)
                    return False
            except httpx.HTTPStatusError as exc:
                self._nb_erreurs += 1
                logger.error(
                    "Webhook mensuel HTTP erreur %d — %s", exc.response.status_code, exc
                )
                return False
            except Exception:
                self._nb_erreurs += 1
                logger.exception("Erreur inattendue lors de l'envoi du webhook mensuel")
                return False
        return False

    async def send_screener_pdf_report(self, result: object) -> bool:
        """
        Envoie le rapport PDF du screener via webhook multipart/form-data.
        Retourne False sans exception si WEBHOOK_URL absent ou si PDF non générable.
        """
        if not self._url:
            return False

        from app.services.screener_pdf_service import ScreenerPdfService

        try:
            svc = ScreenerPdfService()
            pdf_bytes = svc.generate(result)  # type: ignore[arg-type]
        except Exception:
            logger.exception("Impossible de générer le PDF screener pour l'envoi webhook")
            return False

        headers: dict[str, str] = {}
        if self._secret:
            headers["X-Webhook-Secret"] = self._secret

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"screener-{date_str}.pdf"

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        self._url,
                        headers=headers,
                        files={"file": (filename, pdf_bytes, "application/pdf")},
                    )
                    resp.raise_for_status()
                self._derniere_notification = datetime.now(timezone.utc)
                logger.info("Webhook PDF screener envoyé — fichier=%s status=%d", filename, resp.status_code)
                return True
            except httpx.RequestError as exc:
                logger.warning("Erreur réseau webhook PDF (essai %d/2) — %s", attempt + 1, exc)
                if attempt == 1:
                    self._nb_erreurs += 1
                    logger.error("Webhook PDF échoué après retry — %s", exc)
                    return False
            except httpx.HTTPStatusError as exc:
                self._nb_erreurs += 1
                logger.error("Webhook PDF HTTP erreur %d — %s", exc.response.status_code, exc)
                return False
            except Exception:
                self._nb_erreurs += 1
                logger.exception("Erreur inattendue lors de l'envoi du webhook PDF")
                return False
        return False
