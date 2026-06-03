"""E2E — Watchlist (le « portefeuille » suivi : ajout, doublon, liste vide, erreurs)."""
import pytest
from playwright.sync_api import expect

from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.helpers.network import mock_json, mock_status
from tests.e2e.pages.app_pages import WatchlistPage

pytestmark = pytest.mark.e2e


def test_watchlist_ajout(authenticated_page):
    """Ajouter un ticker → nouvelle ligne dans le tableau, parcours propre."""
    with PageMonitor(authenticated_page) as mon:
        page = WatchlistPage(authenticated_page).goto()
        page.add("BNS")
        page.expect_testid_visible("watchlist-row", timeout=15_000)
    assert_page_clean(mon)


def test_watchlist_doublon_bloque_cote_client(authenticated_page):
    """Ajouter deux fois le même ticker+workflow → la garde CLIENT affiche une erreur.

    NB : le frontend (WatchlistPage) bloque le doublon avant tout appel réseau ; le
    chemin backend 409 (DuplicateWatchlistError) est couvert par les tests unitaires
    `tests/services/test_watchlist_duplicate.py`.
    """
    page = WatchlistPage(authenticated_page).goto()
    page.add("RY")
    page.expect_testid_visible("watchlist-row", timeout=15_000)
    page.add("RY")
    page.expect_testid_visible("watchlist-error", timeout=10_000)


def test_watchlist_vide_pas_de_crash(authenticated_page):
    """Watchlist vide (réponse []) → écran rendu sans plantage."""
    with PageMonitor(authenticated_page) as mon:
        mock_json(authenticated_page, "**/watchlist", [])
        WatchlistPage(authenticated_page).goto()
        authenticated_page.wait_for_selector("nav", timeout=10_000)
    assert not mon.react_faults(), mon.react_faults()


def test_watchlist_erreur_chargement(authenticated_page):
    """Un 500 au chargement → bloc d'erreur affiché, pas d'écran blanc."""
    mock_status(authenticated_page, "**/watchlist", 500, {"detail": "indisponible"})
    page = WatchlistPage(authenticated_page).goto()
    page.expect_testid_visible("watchlist-error", timeout=10_000)


def test_watchlist_suppression(authenticated_page):
    """Ajouter un ticker puis le supprimer → retour au compte initial (migré legacy)."""
    page = WatchlistPage(authenticated_page).goto()
    initial = page.rows().count()
    page.add("TD")
    expect(page.rows()).to_have_count(initial + 1, timeout=15_000)
    # TD est en tête (tri created_at desc) → supprimer la première ligne.
    authenticated_page.get_by_role("button", name="Supprimer").first.click()
    expect(page.rows()).to_have_count(initial, timeout=10_000)
