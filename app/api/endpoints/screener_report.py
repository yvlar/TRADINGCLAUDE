from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from app.api.endpoints.screen import ScreenRequest, ScreenResult
from app.services.screener import ScreenerService
from app.services.screener_pdf_service import ScreenerPdfService
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["screener-report"])


@router.get(
    "/screener-report",
    summary="Rapport PDF des résultats du screener",
    response_class=Response,
)
async def get_screener_report(
    request: Request,
    tickers: str = Query(..., description="Tickers séparés par virgule (ex: BNS,TD,RY)"),
    workflow: str = Query("value_graham", description="Workflow d'analyse"),
) -> Response:
    """
    Lance le screener sur les tickers fournis et retourne un rapport PDF téléchargeable.
    Le cache Redis est utilisé si disponible — les tickers déjà analysés sont instantanés.
    """
    try:
        ticker_list = [sanitize_ticker(t.strip()) for t in tickers.split(",") if t.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not ticker_list:
        raise HTTPException(status_code=422, detail="Au moins un ticker requis")
    if len(ticker_list) > 20:
        raise HTTPException(status_code=422, detail="Maximum 20 tickers par appel")

    screener: ScreenerService | None = getattr(request.app.state, "screener", None)
    if screener is None:
        raise HTTPException(status_code=503, detail="ScreenerService non disponible")

    pdf_service: ScreenerPdfService | None = getattr(
        request.app.state, "screener_pdf_service", None
    )
    if pdf_service is None:
        raise HTTPException(status_code=503, detail="ScreenerPdfService non disponible")

    try:
        screen_req = ScreenRequest(tickers=ticker_list, workflow=workflow, max_parallel=5)
        result: ScreenResult = await screener.screen(screen_req)
    except Exception as exc:
        logger.exception("Erreur lors du screener pour le rapport PDF")
        raise HTTPException(status_code=500, detail=f"Erreur screener : {exc}") from exc

    try:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title = f"Rapport Screener — {workflow} — {date_str}"
        pdf_bytes = pdf_service.generate(result, title=title)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du rapport PDF screener")
        raise HTTPException(
            status_code=500, detail=f"Erreur génération PDF : {exc}"
        ) from exc

    filename = f"screener-{workflow}-{date_str}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
