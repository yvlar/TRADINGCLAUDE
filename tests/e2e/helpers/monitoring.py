"""Surveillance navigateur + réseau pour faire échouer un test sur défaut silencieux.

Un parcours « vert » qui crache une `console.error`, une promesse rejetée non
gérée, une Error Boundary React, une erreur d'hydratation, ou une réponse 500 du
backend est en réalité un test rouge. Ces moniteurs capturent ces signaux pour
qu'une assertion explicite les transforme en échec (`helpers.assertions`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from playwright.sync_api import ConsoleMessage, Page, Request, Response

# Bruit de console connu et inoffensif à filtrer (React DevTools, sourcemaps Vite…).
_CONSOLE_ALLOWLIST = (
    re.compile(r"Download the React DevTools", re.I),
    re.compile(r"\[vite\] connect", re.I),
)

# Motifs trahissant un défaut backend renvoyé jusqu'au client.
_BACKEND_FAULT = re.compile(
    r"Traceback|Internal Server Error|ValidationError|DatabaseError|"
    r"IntegrityError|TimeoutError|asyncpg|psycopg",
    re.I,
)

# Motifs React critiques (Error Boundary, hydratation, clés manquantes graves).
_REACT_FAULT = re.compile(
    r"hydrat|did not match|Minified React error|"
    r"boundary|Maximum update depth|Cannot update a component",
    re.I,
)


@dataclass
class CapturedConsole:
    type: str
    text: str
    location: str = ""


@dataclass
class CapturedResponse:
    url: str
    status: int
    method: str
    body_excerpt: str = ""


@dataclass
class PageMonitor:
    """Attache des écouteurs à une page et accumule les signaux de défaut.

    Usage :
        with PageMonitor(page) as mon:
            ... parcours ...
        mon.assert_clean()                  # aucun défaut inattendu
        mon.assert_clean(allow_status=[404]) # tolère certains codes attendus
    """

    page: Page
    console_errors: list[CapturedConsole] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    failed_requests: list[str] = field(default_factory=list)
    bad_responses: list[CapturedResponse] = field(default_factory=list)
    _capture_bodies: bool = True

    def __enter__(self) -> "PageMonitor":
        self.page.on("console", self._on_console)
        self.page.on("pageerror", self._on_page_error)
        self.page.on("requestfailed", self._on_request_failed)
        self.page.on("response", self._on_response)
        return self

    def __exit__(self, *exc: object) -> None:
        # Les écouteurs Playwright sont liés à la page ; rien à détacher
        # explicitement puisque la page est jetée après chaque test.
        return None

    # ---- écouteurs ---------------------------------------------------------

    def _on_console(self, msg: ConsoleMessage) -> None:
        if msg.type not in ("error", "warning"):
            return
        text = msg.text
        if any(p.search(text) for p in _CONSOLE_ALLOWLIST):
            return
        loc = ""
        try:
            loc = f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}"
        except Exception:
            pass
        # Seules les vraies erreurs (ou warnings React critiques) comptent.
        if msg.type == "error" or _REACT_FAULT.search(text):
            self.console_errors.append(CapturedConsole(msg.type, text, loc))

    def _on_page_error(self, error: object) -> None:
        # Promesse rejetée non gérée / exception JS non interceptée.
        self.page_errors.append(str(error))

    def _on_request_failed(self, request: Request) -> None:
        failure = request.failure or ""
        # `net::ERR_ABORTED` est émis par les navigations annulées (lazy chunks,
        # téléchargements de blob) — pas un défaut applicatif.
        if "ERR_ABORTED" in str(failure):
            return
        self.failed_requests.append(f"{request.method} {request.url} — {failure}")

    def _on_response(self, response: Response) -> None:
        if response.status < 400:
            return
        excerpt = ""
        if self._capture_bodies and response.status >= 500:
            try:
                excerpt = response.text()[:500]
            except Exception:
                excerpt = "<corps illisible>"
        self.bad_responses.append(
            CapturedResponse(response.url, response.status, response.request.method, excerpt)
        )

    # ---- agrégations -------------------------------------------------------

    def react_faults(self) -> list[str]:
        faults = [e.text for e in self.console_errors if _REACT_FAULT.search(e.text)]
        faults += [e for e in self.page_errors if _REACT_FAULT.search(e)]
        return faults

    def backend_faults(self) -> list[str]:
        faults = [r.body_excerpt for r in self.bad_responses if _BACKEND_FAULT.search(r.body_excerpt)]
        faults += [e.text for e in self.console_errors if _BACKEND_FAULT.search(e.text)]
        return faults

    def unexpected_responses(self, allow_status: list[int] | None = None) -> list[CapturedResponse]:
        allowed = set(allow_status or [])
        return [r for r in self.bad_responses if r.status not in allowed]
