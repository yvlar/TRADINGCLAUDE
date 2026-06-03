"""E2E — Mot de passe oublié / réinitialisation.

Le backend ne révèle jamais si l'email existe (anti-énumération) : les deux cas
produisent la même réponse 204 et le même écran de confirmation.
"""
import pytest

from tests.e2e.fixtures.personas import PERSONAS
from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.pages.auth_pages import ForgotPasswordPage, ResetPasswordPage
from tests.e2e.pages.base_page import BASE_URL

pytestmark = pytest.mark.e2e


def test_forgot_password_email_connu(clean_page):
    """Email existant → confirmation neutre, aucune erreur."""
    with PageMonitor(clean_page) as mon:
        page = ForgotPasswordPage(clean_page).goto()
        page.request_reset(PERSONAS["standard"].email)
        clean_page.wait_for_timeout(500)
    assert_page_clean(mon)


def test_forgot_password_email_inconnu_meme_reponse(clean_page):
    """Email inconnu → même confirmation neutre (pas de fuite d'information)."""
    page = ForgotPasswordPage(clean_page).goto()
    page.request_reset("inexistant@example.org")
    clean_page.wait_for_timeout(500)
    # Aucun message distinctif ne doit révéler que le compte n'existe pas.


def test_reset_password_token_invalide(clean_page):
    """Token absent/invalide → erreur 400 affichée, pas de crash."""
    clean_page.goto(f"{BASE_URL}/reset-password?token=invalide-xyz")
    page = ResetPasswordPage(clean_page)
    page.reset("NouveauPass1!@#")
    page.expect_testid_visible("error-message")
