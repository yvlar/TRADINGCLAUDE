"""E2E — Analyse individuelle (workflow multi-skills, streaming, erreurs API)."""
import pytest

from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.helpers.network import mock_abort, mock_corrupt, mock_status
from tests.e2e.pages.app_pages import AnalyzePage

pytestmark = pytest.mark.e2e


def test_analyse_happy_path_graham(authenticated_page):
    """Analyse BNS via value_graham → verdict Graham rendu, parcours propre."""
    with PageMonitor(authenticated_page) as mon:
        page = AnalyzePage(authenticated_page).goto()
        page.ticker.fill("BNS")
        page.testid("autofill-button").click()
        page.submit.click()
        page.expect_graham_verdict()
    assert_page_clean(mon)


def test_analyse_workflow_lynch(authenticated_page):
    """Le sélecteur de workflow route vers la séquence Lynch sans erreur."""
    page = AnalyzePage(authenticated_page).goto()
    page.ticker.fill("BNS")
    page.testid("autofill-button").click()
    page.workflow_selector.select_option("fast_grower_lynch")
    page.submit.click()
    page.expect_testid_visible("result-ticker", timeout=30_000)


def test_analyse_ticker_vide_bloque(authenticated_page):
    """Soumettre sans ticker ne déclenche aucune requête d'analyse."""
    page = AnalyzePage(authenticated_page).goto()
    page.submit.click()
    # Pas de résultat attendu — la validation client doit empêcher l'appel.
    assert page.result_ticker.count() == 0


def test_analyse_backend_500_affiche_erreur(authenticated_page):
    """Un 500 backend (stream/analyse) → message d'erreur, pas d'écran blanc."""
    with PageMonitor(authenticated_page) as mon:
        mock_status(authenticated_page, "**/analyze**", 500, {"detail": "Erreur interne"})
        page = AnalyzePage(authenticated_page).goto()
        page.ticker.fill("BNS")
        page.testid("autofill-button").click()
        page.submit.click()
        page.expect_testid_visible("error-message", timeout=15_000)
    # 500 attendu ici, mais aucun Traceback ne doit fuiter dans l'UI.
    assert not mon.backend_faults(), mon.backend_faults()


def test_analyse_api_indisponible(authenticated_page):
    """Connexion coupée → l'app dégrade proprement avec un message d'erreur."""
    mock_abort(authenticated_page, "**/analyze**")
    page = AnalyzePage(authenticated_page).goto()
    page.ticker.fill("BNS")
    page.testid("autofill-button").click()
    page.submit.click()
    page.expect_testid_visible("error-message", timeout=15_000)


def test_analyse_reponse_corrompue(authenticated_page):
    """JSON tronqué → pas de crash React, message d'erreur affiché."""
    with PageMonitor(authenticated_page) as mon:
        mock_corrupt(authenticated_page, "**/analyze**")
        page = AnalyzePage(authenticated_page).goto()
        page.ticker.fill("BNS")
        page.testid("autofill-button").click()
        page.submit.click()
        page.expect_testid_visible("error-message", timeout=15_000)
    assert not mon.react_faults(), mon.react_faults()
