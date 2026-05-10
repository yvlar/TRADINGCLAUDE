"""Scénarios de tests de charge Locust — /analyze, /screen, /telemetry."""
from __future__ import annotations

from locust import HttpUser, between, task

GRAHAM_PAYLOAD = {
    "ticker": "BNS",
    "ratios": {
        "pe": 11.0,
        "pb": 1.3,
        "current_ratio": None,
        "debt_equity": 0.45,
        "eps_growth_10y": 0.27,
        "price": 80.0,
        "book_value": 61.5,
    },
    "workflow": "value_graham",
}

_RATIOS_BANQUES = {
    "pe": 11.0,
    "pb": 1.3,
    "current_ratio": None,
    "debt_equity": 0.45,
    "eps_growth_10y": 0.27,
    "price": 80.0,
    "book_value": 61.5,
}

SCREEN_PAYLOAD = {
    "tickers": ["BNS", "TD", "RY", "BMO", "CM"],
    "workflow": "value_graham",
    "ratios_map": {ticker: _RATIOS_BANQUES for ticker in ["BNS", "TD", "RY", "BMO", "CM"]},
}


class AnalyzeUser(HttpUser):
    """Simule un utilisateur qui lance des analyses individuelles — 70 % du trafic."""

    weight = 7
    wait_time = between(1, 3)

    @task
    def analyze_bns(self) -> None:
        self.client.post("/analyze", json=GRAHAM_PAYLOAD)


class ScreenUser(HttpUser):
    """Simule un utilisateur qui lance un screener multi-tickers — 20 % du trafic."""

    weight = 2
    wait_time = between(2, 5)

    @task
    def screen_banks(self) -> None:
        self.client.post("/screen", json=SCREEN_PAYLOAD)


class TelemetryUser(HttpUser):
    """Simule un dashboard de monitoring — 10 % du trafic."""

    weight = 1
    wait_time = between(5, 10)

    @task
    def get_summary(self) -> None:
        self.client.get("/telemetry/summary?days=7")

    @task
    def get_cache(self) -> None:
        self.client.get("/telemetry/cache")
