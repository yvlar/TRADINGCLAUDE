"""E2E — Suite de non-régression.

Convention : un test par bogue, nommé `test_BUGNNN_<description>`, rattaché au
numéro de ticket. Tout bogue découvert en production OU pendant l'écriture de
cette stratégie y est ancré de façon permanente.

Les BUG ci-dessous sont les défauts RÉELS mis au jour par l'audit E2E de ce
sprint (voir STRATEGIE-QA-E2E.md §« Zones à risque »). Chacun verrouille le
comportement attendu une fois corrigé.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.fixtures.personas import PERSONAS
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.helpers.network import mock_corrupt
from tests.e2e.pages.app_pages import AnalyzePage, WatchlistPage
from tests.e2e.pages.auth_pages import LoginPage
from tests.e2e.pages.base_page import BASE_URL

pytestmark = [pytest.mark.e2e, pytest.mark.regression]


def test_BUG001_ancien_e2e_auth_ciblait_ecran_cle_api_disparu(clean_page):
    """BUG-001 — Les E2E d'auth testaient l'écran « Clé API » supprimé.

    L'app utilise désormais email/mot de passe + cookie JWT. Ce test verrouille
    le fait que le formulaire moderne (email-input + password-input) est présent.
    """
    LoginPage(clean_page).goto()
    # to_have_count auto-attend le montage du chunk lazy LoginPage (count() ne l'attend pas).
    expect(clean_page.get_by_test_id("email-input")).to_have_count(1)
    expect(clean_page.get_by_test_id("password-input")).to_have_count(1)
    # L'ancien libellé « Clé API » ne doit plus exister.
    expect(clean_page.get_by_label("Clé API")).to_have_count(0)


def test_BUG002_authme_401_ne_laisse_pas_page_protegee_visible(standard_page):
    """BUG-002 — Une session invalidée doit retomber sur /login, pas afficher / vide."""
    from tests.e2e.helpers.network import mock_status

    mock_status(standard_page, "**/auth/me", 401, {"detail": "expiré"})
    standard_page.goto(f"{BASE_URL}/watchlist")
    standard_page.wait_for_url("**/login", timeout=10_000)
    assert "/login" in standard_page.url


def test_BUG003_compte_suspendu_ne_peut_pas_se_connecter(clean_page):
    """BUG-003 — Un compte is_active=False ne doit jamais ouvrir de session."""
    persona = PERSONAS["suspended"]
    login = LoginPage(clean_page).goto()
    login.login(persona.email, persona.password)
    login.expect_error()
    assert "/login" in clean_page.url


def test_BUG004_reponse_analyse_corrompue_ne_crashe_pas_react(authenticated_page):
    """BUG-004 — Un flux SSE tronqué ne doit pas déclencher d'Error Boundary.

    Un flux SSE corrompu n'émet aucun event exploitable (ni résultat, ni erreur) :
    on vérifie l'absence de crash React et le retour à l'état idle (bouton réactivé).
    """
    from playwright.sync_api import expect

    with PageMonitor(authenticated_page) as mon:
        mock_corrupt(authenticated_page, "**/analyze-stream**")
        page = AnalyzePage(authenticated_page).goto()
        page.ticker.fill("BNS")
        page.testid("autofill-button").click()
        page.submit.click()
        expect(page.submit).to_be_enabled(timeout=15_000)
    assert not mon.react_faults(), f"Error Boundary déclenchée : {mon.react_faults()}"
    assert page.result_ticker.count() == 0


def test_BUG005_watchlist_doublon_message_clair(authenticated_page):
    """BUG-005 — Doublon → message lisible côté UI (garde client).

    La parité backend (DB unique + 409) est verrouillée par
    `tests/services/test_watchlist_duplicate.py` ; ici on vérifie que l'utilisateur
    voit un message clair plutôt qu'un échec silencieux.
    """
    page = WatchlistPage(authenticated_page).goto()
    page.add("ENB")
    page.expect_testid_visible("watchlist-row", timeout=15_000)
    page.add("ENB")
    page.expect_testid_visible("watchlist-error", timeout=10_000)
