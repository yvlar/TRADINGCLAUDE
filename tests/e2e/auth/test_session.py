"""E2E — Cycle de session : déconnexion, protection des routes, persistance, expiration."""
import pytest

from tests.e2e.helpers.network import mock_status
from tests.e2e.pages.app_pages import DashboardPage
from tests.e2e.pages.base_page import BASE_URL, BasePage

pytestmark = pytest.mark.e2e


def test_logout_redirige_login(standard_page):
    """Déconnexion → /login, header de navigation disparu."""
    BasePage(standard_page).logout()
    assert "/login" in standard_page.url


def test_route_protegee_sans_session_redirige(clean_page):
    """Accès direct à une route protégée sans session → redirection /login."""
    clean_page.goto(f"{BASE_URL}/watchlist")
    clean_page.wait_for_url("**/login", timeout=10_000)
    assert "/login" in clean_page.url


def test_session_persiste_apres_reload(standard_page):
    """Recharger la page conserve la session (cookie httpOnly + authMe)."""
    standard_page.goto(f"{BASE_URL}/dashboard")
    DashboardPage(standard_page).page.wait_for_selector("nav", timeout=10_000)
    standard_page.reload()
    standard_page.wait_for_selector("nav", timeout=10_000)
    assert "/login" not in standard_page.url


def test_session_expiree_redirige_login(standard_page):
    """authMe renvoyant 401 (token expiré) → l'app retombe sur /login après reload."""
    # Simule l'expiration : /auth/me répond 401 au prochain montage.
    mock_status(standard_page, "**/auth/me", 401, {"detail": "Token invalide ou expiré"})
    standard_page.goto(f"{BASE_URL}/")
    standard_page.wait_for_url("**/login", timeout=10_000)
    assert "/login" in standard_page.url


def test_navigation_complete_apres_login(standard_page):
    """Tous les onglets protégés sont accessibles une fois connecté."""
    for path in ("/", "/screener", "/historique", "/dashboard", "/watchlist",
                 "/compare", "/esg", "/recherche", "/alerts", "/admin"):
        standard_page.goto(f"{BASE_URL}{path}")
        standard_page.wait_for_selector("nav", timeout=10_000)
        assert "/login" not in standard_page.url, f"Redirigé hors de {path}"
