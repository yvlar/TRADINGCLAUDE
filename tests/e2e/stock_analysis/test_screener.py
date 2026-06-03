"""E2E — Screener multi-tickers."""
import pytest

from tests.e2e.helpers.assertions import assert_page_clean
from tests.e2e.helpers.monitoring import PageMonitor
from tests.e2e.helpers.network import mock_status
from tests.e2e.pages.app_pages import ScreenerPage

pytestmark = pytest.mark.e2e


def test_screener_happy_path(authenticated_page):
    """Liste de tickers → tableau rempli, parcours propre."""
    with PageMonitor(authenticated_page) as mon:
        page = ScreenerPage(authenticated_page).goto()
        page.screen("BNS, TD")
        page.expect_rows(2)  # 2 tickers → 2 lignes (to_be_visible serait en strict mode)
    assert_page_clean(mon)


def test_screener_normalise_majuscules(authenticated_page):
    """Les tickers saisis en minuscules sont normalisés avant l'appel."""
    page = ScreenerPage(authenticated_page).goto()
    page.screen("bns")
    page.expect_testid_visible("screener-ticker", timeout=30_000)


def test_screener_500_gracieux(authenticated_page):
    """Un 500 sur /screen ne laisse pas l'écran sans retour utilisateur."""
    with PageMonitor(authenticated_page) as mon:
        mock_status(authenticated_page, "**/screen**", 500, {"detail": "boom"})
        page = ScreenerPage(authenticated_page).goto()
        page.screen("BNS")
        authenticated_page.wait_for_timeout(1500)
    assert not mon.react_faults(), mon.react_faults()
