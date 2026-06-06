from __future__ import annotations

import os
from collections.abc import Iterable

from starlette.requests import Request


def trusted_proxies_from_env() -> frozenset[str]:
    """IP des proxys de confiance, lues depuis TRUSTED_PROXY_IPS (CSV).

    Vide par défaut : aucun proxy de confiance → X-Forwarded-For ignoré (le défaut
    sûr, anti-spoof). À renseigner avec l'IP du reverse proxy (Caddy) en production.
    """
    raw = os.environ.get("TRUSTED_PROXY_IPS", "")
    return frozenset(p.strip() for p in raw.split(",") if p.strip())


def resolve_client_ip(request: Request, trusted_proxies: Iterable[str]) -> str:
    """IP réelle du client, à l'épreuve du spoof de X-Forwarded-For.

    X-Forwarded-For n'est honoré que si la connexion directe provient d'un proxy
    de confiance ; sinon un client pourrait forger l'en-tête pour usurper une IP
    (et contourner le rate-limit). Derrière un proxy de confiance unique (Caddy),
    le client d'origine est la première entrée de la liste.
    """
    peer = request.client.host if request.client else "unknown"
    if peer in set(trusted_proxies):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return peer
