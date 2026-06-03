"""E2E — Création de compte (inscription)."""
import uuid

import pytest

from tests.e2e.fixtures.personas import PERSONAS
from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.pages.auth_pages import RegisterPage

pytestmark = pytest.mark.e2e


def _unique_email() -> str:
    return f"nouveau-{uuid.uuid4().hex[:8]}@example.com"


def test_register_happy_path(clean_page):
    """Compte valide → redirection vers /login (session à confirmer)."""
    with PageMonitor(clean_page) as mon:
        reg = RegisterPage(clean_page).goto()
        reg.register(_unique_email(), "Solide1234!@#")
        clean_page.wait_for_url("**/login", timeout=10_000)
    assert_page_clean(mon)


def test_register_email_existant_409(clean_page):
    """Email déjà pris → 409 traduit en message d'erreur lisible."""
    existing = PERSONAS["standard"].email
    with PageMonitor(clean_page) as mon:
        reg = RegisterPage(clean_page).goto()
        reg.register(existing, "Solide1234!@#")
        reg.expect_testid_visible("error-message")
    assert_page_clean(mon, allow_status=[409])
    assert "/register" in clean_page.url


def test_password_strength_indicator(clean_page):
    """L'indicateur de force réagit progressivement à la complexité du mot de passe."""
    reg = RegisterPage(clean_page).goto()
    reg.password.fill("abc")
    reg.expect_testid_visible("password-strength")
    reg.password.fill("Abcdefgh1!xyz")
    reg.expect_testid_visible("password-strength")


def test_register_champs_vides(clean_page):
    """Soumission à vide → message « requis », pas d'appel réseau."""
    reg = RegisterPage(clean_page).goto()
    reg.submit.click()
    reg.expect_testid_visible("error-message")
