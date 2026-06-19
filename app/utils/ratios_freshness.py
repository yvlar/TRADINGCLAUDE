from __future__ import annotations

from datetime import datetime, timezone

SEUIL_AVERTISSEMENT_J = 30
SEUIL_FORT_J = 90


def check_ratios_age(fetched_at: datetime | None, *, label: str) -> str | None:
    """Retourne un avertissement de fraîcheur si les ratios sont périmés, sinon None."""
    if fetched_at is None:
        return None
    # fetched_at peut être naïf (saisie manuelle) — on l'aligne sur UTC pour éviter une comparaison mixte.
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age_j = (datetime.now(timezone.utc) - fetched_at).days
    if age_j > SEUIL_FORT_J:
        return f"{label} : données vieilles de {age_j} j (>{SEUIL_FORT_J} j) — fiabilité réduite"
    if age_j > SEUIL_AVERTISSEMENT_J:
        return f"{label} : données vieilles de {age_j} j (>{SEUIL_AVERTISSEMENT_J} j)"
    return None
