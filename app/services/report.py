from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
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

from app.orchestrator.core import AnalyzeResponse

if TYPE_CHECKING:
    from app.models.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)

# Couleurs sémantiques
_VERT = colors.HexColor("#2E7D32")
_ROUGE = colors.HexColor("#C62828")
_GRIS = colors.HexColor("#616161")
_BLEU_TITRE = colors.HexColor("#1565C0")
_FOND_GRIS = colors.HexColor("#F5F5F5")

# Verdicts positifs → vert
_VERDICTS_POSITIFS = {
    "CANDIDAT_SOLIDE", "EXEMPLAIRE", "WIDE", "ACHETER", "ACHAT_FORT", "ACHAT",
    "COMPOUNDER", "SOUS_EVALUE", "OPPORTUNITE_FORTE", "DHANDHO_FORT",
    "TOP_DECILE", "NARRATIVE_FORTE", "CONFIANCE_JUSTIFIEE",
    "ACHETER_AGRESSIF", "ACHETER_PRUDEMMENT", "PESSIMISME_EXCESSIF",
    "FORTE", "AUCUN_SIGNAL",
}
# Verdicts négatifs → rouge
_VERDICTS_NEGATIFS = {
    "REJETER", "EVITER", "NONE", "VENDRE", "PASSER", "PAS_DHANDHO",
    "NARRATIVE_INCOHERENTE", "ALERTE_ROUGE", "SUREVALUE", "ATTENDRE",
    "EUPHORIE", "VENDRE",
}


def _verdict_color(verdict: str | None) -> colors.HexColor:
    if verdict is None:
        return _GRIS
    v = verdict.upper()
    if v in _VERDICTS_POSITIFS:
        return _VERT
    if v in _VERDICTS_NEGATIFS:
        return _ROUGE
    return _GRIS


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titre_page": ParagraphStyle(
            "titre_page",
            parent=base["Title"],
            fontSize=24,
            textColor=_BLEU_TITRE,
            spaceAfter=8,
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
        "verdict": ParagraphStyle(
            "verdict",
            parent=base["Normal"],
            fontSize=12,
            fontName="Helvetica-Bold",
            spaceAfter=6,
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


def _section_verdict(story: list, styles: dict, label: str, verdict: str | None) -> None:
    if verdict is None:
        return
    couleur = _verdict_color(verdict)
    p = Paragraph(
        f'<font color="#{couleur.hexval()[2:]}"><b>{label} :</b> {verdict}</font>',
        styles["verdict"],
    )
    story.append(p)


def _table_deux_colonnes(data: list[tuple[str, str]]) -> Table:
    """Tableau simple à 2 colonnes pour afficher des paires clé/valeur."""
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


def _section_graham(story: list, styles: dict, graham) -> None:
    story.append(Paragraph("Analyse Graham", styles["titre_section"]))
    _hr(story)

    score_str = f"{graham.defensive_score}/8"
    data = [("Score défensif", score_str)]

    if graham.valeur_intrinseque_simple is not None:
        data.append(("Valeur intrinsèque simple", f"{graham.valeur_intrinseque_simple:.2f}"))
    if graham.valeur_intrinseque_ajustee is not None:
        data.append(("Valeur intrinsèque ajustée", f"{graham.valeur_intrinseque_ajustee:.2f}"))
    if graham.marge_securite is not None:
        data.append(("Marge de sécurité", f"{graham.marge_securite:.1%}"))

    story.append(_table_deux_colonnes(data))
    story.append(Spacer(1, 4))

    # Tableau des critères défensifs
    criteres_data = [["#", "Critère", "Seuil", "✓"]]
    for c in graham.criteria_defensif:
        symbole = "✓" if c.passe else "✗"
        criteres_data.append([str(c.numero), c.nom, c.seuil, symbole])

    t = Table(criteres_data, colWidths=[0.8 * cm, 8.5 * cm, 5.5 * cm, 1.2 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, _GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 4))
    _section_verdict(story, styles, "Verdict Graham", graham.verdict)

    if graham.verdict_detail:
        story.append(Paragraph(graham.verdict_detail, styles["corps"]))

    if graham.drapeaux_rouges:
        story.append(Paragraph("<b>Drapeaux rouges :</b>", styles["corps"]))
        for dr in graham.drapeaux_rouges:
            story.append(Paragraph(f"• {dr}", styles["corps"]))


def _section_earnings_quality(story: list, styles: dict, earnings) -> None:
    story.append(Paragraph("Qualité des résultats", styles["titre_section"]))
    _hr(story)

    data = []
    if earnings.f_score is not None:
        data.append(("F-Score (Piotroski)", f"{earnings.f_score.f_score}/9 — {earnings.f_score.interpretation}"))
    if earnings.m_score is not None and earnings.m_score.m_score is not None:
        data.append(("M-Score (Beneish)", f"{earnings.m_score.m_score:.2f} — {earnings.m_score.interpretation}"))
    if earnings.z_score is not None:
        data.append(("Z-Score (Altman)", f"{earnings.z_score.z_score:.2f} — {earnings.z_score.interpretation}"))
    if earnings.c_score is not None:
        data.append(("C-Score (Montier)", f"{earnings.c_score.c_score} — {earnings.c_score.interpretation}"))

    if data:
        story.append(_table_deux_colonnes(data))
        story.append(Spacer(1, 4))

    _section_verdict(story, styles, "Verdict Earnings", earnings.verdict)
    if earnings.verdict_detail:
        story.append(Paragraph(earnings.verdict_detail, styles["corps"]))


def _section_dorsey_moat(story: list, styles: dict, dorsey) -> None:
    story.append(Paragraph("Analyse Moat (Dorsey)", styles["titre_section"]))
    _hr(story)

    data = [("Type de moat", dorsey.moat_type), ("ROIC durabilité", dorsey.roic_durability)]
    story.append(_table_deux_colonnes(data))
    story.append(Spacer(1, 4))

    if dorsey.sources_identifiees:
        story.append(Paragraph("<b>Sources de moat :</b>", styles["corps"]))
        for src in dorsey.sources_identifiees:
            if hasattr(src, "source") and hasattr(src, "intensite"):
                story.append(Paragraph(f"• {src.source} — {src.intensite}", styles["corps"]))

    _section_verdict(story, styles, "Verdict Dorsey", dorsey.moat_type)
    if dorsey.verdict_detail:
        story.append(Paragraph(dorsey.verdict_detail, styles["corps"]))


def _section_buffett_quality(story: list, styles: dict, buffett) -> None:
    story.append(Paragraph("Qualité Buffett", styles["titre_section"]))
    _hr(story)

    data = [("Quality score", f"{buffett.quality_score}/4")]
    if buffett.owner_earnings is not None:
        data.append(("Owner earnings", f"{buffett.owner_earnings:.2f}"))
    story.append(_table_deux_colonnes(data))
    story.append(Spacer(1, 4))

    _section_verdict(story, styles, "Verdict Buffett", buffett.verdict)
    if buffett.verdict_detail:
        story.append(Paragraph(buffett.verdict_detail, styles["corps"]))


def _section_valuation(story: list, styles: dict, valuation) -> None:
    story.append(Paragraph("Valorisation triangulée", styles["titre_section"]))
    _hr(story)

    data = [
        ("Fourchette basse", f"{valuation.fourchette_basse:.2f}"),
        ("Fourchette centrale", f"{valuation.fourchette_centrale:.2f}"),
        ("Fourchette haute", f"{valuation.fourchette_haute:.2f}"),
    ]
    if valuation.marge_securite_composite is not None:
        data.append(("Marge de sécurité composite", f"{valuation.marge_securite_composite:.1%}"))
    story.append(_table_deux_colonnes(data))
    story.append(Spacer(1, 4))

    _section_verdict(story, styles, "Verdict Valorisation", valuation.verdict)
    if valuation.verdict_detail:
        story.append(Paragraph(valuation.verdict_detail, styles["corps"]))


def _section_thesis(story: list, styles: dict, thesis) -> None:
    story.append(Paragraph("Thèse d'investissement", styles["titre_section"]))
    _hr(story)

    scenarios = []
    if thesis.scenario_bull:
        s = thesis.scenario_bull
        scenarios.append([
            "Bull",
            f"{getattr(s, 'probabilite', '—'):.0%}" if isinstance(getattr(s, 'probabilite', None), float) else "—",
            getattr(s, 'rendement_cible', "—"),
        ])
    if thesis.scenario_base:
        s = thesis.scenario_base
        scenarios.append([
            "Base",
            f"{getattr(s, 'probabilite', '—'):.0%}" if isinstance(getattr(s, 'probabilite', None), float) else "—",
            getattr(s, 'rendement_cible', "—"),
        ])
    if thesis.scenario_bear:
        s = thesis.scenario_bear
        scenarios.append([
            "Bear",
            f"{getattr(s, 'probabilite', '—'):.0%}" if isinstance(getattr(s, 'probabilite', None), float) else "—",
            getattr(s, 'rendement_cible', "—"),
        ])

    if scenarios:
        header = [["Scénario", "Probabilité", "Rendement cible"]]
        t = Table(header + scenarios, colWidths=[4 * cm, 4 * cm, 9 * cm])
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
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 4))

    if thesis.kill_criteria:
        story.append(Paragraph("<b>Kill criteria :</b>", styles["corps"]))
        for kc in thesis.kill_criteria:
            story.append(Paragraph(f"• {kc}", styles["corps"]))

    _section_verdict(story, styles, "Verdict final", thesis.verdict_final)


def _section_tax(story: list, styles: dict, tax) -> None:
    story.append(Paragraph("Fiscalité canadienne", styles["titre_section"]))
    _hr(story)

    data = [("Compte recommandé", tax.compte_recommande)]
    story.append(_table_deux_colonnes(data))
    story.append(Spacer(1, 4))

    if tax.justification_fiscale:
        story.append(Paragraph(tax.justification_fiscale, styles["corps"]))
    if getattr(tax, "impact_retenue_us", None):
        story.append(Paragraph(f"<b>Retenue US :</b> {tax.impact_retenue_us}", styles["corps"]))


def _section_generique(story: list, styles: dict, titre: str, obj) -> None:
    """Section générique pour les skills secondaires : verdict + score si disponible."""
    story.append(Paragraph(titre, styles["titre_section"]))
    _hr(story)

    verdict = getattr(obj, "verdict", None)
    verdict_detail = getattr(obj, "verdict_detail", None)

    data = []
    for attr, label in [
        ("categorie", "Catégorie"),
        ("peg_ratio", "PEG ratio"),
        ("tenbagger_potential", "Tenbagger potentiel"),
        ("score_croissance", "Score croissance"),
        ("fisher_score", "Fisher score"),
        ("management_quality", "Qualité management"),
        ("situation_type_qualifie", "Type de situation"),
        ("marge_securite_score", "Score marge de sécurité"),
        ("preservation_capital_score", "Score préservation capital"),
        ("roc", "ROC"),
        ("earnings_yield", "Earnings yield"),
        ("test_coherence", "Test cohérence"),
        ("narrative_strength", "Force narrative"),
        ("position_cycle", "Position cycle"),
        ("pendule_score", "Score pendule"),
        ("recommandation_timing", "Timing"),
        ("heads_i_win_score", "Score Dhandho"),
        ("asymetrie", "Asymétrie upside/downside"),
        ("kelly_fractionnel", "Kelly fractionnel"),
    ]:
        val = getattr(obj, attr, None)
        if val is not None:
            if isinstance(val, float):
                data.append((label, f"{val:.2f}"))
            elif isinstance(val, bool):
                data.append((label, "Oui" if val else "Non"))
            else:
                data.append((label, str(val)))

    if data:
        story.append(_table_deux_colonnes(data))
        story.append(Spacer(1, 4))

    if verdict:
        _section_verdict(story, styles, "Verdict", verdict)
    if verdict_detail:
        story.append(Paragraph(verdict_detail, styles["corps"]))


def _composite_label(score: float | None) -> str:
    """Retourne FORT/MODERE/FAIBLE selon le score composite 0-100, ou '—' si absent."""
    if score is None:
        return "—"
    if score >= 70:
        return "FORT"
    if score >= 45:
        return "MODERE"
    return "FAIBLE"


def _composite_alerte(score: float | None, threshold: float) -> str:
    """Retourne OUI si score < threshold (alerte active), NON sinon, '—' si score absent."""
    if score is None:
        return "—"
    return "OUI" if score < threshold else "NON"


class ReportService:
    def __init__(self, output_dir: str = "reports") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf(self, response: AnalyzeResponse) -> bytes:
        """Génère un PDF depuis une AnalyzeResponse — retourne les bytes bruts."""
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

        # --- Page de garde ---
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"Rapport d'analyse : {response.ticker}", styles["titre_page"]))
        date_str = response.created_at[:10] if response.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        story.append(Paragraph(f"Date : {date_str}  |  Workflow : {response.workflow}  |  v2.0.0", styles["sous_titre"]))
        story.append(Spacer(1, 0.5 * cm))
        _hr(story)

        # --- Résumé exécutif ---
        story.append(Paragraph("Résumé exécutif", styles["titre_section"]))
        _hr(story)
        data = [
            ("Coût total", f"{response.cost_usd:.6f} USD"),
            ("Skills appliqués", ", ".join(response.skills_applied)),
            ("ID analyse", response.analysis_id),
        ]
        story.append(_table_deux_colonnes(data))
        story.append(Spacer(1, 4))

        # --- Section Graham (toujours présente) ---
        _section_graham(story, styles, response.graham)

        # --- Sections optionnelles ---
        if response.earnings_quality is not None:
            _section_earnings_quality(story, styles, response.earnings_quality)

        if response.dorsey is not None:
            _section_dorsey_moat(story, styles, response.dorsey)

        if response.buffett is not None:
            _section_buffett_quality(story, styles, response.buffett)

        if response.valuation is not None:
            _section_valuation(story, styles, response.valuation)

        if response.thesis is not None:
            _section_thesis(story, styles, response.thesis)

        if response.canadian_tax is not None:
            _section_tax(story, styles, response.canadian_tax)

        # Sections secondaires — verdict + score
        _SECONDARY = [
            (response.lynch, "Catégories Lynch"),
            (response.fisher, "Scuttlebutt Fisher"),
            (response.klarman, "Marge de sécurité Klarman"),
            (response.greenblatt, "Magic Formula Greenblatt"),
            (response.damodaran, "Narrative & Numbers (Damodaran)"),
            (response.marks, "Cycles & Risque (Marks)"),
            (response.pabrai, "Dhandho (Pabrai)"),
        ]
        for obj, titre in _SECONDARY:
            if obj is not None:
                _section_generique(story, styles, titre, obj)

        # --- Pied de page ---
        story.append(Spacer(1, 1 * cm))
        _hr(story)
        story.append(
            Paragraph(
                f"Généré par Copilote Financier IA v2.0.0 — {date_str}",
                styles["pied_page"],
            )
        )

        doc.build(story)
        return buffer.getvalue()

    def save_pdf(self, response: AnalyzeResponse) -> Path:
        """Génère le PDF et le sauvegarde — retourne le chemin du fichier."""
        pdf_bytes = self.generate_pdf(response)
        filename = f"{response.ticker}-{response.analysis_id[:8]}.pdf"
        path = self._output_dir / filename
        path.write_bytes(pdf_bytes)
        logger.info("Rapport PDF sauvegardé : %s (%d octets)", path, len(pdf_bytes))
        return path

    def generate_watchlist_summary_pdf(self, entries: list[WatchlistEntry]) -> bytes:
        """Génère un PDF récapitulatif de toutes les positions de la watchlist."""
        from app.models.watchlist import WatchlistEntry as _WatchlistEntry  # noqa: F401

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

        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Rapport hebdomadaire — Watchlist", styles["titre_page"]))
        story.append(Paragraph(f"Date : {date_str}  |  {len(entries)} position(s)", styles["sous_titre"]))
        story.append(Spacer(1, 0.5 * cm))
        _hr(story)

        story.append(Paragraph("Récapitulatif des positions", styles["titre_section"]))
        _hr(story)

        header = [[
            "Ticker", "Score Graham", "Verdict", "Valeur intrinsèque",
            "Prix vérifié", "Alerte prix",
            "Score composite", "Label", "Alerte composite",
        ]]
        rows = []
        for entry in entries:
            score_str = f"{entry.last_score}/8" if entry.last_score is not None else "—"
            verdict_str = entry.last_verdict or "—"
            intrinsic_str = (
                f"{entry.last_intrinsic_value:.2f} $" if entry.last_intrinsic_value is not None else "—"
            )
            price_str = (
                f"{entry.last_price_checked:.2f} $" if entry.last_price_checked is not None else "—"
            )

            alerte_str = "—"
            if (
                entry.last_intrinsic_value is not None
                and entry.last_price_checked is not None
                and entry.last_intrinsic_value != 0.0
            ):
                ecart = (entry.last_price_checked - entry.last_intrinsic_value) / entry.last_intrinsic_value
                if abs(ecart) >= entry.price_alert_threshold_pct:
                    signe = "+" if ecart > 0 else ""
                    alerte_str = f"Oui ({signe}{ecart:.0%})"

            # Colonnes composite_score
            composite_str = (
                f"{entry.last_composite_score:.1f}" if entry.last_composite_score is not None else "—"
            )
            label_str = _composite_label(entry.last_composite_score)
            alerte_composite_str = _composite_alerte(
                entry.last_composite_score, entry.composite_alert_threshold
            )

            rows.append([
                entry.ticker, score_str, verdict_str, intrinsic_str, price_str, alerte_str,
                composite_str, label_str, alerte_composite_str,
            ])

        table_data = header + rows
        col_widths = [
            1.5 * cm, 1.8 * cm, 2.5 * cm, 2.5 * cm, 2.0 * cm, 1.8 * cm,
            2.0 * cm, 1.8 * cm, 1.6 * cm,
        ]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _BLEU_TITRE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
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
