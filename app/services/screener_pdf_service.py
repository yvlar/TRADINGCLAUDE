from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from app.api.endpoints.screen import ScreenResult

logger = logging.getLogger(__name__)

_VERT = colors.HexColor("#2E7D32")
_ROUGE = colors.HexColor("#C62828")
_GRIS = colors.HexColor("#616161")
_BLEU_TITRE = colors.HexColor("#1565C0")
_FOND_GRIS = colors.HexColor("#F5F5F5")
_OR = colors.HexColor("#F57F17")


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titre_page": ParagraphStyle(
            "titre_page",
            parent=base["Title"],
            fontSize=22,
            textColor=_BLEU_TITRE,
            spaceAfter=8,
            alignment=TA_CENTER,
        ),
        "sous_titre": ParagraphStyle(
            "sous_titre",
            parent=base["Normal"],
            fontSize=10,
            textColor=_GRIS,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "titre_section": ParagraphStyle(
            "titre_section",
            parent=base["Heading2"],
            fontSize=13,
            textColor=_BLEU_TITRE,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "corps": ParagraphStyle(
            "corps",
            parent=base["Normal"],
            fontSize=10,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "pied_page": ParagraphStyle(
            "pied_page",
            parent=base["Normal"],
            fontSize=8,
            textColor=_GRIS,
            alignment=TA_CENTER,
        ),
    }


def _hr(story: list) -> None:
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GRIS, spaceAfter=6))


def _label_color(label: str | None) -> colors.HexColor:
    if label == "FORT":
        return _VERT
    if label == "MODERE":
        return _OR
    return _ROUGE


class ScreenerPdfService:
    """Génère un PDF des résultats du screener (ScreenResult)."""

    def generate(
        self,
        result: "ScreenResult",
        title: str = "Rapport Screener Hebdomadaire",
    ) -> bytes:
        """Retourne le PDF en bytes — prêt pour StreamingResponse."""
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

        # --- En-tête ---
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(title, styles["titre_page"]))
        story.append(
            Paragraph(
                f"Généré le : {date_str} — Workflow : {result.workflow}",
                styles["sous_titre"],
            )
        )
        story.append(
            Paragraph(
                f"{result.tickers_analyses} ticker(s) analysé(s) | "
                f"{result.tickers_echec} erreur(s) | "
                f"Coût total : {result.cout_total_usd:.6f} USD | "
                f"Durée : {result.duration_ms} ms",
                styles["sous_titre"],
            )
        )
        story.append(Spacer(1, 0.3 * cm))
        _hr(story)

        # --- Tableau des résultats ---
        story.append(Paragraph("Résultats du screener", styles["titre_section"]))
        _hr(story)

        header = [["Ticker", "Score", "Label", "Verdict", "Coût USD"]]
        rows = []
        for e in result.resultats:
            verdict_or_err = e.verdict or "—"
            if e.erreur:
                verdict_or_err = (e.erreur[:38] + "…") if len(e.erreur) > 40 else e.erreur
            rows.append([
                e.ticker,
                f"{e.composite_score:.1f}" if e.composite_score is not None else "—",
                e.composite_label or "—",
                verdict_or_err,
                f"{e.cost_usd:.6f}",
            ])

        table_data = header + rows
        if rows:
            col_widths = [2.5 * cm, 2.5 * cm, 3 * cm, 7 * cm, 2.5 * cm]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)

            row_styles: list = [
                ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _FOND_GRIS]),
            ]

            # Coloriser la colonne "Label" par ligne
            for i, entry in enumerate(result.resultats, start=1):
                couleur = _label_color(entry.composite_label)
                row_styles.append(("TEXTCOLOR", (2, i), (2, i), couleur))
                row_styles.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))

            t.setStyle(TableStyle(row_styles))
            story.append(t)
        else:
            story.append(Paragraph("Aucun résultat disponible.", styles["corps"]))

        # --- Section Top Picks ---
        top_picks = [
            e for e in result.resultats if e.composite_label == "FORT" and e.erreur is None
        ]
        if top_picks:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Top Picks — Score FORT", styles["titre_section"]))
            _hr(story)
            top_data = [["Ticker", "Score composite", "Verdict"]]
            for e in top_picks:
                top_data.append([
                    e.ticker,
                    f"{e.composite_score:.1f}" if e.composite_score is not None else "—",
                    e.verdict or "—",
                ])
            t_top = Table(top_data, colWidths=[3.5 * cm, 5 * cm, 9 * cm], repeatRows=1)
            t_top.setStyle(
                TableStyle([
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
                ])
            )
            story.append(t_top)

        # --- Pied de page ---
        story.append(Spacer(1, 0.8 * cm))
        _hr(story)
        story.append(
            Paragraph(
                f"Copilote Financier IA — {date_str}",
                styles["pied_page"],
            )
        )

        doc.build(story)
        return buffer.getvalue()
