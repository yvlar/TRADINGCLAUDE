"""Tests E2E — Page Watchlist.

IMPORTANT : ces tests partagent le même InMemoryWatchlistService (scope session).
Ils doivent s'exécuter dans l'ordre du fichier (pytest exécute de haut en bas).
"""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_liste_vide_message(authenticated_page):
    """Watchlist initialement vide → message 'Aucun ticker en surveillance'."""
    page = authenticated_page
    page.goto("http://localhost:5173/watchlist")
    page.wait_for_selector("text=Watchlist", timeout=8_000)

    rows = page.locator("[data-testid='watchlist-row']")
    if rows.count() > 0:
        pytest.skip("Service watchlist non vide — relancer en session fraîche.")

    expect(page.get_by_text("Aucun ticker en surveillance")).to_be_visible(timeout=5_000)


def test_ajout_ticker(authenticated_page):
    """Ajouter BNS à la watchlist → ligne apparaît dans le tableau."""
    page = authenticated_page
    page.goto("http://localhost:5173/watchlist")
    page.wait_for_selector("text=Watchlist", timeout=8_000)

    page.get_by_label("Ticker").fill("BNS")
    page.get_by_role("button", name="Ajouter").click()

    rows = page.locator("[data-testid='watchlist-row']")
    expect(rows.first).to_be_visible(timeout=8_000)

    tickers_in_table = [rows.nth(i).text_content() for i in range(rows.count())]
    assert any("BNS" in t for t in tickers_in_table)


def test_suppression_ticker(authenticated_page):
    """Ajouter TD puis le supprimer → retour au nombre de lignes précédent."""
    page = authenticated_page
    page.goto("http://localhost:5173/watchlist")
    page.wait_for_selector("text=Watchlist", timeout=8_000)

    initial_count = page.locator("[data-testid='watchlist-row']").count()

    # Ajouter TD
    page.get_by_label("Ticker").fill("TD")
    page.get_by_role("button", name="Ajouter").click()

    rows = page.locator("[data-testid='watchlist-row']")
    expect(rows).to_have_count(initial_count + 1, timeout=8_000)

    # TD est la première ligne (tri par created_at desc) → supprimer la première
    page.get_by_role("button", name="Supprimer").first.click()
    expect(rows).to_have_count(initial_count, timeout=5_000)


def test_doublon_refuse(authenticated_page):
    """Ajouter le même ticker deux fois → message d'erreur côté frontend."""
    page = authenticated_page
    page.goto("http://localhost:5173/watchlist")
    page.wait_for_selector("text=Watchlist", timeout=8_000)

    # Premier ajout RY
    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("RY")
    page.get_by_role("button", name="Ajouter").click()

    # Le champ se vide quand onSuccess est appelé = ajout réussi et entries mis à jour
    expect(ticker_input).to_have_value("", timeout=8_000)

    # Deuxième ajout RY — même workflow value_graham
    page.get_by_label("Ticker").fill("RY")
    page.get_by_role("button", name="Ajouter").click()

    # Le frontend détecte le doublon avant d'appeler l'API
    error = page.locator("[data-testid='watchlist-error']")
    expect(error).to_be_visible(timeout=5_000)
    assert "RY" in error.text_content()
