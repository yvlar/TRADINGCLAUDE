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
    """Sans ticker, le bouton Analyser est désactivé — aucune requête possible."""
    from playwright.sync_api import expect

    page = AnalyzePage(authenticated_page).goto()
    # La validation client désactive le bouton tant que le ticker est vide.
    expect(page.submit).to_be_disabled()
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


def test_analyse_successive_deux_tickers(authenticated_page):
    """Analyser BNS puis AAPL : chaque résultat s'affiche, sans message d'erreur (migré legacy)."""
    from playwright.sync_api import expect

    page = AnalyzePage(authenticated_page).goto()
    page.ticker.fill("BNS")
    page.testid("autofill-button").click()
    page.submit.click()
    page.expect_result("BNS")
    expect(page.error).not_to_be_visible()

    page.ticker.fill("AAPL")
    page.submit.click()
    page.expect_result("AAPL")
    expect(page.error).not_to_be_visible()


def test_resultat_efface_au_changement_ticker(authenticated_page):
    """Resoumettre avec un nouveau ticker remplace l'ancien résultat (migré legacy)."""
    from playwright.sync_api import expect

    page = AnalyzePage(authenticated_page).goto()
    page.ticker.fill("BNS")
    page.testid("autofill-button").click()
    page.submit.click()
    page.expect_result("BNS")

    page.ticker.fill("TD")
    page.submit.click()
    expect(page.result_ticker).to_have_text("TD", timeout=30_000)


def test_analyse_reponse_corrompue(authenticated_page):
    """Flux SSE tronqué → pas de crash React ; l'app revient à l'état idle, sans résultat."""
    from playwright.sync_api import expect

    with PageMonitor(authenticated_page) as mon:
        mock_corrupt(authenticated_page, "**/analyze-stream**")
        page = AnalyzePage(authenticated_page).goto()
        page.ticker.fill("BNS")
        page.testid("autofill-button").click()
        page.submit.click()
        # Le flux se termine sans event exploitable : le bouton se réactive (isStreaming=false).
        expect(page.submit).to_be_enabled(timeout=15_000)
    assert not mon.react_faults(), mon.react_faults()
    assert page.result_ticker.count() == 0
