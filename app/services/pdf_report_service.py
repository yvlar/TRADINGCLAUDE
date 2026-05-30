from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.composite_history_service import CompositeHistoryPoint
from app.services.disclaimer import build_disclaimer_flowables

if TYPE_CHECKING:
    from app.orchestrator.core import AnalyzeResponse
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios

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
            fontSize=28,
            textColor=_BLEU_TITRE,
            spaceAfter=10,
            alignment=TA_CENTER,
        ),
        "sous_titre": ParagraphStyle(
            "sous_titre",
            parent=base["Normal"],
            fontSize=12,
            textColor=_GRIS,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "titre_section": ParagraphStyle(
            "titre_section",
            parent=base["Heading2"],
            fontSize=14,
            textColor=_BLEU_TITRE,
            spaceBefore=14,
            spaceAfter=4,
        ),
        "corps": ParagraphStyle(
            "corps",
            parent=base["Normal"],
            fontSize=10,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "score_central": ParagraphStyle(
            "score_central",
            parent=base["Title"],
            fontSize=48,
            textColor=_BLEU_TITRE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "label_central": ParagraphStyle(
            "label_central",
            parent=base["Normal"],
            fontSize=18,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "pied_page": ParagraphStyle(
            "pied_page",
            parent=base["Normal"],
            fontSize=8,
            textColor=_GRIS,
            alignment=TA_CENTER,
        ),
        "cellule": ParagraphStyle(
            "cellule",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
    }


def _hr(story: list) -> None:
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GRIS, spaceAfter=6))


def _label_color(label: str) -> colors.HexColor:
    if label == "FORT":
        return _VERT
    if label == "MODERE":
        return _OR
    return _ROUGE


def _table_deux_colonnes(data: list[tuple[str, str]]) -> Table:
    rows = [[k, v] for k, v in data]
    t = Table(rows, colWidths=[6 * cm, 11 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), _FOND_GRIS),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _fmt_num(valeur: float | None, gabarit: str = "{:.2f}") -> str:
    """Formate un nombre optionnel ; retourne — si None."""
    return gabarit.format(valeur) if valeur is not None else "—"


def _fmt_eps_growth_label(years: int | None) -> str:
    """Libellé honnête de la croissance BPA : « sur N ans » ou horizon inconnu (Sprint 130)."""
    return f"Croissance BPA sur {years} ans" if years else "Croissance BPA (horizon n.d.)"


def _fmt_ratios_source(source: str | None, fetched_at: "datetime | None") -> str:
    """Traçabilité « <source> · récupéré le AAAA-MM-JJ » ; « source n.d. » si la source manque."""
    src = source or "source n.d."
    if fetched_at is not None:
        return f"{src} · récupéré le {fetched_at.strftime('%Y-%m-%d')}"
    return src


def _build_verdicts_rows(la: "AnalyzeResponse") -> list[tuple[str, str, str]]:
    """Construit les lignes (skill, verdict, détail) pour chaque skill présent dans l'analyse."""
    rows: list[tuple[str, str, str]] = []
    if la.graham is not None:
        rows.append(("Graham", f"{la.graham.verdict} · {la.graham.defensive_score}/8", la.graham.verdict_detail))
    if la.earnings_quality is not None:
        rows.append(("Qualité des bénéfices", la.earnings_quality.verdict, la.earnings_quality.verdict_detail))
    if la.dorsey is not None:
        rows.append(("Moat (Dorsey)", la.dorsey.moat_type, la.dorsey.verdict_detail))
    if la.buffett is not None:
        rows.append(("Qualité (Buffett)", f"{la.buffett.verdict} · {la.buffett.quality_score}/4", la.buffett.verdict_detail))
    if la.valuation is not None:
        rows.append(("Valorisation", la.valuation.verdict, la.valuation.verdict_detail))
    if la.thesis is not None:
        rows.append(("Thèse", f"{la.thesis.verdict_final} · {la.thesis.position_size_pct:.1f}%", la.thesis.synthese_narrative))
    if la.munger is not None:
        rows.append(("Munger", la.munger.verdict_comportemental, la.munger.verdict_detail))
    if la.canadian_tax is not None:
        rows.append(("Fiscalité (compte)", la.canadian_tax.compte_recommande, la.canadian_tax.justification_fiscale))
    if la.lynch is not None:
        rows.append(("Lynch", f"{la.lynch.verdict} · {la.lynch.categorie}", la.lynch.verdict_detail))
    if la.fisher is not None:
        rows.append(("Fisher", f"{la.fisher.verdict} · {la.fisher.fisher_score}/30", la.fisher.verdict_detail))
    if la.klarman is not None:
        rows.append(("Klarman", la.klarman.verdict, la.klarman.verdict_detail))
    if la.greenblatt is not None:
        rows.append(("Greenblatt", la.greenblatt.verdict, la.greenblatt.verdict_detail))
    if la.damodaran is not None:
        rows.append(("Damodaran", la.damodaran.verdict, la.damodaran.verdict_detail))
    if la.marks is not None:
        rows.append(("Marks (timing)", la.marks.recommandation_timing, la.marks.verdict_detail))
    if la.pabrai is not None:
        rows.append(("Pabrai (Dhandho)", f"{la.pabrai.verdict} · {la.pabrai.heads_i_win_score}/9", la.pabrai.verdict_detail))
    if la.esg is not None:
        rows.append(("ESG", f"{la.esg.verdict} · {la.esg.esg_score}/15", la.esg.verdict_detail))
    return rows


def _table_verdicts(
    rows: list[tuple[str, str, str]], cellule_style: ParagraphStyle
) -> Table:
    table_data: list[list] = [["Skill", "Verdict", "Détail"]]
    for libelle, verdict, detail in rows:
        table_data.append(
            [
                Paragraph(escape(libelle), cellule_style),
                Paragraph(escape(verdict), cellule_style),
                Paragraph(escape(detail) if detail else "—", cellule_style),
            ]
        )
    t = Table(table_data, colWidths=[3.8 * cm, 4.2 * cm, 9 * cm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _FOND_GRIS]),
            ]
        )
    )
    return t


def _build_ratios_rows(r: "GrahamRatios") -> list[tuple[str, str]]:
    """Tableau des ratios clés Graham pour le PDF."""
    rows: list[tuple[str, str]] = [
        ("Cours", _fmt_num(r.price)),
        ("BPA (TTM)", _fmt_num(r.eps_ttm)),
        ("Valeur comptable / action", _fmt_num(r.book_value)),
        ("P/E", _fmt_num(r.pe)),
        ("P/B", _fmt_num(r.pb)),
        ("Dette / Capitaux propres", _fmt_num(r.debt_equity)),
        (
            _fmt_eps_growth_label(r.eps_growth_years),
            f"{r.eps_growth_total:.0%}" if r.eps_growth_total is not None else "—",
        ),
        ("Ratio de liquidité", _fmt_num(r.current_ratio)),
    ]
    # Traçabilité : omise proprement pour les analyses persistées avant ce champ (tout None)
    if r.ratios_fetched_at is not None or r.ratios_source is not None:
        rows.append(("Source des ratios", _fmt_ratios_source(r.ratios_source, r.ratios_fetched_at)))
    return rows


class PdfReportService:
    async def generate_ticker_report(
        self,
        ticker: str,
        history: list[CompositeHistoryPoint],
        last_analysis: "AnalyzeResponse | None",
        ratios: "GrahamRatios | None" = None,
        annotation: str | None = None,
        esg_score: float | None = None,
    ) -> bytes:
        """Retourne le PDF en bytes — prêt pour StreamingResponse.

        ratios / annotation / esg_score enrichissent le rapport d'une analyse ciblée
        (verdicts skill par skill, ratios clés, note, score ESG) — None = section omise.
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

        # --- Page 1 : Titre + composite_score actuel + verdict global ---
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"Rapport — {ticker}", styles["titre_page"]))
        story.append(Paragraph(f"Généré le : {date_str}", styles["sous_titre"]))
        story.append(Spacer(1, 0.5 * cm))
        _hr(story)

        if history:
            dernier = history[-1]
            label = dernier.label
            couleur = _label_color(label)
            story.append(Paragraph(f"{dernier.score:.1f}", styles["score_central"]))
            story.append(
                Paragraph(
                    f'<font color="#{couleur.hexval()[2:]}">{label}</font>',
                    styles["label_central"],
                )
            )
            story.append(
                Paragraph(
                    f"Score composite au {dernier.recorded_at.strftime('%Y-%m-%d')} — workflow : {dernier.workflow}",
                    styles["sous_titre"],
                )
            )
        else:
            story.append(Paragraph("Aucun historique composite disponible.", styles["corps"]))

        if last_analysis is not None:
            story.append(Spacer(1, 0.5 * cm))
            _hr(story)
            story.append(Paragraph("Résumé de la dernière analyse", styles["titre_section"]))
            _hr(story)
            data: list[tuple[str, str]] = [
                (
                    "Date analyse",
                    last_analysis.created_at[:10] if last_analysis.created_at else "—",
                ),
                ("Skills appliqués", ", ".join(last_analysis.skills_applied or [])),
                ("Coût total", f"{last_analysis.cost_usd:.6f} USD"),
            ]
            if last_analysis.graham is not None:
                data.append(("Score Graham", f"{last_analysis.graham.defensive_score}/8"))
                data.append(("Verdict Graham", last_analysis.graham.verdict or "—"))
            story.append(_table_deux_colonnes(data))

        if ratios is not None:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Ratios clés", styles["titre_section"]))
            _hr(story)
            story.append(_table_deux_colonnes(_build_ratios_rows(ratios)))

        if esg_score is not None:
            story.append(Spacer(1, 0.3 * cm))
            story.append(
                Paragraph(f"Score ESG : {esg_score:.1f}/15", styles["corps"])
            )

        if annotation:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Annotation", styles["titre_section"]))
            _hr(story)
            story.append(Paragraph(escape(annotation), styles["corps"]))

        # --- Page 2 : Tableau évolution composite_score ---
        story.append(PageBreak())
        story.append(
            Paragraph(f"Évolution du composite score — {ticker}", styles["titre_page"])
        )
        story.append(Spacer(1, 0.3 * cm))
        _hr(story)

        if history:
            header = [["Date", "Score", "Label", "Workflow"]]
            rows = [
                [
                    pt.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    f"{pt.score:.1f}",
                    pt.label,
                    pt.workflow,
                ]
                for pt in history
            ]
            table_data = header + rows
            t = Table(
                table_data,
                colWidths=[4.5 * cm, 3 * cm, 3.5 * cm, 6 * cm],
                repeatRows=1,
            )
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _FOND_GRIS]),
                    ]
                )
            )
            story.append(t)
        else:
            story.append(
                Paragraph("Aucun point d'historique disponible.", styles["corps"])
            )

        # --- Page 3 : Résultats skills principaux (Graham, Buffett, Dorsey) ---
        if last_analysis is not None:
            story.append(PageBreak())
            story.append(
                Paragraph(f"Résultats des skills — {ticker}", styles["titre_page"])
            )
            _hr(story)

            verdicts_rows = _build_verdicts_rows(last_analysis)
            if verdicts_rows:
                story.append(Paragraph("Verdicts par skill", styles["titre_section"]))
                _hr(story)
                story.append(_table_verdicts(verdicts_rows, styles["cellule"]))
                story.append(Spacer(1, 0.4 * cm))

            if last_analysis.graham is not None:
                g = last_analysis.graham
                story.append(Paragraph("Analyse Graham", styles["titre_section"]))
                _hr(story)
                skill_data: list[tuple[str, str]] = [
                    ("Score défensif", f"{g.defensive_score}/8"),
                    ("Verdict", g.verdict or "—"),
                ]
                if g.valeur_intrinseque_simple is not None:
                    skill_data.append(
                        ("Valeur intrinsèque simple", f"{g.valeur_intrinseque_simple:.2f}")
                    )
                if g.marge_securite is not None:
                    skill_data.append(("Marge de sécurité", f"{g.marge_securite:.1%}"))
                story.append(_table_deux_colonnes(skill_data))
                story.append(Spacer(1, 4))
                if g.verdict_detail:
                    story.append(Paragraph(g.verdict_detail, styles["corps"]))

            if last_analysis.buffett is not None:
                b = last_analysis.buffett
                story.append(Paragraph("Qualité Buffett", styles["titre_section"]))
                _hr(story)
                buff_data: list[tuple[str, str]] = [
                    ("Quality score", f"{b.quality_score}/4"),
                    ("Verdict", b.verdict or "—"),
                ]
                if b.owner_earnings is not None:
                    buff_data.append(("Owner earnings", f"{b.owner_earnings:.2f}"))
                story.append(_table_deux_colonnes(buff_data))
                story.append(Spacer(1, 4))
                if b.verdict_detail:
                    story.append(Paragraph(b.verdict_detail, styles["corps"]))

            if last_analysis.dorsey is not None:
                d = last_analysis.dorsey
                story.append(Paragraph("Analyse Moat (Dorsey)", styles["titre_section"]))
                _hr(story)
                dorsey_data: list[tuple[str, str]] = [
                    ("Type de moat", d.moat_type),
                    ("ROIC durabilité", d.roic_durability),
                ]
                story.append(_table_deux_colonnes(dorsey_data))
                story.append(Spacer(1, 4))
                if d.verdict_detail:
                    story.append(Paragraph(d.verdict_detail, styles["corps"]))

        # --- Avertissement réglementaire + pied de page ---
        story.extend(build_disclaimer_flowables())
        story.append(Spacer(1, 1 * cm))
        _hr(story)
        story.append(
            Paragraph(
                f"Généré par Copilote Financier IA — {date_str}",
                styles["pied_page"],
            )
        )

        doc.build(story)
        return buffer.getvalue()
