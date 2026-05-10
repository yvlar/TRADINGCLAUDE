"""Tests E2E — Page d'analyse individuelle."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_graham_bns_affiche_resultat(authenticated_page):
    """Analyser BNS avec ratios Graham par défaut → résultat affiché avec score et verdict."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Cliquer sur Analyser avec les ratios BNS par défaut
    page.get_by_role("button", name="Analyser").click()

    # Attendre que le résultat apparaisse
    result_ticker = page.locator("[data-testid='result-ticker']")
    expect(result_ticker).to_be_visible(timeout=15_000)
    assert "BNS" in result_ticker.text_content()

    # Score Graham visible
    expect(page.locator("[data-testid='graham-score']")).to_be_visible()

    # Verdict visible
    expect(page.locator("[data-testid='graham-verdict']")).to_be_visible()


def test_resultat_efface_au_changement_ticker(authenticated_page):
    """Soumettre une analyse, changer le ticker et resoumettre — l'ancien résultat disparaît."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Première analyse BNS
    page.get_by_role("button", name="Analyser").click()
    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=15_000)

    # Changer le ticker pour TD
    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("")
    ticker_input.type("TD")

    # Re-soumettre
    page.get_by_role("button", name="Analyser").click()

    # L'ancien résultat doit disparaître pendant le chargement
    # et le nouveau résultat doit montrer TD
    result_ticker = page.locator("[data-testid='result-ticker']")
    expect(result_ticker).to_be_visible(timeout=15_000)
    expect(result_ticker).to_have_text("TD")


def test_workflow_fast_grower_lynch_pas_de_graham(authenticated_page):
    """workflow fast_grower_lynch sans lynch_ratios → aucune section Graham affichée."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Sélectionner fast_grower_lynch via le select natif caché
    page.locator("[data-testid='workflow-selector']").select_option("fast_grower_lynch")

    page.get_by_role("button", name="Analyser").click()

    # Attendre que la requête se termine (le ticker au moins)
    page.wait_for_timeout(3_000)

    # Sans lynch_ratios, aucun skill ne tourne → pas de section Graham
    assert not page.locator("[data-testid='graham-score']").is_visible()


def test_analyse_successif_deux_tickers(authenticated_page):
    """Analyser BNS puis AAPL successivement : chaque résultat s'affiche sans erreur."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Première analyse BNS
    page.get_by_role("button", name="Analyser").click()
    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=15_000)
    expect(page.locator("[data-testid='error-message']")).not_to_be_visible()

    # Changer pour AAPL
    page.get_by_label("Ticker").fill("AAPL")
    page.get_by_role("button", name="Analyser").click()
    result = page.locator("[data-testid='result-ticker']")
    expect(result).to_be_visible(timeout=15_000)
    expect(result).to_have_text("AAPL")
    expect(page.locator("[data-testid='error-message']")).not_to_be_visible()


def test_erreur_ratios_invalides_affiche_message(authenticated_page):
    """Vider le champ P/E (null) et soumettre → message d'erreur visible."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Vider P/E pour provoquer une erreur côté backend
    pe_input = page.get_by_label("P/E")
    pe_input.fill("")

    # Vider P/B aussi
    page.get_by_label("P/B").fill("")

    page.get_by_role("button", name="Analyser").click()

    # Un message d'erreur doit apparaître (backend retourne 422 ou erreur)
    error_div = page.locator("[data-testid='error-message']")
    expect(error_div).to_be_visible(timeout=10_000)
