"""Tests E2E — Page Screener."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_3_tickers_affiche_tableau(authenticated_page):
    """Screener sur BNS, TD, RY → tableau avec 3 lignes."""
    page = authenticated_page
    page.goto("http://localhost:5173/screener")
    page.wait_for_selector("text=Screener", timeout=8_000)

    tickers_area = page.get_by_label("Tickers")
    tickers_area.fill("BNS, TD, RY")

    page.get_by_role("button", name="Lancer le screener").click()

    # Attendre les lignes du tableau
    rows = page.locator("[data-testid='screener-row']")
    expect(rows.first).to_be_visible(timeout=20_000)
    expect(rows).to_have_count(3)


def test_badge_verdict_colore(authenticated_page):
    """Chaque ligne du screener affiche un badge verdict."""
    page = authenticated_page
    page.goto("http://localhost:5173/screener")
    page.wait_for_selector("text=Screener", timeout=8_000)

    page.get_by_label("Tickers").fill("BNS")
    page.get_by_role("button", name="Lancer le screener").click()

    badge = page.locator("[data-testid='verdict-badge']").first
    expect(badge).to_be_visible(timeout=15_000)
    # Le stub retourne "CANDIDAT_SOLIDE" pour le verdict Graham
    assert badge.text_content().strip() != ""


def test_ticker_majuscule_auto(authenticated_page):
    """Le ticker saisi en minuscules apparaît en majuscules dans le tableau."""
    page = authenticated_page
    page.goto("http://localhost:5173/screener")
    page.wait_for_selector("text=Screener", timeout=8_000)

    page.get_by_label("Tickers").fill("bns")
    page.get_by_role("button", name="Lancer le screener").click()

    ticker_cell = page.locator("[data-testid='screener-ticker']").first
    expect(ticker_cell).to_be_visible(timeout=15_000)
    assert ticker_cell.text_content().strip() == "BNS"
