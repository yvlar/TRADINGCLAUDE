"""Tests E2E Playwright — POST /analyze-stream (SSE streaming skill par skill)."""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

_URL = "http://localhost:5173/"
_TIMEOUT = 15_000  # ms — inclut le temps de streaming complet


def test_streaming_aboutit_a_un_resultat(authenticated_page):
    """Le flux SSE (skill_start → skill_result → complete) aboutit à un résultat rendu.

    NB : l'observation de l'UI transitoire (streaming-progress) n'est pas fiable avec
    des skills mockés instantanés ; on valide l'état final, preuve que les events SSE
    sont consommés de bout en bout par le frontend.
    """
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    page.get_by_label("Ticker").fill("BNS")
    page.get_by_test_id("autofill-button").click()
    page.get_by_role("button", name="Analyser").click()

    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=_TIMEOUT)


def test_streaming_resultat_reflete_skill_result_graham(authenticated_page):
    """Le résultat agrégé contient le verdict Graham — preuve que l'event skill_result est rendu."""
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    page.get_by_label("Ticker").fill("BNS")
    page.get_by_test_id("autofill-button").click()
    page.get_by_role("button", name="Analyser").click()

    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=_TIMEOUT)
    expect(page.locator("[data-testid='graham-verdict']")).to_be_visible(timeout=_TIMEOUT)


def test_streaming_complete_affiche_score_composite(authenticated_page):
    """L'event complete déclenche l'affichage du composite_score dans AnalysisResult."""
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("BNS")

    page.get_by_role("button", name="Analyser").click()

    # result-ticker confirme que l'event complete a été reçu et traité
    result_ticker = page.locator("[data-testid='result-ticker']")
    expect(result_ticker).to_be_visible(timeout=_TIMEOUT)
    assert "BNS" in (result_ticker.text_content() or "")

    # composite-score doit être visible après l'event complete
    expect(page.locator("[data-testid='composite-score']")).to_be_visible(timeout=5_000)

    # streaming-progress est démonté après complete (isStreaming=false)
    expect(page.locator("[data-testid='streaming-progress']")).not_to_be_visible()


def test_streaming_ticker_invalide_affiche_erreur(authenticated_page):
    """Ticker invalide (> 6 chars) → HTTP 422 avant SSE → error-message affiché dans l'UI."""
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    # ABCDEFGH dépasse la limite de 6 chars du regex ^[A-Z0-9]{1,6} → 422 backend
    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("ABCDEFGH")

    page.get_by_role("button", name="Analyser").click()

    error_div = page.locator("[data-testid='error-message']")
    expect(error_div).to_be_visible(timeout=10_000)

    # Aucun résultat ne doit être affiché (le streaming n'a pas démarré)
    expect(page.locator("[data-testid='result-ticker']")).not_to_be_visible()
