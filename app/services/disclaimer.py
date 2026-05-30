from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer

# Source de vérité unique du texte d'avertissement côté backend (PDF).
# Le pendant frontend vit dans frontend/src/constants/disclaimer.ts — garder
# les deux formulations alignées (exposition réglementaire AMF/SEC/MiFID).
DISCLAIMER_TITLE = "Avertissement"
DISCLAIMER_TEXT = (
    "Ce système produit de la recherche éducative — pas un conseil financier. "
    "Investir comporte un risque de perte en capital."
)

_GRIS = colors.HexColor("#616161")

_STYLE_DISCLAIMER = ParagraphStyle(
    "disclaimer",
    fontName="Helvetica-Oblique",
    fontSize=8,
    textColor=_GRIS,
    leading=10,
    alignment=TA_LEFT,
)


def build_disclaimer_flowables() -> list[Flowable]:
    """Bloc d'avertissement réutilisable, à insérer dans le `story` de tout rapport PDF."""
    return [
        Spacer(1, 0.4 * cm),
        HRFlowable(width="100%", thickness=0.5, color=_GRIS, spaceAfter=4),
        Paragraph(f"<b>{DISCLAIMER_TITLE}</b> — {DISCLAIMER_TEXT}", _STYLE_DISCLAIMER),
    ]
