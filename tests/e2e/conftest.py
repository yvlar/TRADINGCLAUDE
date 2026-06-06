"""Fixtures de session pour les tests E2E — FastAPI réel + Playwright + mocks Claude."""
from __future__ import annotations

import os
import socket
import threading
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest
import uvicorn

from app.api.main import app
from app.middleware.auth import BearerTokenMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.watchlist import WatchlistCreate, WatchlistEntry
from app.services.watchlist_service import DuplicateWatchlistError
from tests.e2e.fixtures.claude_stubs import (
    buffett_stub,
    canadian_tax_stub,
    damodaran_stub,
    dorsey_stub,
    earnings_stub,
    fisher_stub,
    graham_stub,
    greenblatt_stub,
    klarman_stub,
    lynch_stub,
    marks_stub,
    munger_stub,
    pabrai_stub,
    thesis_stub,
    valuation_stub,
)
from tests.e2e.fixtures.personas import PERSONAS, InMemoryUserService

# ---------------------------------------------------------------------------
# Paths à patcher (identiques au conftest parent)
# ---------------------------------------------------------------------------

_SKILL_PROMPT_PATCHES = [
    "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
    "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
    "app.skills.tier2.dorsey_moat.skill.DorseyMoatSkill._load_system_prompt",
    "app.skills.tier2.buffett_quality.skill.BuffettQualitySkill._load_system_prompt",
    "app.skills.tier2.stock_valuation.skill.StockValuationSkill._load_system_prompt",
    "app.skills.tier2.thesis_builder.skill.ThesisBuilderSkill._load_system_prompt",
    "app.skills.tier2.munger_mental.skill.MungerMentalSkill._load_system_prompt",
    "app.skills.tier2.canadian_tax.skill.CanadianTaxSkill._load_system_prompt",
    "app.skills.tier2.lynch_categories.skill.LynchCategoriesSkill._load_system_prompt",
    "app.skills.tier2.fisher_scuttlebutt.skill.FisherScuttlebuttSkill._load_system_prompt",
    "app.skills.tier2.klarman_margin.skill.KlarmanMarginSkill._load_system_prompt",
    "app.skills.tier2.greenblatt.skill.GreenblattSkill._load_system_prompt",
    "app.skills.tier2.damodaran_narrative.skill.DamodararNarrativeSkill._load_system_prompt",
    "app.skills.tier2.marks_cycles.skill.MarksCyclesSkill._load_system_prompt",
    "app.skills.tier2.pabrai_dhandho.skill.PabraiDhandhoSkill._load_system_prompt",
]

# (chemin du module, coroutine stub)
_SKILL_CLAUDE_PATCHES = [
    ("app.skills.tier2.graham_analysis.skill.call_claude_with_retry", graham_stub),
    ("app.skills.tier2.earnings_quality.skill.call_claude_with_retry", earnings_stub),
    ("app.skills.tier2.dorsey_moat.skill.call_claude_with_retry", dorsey_stub),
    ("app.skills.tier2.buffett_quality.skill.call_claude_with_retry", buffett_stub),
    ("app.skills.tier2.stock_valuation.skill.call_claude_with_retry", valuation_stub),
    ("app.skills.tier2.thesis_builder.skill.call_claude_with_retry", thesis_stub),
    ("app.skills.tier2.munger_mental.skill.call_claude_with_retry", munger_stub),
    ("app.skills.tier2.canadian_tax.skill.call_claude_with_retry", canadian_tax_stub),
    ("app.skills.tier2.lynch_categories.skill.call_claude_with_retry", lynch_stub),
    ("app.skills.tier2.fisher_scuttlebutt.skill.call_claude_with_retry", fisher_stub),
    ("app.skills.tier2.klarman_margin.skill.call_claude_with_retry", klarman_stub),
    ("app.skills.tier2.greenblatt.skill.call_claude_with_retry", greenblatt_stub),
    ("app.skills.tier2.damodaran_narrative.skill.call_claude_with_retry", damodaran_stub),
    ("app.skills.tier2.marks_cycles.skill.call_claude_with_retry", marks_stub),
    ("app.skills.tier2.pabrai_dhandho.skill.call_claude_with_retry", pabrai_stub),
]


# ---------------------------------------------------------------------------
# InMemoryWatchlistService
# ---------------------------------------------------------------------------

class InMemoryWatchlistService:
    """Remplace WatchlistService en mémoire pour les tests E2E (pas de PostgreSQL)."""

    def __init__(self) -> None:
        self._store: dict[str, WatchlistEntry] = {}

    async def add_entry(self, create: WatchlistCreate) -> WatchlistEntry:
        t = create.ticker.upper()
        for entry in self._store.values():
            if entry.ticker == t and entry.workflow == create.workflow:
                # Même erreur domaine que le vrai WatchlistService → 409 via l'endpoint
                raise DuplicateWatchlistError(
                    f"Ticker {t} déjà présent dans la watchlist pour ce workflow"
                )
        entry = WatchlistEntry(
            id=str(uuid.uuid4()),
            ticker=t,
            workflow=create.workflow,
            ratios=create.ratios,
            score_alerte_min=create.score_alerte_min,
            created_at=datetime.now(timezone.utc),
        )
        self._store[entry.id] = entry
        return entry

    async def list_entries(self) -> list[WatchlistEntry]:
        return sorted(self._store.values(), key=lambda e: e.created_at, reverse=True)

    async def get_entry(self, entry_id: str) -> WatchlistEntry | None:
        return self._store.get(entry_id)

    async def delete_entry(self, entry_id: str) -> bool:
        if entry_id in self._store:
            del self._store[entry_id]
            return True
        return False

    async def update_last_analyzed(
        self, entry_id: str, score: int | None, verdict: str | None,
        intrinsic_value: float | None = None,
    ) -> None:
        if entry_id in self._store:
            e = self._store[entry_id]
            self._store[entry_id] = e.model_copy(update={
                "last_analyzed_at": datetime.now(timezone.utc),
                "last_score": score,
                "last_verdict": verdict,
                "last_intrinsic_value": intrinsic_value,
            })

    async def update_price_checked(self, entry_id: str, price: float) -> None:
        if entry_id in self._store:
            e = self._store[entry_id]
            self._store[entry_id] = e.model_copy(update={"last_price_checked": price})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    # create_connection itère sur getaddrinfo (IPv4 + IPv6) : indispensable car
    # Vite/Node lient « localhost » qui peut résoudre en ::1, alors qu'un
    # socket.socket() brut (AF_INET) ne tente que 127.0.0.1 → faux « port fermé ».
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, retries: int = 60, delay: float = 0.2) -> bool:
    for _ in range(retries):
        if _is_port_open(host, port, timeout=0.5):
            return True
        time.sleep(delay)
    return False


def _make_mock_pool() -> AsyncMock:
    """Pool asyncpg mocké — fetchrow(INSERT RETURNING id) retourne un UUID valide."""
    pool = AsyncMock()
    pool.close = AsyncMock()
    pool.execute = AsyncMock(return_value="UPDATE 1")
    pool.fetchval = AsyncMock(return_value=0)

    async def _fetchrow(query: str, *args, **kwargs):
        if "RETURNING id" in query:
            return {"id": uuid.uuid4()}
        # get_history, get_metrics queries
        if "COUNT(*)" in query or "total" in query.lower():
            return {"total": 0, "total_cost": 0.0, "avg_cache_hit": 0.0}
        return None

    async def _fetch(*args, **kwargs):
        return []

    pool.fetchrow = AsyncMock(side_effect=_fetchrow)
    pool.fetch = AsyncMock(side_effect=_fetch)
    return pool


def _make_yahoo_mock():
    """Yahoo extractor mocké retournant des GrahamRatios + EarningsQualityRatios valides pour BNS."""
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    mock = AsyncMock()
    mock.extract = AsyncMock(return_value=GrahamRatios(
        pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
        eps_growth_total=0.27, price=80.0, book_value=61.5,
        eps_ttm=7.25, revenue_bn=38.0, dividend_years=190,
    ))
    mock.extract_earnings_quality = AsyncMock(return_value=EarningsQualityRatios(
        sales_t=38e9, sales_t1=36e9,
        cogs_t=15e9, cogs_t1=14e9,
        net_income_t=8e9, cfo_t=10e9,
        receivables_t=5e9, current_assets_t=20e9,
        current_liabilities_t=15e9, total_assets_t=100e9,
        receivables_t1=4.5e9, total_assets_t1=95e9,
    ))
    return mock


# ---------------------------------------------------------------------------
# Fixture principale de session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def backend_server():
    """
    Démarre FastAPI sur le port 8000 avec tous les mocks appliqués.
    Vérifie que le Vite dev server est accessible sur le port 5173.
    """
    # Petite fenêtre de grâce : Vite peut finir de démarrer juste après wait-on.
    if not _wait_for_port("localhost", 5173, retries=25, delay=0.4):
        msg = (
            "Vite dev server non accessible sur le port 5173. "
            "Démarrer avec : cd frontend && npm run dev"
        )
        # En CI, un skip massif masquerait un faux vert (cf. run #1) : on échoue fort.
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)

    # Port 8000 déjà utilisé → skip plutôt que crash
    if _is_port_open("localhost", 8000):
        pytest.skip(
            "Le port 8000 est déjà utilisé. Arrêter le serveur existant avant de lancer les E2E."
        )

    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)

    mock_qdrant_resp = MagicMock()
    mock_qdrant_resp.status_code = 200
    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.get = AsyncMock(return_value=mock_qdrant_resp)
    mock_qdrant_ctx = AsyncMock()
    mock_qdrant_ctx.__aenter__ = AsyncMock(return_value=mock_qdrant_client)
    mock_qdrant_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_rag = AsyncMock()
    mock_rag.ensure_collection = AsyncMock()
    mock_rag.close = AsyncMock()

    mock_pool = _make_mock_pool()

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-e2e-test-key",
            "API_KEY": "test-secret",
            "DATABASE_URL": "postgresql://unused:5432/unused",
            "QDRANT_URL": "http://localhost:6333",
            "REDIS_URL": "redis://localhost:6379",
        }))
        mock_create_pool = stack.enter_context(
            patch("asyncpg.create_pool", new_callable=AsyncMock)
        )
        mock_create_pool.return_value = mock_pool

        stack.enter_context(
            patch("anthropic.AsyncAnthropic", return_value=MagicMock())
        )
        stack.enter_context(
            patch("app.api.main.aioredis.from_url", return_value=fake_redis)
        )
        stack.enter_context(
            patch("app.api.main.httpx.AsyncClient", return_value=mock_qdrant_ctx)
        )
        stack.enter_context(
            patch("app.api.main.RagClient", return_value=mock_rag)
        )

        for prompt_path in _SKILL_PROMPT_PATCHES:
            stack.enter_context(patch(prompt_path, return_value="prompt de test E2E"))

        for skill_path, stub_fn in _SKILL_CLAUDE_PATCHES:
            stack.enter_context(patch(skill_path, new=AsyncMock(side_effect=stub_fn)))

        # Désactiver BearerToken (clé capturée à import time, pas patchable via os.environ)
        _orig_bearer_init = BearerTokenMiddleware.__init__

        def _disabled_bearer_init(self, _app, *args, **kwargs) -> None:
            # Accepte la signature étendue (redis_url, trusted_proxies — E1-S2) tout
            # en désactivant l'auth (api_key="" → bypass dev) pour le harnais e2e.
            _orig_bearer_init(self, _app, api_key="")

        stack.enter_context(
            patch.object(BearerTokenMiddleware, "__init__", _disabled_bearer_init)
        )

        # Injecter fakeredis dans RateLimitMiddleware et lever la limite pour les tests
        def _fakeredis_rl_init(self, _app, redis_url: str = "") -> None:
            from starlette.middleware.base import BaseHTTPMiddleware
            BaseHTTPMiddleware.__init__(self, _app)
            self._redis = fake_redis
            self._trusted_proxies = frozenset()  # E1-S2 : requis par resolve_client_ip

        stack.enter_context(
            patch.object(RateLimitMiddleware, "__init__", _fakeredis_rl_init)
        )
        stack.enter_context(
            patch.object(RateLimitMiddleware, "MAX_REQUESTS", 10_000)
        )

        # Forcer la reconstruction du middleware stack (peut être mis en cache par les tests units)
        app.middleware_stack = None

        config = uvicorn.Config(
            app, host="127.0.0.1", port=8000,
            log_level="warning", loop="asyncio",
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        if not _wait_for_port("127.0.0.1", 8000):
            server.should_exit = True
            pytest.fail("Le serveur FastAPI E2E n'a pas démarré dans les délais.")

        # Override app.state après démarrage
        yahoo_mock = _make_yahoo_mock()
        app.state.watchlist_service = InMemoryWatchlistService()
        app.state.yahoo_extractor = yahoo_mock
        # Override aussi l'extractor interne du screener
        app.state.screener._extractor = yahoo_mock
        # Service utilisateur en mémoire avec personas — rend le flux email/mot de
        # passe + JWT cookie réellement traversable (le pool asyncpg mocké ne sait
        # pas authentifier). auth_token_service reste réel (JWT + fakeredis).
        app.state.user_service = InMemoryUserService.with_personas()

        yield

        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser_context(backend_server, playwright):
    """Contexte Playwright avec l'API key injectée dans localStorage."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(base_url="http://localhost:5173")
    # Injecter l'API key dans localStorage avant navigation
    context.add_init_script("""
        window.localStorage.setItem('api_token', 'test-secret');
    """)
    yield context
    context.close()
    browser.close()


@pytest.fixture
def page(browser_context):
    """Page Playwright fraîche par test."""
    p = browser_context.new_page()
    yield p
    p.close()


@pytest.fixture
def authenticated_page(login_as):
    """Page authentifiée via le VRAI flux cookie JWT + CSRF (persona standard).

    L'ancienne implémentation s'appuyait sur `api_token` en localStorage : ce
    chemin n'authentifie plus depuis le passage à l'auth par cookie (authMe →
    401 → redirection /login). On se connecte donc réellement via l'UI.
    """
    return login_as("standard")


# ---------------------------------------------------------------------------
# Fixtures auth réelle (cookie JWT) + personas + monitoring — Sprint E2E QA
# ---------------------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Mémorise l'échec de la phase « call » pour déclencher la sauvegarde de trace."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item._e2e_failed = report.failed


_TRACE_DIR = os.path.join(os.path.dirname(__file__), ".traces")


@pytest.fixture(scope="session")
def clean_browser(backend_server, playwright):
    """Navigateur Chromium partagé pour les contextes cookie — évite un relaunch par test."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def clean_context(clean_browser, request):
    """Contexte SANS api_token en localStorage — exerce le vrai flux cookie JWT.

    Indispensable pour les parcours d'auth : `browser_context` injecte un Bearer
    token qui court-circuite la session cookie et masquerait les régressions. Seul
    le contexte (pas le navigateur) est recréé par test → isolation sans coût de boot.

    Tracing opt-in via `E2E_TRACE=1` (trace sur échec) ou `E2E_TRACE=all` (toujours)
    — les .zip Playwright atterrissent dans `tests/e2e/.traces/` pour le trace viewer.
    """
    context = clean_browser.new_context(base_url="http://localhost:5173")
    trace_mode = os.environ.get("E2E_TRACE")
    if trace_mode:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield context

    if trace_mode:
        failed = getattr(request.node, "_e2e_failed", False)
        if failed or trace_mode == "all":
            os.makedirs(_TRACE_DIR, exist_ok=True)
            safe = request.node.name.replace("/", "_").replace("[", "_").replace("]", "")
            context.tracing.stop(path=os.path.join(_TRACE_DIR, f"{safe}.zip"))
        else:
            context.tracing.stop()
    context.close()


@pytest.fixture
def clean_page(clean_context):
    """Page fraîche sans session — point de départ des tests de login/register."""
    p = clean_context.new_page()
    yield p
    p.close()


@pytest.fixture
def login_as(clean_context):
    """Factory : connecte un persona via l'UI réelle et retourne sa page authentifiée."""
    from tests.e2e.pages.auth_pages import LoginPage

    def _login(persona_key: str = "standard"):
        persona = PERSONAS[persona_key]
        p = clean_context.new_page()
        login = LoginPage(p).goto()
        login.login(persona.email, persona.password)
        p.wait_for_url("http://localhost:5173/", timeout=10_000)
        p.wait_for_selector("nav", timeout=10_000)
        return p

    return _login


@pytest.fixture
def standard_page(login_as):
    """Page authentifiée en tant qu'utilisateur standard (cas nominal)."""
    return login_as("standard")


@pytest.fixture
def admin_page(login_as):
    """Page authentifiée en tant qu'administrateur."""
    return login_as("admin")


@pytest.fixture
def monitor(page):
    """Attache un PageMonitor à la page par défaut (console + réseau + React)."""
    from tests.e2e.helpers.monitoring import PageMonitor

    with PageMonitor(page) as mon:
        yield mon


@pytest.fixture(autouse=True)
def _reset_watchlist_state(backend_server):
    """Isole l'état watchlist entre tests — le service en mémoire est partagé (session)."""
    svc = getattr(app.state, "watchlist_service", None)
    if isinstance(svc, InMemoryWatchlistService):
        svc._store.clear()
    yield
