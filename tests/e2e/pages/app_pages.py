"""Page Objects des écrans applicatifs protégés : Analyse, Screener, Watchlist…"""
from __future__ import annotations

from playwright.sync_api import Locator, expect

from tests.e2e.pages.base_page import BasePage


class AnalyzePage(BasePage):
    path = "/"

    @property
    def ticker(self) -> Locator:
        return self.page.get_by_label("Ticker")

    @property
    def submit(self) -> Locator:
        return self.page.get_by_role("button", name="Analyser")

    @property
    def workflow_selector(self) -> Locator:
        return self.testid("workflow-selector")

    @property
    def result_ticker(self) -> Locator:
        return self.testid("result-ticker")

    @property
    def error(self) -> Locator:
        return self.testid("error-message")

    def analyze(self, ticker: str, workflow: str | None = None) -> None:
        self.ticker.fill(ticker)
        if workflow:
            self.workflow_selector.select_option(workflow)
        self.submit.click()

    def expect_result(self, ticker: str, timeout: int = 30_000) -> None:
        expect(self.result_ticker).to_contain_text(ticker, timeout=timeout)

    def expect_graham_verdict(self, timeout: int = 30_000) -> None:
        expect(self.testid("graham-verdict")).to_be_visible(timeout=timeout)


class ScreenerPage(BasePage):
    path = "/screener"

    @property
    def tickers(self) -> Locator:
        return self.page.get_by_label("Tickers")

    @property
    def submit(self) -> Locator:
        return self.page.get_by_role("button", name="Lancer le screener")

    def screen(self, tickers: str) -> None:
        self.tickers.fill(tickers)
        self.submit.click()

    def rows(self) -> Locator:
        return self.testid("screener-row")

    def expect_rows(self, count: int, timeout: int = 30_000) -> None:
        expect(self.rows()).to_have_count(count, timeout=timeout)


class WatchlistPage(BasePage):
    path = "/watchlist"

    @property
    def ticker(self) -> Locator:
        return self.page.get_by_label("Ticker")

    @property
    def workflow(self) -> Locator:
        return self.page.get_by_label("Workflow")

    @property
    def add_button(self) -> Locator:
        return self.page.get_by_role("button", name="Ajouter")

    @property
    def error(self) -> Locator:
        return self.testid("watchlist-error")

    def add(self, ticker: str, workflow: str | None = None) -> None:
        self.ticker.fill(ticker)
        if workflow:
            self.workflow.select_option(workflow)
        self.add_button.click()

    def rows(self) -> Locator:
        return self.testid("watchlist-row")


class DashboardPage(BasePage):
    path = "/dashboard"

    @property
    def grid(self) -> Locator:
        return self.testid("dashboard-grid")


class HistoryPage(BasePage):
    path = "/historique"

    @property
    def search_input(self) -> Locator:
        return self.testid("history-search-input")

    @property
    def search_button(self) -> Locator:
        return self.testid("history-search-btn")

    @property
    def empty(self) -> Locator:
        return self.testid("history-empty")

    def next_page(self) -> None:
        self.testid("history-pagination-next").click()


class SearchPage(BasePage):
    path = "/recherche"

    @property
    def input(self) -> Locator:
        return self.testid("search-input")

    @property
    def submit(self) -> Locator:
        return self.testid("search-submit")

    def search(self, query: str) -> None:
        self.input.fill(query)
        self.submit.click()


class AdminPage(BasePage):
    path = "/admin"


class AlertsPage(BasePage):
    path = "/alerts"


class ComparePage(BasePage):
    path = "/compare"

    @property
    def tickers(self) -> Locator:
        return self.testid("compare-ticker-input")

    @property
    def submit(self) -> Locator:
        return self.testid("compare-submit-btn")


class EsgPage(BasePage):
    path = "/esg"
