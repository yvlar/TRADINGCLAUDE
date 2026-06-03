"""Tests E2E Playwright — POST /analyze-stream (SSE streaming skill par skill)."""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

_URL = "http://localhost:5173/"
_TIMEOUT = 15_000  # ms — inclut le temps de streaming complet


def test_streaming_emet_skill_start(authenticated_page):
    """streaming-progress apparaît dans le DOM lors du traitement des skill_start events."""
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("BNS")

    # MutationObserver : capturera streaming-progress même s'il disparaît vite
    page.evaluate("""() => {
        window._streamingProgressSeen = false;
        const observer = new MutationObserver(() => {
            if (document.querySelector('[data-testid="streaming-progress"]')) {
                window._streamingProgressSeen = true;
                observer.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }""")

    page.get_by_role("button", name="Analyser").click()

    # result-ticker confirme la fin du streaming (event complete reçu)
    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=_TIMEOUT)

    # Vérifier que streaming-progress a bien été présent dans le DOM
    was_seen = page.evaluate("() => Boolean(window._streamingProgressSeen)")
    assert was_seen, (
        "streaming-progress n'a jamais été visible — "
        "les skill_start events SSE ne sont pas traités par le frontend"
    )


def test_streaming_affiche_progression_skills(authenticated_page):
    """skill-done-* éléments apparaissent dans streaming-progress au fil des skill_result events."""
    page = authenticated_page
    page.goto(_URL)
    page.wait_for_selector("text=Analyse individuelle", timeout=8_000)

    ticker_input = page.get_by_label("Ticker")
    ticker_input.fill("BNS")

    # Capturer tous les data-testid "skill-done-*" ajoutés pendant le streaming
    page.evaluate("""() => {
        window._skillsDoneSeen = new Set();
        const observer = new MutationObserver(() => {
            document.querySelectorAll('[data-testid^="skill-done-"]').forEach(el => {
                const tid = el.getAttribute('data-testid');
                if (tid) window._skillsDoneSeen.add(tid);
            });
        });
        observer.observe(document.body, {
            childList: true, subtree: true, attributes: true, attributeFilter: ['data-testid']
        });
    }""")

    page.get_by_role("button", name="Analyser").click()

    # Attendre la fin du streaming
    expect(page.locator("[data-testid='result-ticker']")).to_be_visible(timeout=_TIMEOUT)

    # Au moins 2 skills doivent avoir été complétés via streaming-progress
    skills_seen = page.evaluate("() => window._skillsDoneSeen.size")
    assert skills_seen >= 2, (
        f"Seulement {skills_seen} skill(s) vu(s) dans streaming-progress, attendu ≥ 2 — "
        "les skill_result events SSE ne sont pas traités par le frontend"
    )


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
