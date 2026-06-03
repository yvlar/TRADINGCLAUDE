"""Assertions personnalisées (« custom matchers ») pour les parcours E2E.

L'API `expect` de Playwright Python ne s'étend pas comme `expect.extend` en JS ;
on fournit donc des fonctions d'assertion explicites, composables, à message clair.
"""
from __future__ import annotations

from tests.e2e.helpers.monitoring import PageMonitor


def assert_no_console_errors(monitor: PageMonitor) -> None:
    """Échoue si la moindre console.error inattendue a été émise."""
    if monitor.console_errors:
        details = "\n".join(f"  [{c.type}] {c.text}  ({c.location})" for c in monitor.console_errors)
        raise AssertionError(f"{len(monitor.console_errors)} erreur(s) console détectée(s) :\n{details}")


def assert_no_page_errors(monitor: PageMonitor) -> None:
    """Échoue sur exception JS non interceptée / promesse rejetée non gérée."""
    if monitor.page_errors:
        details = "\n".join(f"  {e}" for e in monitor.page_errors)
        raise AssertionError(f"{len(monitor.page_errors)} erreur(s) page (unhandled) :\n{details}")


def assert_no_react_faults(monitor: PageMonitor) -> None:
    """Échoue sur Error Boundary, erreur d'hydratation ou erreur React minifiée."""
    faults = monitor.react_faults()
    if faults:
        raise AssertionError("Défaut(s) React détecté(s) :\n" + "\n".join(f"  {f}" for f in faults))


def assert_no_backend_faults(monitor: PageMonitor) -> None:
    """Échoue si une réponse 5xx expose un Traceback / ValidationError / DatabaseError."""
    faults = monitor.backend_faults()
    if faults:
        raise AssertionError("Défaut(s) backend détecté(s) :\n" + "\n".join(f"  {f}" for f in faults))


def assert_no_unexpected_network_errors(
    monitor: PageMonitor, allow_status: list[int] | None = None
) -> None:
    """Échoue sur toute réponse ≥ 400 hors codes explicitement attendus + requêtes échouées."""
    unexpected = monitor.unexpected_responses(allow_status)
    if unexpected:
        details = "\n".join(f"  {r.method} {r.url} → {r.status}" for r in unexpected)
        raise AssertionError(
            f"{len(unexpected)} réponse(s) réseau inattendue(s) "
            f"(autorisés={allow_status or []}) :\n{details}"
        )
    if monitor.failed_requests:
        details = "\n".join(f"  {f}" for f in monitor.failed_requests)
        raise AssertionError(f"{len(monitor.failed_requests)} requête(s) échouée(s) :\n{details}")


def assert_page_clean(monitor: PageMonitor, allow_status: list[int] | None = None) -> None:
    """Garde-fou global : agrège toutes les vérifications de défaut silencieux.

    À appeler en fin de chaque parcours « happy path ». Les codes de `allow_status`
    sont tolérés (ex. un test qui provoque délibérément un 404).
    """
    assert_no_console_errors(monitor)
    assert_no_page_errors(monitor)
    assert_no_react_faults(monitor)
    assert_no_backend_faults(monitor)
    assert_no_unexpected_network_errors(monitor, allow_status)
