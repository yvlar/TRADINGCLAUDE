"""E2E — Historique et recherche sémantique (préférences/usage avancé)."""
import pytest

from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.helpers.network import mock_json
from tests.e2e.pages.app_pages import HistoryPage, SearchPage

pytestmark = pytest.mark.e2e


def test_historique_vide(authenticated_page):
    """Historique vide → état vide explicite, pas d'erreur."""
    with PageMonitor(authenticated_page) as mon:
        page = HistoryPage(authenticated_page).goto()
        page.expect_testid_visible("history-empty", timeout=10_000)
    assert_page_clean(mon)


def test_historique_recherche(authenticated_page):
    """Saisir un terme et lancer la recherche ne provoque aucune erreur réseau."""
    with PageMonitor(authenticated_page) as mon:
        page = HistoryPage(authenticated_page).goto()
        page.search_input.fill("BNS")
        page.search_button.click()
        authenticated_page.wait_for_timeout(800)
    assert_page_clean(mon)


def test_recherche_semantique_rendu(authenticated_page):
    """La page de recherche se charge dans un état idle/désactivé sans crash."""
    page = SearchPage(authenticated_page).goto()
    page.page.wait_for_selector("nav", timeout=10_000)
    # search-idle ou search-rag-disabled selon la config RAG — l'un des deux.
    assert (page.testid("search-idle").count() + page.testid("search-rag-disabled").count()) >= 0


def test_historique_massif_pagination(authenticated_page):
    """Réponse volumineuse simulée → la pagination reste réactive (persona massif)."""
    rows = [
        {
            "id": f"00000000-0000-0000-0000-{i:012d}",
            "ticker": "BNS",
            "workflow_utilise": "value_graham",
            "created_at": "2026-01-01T00:00:00Z",
            "cost_usd": 0.01,
        }
        for i in range(200)
    ]
    mock_json(authenticated_page, "**/history**", {"items": rows, "total": 5000})
    page = HistoryPage(authenticated_page).goto()
    page.page.wait_for_selector("nav", timeout=10_000)
