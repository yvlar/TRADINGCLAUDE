from __future__ import annotations

import math
from typing import Annotated

from pydantic import AfterValidator


def _rejeter_non_fini(valeur: float | None) -> float | None:
    """Rejette NaN/inf — un score ou ratio non fini est une sortie LLM aberrante, jamais persistable."""
    if valeur is not None and not math.isfinite(valeur):
        raise ValueError("valeur numérique non finie (NaN/inf) interdite")
    return valeur


# Type réutilisable : tout float|None de score/ratio exposé doit au minimum rejeter NaN/inf.
FiniteFloatOrNone = Annotated[float | None, AfterValidator(_rejeter_non_fini)]


def valider_borne_plausible(valeur: float | None, borne_abs: float, nom: str) -> None:
    """Rejette une valeur finie hors de [-borne_abs, borne_abs] — score LLM invraisemblable (NaN/inf déjà filtré en amont)."""
    if valeur is not None and abs(valeur) > borne_abs:
        raise ValueError(
            f"{nom} hors plage plausible [-{borne_abs}, {borne_abs}] : {valeur}"
        )
