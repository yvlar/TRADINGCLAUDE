from __future__ import annotations

import os

# Source unique des environnements non-production tolérant les replis de dev.
# Tout garde-fou fail-closed (CSRF, CORS, auth, secret JWT) s'appuie dessus.
_DEV_ENVS = frozenset({"dev", "development", "test", "testing"})


def is_dev_environment() -> bool:
    """Vrai si APP_ENV désigne explicitement un environnement de dev/test.

    APP_ENV absent, vide ou inconnu est traité comme production (défaut sûr) :
    les protections fail-closed restent actives plutôt que de se désactiver
    silencieusement sur une variable d'environnement oubliée.
    """
    return os.environ.get("APP_ENV", "").strip().lower() in _DEV_ENVS
