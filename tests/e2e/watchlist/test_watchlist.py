"""E2E — Watchlist (le « portefeuille » suivi : ajout, doublon, liste vide, erreurs)."""
import pytest

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


def test_watchlist_doublon_refuse(authenticated_page):
    """Ajouter deux fois le même ticker+workflow → message d'erreur (contrôle doublon)."""
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
