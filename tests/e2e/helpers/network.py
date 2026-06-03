"""Helpers d'interception réseau Playwright pour simuler les cas d'erreur API.

Le harnais mocke déjà Claude/DB ; ces helpers couvrent l'autre moitié : forcer
un endpoint donné à répondre 4xx/5xx, renvoyer un corps vide, massif, ou corrompu,
ou ne jamais répondre (timeout) — sans toucher au backend réel.

⚠️ Les globs larges (`**/screen**`, `**/watchlist`) matchent aussi la navigation
du DOCUMENT HTML (ex. `localhost:5173/screener`). On laisse donc TOUJOURS passer
les requêtes de type `document` : sinon la page rend le JSON mocké au lieu de l'app.
"""
from __future__ import annotations

import json

from playwright.sync_api import Page, Route


def _skip_document(route: Route) -> bool:
    """Ne mocke QUE les appels API (xhr/fetch).

    Indispensable : un glob large (`**/analyze**`, `**/screen**`) matche aussi le
    DOCUMENT HTML et, en dev Vite, les MODULES JS de la page (`/src/pages/AnalyzePage.tsx`,
    resource_type `script`). Les intercepter casse le chargement de la page (le
    formulaire ne s'affiche jamais). On laisse donc passer tout sauf xhr/fetch.
    """
    if route.request.resource_type not in ("xhr", "fetch"):
        route.fallback()
        return True
    return False


def mock_status(page: Page, url_glob: str, status: int, body: dict | None = None) -> None:
    """Force toute requête API correspondant à `url_glob` à répondre avec `status`."""

    def handler(route: Route) -> None:
        if _skip_document(route):
            return
        route.fulfill(
            status=status,
            content_type="application/json",
            body=json.dumps(body if body is not None else {"detail": f"Forcé {status}"}),
        )

    page.route(url_glob, handler)


def mock_json(page: Page, url_glob: str, payload: object, status: int = 200) -> None:
    """Répond avec un JSON arbitraire (vide, massif, ou bien formé)."""

    def handler(route: Route) -> None:
        if _skip_document(route):
            return
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))

    page.route(url_glob, handler)


def mock_corrupt(page: Page, url_glob: str) -> None:
    """Répond avec un JSON tronqué/illisible pour éprouver la robustesse du parsing."""

    def handler(route: Route) -> None:
        if _skip_document(route):
            return
        route.fulfill(status=200, content_type="application/json", body='{"ticker": "BNS", ')

    page.route(url_glob, handler)


def mock_abort(page: Page, url_glob: str, error: str = "failed") -> None:
    """Coupe la connexion : simule une API indisponible / réseau perdu."""

    def handler(route: Route) -> None:
        if _skip_document(route):
            return
        route.abort(error)

    page.route(url_glob, handler)


def mock_never_responds(page: Page, url_glob: str) -> None:
    """Ne répond jamais : simule un timeout côté client."""

    def handler(route: Route) -> None:
        if _skip_document(route):
            return
        # Ni fulfill ni abort : la requête reste pendante.

    page.route(url_glob, handler)
