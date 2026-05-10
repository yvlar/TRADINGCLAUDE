"""Tests E2E Sprint 33 — Auto-fill + checkbox Qualité bénéfices → analyse complète."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_autofill_remplit_champs_graham(authenticated_page):
    """Cliquer Auto-fill sur BNS → champs P/E et P/B pré-remplis depuis GET /extract."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Bouton désactivé avant de saisir un ticker
    autofill_btn = page.locator("[data-testid='autofill-button']")
    expect(autofill_btn).to_be_disabled()

    # Saisir BNS
    page.get_by_label("Ticker").fill("BNS")
    expect(autofill_btn).to_be_enabled()

    # Déclencher Auto-fill
    autofill_btn.click()

    # Attendre que le bouton repasse à "Auto-fill" (fin du chargement)
    expect(autofill_btn).to_have_text("Auto-fill", timeout=10_000)

    # P/E et P/B doivent être pré-remplis avec les valeurs du mock (11.0 et 1.3)
    expect(page.get_by_label("P/E")).to_have_value("11")
    expect(page.get_by_label("P/B")).to_have_value("1.3")


def test_autofill_active_checkbox_earnings(authenticated_page):
    """Après Auto-fill réussi avec earnings_quality disponible → checkbox activée et badge affiché."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Checkbox désactivée avant Auto-fill
    earnings_checkbox = page.locator("[data-testid='earnings-checkbox']")
    expect(earnings_checkbox).to_be_disabled()

    # Auto-fill BNS
    page.get_by_label("Ticker").fill("BNS")
    page.locator("[data-testid='autofill-button']").click()
    expect(page.locator("[data-testid='autofill-button']")).to_have_text("Auto-fill", timeout=10_000)

    # Checkbox doit maintenant être activée
    expect(earnings_checkbox).to_be_enabled()

    # Badge "✓ chargé (Yahoo Finance)" visible
    expect(page.locator("text=✓ chargé (Yahoo Finance)")).to_be_visible()


def test_autofill_earnings_inclus_dans_analyse(authenticated_page):
    """Auto-fill + cocher Qualité bénéfices + Analyser → résultat affiché avec BNS."""
    page = authenticated_page
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # Auto-fill BNS
    page.get_by_label("Ticker").fill("BNS")
    page.locator("[data-testid='autofill-button']").click()
    expect(page.locator("[data-testid='autofill-button']")).to_have_text("Auto-fill", timeout=10_000)

    # Cocher la checkbox earnings (maintenant active)
    earnings_checkbox = page.locator("[data-testid='earnings-checkbox']")
    expect(earnings_checkbox).to_be_enabled()
    earnings_checkbox.check()
    expect(earnings_checkbox).to_be_checked()

    # Lancer l'analyse
    page.get_by_role("button", name="Analyser").click()

    # Résultat affiché pour BNS
    result_ticker = page.locator("[data-testid='result-ticker']")
    expect(result_ticker).to_be_visible(timeout=15_000)
    assert "BNS" in result_ticker.text_content()

    # Score Graham visible (workflow value_graham par défaut)
    expect(page.locator("[data-testid='graham-score']")).to_be_visible()
