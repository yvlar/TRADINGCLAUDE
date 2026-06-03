"""Page Objects d'authentification : Login, Register, Forgot/Reset password."""
from __future__ import annotations

from playwright.sync_api import Locator, expect

from tests.e2e.pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    @property
    def email(self) -> Locator:
        return self.testid("email-input")

    @property
    def password(self) -> Locator:
        return self.testid("password-input")

    @property
    def submit(self) -> Locator:
        return self.testid("submit-button")

    @property
    def error(self) -> Locator:
        return self.testid("error-message")

    def login(self, email: str, password: str, remember_me: bool = False) -> None:
        self.email.fill(email)
        self.password.fill(password)
        if remember_me:
            self.testid("remember-me").check()
        self.submit.click()

    def expect_error(self, fragment: str | None = None) -> None:
        expect(self.error).to_be_visible(timeout=8_000)
        if fragment:
            expect(self.error).to_contain_text(fragment)

    def toggle_password_visibility(self) -> None:
        self.page.get_by_role("button", name="Afficher le mot de passe").click()


class RegisterPage(BasePage):
    path = "/register"

    @property
    def email(self) -> Locator:
        return self.testid("email-input")

    @property
    def password(self) -> Locator:
        return self.testid("password-input")

    @property
    def submit(self) -> Locator:
        return self.testid("submit-button")

    @property
    def strength(self) -> Locator:
        return self.testid("password-strength")

    @property
    def error(self) -> Locator:
        return self.testid("error-message")

    def register(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit.click()


class ForgotPasswordPage(BasePage):
    path = "/forgot-password"

    def request_reset(self, email: str) -> None:
        self.page.get_by_label("Adresse email").fill(email)
        self.page.get_by_role("button").filter(has_text="Envoyer").first.click()


class ResetPasswordPage(BasePage):
    path = "/reset-password"

    def reset(self, new_password: str) -> None:
        self.testid("new-password-input").fill(new_password)
        self.page.get_by_role("button").filter(has_text="Réinitialiser").first.click()
