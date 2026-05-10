from __future__ import annotations

import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class PriceAlertService:
    """Vérifie l'écart entre le prix courant et la valeur intrinsèque de la watchlist."""

    async def check_price_alerts(
        self,
        db_pool: asyncpg.Pool,
        yahoo_extractor: Any,
    ) -> list[str]:
        """
        Pour chaque entrée watchlist avec last_intrinsic_value :
        1. Extraire le prix courant via YahooFinanceExtractor
        2. Calculer l'écart = |prix - intrinsic| / intrinsic
        3. Si écart >= price_alert_threshold_pct → logguer WARNING
        4. Mettre à jour last_price_checked
        Retourne la liste des tickers ayant déclenché une alerte.
        """
        alerted: list[str] = []
        rows = await db_pool.fetch(
            """
            SELECT id, ticker, last_intrinsic_value, price_alert_threshold_pct
            FROM watchlist
            WHERE last_intrinsic_value IS NOT NULL
            ORDER BY ticker
            """
        )
        logger.info(
            "Vérification alertes prix — %d entrée(s) avec valeur intrinsèque", len(rows)
        )
        for row in rows:
            ticker: str = row["ticker"]
            entry_id = str(row["id"])
            intrinsic = float(row["last_intrinsic_value"])
            threshold = float(row["price_alert_threshold_pct"])
            try:
                ratios = await yahoo_extractor.extract(ticker)
                current_price: float = ratios.price
                ecart = abs(current_price - intrinsic) / intrinsic
                await db_pool.execute(
                    "UPDATE watchlist SET last_price_checked = $2 WHERE id = $1::uuid",
                    entry_id,
                    current_price,
                )
                if ecart >= threshold:
                    logger.warning(
                        "ALERTE PRIX — %s : écart %.1f%% ≥ seuil %.1f%%"
                        " (prix=%.2f, intrinsèque=%.2f)",
                        ticker,
                        ecart * 100,
                        threshold * 100,
                        current_price,
                        intrinsic,
                    )
                    alerted.append(ticker)
                else:
                    logger.info(
                        "Prix OK — %s : écart %.1f%% < seuil %.1f%%",
                        ticker,
                        ecart * 100,
                        threshold * 100,
                    )
            except Exception:
                logger.exception("Erreur lors de la vérification du prix pour %s", ticker)
        return alerted
