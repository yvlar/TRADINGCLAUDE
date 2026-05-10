# Sprint 4 — Prompt d'implémentation
**Observabilité — Langfuse, metrics, timeout, retry**
*Généré le 7 mai 2026 — à utiliser après la complétion du Sprint 3*

---

# PRÉREQUIS

Les Sprints 1, 2 et 3 doivent être complétés :
- `app/skills/base.py` : `SkillBase`, `Citation`, `UsageDetail`
- `app/utils/costs.py` : `PRICING`, `calculate_cost()`
- `app/rag/` : RAG opérationnel
- `earnings_quality` skill implémenté
- `GET /history` opérationnel
- Tous les tests passent (`pytest tests/ -v`)

---

# RÔLE

Développeur Python senior spécialiste RAG et architecture de systèmes LLM.
Tu maîtrises FastAPI, asyncpg, le SDK Anthropic Python, et les outils
d'observabilité LLM (Langfuse, structured logging, metrics).

---

# CONTEXTE

Projet : copilote financier RAG — analyse d'investissement multi-frameworks.
**Phase 2-3 — objectif :** rendre l'infrastructure observable et résiliente.

**Trois problèmes à résoudre :**

1. **Aucun timeout sur `messages.create()`** — une réponse lente de Claude
   bloque le thread ASGI indéfiniment
2. **Aucun retry** — une erreur 529 (Claude overloaded) fait échouer l'analyse
   sans recours
3. **Observabilité partielle** — le JSON logging (Sprint 2) trace les métriques
   mais n'offre pas de visualisation : impossible de voir rapidement le coût
   cumulé, le taux de cache ou les outliers de latence sans éplucher les logs

**Décisions d'architecture pour ce sprint :**

| Décision | Choix retenu | Raison |
|----------|-------------|--------|
| Retry library | stdlib (`asyncio.sleep`) | Pas de dépendance externe pour 30 lignes |
| Langfuse deployment | Cloud (free tier) ou self-hosted optionnel | Aucun nouveau service Docker requis |
| Langfuse SDK | Synchrone (`langfuse>=2.0.0`), flush en background | Pas de blocage de la boucle async |
| Dashboard | `GET /metrics` + Langfuse UI | PostgreSQL pour les agrégats, Langfuse pour les traces individuelles |
| Config skills | `SkillConfig` dataclass partagée | Évite de modifier 15 constructeurs séparément |

**Langfuse est optionnel** : si `LANGFUSE_SECRET_KEY` est absent du `.env`,
le `LangfuseTracer` est `None` et les skills se comportent exactement comme
en Sprint 3. La résilience (timeout + retry) est active dans tous les cas.

**Stack :** Python 3.11, FastAPI, Anthropic SDK, asyncpg, langfuse
**Langue du code :** anglais | **Commentaires, docstrings :** français
**Tests :** pytest-asyncio, aucun service réel

---

# TÂCHE

Exécuter les 4 tâches dans l'ordre. S4-3 et S4-4 forment un bloc atomique
(même fichier `app/utils/retry.py`). S4-1 dépend du retry. S4-2 est indépendant.

---

## S4-3 + S4-4 — `app/utils/retry.py` : timeout + retry 529

Les deux tâches sont implémentées dans une seule fonction qui encapsule
`client.messages.create()` avec timeout configurable et retry exponentiel.

**Créer `app/utils/retry.py` :**

```python
# app/utils/retry.py
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S   = 60.0
_DEFAULT_MAX_RETRIES = 3


async def call_claude_with_retry(
    client:      anthropic.AsyncAnthropic,
    *,
    timeout_s:   float = _DEFAULT_TIMEOUT_S,
    max_retries: int   = _DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> anthropic.types.Message:
    """
    Appelle client.messages.create() avec :
    - Timeout configurable (par défaut 60 s)
    - Retry exponentiel sur les erreurs 529 (Claude overloaded)
    - Jitter aléatoire pour éviter les requêtes synchronisées entre instances

    Les erreurs autres que 529 propagent immédiatement sans retry.
    Les erreurs de timeout ne sont pas retriées (budget temps épuisé).
    """
    for attempt in range(max_retries + 1):
        try:
            return await client.messages.create(timeout=timeout_s, **kwargs)

        except anthropic.APITimeoutError:
            # Ne pas retrier un timeout — on n'a plus de budget temps
            logger.error(
                "Timeout Claude après %.0f s (tentative %d/%d)",
                timeout_s, attempt + 1, max_retries + 1,
            )
            raise

        except anthropic.APIStatusError as exc:
            if exc.status_code != 529:
                raise  # erreur non retriable — propager immédiatement

            if attempt >= max_retries:
                logger.error(
                    "Claude surchargé (529) — abandon après %d tentatives",
                    max_retries + 1,
                )
                raise

            delay = (2 ** attempt) + random.uniform(0.0, 1.0)
            logger.warning(
                "Claude surchargé (529) — retry %d/%d dans %.1f s",
                attempt + 1,
                max_retries,
                delay,
                extra={"attempt": attempt + 1, "delay_s": round(delay, 1)},
            )
            await asyncio.sleep(delay)

    raise RuntimeError("call_claude_with_retry : boucle épuisée sans résultat")
```

**Ajouter dans `requirements.txt` :**
```
# (rien de nouveau — stdlib uniquement pour le retry)
```

**Mettre à jour les variables d'environnement dans `.env.example` :**
```
CLAUDE_TIMEOUT_S=60       # Timeout en secondes sur chaque appel messages.create
CLAUDE_MAX_RETRIES=3      # Nombre de retry sur erreur 529 (0 = pas de retry)
```

---

## S4-1 — Intégration Langfuse

### `app/observability/__init__.py` (vide)

### `app/observability/langfuse_client.py`

```python
# app/observability/langfuse_client.py
from __future__ import annotations

import logging

from app.skills.base import UsageDetail

logger = logging.getLogger(__name__)


class LangfuseTracer:
    """
    Wrapper autour du SDK Langfuse pour tracer les appels Claude.
    Instancié uniquement si LANGFUSE_SECRET_KEY est présente.
    Toutes les méthodes sont synchrones — le SDK Langfuse bufferise en arrière-plan.
    """

    def __init__(self, secret_key: str, public_key: str, host: str) -> None:
        from langfuse import Langfuse  # import paresseux — optionnel
        self._lf = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
        )
        logger.info("LangfuseTracer initialisé (host=%s)", host)

    def record_generation(
        self,
        *,
        skill_id:     str,
        ticker:       str,
        model:        str,
        input_data:   str,      # JSON sérialisé de l'input Pydantic
        output_data:  str,      # JSON sérialisé de l'output Pydantic
        usage_detail: UsageDetail,
        latency_ms:   int,
    ) -> None:
        """Enregistre une génération Claude dans Langfuse."""
        total_consumed = (
            usage_detail.tokens_input
            + usage_detail.tokens_cache_read
            + usage_detail.tokens_cache_creation
        )
        cache_hit_ratio = (
            round(usage_detail.tokens_cache_read / total_consumed, 4)
            if total_consumed > 0 else 0.0
        )

        try:
            trace = self._lf.trace(
                name=f"{skill_id}/{ticker}",
                metadata={"ticker": ticker, "skill_id": skill_id},
            )
            trace.generation(
                name=skill_id,
                model=model,
                input=input_data,
                output=output_data,
                usage={
                    "input":  usage_detail.tokens_input,
                    "output": usage_detail.tokens_output,
                    "total":  usage_detail.tokens_input + usage_detail.tokens_output,
                    "unit":   "TOKENS",
                },
                metadata={
                    "cost_usd":               usage_detail.cost_usd,
                    "tokens_cache_read":      usage_detail.tokens_cache_read,
                    "tokens_cache_creation":  usage_detail.tokens_cache_creation,
                    "cache_hit_ratio":        cache_hit_ratio,
                    "latency_ms":             latency_ms,
                },
            )
        except Exception:
            # Ne jamais faire planter le skill à cause de l'observabilité
            logger.exception("Erreur Langfuse — trace ignorée pour %s/%s", skill_id, ticker)

    def shutdown(self) -> None:
        """Flush les traces en attente avant l'arrêt du service."""
        try:
            self._lf.flush()
        except Exception:
            logger.exception("Erreur lors du flush Langfuse")
```

**Ajouter dans `requirements.txt` :**
```
langfuse>=2.0.0
```

**Ajouter dans `.env.example` :**
```
# Langfuse — optionnel. Si absent, le traçage Langfuse est désactivé.
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # ou http://localhost:3000 si self-hosted
```

---

### `SkillConfig` — ajouter dans `app/skills/base.py`

```python
# Ajouter en tête de app/skills/base.py, après les imports existants
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class SkillConfig:
    """
    Configuration partagée par tous les skills Tier 2.
    Injectée depuis le lifespan FastAPI — un seul objet créé au démarrage.
    """
    timeout_s:   float = 60.0
    max_retries: int   = 3
    tracer:      Any   = None   # LangfuseTracer | None — Any pour éviter l'import circulaire
```

---

### Mettre à jour `GrahamAnalysisSkill` dans `skill.py`

**Changements :**

1. Accepter `config: SkillConfig` en paramètre de constructeur (remplace les params individuels)
2. Remplacer `await self._client.messages.create(...)` par `await call_claude_with_retry(...)`
3. Appeler `self._config.tracer.record_generation(...)` après chaque exécution réussie

```python
# Imports à ajouter dans skill.py
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.retry import call_claude_with_retry

class GrahamAnalysisSkill(SkillBase):
    ...

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model:  str,
        config: SkillConfig | None = None,
        rag_service: RagService | None = None,
        top_k:  int = 5,
    ) -> None:
        self._client  = client
        self._model   = model
        self._config  = config or SkillConfig()
        self._rag     = rag_service
        self._top_k   = top_k
        self._system_prompt_text = self._load_system_prompt()

    async def execute(
        self, input_data: GrahamAnalysisInput
    ) -> tuple[GrahamAnalysisOutput, UsageDetail]:

        citations    = await self.get_citations(rag_query, k=self._top_k)
        user_message = self._build_user_message(input_data, citations)

        t0 = time.perf_counter()
        response = await call_claude_with_retry(
            self._client,
            timeout_s=self._config.timeout_s,
            max_retries=self._config.max_retries,
            model=self._model,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
            max_tokens=2048,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        # ... calcul cost_usd, UsageDetail, log structuré (inchangés depuis Sprint 2) ...

        # Trace Langfuse (optionnel)
        if self._config.tracer is not None:
            self._config.tracer.record_generation(
                skill_id=self.skill_id,
                ticker=input_data.ticker,
                model=self._model,
                input_data=input_data.model_dump_json(),
                output_data=graham_output.model_dump_json(),
                usage_detail=usage_detail,
                latency_ms=latency_ms,
            )

        return graham_output, usage_detail
```

**Appliquer le même pattern à `EarningsQualitySkill`** — même constructeur, même appel `call_claude_with_retry`, même trace Langfuse.

---

### Mettre à jour le lifespan dans `app/api/main.py`

Version : `_VERSION = "0.3.0"`

```python
import os
from app.observability.langfuse_client import LangfuseTracer
from app.skills.base import SkillConfig
from app.utils.retry import _DEFAULT_TIMEOUT_S, _DEFAULT_MAX_RETRIES

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... vars existantes ...
    timeout_s   = float(_get_env("CLAUDE_TIMEOUT_S",  str(_DEFAULT_TIMEOUT_S)))
    max_retries = int(_get_env("CLAUDE_MAX_RETRIES",  str(_DEFAULT_MAX_RETRIES)))

    # Langfuse — optionnel
    tracer: LangfuseTracer | None = None
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if lf_secret:
        tracer = LangfuseTracer(
            secret_key=lf_secret,
            public_key=_get_env("LANGFUSE_PUBLIC_KEY"),
            host=_get_env("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    else:
        logger.warning("LANGFUSE_SECRET_KEY absente — traçage Langfuse désactivé")

    skill_config = SkillConfig(
        timeout_s=timeout_s,
        max_retries=max_retries,
        tracer=tracer,
    )

    graham_skill = GrahamAnalysisSkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    earnings_skill = EarningsQualitySkill(
        client=anthropic_client,
        model=model,
        config=skill_config,
        rag_service=rag_service,
        top_k=top_k,
    )
    orchestrator = Orchestrator(db_pool=db_pool, graham_skill=graham_skill, earnings_skill=earnings_skill)

    app.state.orchestrator = orchestrator
    app.state.db_pool      = db_pool
    app.state.qdrant_url   = qdrant_url

    yield

    if tracer:
        tracer.shutdown()
    await db_pool.close()
    await rag_client.close()
```

---

## S4-2 — Dashboard : `GET /metrics`

### Modèles dans `app/orchestrator/core.py`

```python
class TickerMetrics(BaseModel):
    ticker:    str
    analyses:  int
    cost_usd:  float


class MetricsResponse(BaseModel):
    period_days:            int
    total_analyses:         int
    total_cost_usd:         float
    avg_cost_per_analysis:  float
    cache_hit_ratio_avg:    float
    top_tickers:            list[TickerMetrics]
    skills_usage:           dict[str, int]
```

### Méthode `get_metrics()` dans `Orchestrator`

```python
async def get_metrics(self, days: int = 30) -> MetricsResponse:
    """Agrège les métriques depuis analysis_history sur la période demandée."""

    # Statistiques globales
    global_row = await self._db.fetchrow(
        """
        SELECT
            COUNT(*)                                                    AS total,
            COALESCE(SUM(cost_usd), 0)                                  AS total_cost,
            COALESCE(AVG(
                CASE
                    WHEN tokens_input + tokens_cache_read + tokens_cache_creation > 0
                    THEN tokens_cache_read::float
                         / (tokens_input + tokens_cache_read + tokens_cache_creation)
                    ELSE 0
                END
            ), 0)                                                        AS avg_cache_hit
        FROM analysis_history
        WHERE created_at >= NOW() - ($1 || ' days')::interval
        """,
        str(days),
    )

    # Top tickers par coût
    ticker_rows = await self._db.fetch(
        """
        SELECT ticker, COUNT(*) AS nb, SUM(cost_usd) AS total_cost
        FROM analysis_history
        WHERE created_at >= NOW() - ($1 || ' days')::interval
        GROUP BY ticker
        ORDER BY total_cost DESC
        LIMIT 20
        """,
        str(days),
    )

    # Utilisation des skills (dénormalisé depuis le tableau JSONB)
    skill_rows = await self._db.fetch(
        """
        SELECT skill, COUNT(*) AS nb
        FROM analysis_history,
             jsonb_array_elements_text(skills_used) AS skill
        WHERE created_at >= NOW() - ($1 || ' days')::interval
        GROUP BY skill
        ORDER BY nb DESC
        """,
        str(days),
    )

    total      = int(global_row["total"])
    total_cost = float(global_row["total_cost"])

    return MetricsResponse(
        period_days=days,
        total_analyses=total,
        total_cost_usd=round(total_cost, 6),
        avg_cost_per_analysis=round(total_cost / total, 6) if total > 0 else 0.0,
        cache_hit_ratio_avg=round(float(global_row["avg_cache_hit"]), 4),
        top_tickers=[
            TickerMetrics(
                ticker=row["ticker"],
                analyses=int(row["nb"]),
                cost_usd=round(float(row["total_cost"]), 6),
            )
            for row in ticker_rows
        ],
        skills_usage={row["skill"]: int(row["nb"]) for row in skill_rows},
    )
```

### Endpoint dans `app/api/main.py`

```python
from app.orchestrator.core import MetricsResponse, TickerMetrics  # ajouter aux imports

@app.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Métriques agrégées sur la période",
)
async def metrics(
    request: Request,
    days:    int = 30,
) -> MetricsResponse:
    """
    Retourne les métriques d'utilisation depuis analysis_history.
    - `days` : fenêtre de temps en jours (défaut 30, max 365)
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days doit être entre 1 et 365")
    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_metrics(days=days)
```

---

# MISE À JOUR DES TESTS

## Créer `tests/test_retry.py`

```python
"""Tests unitaires de app/utils/retry.py — aucun appel réseau réel."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

import anthropic

from app.utils.retry import call_claude_with_retry


class TestCallClaudeWithRetry:

    @pytest.mark.asyncio
    async def test_succes_premier_appel(self):
        """Retourne directement la réponse si pas d'erreur."""
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        result = await call_claude_with_retry(
            mock_client, model="claude-sonnet-4-6", messages=[], max_tokens=100
        )

        assert result is mock_response
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_passe_a_messages_create(self):
        """Le paramètre timeout_s est transmis à messages.create."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = MagicMock()

        await call_claude_with_retry(
            mock_client, timeout_s=42.0, model="test", messages=[], max_tokens=10
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["timeout"] == 42.0

    @pytest.mark.asyncio
    async def test_retry_sur_erreur_529(self):
        """Retente sur APIStatusError 529, réussit au 2e essai."""
        mock_response = MagicMock()
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [err_529, mock_response]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await call_claude_with_retry(
                mock_client, timeout_s=5.0, max_retries=2,
                model="test", messages=[], max_tokens=10,
            )

        assert result is mock_response
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_epuise_les_retries_et_propage(self):
        """Après max_retries, propage l'erreur 529."""
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = err_529

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(anthropic.APIStatusError):
                await call_claude_with_retry(
                    mock_client, timeout_s=5.0, max_retries=2,
                    model="test", messages=[], max_tokens=10,
                )

        assert mock_client.messages.create.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_pas_de_retry_sur_erreur_400(self):
        """Les erreurs autres que 529 ne sont pas retriées."""
        err_400 = anthropic.APIStatusError(
            "bad request", response=MagicMock(status_code=400), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = err_400

        with pytest.raises(anthropic.APIStatusError):
            await call_claude_with_retry(
                mock_client, timeout_s=5.0, max_retries=3,
                model="test", messages=[], max_tokens=10,
            )

        mock_client.messages.create.assert_called_once()  # aucun retry

    @pytest.mark.asyncio
    async def test_timeout_erreur_pas_retriee(self):
        """APITimeoutError est propagée immédiatement sans retry."""
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )

        with pytest.raises(anthropic.APITimeoutError):
            await call_claude_with_retry(
                mock_client, timeout_s=1.0, max_retries=3,
                model="test", messages=[], max_tokens=10,
            )

        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sleep_appele_entre_retries(self):
        """asyncio.sleep est appelé entre chaque tentative."""
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [err_529, err_529, MagicMock()]

        with patch("app.utils.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await call_claude_with_retry(
                mock_client, timeout_s=5.0, max_retries=3,
                model="test", messages=[], max_tokens=10,
            )

        assert mock_sleep.call_count == 2  # 2 retries = 2 sleeps
```

## Ajouts dans `tests/test_skill.py`

```python
class TestSkillAvecConfig:
    @pytest.mark.asyncio
    async def test_execute_utilise_timeout_config(self, ratios_msft, graham_output_msft):
        """Le timeout de SkillConfig est passé à call_claude_with_retry."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=graham_output_msft.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=100, output_tokens=50,
            cache_read_input_tokens=0, cache_creation_input_tokens=500,
        )
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        config = SkillConfig(timeout_s=42.0, max_retries=0)
        skill = GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", config=config)
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["timeout"] == 42.0

    @pytest.mark.asyncio
    async def test_execute_appelle_tracer_si_present(self, ratios_msft, graham_output_msft):
        """Si config.tracer est fourni, record_generation est appelé."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=graham_output_msft.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=100, output_tokens=50,
            cache_read_input_tokens=0, cache_creation_input_tokens=500,
        )
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        mock_tracer = MagicMock()
        config = SkillConfig(tracer=mock_tracer)
        skill = GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", config=config)
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill.execute(inp)

        mock_tracer.record_generation.assert_called_once()
        call_kwargs = mock_tracer.record_generation.call_args.kwargs
        assert call_kwargs["skill_id"]  == "graham_analysis"
        assert call_kwargs["ticker"]    == "MSFT"
        assert call_kwargs["model"]     == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_execute_sans_tracer_ne_plante_pas(self, ratios_msft, graham_output_msft):
        """Sans tracer, execute() fonctionne normalement."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=graham_output_msft.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=100, output_tokens=50,
            cache_read_input_tokens=0, cache_creation_input_tokens=500,
        )
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = GrahamAnalysisSkill(
            client=mock_client, model="claude-sonnet-4-6", config=SkillConfig(tracer=None)
        )
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill.execute(inp)
        assert isinstance(output, GrahamAnalysisOutput)
```

## Ajouts dans `tests/test_api.py`

```python
class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_retourne_200(self, async_client):
        from app.orchestrator.core import MetricsResponse
        app.state.orchestrator.get_metrics = AsyncMock(
            return_value=MetricsResponse(
                period_days=30, total_analyses=5, total_cost_usd=0.012,
                avg_cost_per_analysis=0.0024, cache_hit_ratio_avg=0.82,
                top_tickers=[], skills_usage={"graham_analysis": 5},
            )
        )
        r = await async_client.get("/metrics")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_champs_presents(self, async_client):
        from app.orchestrator.core import MetricsResponse
        app.state.orchestrator.get_metrics = AsyncMock(
            return_value=MetricsResponse(
                period_days=30, total_analyses=10, total_cost_usd=0.05,
                avg_cost_per_analysis=0.005, cache_hit_ratio_avg=0.75,
                top_tickers=[], skills_usage={},
            )
        )
        r = await async_client.get("/metrics")
        data = r.json()
        for field in ("period_days", "total_analyses", "total_cost_usd",
                      "cache_hit_ratio_avg", "top_tickers", "skills_usage"):
            assert field in data

    @pytest.mark.asyncio
    async def test_metrics_days_trop_grand_retourne_422(self, async_client):
        r = await async_client.get("/metrics?days=400")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_metrics_days_zero_retourne_422(self, async_client):
        r = await async_client.get("/metrics?days=0")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_version_014(self, async_client):
        """Version passe à 0.3.0 après Sprint 4."""
        r = await async_client.get("/healthz")
        assert r.json()["version"] == "0.3.0"
```

## Mettre à jour la fixture `async_client` dans `tests/test_api.py`

Le constructeur de `GrahamAnalysisSkill` a changé (`config=SkillConfig()`).
Mettre à jour le patch pour passer `config=SkillConfig()` ou utiliser `MagicMock()` :

```python
# Dans async_client, le patch de _load_system_prompt reste inchangé.
# La fixture mock l'orchestrateur entier après lifespan — aucun changement.
```

Le patch existant de `_load_system_prompt` suffit — le constructeur `SkillConfig()`
ne nécessite pas de mock supplémentaire puisque `tracer=None` par défaut.

---

# CONTRAINTES NON-NÉGOCIABLES

- `LangfuseTracer` est `None` si `LANGFUSE_SECRET_KEY` absent — aucun crash
- Une erreur Langfuse (`record_generation` lève une exception) ne fait jamais
  échouer l'analyse — `try/except Exception` obligatoire dans `record_generation`
- Le timeout est transmis à `messages.create(timeout=...)` — pas via `asyncio.wait_for`
- Pas de retry sur `APITimeoutError` — le timeout est un signal explicite de dépassement
- `max_retries=0` désactive le retry (0 tentative supplémentaire = 1 seul appel)
- `SkillConfig` est créée une seule fois dans le lifespan et partagée entre tous les skills
- Tous les nouveaux tests passent sans service réel (Langfuse, Claude, PostgreSQL)

---

# CRITÈRE DE SUCCÈS UNIQUE

```bash
# 1. Tous les tests passent
pytest tests/ -v

# 2. Vérification timeout : configurable via env
CLAUDE_TIMEOUT_S=10 docker-compose up -d --build copilote
curl localhost:8000/healthz
# Attendu : {"version": "0.3.0", ...}

# 3. Métriques
curl "localhost:8000/metrics?days=7"
# Attendu :
# {
#   "period_days": 7,
#   "total_analyses": N,
#   "total_cost_usd": X.XXXXXX,
#   "avg_cost_per_analysis": X.XXXXXX,
#   "cache_hit_ratio_avg": 0.XXXX,
#   "top_tickers": [...],
#   "skills_usage": {"graham_analysis": N, ...}
# }

# 4. Test du retry (simuler une surcharge)
# → Lancer la suite de tests test_retry.py isolément
pytest tests/test_retry.py -v
# Attendu : 7/7 tests passent

# 5. Si Langfuse configuré — vérifier dans l'UI Langfuse
# → Lancer une analyse, ouvrir cloud.langfuse.com
# → La trace doit apparaître avec cost_usd, cache_hit_ratio, latency_ms
```

---

# FORMAT DE SORTIE

**Fichiers à CRÉER :**

| Fichier | Description |
|---------|-------------|
| `app/utils/retry.py` | `call_claude_with_retry()` — timeout + backoff exponentiel sur 529 |
| `app/observability/__init__.py` | Package marker (vide) |
| `app/observability/langfuse_client.py` | `LangfuseTracer` — wrapper optionnel Langfuse SDK |
| `tests/test_retry.py` | 7 tests unitaires du retry (mock `asyncio.sleep`, `APIStatusError`) |

**Fichiers à MODIFIER :**

| Fichier | Changement |
|---------|-----------|
| `app/skills/base.py` | Ajouter `SkillConfig` dataclass |
| `app/skills/tier2/graham_analysis/skill.py` | Constructeur `config: SkillConfig`, `call_claude_with_retry()`, trace Langfuse |
| `app/skills/tier2/earnings_quality/skill.py` | Même pattern que graham_analysis |
| `app/orchestrator/core.py` | `MetricsResponse`, `TickerMetrics`, `get_metrics()` |
| `app/api/main.py` | Version 0.3.0, init `LangfuseTracer` + `SkillConfig`, endpoint `GET /metrics`, `shutdown()` dans lifespan |
| `requirements.txt` | Ajouter `langfuse>=2.0.0` |
| `.env.example` | Ajouter `CLAUDE_TIMEOUT_S`, `CLAUDE_MAX_RETRIES`, `LANGFUSE_*` |
| `tests/test_skill.py` | Classe `TestSkillAvecConfig` — 3 tests |
| `tests/test_api.py` | Classe `TestMetrics` — 5 tests, version 0.3.0 |

---

# MODE DE RÉPONSE

1. Implémenter S4-3 + S4-4 (retry) en premier — c'est la fondation des deux autres
2. Implémenter S4-1 (Langfuse) ensuite — s'appuie sur `call_claude_with_retry`
3. Implémenter S4-2 (metrics) en dernier — indépendant mais validé en bout de chaîne
4. Pas de commentaires décoratifs (`# ===`), pas de TODO, pas de placeholders
5. Après les fichiers, donner uniquement :
   - Liste des fichiers créés/modifiés (path + 1 ligne de description)
   - Commande de validation (`pytest tests/ -v` + curl)
   - Points d'attention si applicable

---

*Sprint 4 — à exécuter après complétion et validation du Sprint 3.*
*Réviser ce prompt si l'architecture change entre la rédaction et l'exécution.*
