from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class SlackService:
    """Envoie des messages Slack via Incoming Webhook — optionnel si SLACK_WEBHOOK_URL absent."""

    def __init__(self) -> None:
        self._url: str | None = os.environ.get("SLACK_WEBHOOK_URL") or None

    @property
    def url_configuree(self) -> bool:
        return bool(self._url)

    async def _post(self, text: str) -> bool:
        """Envoie un message texte sur le canal Slack avec 1 retry sur erreur réseau."""
        if not self._url:
            return False

        payload = {"text": text}

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self._url, json=payload)
                    resp.raise_for_status()
                logger.info("Message Slack envoyé — extrait=%s", text[:60])
                return True
            except httpx.RequestError as exc:
                logger.warning("Erreur réseau Slack (essai %d/2) — %s", attempt + 1, exc)
                if attempt == 1:
                    logger.error("Slack échoué après retry — %s", exc)
                    return False
            except httpx.HTTPStatusError as exc:
                logger.error("Slack HTTP erreur %d — %s", exc.response.status_code, exc)
                return False
            except Exception:
                logger.exception("Erreur inattendue lors de l'envoi Slack")
                return False
        return False

    async def send_text(self, text: str) -> bool:
        """Envoie un message texte sur le canal Slack. Retourne False si URL absente ou erreur."""
        return await self._post(text)

    async def send_esg_alert(self, ticker: str, score: float, threshold: float) -> bool:
        """Formate et envoie une alerte ESG sur Slack."""
        text = (
            f":warning: *ALERTE ESG — {ticker}* : "
            f"score {score:.1f} < seuil {threshold:.1f}"
        )
        return await self._post(text)

    async def send_screener_summary(
        self, nb_analyses: int, nb_fort: int, cout_usd: float
    ) -> bool:
        """Formate et envoie un résumé screener sur Slack (utilise après run_scheduled_screener)."""
        text = (
            f":mag: *Screener hebdomadaire* — "
            f"{nb_fort} opportunité(s) FORT sur {nb_analyses} analysé(s) "
            f"(coût : {cout_usd:.4f} USD)"
        )
        return await self._post(text)

    async def send_monthly_report_summary(
        self, nb_positions: int, nb_fort: int
    ) -> bool:
        """Formate et envoie un résumé rapport mensuel sur Slack."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m")
        text = (
            f":bar_chart: *Rapport mensuel {date_str}* — "
            f"{nb_positions} position(s), {nb_fort} FORT"
        )
        return await self._post(text)
