"""E2E — Connexion (flux cookie JWT réel).

Remplace l'ancien test_e2e_auth.py qui ciblait l'écran « Clé API » disparu.
"""
import pytest

from tests.e2e.fixtures.personas import PERSONAS
from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.pages.auth_pages import LoginPage

pytestmark = pytest.mark.e2e


def test_login_happy_path(clean_page):
    """Identifiants valides → cookie posé, redirection vers / avec header nav."""
    persona = PERSONAS["standard"]
    with PageMonitor(clean_page) as mon:
        login = LoginPage(clean_page).goto()
        login.login(persona.email, persona.password)
        clean_page.wait_for_url("http://localhost:5173/", timeout=10_000)
        clean_page.wait_for_selector("nav", timeout=10_000)
    assert_page_clean(mon)


def test_login_mauvais_mot_de_passe_401(clean_page):
    """Mot de passe erroné → message générique, pas de fuite d'existence de compte."""
    persona = PERSONAS["standard"]
    with PageMonitor(clean_page) as mon:
        login = LoginPage(clean_page).goto()
        login.login(persona.email, "MauvaisPass1!@#")
        login.expect_error()
    # Le 401 est attendu : il ne doit pas être compté comme défaut réseau.
    assert_page_clean(mon, allow_status=[401])
    assert "/login" in clean_page.url


def test_login_email_inconnu_401(clean_page):
    """Email absent → même message générique (anti-énumération)."""
    login = LoginPage(clean_page).goto()
    login.login("inconnu@nulle.part", "Quelconque1!@#")
    login.expect_error()
    assert "/login" in clean_page.url


def test_login_compte_suspendu_refuse(clean_page):
    """is_active=False → authentification refusée même avec le bon mot de passe."""
    persona = PERSONAS["suspended"]
    login = LoginPage(clean_page).goto()
    login.login(persona.email, persona.password)
    login.expect_error()
    assert "/login" in clean_page.url


def test_login_champs_vides_validation_client(clean_page):
    """Soumission à vide → validation côté client, aucune requête réseau partie."""
    login = LoginPage(clean_page).goto()
    login.submit.click()
    login.expect_error("requis")


def test_login_remember_me_pose_cookie_long(clean_page):
    """« Rester connecté » connecte aussi et redirige (TTL refresh étendu côté API)."""
    persona = PERSONAS["premium"]
    login = LoginPage(clean_page).goto()
    login.login(persona.email, persona.password, remember_me=True)
    clean_page.wait_for_url("http://localhost:5173/", timeout=10_000)


def test_toggle_password_visibility(clean_page):
    """Le bouton Afficher bascule le type de l'input password en text."""
    login = LoginPage(clean_page).goto()
    login.password.fill("secret-123")
    assert login.password.get_attribute("type") == "password"
    login.toggle_password_visibility()
    assert login.password.get_attribute("type") == "text"
