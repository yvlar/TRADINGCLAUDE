from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QuotaStatusResponse(BaseModel):
    """État du quota mensuel d'analyses du tenant courant (E5-S6) — lecture seule.

    Alimentée par `QuotaService.read_status` : plan, analyses consommées ce mois, borne
    `max_analyses_per_month` et restant. `limit`/`remaining` valent `None` quand le plan n'a
    pas pu être résolu (fail-open) — le header affiche alors le plan sans compteur plutôt qu'une
    borne factice. Aucune incrémentation : appeler cet endpoint ne consomme pas de quota.
    """

    plan: str
    used: int
    # None = plan non résolu côté serveur (fail-open) → pas de borne affichée par le client.
    limit: int | None
    remaining: int | None
    # Bascule du compteur mensuel : 1er du mois suivant à 00:00 UTC.
    reset_at: datetime
