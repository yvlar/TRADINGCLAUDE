from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.services.monthly_report_service import MonthlyReportService
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.watchlist_pdf_service import WatchlistPdfService
from app.services.watchlist_service import WatchlistService
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monthly-report"])


@router.get(
    "/monthly-report",
    summary="Rapport PDF mensuel - watchlist + screener FORT",
    response_class=Response,
)
async def get_monthly_report(request: Request) -> Response:
    """
    Genere le rapport PDF mensuel (watchlist + tickers FORT) et le retourne en telechargement.
    Utile pour declencher manuellement sans attendre le cron du 1er du mois.
    Retourne 404 si la watchlist est vide.
    """
    monthly_service: MonthlyReportService | None = getattr(
        request.app.state, "monthly_report_service", None
    )
    if monthly_service is None:
        raise HTTPException(status_code=503, detail="MonthlyReportService non disponible")

    db_pool = request.app.state.db_pool
    watchlist_pdf_service: WatchlistPdfService = request.app.state.watchlist_pdf_service
    screener_pdf_service: ScreenerPdfService = request.app.state.screener_pdf_service
    watchlist_service: WatchlistService | None = getattr(
        request.app.state, "watchlist_service", None
    )

    try:
        watchlist_pdf, _ = await monthly_service.generate(
            db_pool=db_pool,
            watchlist_pdf_service=watchlist_pdf_service,
            screener_pdf_service=screener_pdf_service,
            watchlist_service=watchlist_service,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise sanitized_http_500(exc, logger, "Erreur lors de la generation du rapport mensuel") from exc

    date_str = datetime.now(timezone.utc).strftime("%Y-%m")
    filename = f"rapport-mensuel-{date_str}.pdf"
    return Response(
        content=watchlist_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
