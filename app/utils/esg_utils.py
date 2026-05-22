"""Utilitaires ESG partages entre endpoints, services et workers."""
from __future__ import annotations


def esg_verdict(score: float | None) -> str:
    """Retourne le verdict ESG textuel depuis un score numerique.

    Bareme : >=10 -> ESG_FORT, >=5 -> ESG_MODERE, sinon ESG_FAIBLE, None -> N/A.
    """
    if score is None:
        return "N/A"
    if score >= 10:
        return "ESG_FORT"
    if score >= 5:
        return "ESG_MODERE"
    return "ESG_FAIBLE"
