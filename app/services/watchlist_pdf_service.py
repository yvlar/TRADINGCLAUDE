from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO

import asyncpg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.report import _composite_alerte, _composite_label
from app.services.screener_pdf_service import (
    _BLEU_TITRE,
    _FOND_GRIS,
    _GRIS,
    _VERT,
    _build_styles,
    _hr,
    _label_color,
)

logger = logging.getLogger(__name__)

_QUERY_WATCHLIST_PDF = """
SELECT
    w.ticker,
    w.created_at,
    w.composite_alert_threshold,
    COALESCE(csh.score, w.last_composite_score) AS composite_score_latest,
    csh.label                                   AS composite_label_latest,
    ah.derniere_analyse
FROM watchlist w
LEFT JOIN LATERAL (
    SELECT score, label
    FROM composite_score_history
    WHERE ticker = w.ticker
    ORDER BY recorded_at DESC
    LIMIT 1
) csh ON true
LEFT JOIN LATERAL (
    SELECT created_at AS derniere_analyse
    FROM analysis_history
    WHERE ticker = w.ticker
    ORDER BY created_at DESC
    LIMIT 1
) ah ON true
ORDER BY w.created_at DESC
"""


class WatchlistPdfService:
    """Génère un PDF complet de la watchlist (positions + composite scores + historique)."""

    async def generate_watchlist_pdf(
        self,
        pool: asyncpg.Pool,
        composite_history_service: object | None = None,
    ) -> bytes:
        """
        Génère le rapport PDF complet de la watchlist.
        Lève ValueError si la watchlist est vide.
        """
        rows = await pool.fetch(_QUERY_WATCHLIST_PDF)
        if not rows:
            raise ValueError("Watchlist vide — aucun ticker à inclure dans le rapport")

        return self._build_pdf([dict(r) for r in rows])

    def _build_pdf(self, rows: list[dict]) -> bytes:
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

        scores = [
            float(r["composite_score_latest"])
            for r in rows
            if r.get("composite_score_latest") is not None
        ]
        score_moyen = sum(scores) / len(scores) if scores else None

        # --- En-tête ---
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Rapport Watchlist", styles["titre_page"]))
        meta = f"Généré le : {date_str} | {len(rows)} position(s)"
        if score_moyen is not None:
            meta += f" | Score moyen : {score_moyen:.1f}"
        story.append(Paragraph(meta, styles["sous_titre"]))
        story.append(Spacer(1, 0.3 * cm))
        _hr(story)

        # --- Tableau principal ---
        story.append(Paragraph("Positions surveillées", styles["titre_section"]))
        _hr(story)

        header = [["Ticker", "Score", "Label", "Alerte", "Dernière analyse"]]
        data_rows = []
        for r in rows:
            score = r.get("composite_score_latest")
            score = float(score) if score is not None else None
            threshold = float(r.get("composite_alert_threshold") or 15.0)
            label = r.get("composite_label_latest") or _composite_label(score)
            alerte = _composite_alerte(score, threshold)
            derniere = r.get("derniere_analyse")
            derniere_str = derniere.strftime("%Y-%m-%d") if derniere else "—"
            data_rows.append([
                r["ticker"],
                f"{score:.1f}" if score is not None else "—",
                label,
                alerte,
                derniere_str,
            ])

        col_widths = [3 * cm, 3 * cm, 3.5 * cm, 3 * cm, 4.5 * cm]
        t = Table(header + data_rows, colWidths=col_widths, repeatRows=1)

        row_styles: list = [
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
        ]
        for i, r in enumerate(rows, start=1):
            score = r.get("composite_score_latest")
            score = float(score) if score is not None else None
            lbl = r.get("composite_label_latest") or _composite_label(score)
            couleur = _label_color(lbl)
            row_styles.append(("TEXTCOLOR", (2, i), (2, i), couleur))
            row_styles.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))

        t.setStyle(TableStyle(row_styles))
        story.append(t)

        # --- Section Top Picks ---
        top_picks = [
            r for r in rows
            if (r.get("composite_label_latest") or _composite_label(
                float(r["composite_score_latest"]) if r.get("composite_score_latest") is not None else None
            )) == "FORT"
        ]
        if top_picks:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Top Picks — Score FORT", styles["titre_section"]))
            _hr(story)
            top_data = [["Ticker", "Score composite", "Label"]]
            for r in top_picks:
                score = r.get("composite_score_latest")
                score = float(score) if score is not None else None
                lbl = r.get("composite_label_latest") or "FORT"
                top_data.append([
                    r["ticker"],
                    f"{score:.1f}" if score is not None else "—",
                    lbl,
                ])
            t_top = Table(top_data, colWidths=[3.5 * cm, 5 * cm, 8.5 * cm], repeatRows=1)
            t_top.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _VERT),
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
            story.append(t_top)

        # --- Pied de page ---
        story.append(Spacer(1, 0.8 * cm))
        _hr(story)
        story.append(Paragraph(f"Copilote Financier IA — {date_str}", styles["pied_page"]))

        doc.build(story)
        return buffer.getvalue()
