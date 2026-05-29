"""
Endpoint d'export CSV/Excel — POST /export/screen.

Accepte les memes parametres que POST /screen, execute l'analyse,
et retourne le resultat en fichier CSV ou Excel telechargeable.
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.endpoints.screen import ScreenRequest
from app.services.export import export_to_csv, export_to_excel
from app.services.screener import ScreenerService
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter()

_MIME_CSV = "text/csv; charset=utf-8"
_MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post(
    "/export/screen",
    summary="Export screener CSV ou Excel",
    description=(
        "Lance le screener sur la liste de tickers et retourne le resultat "
        "en fichier CSV (defaut) ou Excel selon le parametre `format`. "
        "Memes parametres que POST /screen. Maximum 20 tickers."
    ),
    responses={
        200: {
            "description": "Fichier CSV ou Excel telechargeable",
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
        }
    },
)
async def export_screen(
    request: Request,
    body: ScreenRequest,
    format: Literal["csv", "xlsx"] = "csv",
) -> Response:
    """Lance le screener et retourne le resultat en CSV ou Excel."""
    screener: ScreenerService = request.app.state.screener

    try:
        result = await screener.screen(body)
    except Exception as exc:
        raise sanitized_http_500(exc, logger, f"Erreur screener export sur {body.tickers}") from exc

    tickers_str = "_".join(body.tickers[:3])
    if len(body.tickers) > 3:
        tickers_str += f"_+{len(body.tickers) - 3}"

    if format == "xlsx":
        try:
            content = export_to_excel(result)
        except RuntimeError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        filename = f"screener_{tickers_str}.xlsx"
        media_type = _MIME_XLSX
    else:
        content = export_to_csv(result)
        filename = f"screener_{tickers_str}.csv"
        media_type = _MIME_CSV

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
