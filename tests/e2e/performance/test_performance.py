"""E2E — Budgets de performance perçue (chargement, lazy chunks, réactivité).

Ce ne sont pas des benchmarks fins : ce sont des garde-fous grossiers qui
échouent si une régression rend le premier rendu anormalement lent ou casse le
découpage en chunks (Suspense/RouteFallback).
"""
import time

import pytest

from tests.e2e.pages.base_page import BASE_URL

pytestmark = [pytest.mark.e2e, pytest.mark.performance]

# Budgets volontairement larges (CI partagé, navigateur headless) — on cible les
# régressions d'un ordre de grandeur, pas la micro-optimisation.
_LOGIN_TTI_BUDGET_S = 6.0
_ROUTE_NAV_BUDGET_S = 5.0


def test_login_time_to_interactive(clean_page):
    """La page de login devient interactive sous le budget."""
    start = time.perf_counter()
    clean_page.goto(f"{BASE_URL}/login")
    clean_page.get_by_test_id("submit-button").wait_for(state="visible", timeout=10_000)
    elapsed = time.perf_counter() - start
    assert elapsed < _LOGIN_TTI_BUDGET_S, f"Login TTI {elapsed:.2f}s > {_LOGIN_TTI_BUDGET_S}s"


def test_lazy_chunks_se_chargent(standard_page):
    """Chaque route lazy se monte sous budget (vérifie le découpage Vite/Suspense)."""
    for path in ("/screener", "/dashboard", "/watchlist", "/esg"):
        start = time.perf_counter()
        standard_page.goto(f"{BASE_URL}{path}")
        standard_page.wait_for_selector("nav", timeout=10_000)
        elapsed = time.perf_counter() - start
        assert elapsed < _ROUTE_NAV_BUDGET_S, f"{path} monté en {elapsed:.2f}s"


def test_pas_de_requete_bloquante_au_montage(standard_page):
    """Le dashboard atteint l'état interactif sans rester bloqué sur un spinner."""
    standard_page.goto(f"{BASE_URL}/dashboard")
    standard_page.wait_for_selector("nav", timeout=10_000)
    # Aucun route-fallback persistant ne doit subsister après stabilisation.
    standard_page.wait_for_timeout(1000)
    assert standard_page.get_by_test_id("route-fallback").count() == 0
