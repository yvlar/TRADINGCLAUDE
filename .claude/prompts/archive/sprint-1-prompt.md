# Sprint 1 — Prompt d'implémentation
**Corrections immédiates avant Phase 1 RAG**
*Généré le 7 mai 2026 — à utiliser dans une session Claude fraîche*

---

# RÔLE

Développeur Python senior spécialiste RAG et architecture de systèmes LLM.
Tu maîtrises FastAPI, asyncpg, Qdrant, le SDK Anthropic Python (prompt caching,
structured output), et les patterns de production pour les applications IA.

---

# CONTEXTE

Projet : copilote financier RAG — analyse d'investissement multi-frameworks
basé sur 15 skills (Graham, Buffett, Dorsey, Damodaran, etc.).

**Stack :** Python 3.11, FastAPI, Anthropic SDK, asyncpg, Qdrant, PostgreSQL, Redis
**Source de vérité :** `architecture-copilote-financier.md` (sections 3.2, 7.3, 8.2, 9.1, 10)
**Phase active :** Phase 0 — aucune connexion Qdrant réelle, `get_citations()` retourne `[]`

**Contraintes non-négociables :**
- Type hints stricts (pas de `Any` non justifié)
- Async/await sur tout I/O
- Pydantic v2 pour tous les modèles de données
- `cost_usd` calculé et persisté sur chaque appel Claude
- Aucun `print()` — utiliser `logging` (`logger = logging.getLogger(__name__)`)
- Langue du code : anglais | Commentaires, docstrings : français
- Tests : pytest-asyncio, aucun service réel dans les tests unitaires

**État actuel avant Sprint 1 :**

| Fichier | Problème |
|---------|----------|
| `app/skills/tier2/graham_analysis/skill.py` | Contient `SkillBase`, `Citation`, `_PRICING`, `_calculate_cost` — tout doit être extrait |
| `app/orchestrator/core.py:87-90` | `tokens_input=0, tokens_output=0, tokens_cache_read=0, tokens_cache_creation=0` en dur |
| `app/skills/tier2/graham_analysis/schemas.py` | Aucun `@model_validator` sur le nombre de critères |
| `app/api/main.py:76-78` | `/healthz` retourne `{"status":"ok","version":"0.1.0"}` sans vérifier PostgreSQL ni Qdrant |
| `tests/test_skill.py:161` | `asyncio.get_event_loop().run_until_complete(...)` déprécié Python 3.10+ |

---

# TÂCHE

Exécuter les 7 tâches du Sprint 1 dans l'ordre. Chaque tâche est indépendante
sauf S1-3 qui dépend de S1-1 et S1-2, et S1-4 qui dépend de S1-3.

---

## S1-1 — Créer `app/skills/base.py`

Créer le fichier `app/skills/base.py`. Ce fichier devient la source de vérité
de l'interface commune à tous les skills (section 3.2 de l'architecture).

**Contenu exact :**

```python
# app/skills/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class Citation(BaseModel):
    """Référence RAG retournée par get_citations. Liste vide en Phase 0."""

    source: str
    extrait: str
    score: float


class UsageDetail(BaseModel):
    """Compteurs de tokens et coût d'un appel Claude — remontés par execute()."""

    tokens_input: int
    tokens_output: int
    tokens_cache_read: int
    tokens_cache_creation: int
    cost_usd: float
    model: str


class SkillBase(ABC):
    """Classe de base dont héritent tous les skills Tier 2 (section 3.2)."""

    skill_id: ClassVar[str]
    tier: ClassVar[int]
    description: ClassVar[str]

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> tuple[BaseModel, UsageDetail]:
        """Exécute le skill via l'API Claude. Retourne (output, usage_detail)."""
        ...

    def get_system_prompt(self) -> list[dict[str, Any]]:
        """Retourne le system prompt formaté avec cache_control (section 8.2)."""
        raise NotImplementedError

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """Recherche RAG dans Qdrant. Retourne une liste vide en Phase 0."""
        return []
```

**Créer aussi `app/skills/__init__.py` s'il n'existe pas déjà (fichier vide).**

---

## S1-2 — Créer `app/utils/costs.py`

Extraire `_PRICING` et `_calculate_cost` depuis `app/skills/tier2/graham_analysis/skill.py`
vers un module utilitaire partagé.

**Créer `app/utils/__init__.py` (vide) si absent.**

**Contenu de `app/utils/costs.py` :**

```python
# app/utils/costs.py
from __future__ import annotations

import anthropic

PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input":          3.00 / 1_000_000,
        "output":         15.00 / 1_000_000,
        "cache_read":     0.30 / 1_000_000,
        "cache_creation": 3.75 / 1_000_000,
    },
    "claude-opus-4-7": {
        "input":          15.00 / 1_000_000,
        "output":         75.00 / 1_000_000,
        "cache_read":     1.50 / 1_000_000,
        "cache_creation": 18.75 / 1_000_000,
    },
    "claude-haiku-4-5-20251001": {
        "input":          0.80 / 1_000_000,
        "output":         4.00 / 1_000_000,
        "cache_read":     0.08 / 1_000_000,
        "cache_creation": 1.00 / 1_000_000,
    },
}


def calculate_cost(usage: anthropic.types.Usage, model: str) -> float:
    """Calcule le coût en USD depuis l'objet usage de l'API Anthropic."""
    pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    return (
        usage.input_tokens * pricing["input"]
        + usage.output_tokens * pricing["output"]
        + getattr(usage, "cache_read_input_tokens", 0) * pricing["cache_read"]
        + getattr(usage, "cache_creation_input_tokens", 0) * pricing["cache_creation"]
    )
```

---

## S1-3 — Mettre à jour `app/skills/tier2/graham_analysis/skill.py`

Réécrire `skill.py` pour :
1. Supprimer `SkillBase`, `Citation`, `_PRICING`, `_calculate_cost`, `_parse_claude_json` locaux
2. Importer depuis `app.skills.base` et `app.utils.costs`
3. Changer la signature de `execute()` : retourne `tuple[GrahamAnalysisOutput, UsageDetail]`
4. Supprimer l'injection de `cost_usd` dans `data` avant validation Pydantic

**`_parse_claude_json` reste dans ce fichier** (c'est une fonction de parsing propre au skill).

**Nouveau `skill.py` complet :**

```python
# app/skills/tier2/graham_analysis/skill.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, ClassVar

import anthropic

from app.skills.base import Citation, SkillBase, UsageDetail
from app.utils.costs import calculate_cost
from .schemas import GrahamAnalysisInput, GrahamAnalysisOutput


def _parse_claude_json(text: str) -> dict[str, Any]:
    """Parse le JSON depuis la réponse Claude, gère les blocs markdown optionnels."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class GrahamAnalysisSkill(SkillBase):
    """
    Skill Tier 2 : filtrage value Graham — 8 critères défensifs + 5 entrepreneuriaux.
    Correspond au skill claude `graham-stock-screening` vectorisé dans Qdrant en Phase 1.
    """

    skill_id: ClassVar[str] = "graham_analysis"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique les critères quantitatifs de Graham (chapitres 14-15 de The Intelligent Investor) "
        "et calcule la valeur intrinsèque par les deux formules Graham."
    )

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model
        self._system_prompt_text = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Charge le contenu de prompts/system.md."""
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    def get_system_prompt(self) -> list[dict[str, Any]]:
        """
        Format liste avec cache_control pour activer le prompt caching Anthropic.
        Section 8.2 de l'architecture.
        """
        return [
            {
                "type": "text",
                "text": self._system_prompt_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _build_user_message(self, input_data: GrahamAnalysisInput) -> str:
        """Construit le message utilisateur avec les ratios sérialisés en JSON."""
        ratios_json = input_data.ratios.model_dump_json(indent=2)
        return (
            f"Analyse les ratios financiers de **{input_data.ticker}** :\n\n"
            f"```json\n{ratios_json}\n```\n\n"
            "Applique les 8 critères défensifs et les 5 critères entrepreneuriaux de Graham. "
            "Retourne uniquement le JSON structuré conforme au format de sortie défini."
        )

    async def execute(
        self, input_data: GrahamAnalysisInput
    ) -> tuple[GrahamAnalysisOutput, UsageDetail]:
        """
        Appelle l'API Claude avec le system prompt caché et les ratios en message utilisateur.
        Parse la réponse JSON et retourne (GrahamAnalysisOutput, UsageDetail).
        """
        user_message = self._build_user_message(input_data)

        response = await self._client.messages.create(
            model=self._model,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
            max_tokens=2048,
        )

        raw_text = response.content[0].text
        data = _parse_claude_json(raw_text)

        cost_usd = calculate_cost(response.usage, self._model)

        usage_detail = UsageDetail(
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            tokens_cache_read=getattr(response.usage, "cache_read_input_tokens", 0),
            tokens_cache_creation=getattr(response.usage, "cache_creation_input_tokens", 0),
            cost_usd=cost_usd,
            model=self._model,
        )

        graham_output = GrahamAnalysisOutput.model_validate(data)
        return graham_output, usage_detail
```

**Note :** `GrahamAnalysisOutput` ne reçoit plus `cost_usd` injecté dans `data`.
Le champ `cost_usd` reste dans le schéma avec sa valeur par défaut `0.0` — la source
de coût pour les clients de l'API sera `AnalyzeResponse.cost_usd` (venant de `UsageDetail`).

---

## S1-4 — Corriger `_persist()` dans `app/orchestrator/core.py`

1. Mettre à jour `run_company_analysis()` pour déballer le tuple retourné par `execute()`
2. Passer `UsageDetail` à `_persist()`
3. Utiliser les vrais compteurs de tokens dans l'INSERT SQL

**Fichier `core.py` complet :**

```python
# app/orchestrator/core.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg
from pydantic import BaseModel

from app.skills.base import UsageDetail
from app.skills.tier2.graham_analysis.schemas import (
    GrahamAnalysisInput,
    GrahamAnalysisOutput,
    GrahamRatios,
)
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill

logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    """Corps de la requête POST /analyze — section 5.2 de l'architecture."""

    ticker: str
    ratios: GrahamRatios


class AnalyzeResponse(BaseModel):
    """Réponse complète du workflow company_analysis en Phase 0."""

    analysis_id: str
    ticker: str
    workflow: str
    skills_applied: list[str]
    graham: GrahamAnalysisOutput
    cost_usd: float
    created_at: str


class Orchestrator:
    """
    Orchestre le workflow company_analysis selon la section 9.1 de l'architecture.
    Phase 0 : appelle uniquement graham_analysis.
    """

    def __init__(self, db_pool: asyncpg.Pool, graham_skill: GrahamAnalysisSkill) -> None:
        self._db = db_pool
        self._graham = graham_skill

    async def run_company_analysis(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """
        Exécute le workflow company_analysis Phase 0.
        Séquence : graham_analysis → persist → retourne AnalyzeResponse.
        """
        graham_input = GrahamAnalysisInput(ticker=request.ticker, ratios=request.ratios)
        graham_output, usage_detail = await self._graham.execute(graham_input)

        analysis_id = await self._persist(request, graham_output, usage_detail)

        return AnalyzeResponse(
            analysis_id=str(analysis_id),
            ticker=request.ticker,
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output,
            cost_usd=usage_detail.cost_usd,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _persist(
        self,
        request: AnalyzeRequest,
        graham_output: GrahamAnalysisOutput,
        usage_detail: UsageDetail,
    ) -> str:
        """Insère l'analyse dans analysis_history et retourne l'UUID généré."""
        skills_used = json.dumps(["graham_analysis"])
        input_data = json.dumps(request.ratios.model_dump())
        result = json.dumps(graham_output.model_dump())

        row = await self._db.fetchrow(
            """
            INSERT INTO analysis_history (
                ticker, workflow_name, skills_used, input_data, result,
                cost_usd, tokens_input, tokens_output,
                tokens_cache_read, tokens_cache_creation
            )
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            request.ticker,
            "company_analysis",
            skills_used,
            input_data,
            result,
            usage_detail.cost_usd,
            usage_detail.tokens_input,
            usage_detail.tokens_output,
            usage_detail.tokens_cache_read,
            usage_detail.tokens_cache_creation,
        )

        return str(row["id"])
```

---

## S1-5 — Ajouter `@model_validator` dans `schemas.py`

Modifier `app/skills/tier2/graham_analysis/schemas.py` :

1. Ajouter l'import `model_validator` depuis pydantic
2. Supprimer `Citation` de ce fichier (déplacée dans `app/skills/base.py`)
3. Mettre à jour les imports dans `skill.py` qui importait `Citation` depuis `.schemas`
4. Ajouter le validateur sur `GrahamAnalysisOutput`

**Diff à appliquer dans `schemas.py` :**

```python
# Remplacer la ligne d'import existante :
from pydantic import BaseModel, Field

# Par :
from pydantic import BaseModel, Field, model_validator
```

```python
# Supprimer la classe Citation entière (lignes 6-11 actuelles) :
class Citation(BaseModel):
    """Référence RAG retournée par get_citations. Liste vide en Phase 0."""
    source: str = Field(...)
    extrait: str = Field(...)
    score: float = Field(...)
```

```python
# Ajouter après le champ cost_usd dans GrahamAnalysisOutput :
    @model_validator(mode="after")
    def valider_comptes_criteres(self) -> "GrahamAnalysisOutput":
        if len(self.criteria_defensif) != 8:
            raise ValueError(
                f"criteria_defensif : attendu 8 critères, reçu {len(self.criteria_defensif)}"
            )
        if len(self.criteria_entreprenant) != 5:
            raise ValueError(
                f"criteria_entreprenant : attendu 5 critères, reçu {len(self.criteria_entreprenant)}"
            )
        return self
```

**`schemas.py` complet après modification :**

```python
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class GrahamRatios(BaseModel):
    """Ratios financiers fournis manuellement par l'utilisateur en Phase 0."""

    pe: float = Field(description="Price/Earnings ratio (cours / BPA)")
    pb: float = Field(description="Price/Book ratio (cours / valeur comptable par action)")
    current_ratio: float | None = Field(None, description="Actif circulant / Passif circulant (None pour les banques)")
    debt_equity: float = Field(description="Dette totale / Capitaux propres")
    eps_growth_10y: float = Field(
        description="Croissance totale du BPA sur 10 ans, format fraction (0.85 = 85 % total)"
    )
    price: float = Field(description="Cours actuel de l'action")
    book_value: float = Field(description="Valeur comptable par action (book value per share)")
    eps_ttm: float | None = Field(None, description="BPA des 12 derniers mois. Calculé price/pe si absent.")
    revenue_bn: float | None = Field(None, description="Revenus annuels en milliards de la devise du titre")
    dividend_years: int | None = Field(None, description="Nombre d'années consécutives de dividendes versés")
    no_deficit_years: int | None = Field(None, description="Nombre d'années sans déficit sur les dernières années")


class GrahamAnalysisInput(BaseModel):
    """Input du skill graham_analysis — correspond au body du POST /analyze."""

    ticker: str = Field(description="Symbole boursier (ex: MSFT, BNS.TO)")
    ratios: GrahamRatios


class GrahamCriterion(BaseModel):
    """Évaluation d'un critère Graham individuel."""

    numero: int = Field(description="Numéro du critère (1-8 pour défensif, 1-5 pour entreprenant)")
    nom: str = Field(description="Nom court du critère")
    passe: bool = Field(description="True si le critère est satisfait")
    valeur_observee: str = Field(description="Valeur constatée depuis les ratios, ou DONNÉES_MANQUANTES")
    seuil: str = Field(description="Seuil Graham applicable")
    commentaire: str = Field(description="Explication concise du résultat")


class GrahamAnalysisOutput(BaseModel):
    """Résultat complet du skill graham_analysis produit par Claude (section 11.2)."""

    ticker: str
    profil_applique: str = Field(description="Toujours LES_DEUX en Phase 0")
    defensive_score: int = Field(ge=0, le=8, description="Critères défensifs satisfaits sur 8")
    enterprising_score: int = Field(ge=0, le=5, description="Critères entrepreneuriaux satisfaits sur 5")
    criteria_defensif: list[GrahamCriterion] = Field(description="Les 8 critères défensifs évalués")
    criteria_entreprenant: list[GrahamCriterion] = Field(description="Les 5 critères entrepreneuriaux évalués")
    valeur_intrinseque_simple: float | None = Field(
        None, description="V = BPA × (8.5 + 2g). Null si BPA incalculable."
    )
    valeur_intrinseque_ajustee: float | None = Field(
        None, description="V = BPA × (8.5 + 2g) × (4.4/Y). Null si BPA incalculable."
    )
    marge_securite: float | None = Field(
        None, description="(V_ajustée - prix) / V_ajustée. Positif = sous-évalué."
    )
    drapeaux_rouges: list[str] = Field(description="Drapeaux rouges identifiés depuis les ratios")
    verdict: str = Field(description="REJETER | WATCHLIST | CANDIDAT_SOLIDE | EXEMPLAIRE")
    verdict_detail: str = Field(description="Explication narrative du verdict en 2-3 phrases")
    recommandation_prochaine_etape: list[str] = Field(
        description="Skills recommandés pour la suite de l'analyse"
    )
    citations: list[str] = Field(default_factory=list, description="Vide en Phase 0, alimenté par RAG en Phase 1+")
    cost_usd: float = Field(default=0.0, description="Coût API Claude de cet appel en USD")

    @model_validator(mode="after")
    def valider_comptes_criteres(self) -> "GrahamAnalysisOutput":
        if len(self.criteria_defensif) != 8:
            raise ValueError(
                f"criteria_defensif : attendu 8 critères, reçu {len(self.criteria_defensif)}"
            )
        if len(self.criteria_entreprenant) != 5:
            raise ValueError(
                f"criteria_entreprenant : attendu 5 critères, reçu {len(self.criteria_entreprenant)}"
            )
        return self
```

---

## S1-6 — Corriger le test déprécié dans `tests/test_skill.py`

Remplacer le test `test_get_citations_retourne_liste_vide` qui utilise
`asyncio.get_event_loop().run_until_complete()` (déprécié Python 3.10+).

**Chercher et remplacer dans `tests/test_skill.py` :**

```python
# AVANT (lignes ~158-164) :
    def test_get_citations_retourne_liste_vide(self, skill):
        """En Phase 0, get_citations retourne toujours []."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            skill.get_citations("current ratio")
        )
        assert result == []

# APRÈS :
    @pytest.mark.asyncio
    async def test_get_citations_retourne_liste_vide(self, skill):
        """En Phase 0, get_citations retourne toujours []."""
        result = await skill.get_citations("current ratio")
        assert result == []
```

**Mettre aussi à jour les tests `TestGrahamAnalysisSkillExecute` qui testent le retour de `execute()` :**

`execute()` retourne maintenant `tuple[GrahamAnalysisOutput, UsageDetail]`.
Les tests qui font `output = await skill.execute(inp)` doivent devenir
`output, usage = await skill.execute(inp)`.

Tests à mettre à jour dans `TestGrahamAnalysisSkillExecute` :
- `test_execute_retourne_output_valide` → `assert isinstance(output, GrahamAnalysisOutput)`
- `test_execute_ticker_correct` → `assert output.ticker == "MSFT"`
- `test_execute_cost_usd_non_nul` → remplacer par `assert usage.cost_usd > 0.0`
- `test_execute_citations_vides` → `assert output.citations == []`
- `test_execute_appelle_messages_create` → inchangé (inspecte le mock)
- `test_execute_passe_model_correct` → inchangé
- `test_execute_passe_system_avec_cache_control` → inchangé
- `test_execute_gere_json_dans_bloc_markdown` → déballer le tuple

**Ajouter deux nouveaux tests dans `TestGrahamAnalysisSkillExecute` :**

```python
    @pytest.mark.asyncio
    async def test_execute_retourne_usage_detail(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        _, usage = await skill_avec_mock_client.execute(inp)
        assert isinstance(usage, UsageDetail)

    @pytest.mark.asyncio
    async def test_execute_usage_tokens_non_nuls(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        _, usage = await skill_avec_mock_client.execute(inp)
        assert usage.tokens_input == 1000
        assert usage.tokens_output == 200
        assert usage.tokens_cache_creation == 1500
        assert usage.model == "claude-sonnet-4-6"
```

**Mettre à jour les imports dans `test_skill.py` :**

```python
# Ajouter à la liste des imports depuis app :
from app.skills.base import UsageDetail
from app.utils.costs import PRICING, calculate_cost
```

Et supprimer les imports depuis `skill.py` pour `_PRICING` et `_calculate_cost`
(renommés en `PRICING` et `calculate_cost`, maintenant dans `app.utils.costs`).

**Mettre aussi à jour `tests/test_orchestrator.py` :**

Le mock du skill doit maintenant retourner un tuple `(GrahamAnalysisOutput, UsageDetail)`.
Trouver le mock de `graham_skill.execute` et ajouter le `UsageDetail` :

```python
# Dans la fixture ou le patch de execute(), changer :
mock_skill.execute.return_value = graham_output_msft

# En :
from app.skills.base import UsageDetail
mock_usage = UsageDetail(
    tokens_input=1000,
    tokens_output=200,
    tokens_cache_read=0,
    tokens_cache_creation=1500,
    cost_usd=0.0056,
    model="claude-sonnet-4-6",
)
mock_skill.execute.return_value = (graham_output_msft, mock_usage)
```

Ajouter un test dans `TestOrchestrator` :

```python
async def test_persist_appele_avec_vrais_tokens(self, ...):
    """_persist reçoit un UsageDetail avec des tokens non-zéro."""
    # Inspecter l'appel DB pour confirmer que les params 7-10 ne sont pas 0
```

---

## S1-7 — Enrichir `/healthz` dans `app/api/main.py`

**Changements requis :**

1. Ajouter `httpx` aux imports (déjà dans `requirements-dev.txt`, à ajouter dans `requirements.txt`)
2. Stocker `db_pool` et l'URL Qdrant dans `app.state`
3. Reécrire `/healthz` pour tester PostgreSQL et Qdrant
4. Bumper la version à `"0.1.1"`
5. Gérer le cas où un service est indisponible : retourner HTTP 503

**Ajouter dans `requirements.txt` :**

```
httpx>=0.27.0
```

**Modifications dans `main.py` :**

```python
# Changer la version :
_VERSION = "0.1.1"
```

```python
# Dans le bloc lifespan, après avoir créé db_pool, ajouter :
qdrant_url = _get_env("QDRANT_URL", "http://qdrant:6333")

app.state.orchestrator = orchestrator
app.state.db_pool = db_pool
app.state.qdrant_url = qdrant_url
```

```python
# Remplacer le endpoint /healthz entier :
import httpx
from fastapi.responses import JSONResponse

@app.get("/healthz", summary="Vérification de santé du service")
async def healthz(request: Request) -> JSONResponse:
    """Vérifie le statut du service, de PostgreSQL et de Qdrant."""
    checks: dict[str, str] = {"status": "ok", "version": _VERSION}
    status_code = 200

    # Vérification PostgreSQL
    try:
        await request.app.state.db_pool.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        logger.exception("PostgreSQL indisponible lors du healthz")
        checks["postgres"] = "error"
        checks["status"] = "degraded"
        status_code = 503

    # Vérification Qdrant
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{request.app.state.qdrant_url}/healthz")
            checks["qdrant"] = "ok" if resp.status_code == 200 else "error"
            if resp.status_code != 200:
                checks["status"] = "degraded"
                status_code = 503
    except Exception:
        logger.exception("Qdrant indisponible lors du healthz")
        checks["qdrant"] = "error"
        checks["status"] = "degraded"
        status_code = 503

    return JSONResponse(content=checks, status_code=status_code)
```

**Mettre à jour `tests/test_api.py` :**

Le test `test_status_ok` doit vérifier `checks["status"] == "ok"` — inchangé.
Ajouter un test pour le cas PostgreSQL indisponible → 503 :

```python
@pytest.mark.asyncio
async def test_healthz_postgres_indisponible_retourne_503(self, async_client):
    """Si db_pool.fetchval lève une exception, /healthz retourne 503."""
    app.state.db_pool.fetchval = AsyncMock(side_effect=Exception("connexion refusée"))
    r = await async_client.get("/healthz")
    assert r.status_code == 503
    assert r.json()["postgres"] == "error"
```

Mettre à jour `test_version_presente` pour `"0.1.1"` ou lire `_VERSION` dynamiquement.

---

# CONTRAINTES NON-NÉGOCIABLES

- Ne pas modifier l'interface publique de l'API (les champs de `AnalyzeResponse` restent identiques)
- `execute()` sur tous les skills futurs devra retourner `tuple[BaseModel, UsageDetail]`
- Ne pas introduire de dépendances hors `requirements.txt` sans justification explicite
- Chaque fichier fourni est complet et autonome — pas de diff partiel
- Aucun `print()`, aucun `TODO`, aucun placeholder

---

# CRITÈRE DE SUCCÈS UNIQUE

La séquence suivante s'exécute sans erreur et sans warning dépréciation :

```bash
# Tous les tests passent
pytest tests/ -v

# Validation spécifique Sprint 1 :
# 1. Le @model_validator rejette 7 critères
# 2. UsageDetail est retourné par execute()
# 3. Le test get_citations utilise async/await
# 4. /healthz retourne postgres et qdrant dans le JSON
```

En production (`docker-compose up -d`) :

```bash
curl localhost:8000/healthz
# Attendu : {"status":"ok","version":"0.1.1","postgres":"ok","qdrant":"ok"}
```

---

# FORMAT DE SORTIE

Fichiers Python directement dans le repo courant, dans leur chemin définitif.

**Fichiers à CRÉER :**

| Fichier | Description |
|---------|-------------|
| `app/skills/base.py` | `Citation`, `UsageDetail`, `SkillBase` — interface commune |
| `app/skills/__init__.py` | Package marker (vide) |
| `app/utils/__init__.py` | Package marker (vide) |
| `app/utils/costs.py` | `PRICING`, `calculate_cost()` |

**Fichiers à MODIFIER :**

| Fichier | Changement |
|---------|-----------|
| `app/skills/tier2/graham_analysis/skill.py` | Supprimer code extrait, importer depuis base/costs, `execute()` → tuple |
| `app/skills/tier2/graham_analysis/schemas.py` | Supprimer `Citation`, ajouter `@model_validator` |
| `app/orchestrator/core.py` | Déballer tuple, passer `UsageDetail` à `_persist()`, vrais tokens |
| `app/api/main.py` | Version 0.1.1, `app.state.db_pool`, `/healthz` enrichi avec `httpx` |
| `requirements.txt` | Ajouter `httpx>=0.27.0` |
| `tests/test_skill.py` | Corriger `get_event_loop`, déballer tuple, imports mis à jour |
| `tests/test_schemas.py` | Ajouter tests `@model_validator` (7 critères → ValueError) |
| `tests/test_orchestrator.py` | Mock `execute` retourne tuple, ajouter test tokens non-zéro |
| `tests/test_api.py` | Mettre à jour version, ajouter test healthz 503 |

---

# MODE DE RÉPONSE

1. Lire `architecture-copilote-financier.md` sections 3.2, 8.2, 9.1, 10 AVANT de modifier
2. Traiter les tâches dans l'ordre S1-1 → S1-7 (les dépendances le requièrent)
3. Pas de commentaires décoratifs (`# ===`), pas de TODO, pas de placeholders
4. Après les fichiers, donner uniquement :
   - Liste des fichiers créés/modifiés (path + 1 ligne de description)
   - Commande de validation (`pytest tests/ -v`)
   - Points d'attention si applicable

---

*Sprint 1 — à exécuter avant toute implémentation Phase 1 (RAG, Qdrant, ingestion).*
*Réviser ce prompt si l'architecture change entre la rédaction et l'exécution.*
