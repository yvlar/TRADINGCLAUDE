from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO

import asyncpg

from app.services.screener_pdf_service import (
    _BLEU_TITRE,
    _FOND_GRIS,
    _GRIS,
    _build_styles,
    _hr,
)
from app.services.screener_pdf_service import ScreenerPdfService
from app.services.watchlist_pdf_service import WatchlistPdfService
from app.services.watchlist_service import WatchlistService
from app.utils.esg_utils import esg_verdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

# Tickers watchlist dont le dernier composite_label est FORT
_QUERY_FORT_TICKERS = """
SELECT ticker, score, label
FROM (
    SELECT DISTINCT ON (ticker) ticker, score, label
    FROM composite_score_history
    WHERE ticker IN (SELECT ticker FROM watchlist)
    ORDER BY ticker, recorded_at DESC
) latest
WHERE label = 'FORT'
ORDER BY score DESC
"""


class MonthlyReportService:
    """Genere le rapport PDF mensuel consolide (watchlist + screener des tickers FORT + ESG)."""

    async def generate(
        self,
        db_pool: asyncpg.Pool,
        watchlist_pdf_service: WatchlistPdfService,
        screener_pdf_service: ScreenerPdfService,
        watchlist_service: WatchlistService | None = None,
    ) -> tuple[bytes, bytes]:
        """Retourne (watchlist_pdf_bytes, screener_pdf_bytes) pour les tickers FORT.

        Si watchlist_service est fourni et qu au moins un ticker a un last_esg_score
        non-null, une section ESG est ajoutee a la fin du PDF watchlist (Sprint 88).
        Leve ValueError si la watchlist est vide.
        """
        watchlist_pdf = await watchlist_pdf_service.generate_watchlist_pdf(pool=db_pool)

        if watchlist_service is not None:
            esg_rows = await watchlist_service.get_all_with_composite()
            if any(r.get("last_esg_score") is not None for r in esg_rows):
                watchlist_pdf = self._append_esg_section(watchlist_pdf, esg_rows)

        rows = await db_pool.fetch(_QUERY_FORT_TICKERS)

        from app.api.endpoints.screen import ScreenEntry, ScreenResult

        entries = [
            ScreenEntry(
                ticker=row["ticker"],
                defensive_score=None,
                verdict=None,
                composite_score=float(row["score"]),
                composite_label=row["label"],
                workflow_utilise="composite_history",
                cost_usd=0.0,
                depuis_cache=True,
                erreur=None,
            )
            for row in rows
        ]

        screen_result = ScreenResult(
            tickers_analyses=len(entries),
            tickers_echec=0,
            tickers_depuis_cache=len(entries),
            cout_total_usd=0.0,
            resultats=entries,
            workflow="monthly_report",
            duration_ms=0,
        )

        screener_pdf = screener_pdf_service.generate(
            screen_result, title="Rapport Mensuel - Opportunites FORT"
        )

        return watchlist_pdf, screener_pdf

    def _build_esg_section_pdf(self, esg_rows: list[dict]) -> bytes:
        """Genere un mini-PDF contenant uniquement la section ESG (titre + tableau).

        Tri : tickers avec score non-null en premier (DESC), puis null.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = _build_styles()
        story: list = []
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Section ESG - Scores et seuils", styles["titre_section"]))
        story.append(Paragraph(
            f"Snapshot ESG de la watchlist au {date_str}.",
            styles["sous_titre"],
        ))
        _hr(story)

        sorted_rows = sorted(
            esg_rows,
            key=lambda r: (
                r.get("last_esg_score") is None,
                -(r.get("last_esg_score") or 0.0),
            ),
        )

        header = [["Ticker", "Score ESG", "Verdict ESG", "Seuil alerte"]]
        data_rows = []
        for row in sorted_rows:
            score = row.get("last_esg_score")
            threshold = row.get("esg_alert_threshold")
            score_str = f"{float(score):.1f}" if score is not None else "--"
            threshold_str = f"{float(threshold):.1f}" if threshold is not None else "--"
            data_rows.append([
                row.get("ticker", ""),
                score_str,
                esg_verdict(score) if score is not None else "--",
                threshold_str,
            ])

        col_widths = [3 * cm, 3.5 * cm, 4.5 * cm, 3.5 * cm]
        table = Table(header + data_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _FOND_GRIS]),
        ]))
        story.append(table)

        story.append(Spacer(1, 0.5 * cm))
        _hr(story)
        story.append(Paragraph(
            f"Copilote Financier IA - Section ESG - {date_str}",
            styles["pied_page"],
        ))

        doc.build(story)
        return buffer.getvalue()

    def _append_esg_section(self, watchlist_pdf: bytes, esg_rows: list[dict]) -> bytes:
        """Concatene le PDF watchlist avec la section ESG via pypdf.

        Si la concatenation echoue (ex: bytes de test non parseables), retourne le PDF
        watchlist original sans interruption - la section ESG est best-effort.
        """
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            logger.warning("pypdf indisponible - section ESG non ajoutee au rapport mensuel")
            return watchlist_pdf

        try:
            esg_pdf = self._build_esg_section_pdf(esg_rows)
            writer = PdfWriter()
            for page in PdfReader(BytesIO(watchlist_pdf)).pages:
                writer.add_page(page)
            for page in PdfReader(BytesIO(esg_pdf)).pages:
                writer.add_page(page)
            output = BytesIO()
            writer.write(output)
            return output.getvalue()
        except Exception as exc:
            logger.warning("Concatenation ESG impossible - retour PDF watchlist original (%s)", exc)
            return watchlist_pdf
