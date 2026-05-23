"""Tests E2E — Authentification (LoginPage, déconnexion, redirections)."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_redirect_login_sans_token(backend_server, browser_context):
    """Sans api_token dans localStorage, / redirige vers /login."""
    # Contexte sans init_script pour cette session

    with browser_context.browser.new_context(base_url="http://localhost:5173") as ctx:
        p = ctx.new_page()
        p.goto("http://localhost:5173/")
        p.wait_for_url("**/login", timeout=8_000)
        assert "/login" in p.url
        p.close()


def test_login_cle_valide(backend_server, browser_context):
    """Saisir une clé API valide connecte l'utilisateur et navigue vers /."""
    with browser_context.browser.new_context(base_url="http://localhost:5173") as ctx:
        p = ctx.new_page()
        p.goto("http://localhost:5173/login")
        p.get_by_label("Clé API").fill("test-secret")
        p.get_by_role("button", name="Se connecter").click()
        p.wait_for_url("http://localhost:5173/", timeout=8_000)
        assert p.url.rstrip("/") == "http://localhost:5173"
        p.close()


def test_login_cle_vide_desactive_bouton(backend_server, browser_context):
    """Le bouton Se connecter est désactivé quand le champ clé est vide."""
    with browser_context.browser.new_context(base_url="http://localhost:5173") as ctx:
        p = ctx.new_page()
        p.goto("http://localhost:5173/login")
        btn = p.get_by_role("button", name="Se connecter")
        assert btn.is_disabled()
        p.close()


def test_deconnexion_redirect_login(authenticated_page):
    """Cliquer sur Déconnexion redirige vers /login."""
    page = authenticated_page
    page.get_by_role("button", name="Déconnexion").click()
    page.wait_for_url("**/login", timeout=8_000)
    assert "/login" in page.url
    # Le formulaire de login est visible après déconnexion
    expect(page.get_by_role("button", name="Se connecter")).to_be_visible(timeout=5_000)
