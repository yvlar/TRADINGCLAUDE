"""E2E — Sécurité : protection des routes, RBAC admin, CSRF, anti-énumération."""
import pytest

from tests.e2e.fixtures.personas import PERSONAS
from tests.e2e.helpers.network import mock_status
from tests.e2e.pages.auth_pages import LoginPage
from tests.e2e.pages.base_page import BASE_URL

pytestmark = pytest.mark.e2e

_PROTECTED = ["/", "/screener", "/historique", "/dashboard", "/watchlist",
              "/compare", "/esg", "/recherche", "/alerts", "/admin"]


@pytest.mark.parametrize("path", _PROTECTED)
def test_routes_protegees_redirigent_sans_session(clean_context, path):
    """Aucune route protégée n'est accessible sans session (defense in depth UI)."""
    p = clean_context.new_page()
    p.goto(f"{BASE_URL}{path}")
    p.wait_for_url("**/login", timeout=10_000)
    assert "/login" in p.url
    p.close()


def test_message_login_ne_revele_pas_existence(clean_page):
    """Mauvais mot de passe et email inconnu produisent le MÊME message."""
    login = LoginPage(clean_page).goto()

    login.login(PERSONAS["standard"].email, "FauxPass1!@#")
    login.expect_error()
    msg_existant = login.error.inner_text()

    clean_page.goto(f"{BASE_URL}/login")
    login.login("vraiment-inconnu@nulle.part", "FauxPass1!@#")
    login.expect_error()
    msg_inconnu = login.error.inner_text()

    assert msg_existant == msg_inconnu, "Le message d'erreur divulgue l'existence du compte"


def test_aucun_secret_dans_localstorage_apres_login(standard_page):
    """Le flux cookie ne doit pas écrire de JWT/secret en localStorage."""
    storage = standard_page.evaluate("() => JSON.stringify(window.localStorage)")
    lowered = storage.lower()
    for needle in ("access_token", "refresh_token", "bearer", "hashed", "argon2"):
        assert needle not in lowered, f"Secret potentiel exposé en localStorage : {needle}"


def test_csrf_token_cookie_present_apres_login(standard_page):
    """Le cookie csrf_token (non-httpOnly, double-submit) est bien posé."""
    cookies = standard_page.context.cookies()
    names = {c["name"] for c in cookies}
    assert "csrf_token" in names, "Cookie CSRF manquant après connexion"
    # access_token doit être httpOnly (inaccessible au JS).
    access = next((c for c in cookies if c["name"] == "access_token"), None)
    if access is not None:
        assert access.get("httpOnly") is True, "access_token devrait être httpOnly"


def test_session_revoquee_bloque_navigation(standard_page):
    """Token révoqué (401 sur /auth/me) → l'app n'expose plus le contenu protégé."""
    mock_status(standard_page, "**/auth/me", 401, {"detail": "Token révoqué"})
    standard_page.goto(f"{BASE_URL}/dashboard")
    standard_page.wait_for_url("**/login", timeout=10_000)
    assert "/login" in standard_page.url
