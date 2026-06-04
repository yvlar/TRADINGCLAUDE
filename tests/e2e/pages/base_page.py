"""Page Object de base — services partagés par toutes les pages."""
from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

BASE_URL = "http://localhost:5173"


class BasePage:
    """Racine des Page Objects : navigation, attentes et accès testid communs."""

    path = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    # ---- navigation --------------------------------------------------------

    def goto(self, path: str | None = None) -> "BasePage":
        self.page.goto(f"{BASE_URL}{path if path is not None else self.path}")
        return self

    def wait_url(self, glob: str, timeout: int = 8_000) -> None:
        self.page.wait_for_url(glob, timeout=timeout)

    # ---- sélecteurs --------------------------------------------------------

    def testid(self, value: str) -> Locator:
        return self.page.get_by_test_id(value)

    def expect_testid_visible(self, value: str, timeout: int = 8_000) -> None:
        expect(self.testid(value)).to_be_visible(timeout=timeout)

    # ---- chrome applicatif (header présent seulement si authentifié) -------

    @property
    def nav(self) -> Locator:
        return self.page.locator("nav")

    def logout(self) -> None:
        self.page.get_by_role("button", name="Déconnexion").click()
        self.wait_url("**/login")

    def open_command_palette(self) -> None:
        self.testid("command-palette-trigger").click()
        self.expect_testid_visible("command-palette-input")
