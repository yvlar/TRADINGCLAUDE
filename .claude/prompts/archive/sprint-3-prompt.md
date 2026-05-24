# Sprint 3 — Prompt d'implémentation
**Deuxième skill — earnings_quality + context enrichment + GET /history**
*Généré le 7 mai 2026 — à utiliser après la complétion du Sprint 2*

---

# PRÉREQUIS

Les Sprints 1 et 2 doivent être complétés :
- `app/skills/base.py` : `SkillBase`, `Citation`, `UsageDetail`
- `app/rag/` : `RagClient`, `EmbeddingClient`, `RagService`
- `execute()` retourne `tuple[BaseModel, UsageDetail]`
- Tous les tests passent (`pytest tests/ -v`)

---

# RÔLE

Développeur Python senior spécialiste RAG et architecture de systèmes LLM.
Tu maîtrises FastAPI, asyncpg, Qdrant, le SDK Anthropic Python (prompt caching,
structured output), et les patterns de production pour les applications IA.

---

# CONTEXTE

Projet : copilote financier RAG — analyse d'investissement multi-frameworks.
**Phase 2 amorce — objectif :** deuxième skill opérationnel, context enrichment
entre skills, et endpoint historique.

**Stack :** Python 3.11, FastAPI, Anthropic SDK, asyncpg, Pydantic v2
**Source de vérité du skill :** `.claude/skills/earnings-quality-fraud-detection/SKILL.md`
et ses 5 fichiers de référence (`beneish-m-score.md`, `altman-z-score.md`,
`piotroski-f-score.md`, `montier-c-score.md`, `sloan-accruals.md`).

**Workflow cible après ce sprint (section 4.1 de l'architecture) :**
```
Phase 1 : [graham_analysis, earnings_quality]
```
`earnings_quality` n'est exécuté que si le body JSON contient `earnings_ratios`.
Si absent, le workflow reste `[graham_analysis]` — aucune régression Phase 0.

**Contraintes non-négociables :**
- Type hints stricts (pas de `Any` non justifié)
- Async/await sur tout I/O
- Pydantic v2 pour tous les modèles
- Prompt system.md > 1 024 tokens (cache_control requis)
- Aucun `print()`, aucun TODO, aucun placeholder
- Langue du code : anglais | Commentaires, docstrings : français
- Tests : pytest-asyncio, aucun service réel

---

# TÂCHE

Exécuter les 4 tâches dans l'ordre. S3-2 et S3-3 dépendent de S3-1.

---

## S3-1 — Créer le skill `earnings_quality`

### Structure à créer

```
app/skills/tier2/earnings_quality/
    __init__.py
    schemas.py
    skill.py
    prompts/
        system.md
```

---

### `schemas.py` — modèles Pydantic

**`EarningsQualityRatios`** — données brutes des états financiers T et T-1.
Les champs `| None` permettent de calculer les scores disponibles même si certaines
données manquent. Si un champ requis pour un score est `None`, le score retourne
`"DONNÉES_MANQUANTES"` dans l'output.

```python
class EarningsQualityRatios(BaseModel):
    """
    Données des états financiers sur deux exercices (T = courant, t1 = exercice précédent).
    Toutes les valeurs monétaires dans la devise du titre (pas normalisées).
    """
    # Compte de résultat
    sales_t:           float           # Revenus de l'exercice courant
    sales_t1:          float           # Revenus de l'exercice précédent
    cogs_t:            float           # Coût des ventes T
    cogs_t1:           float           # Coût des ventes T-1
    net_income_t:      float           # Bénéfice net T
    cfo_t:             float           # Cash flow d'exploitation T
    ebit_t:            float | None = None
    sga_t:             float | None = None
    sga_t1:            float | None = None
    depreciation_t:    float | None = None
    depreciation_t1:   float | None = None

    # Bilan T
    receivables_t:        float        # Créances clients T
    current_assets_t:     float        # Actifs courants T
    current_liabilities_t: float       # Passifs courants T
    total_assets_t:       float        # Total actif T
    inventory_t:          float | None = None
    ppe_net_t:            float | None = None  # PP&E net T
    ppe_gross_t:          float | None = None  # PP&E brut T
    ltd_t:                float | None = None  # Dette long terme T
    retained_earnings_t:  float | None = None
    total_liabilities_t:  float | None = None
    market_cap_t:         float | None = None  # Pour Z-Score cotées
    book_equity_t:        float | None = None  # Pour Z' privées

    # Bilan T-1
    receivables_t1:       float        # Créances clients T-1
    total_assets_t1:      float        # Total actif T-1
    current_assets_t1:    float | None = None
    current_liabilities_t1: float | None = None
    inventory_t1:         float | None = None
    ppe_net_t1:           float | None = None
    ppe_gross_t1:         float | None = None
    ltd_t1:               float | None = None

    # Capital
    shares_issued_net: bool | None = None  # True si émission nette d'actions en T


class GrahamContext(BaseModel):
    """Résumé du verdict Graham passé en contexte à earnings_quality (context enrichment)."""
    verdict:          str
    defensive_score:  int
    marge_securite:   float | None
    drapeaux_rouges:  list[str]


class EarningsQualityInput(BaseModel):
    """Input du skill earnings_quality."""
    ticker:          str
    ratios:          EarningsQualityRatios
    graham_context:  GrahamContext | None = None  # alimenté par l'orchestrateur en Phase 1+
```

**Modèles de détail par cadre :**

```python
class MScoreDetail(BaseModel):
    dsri:   float | None
    gmi:    float | None
    aqi:    float | None
    sgi:    float | None
    depi:   float | None
    sgai:   float | None
    tata:   float | None
    lvgi:   float | None
    m_score: float | None
    interpretation: str  # "faible_risque" | "zone_grise" | "risque_eleve" | "DONNÉES_MANQUANTES"


class ZScoreDetail(BaseModel):
    variante:       str    # "Z_original" | "Z_prime" | "Z_double_prime"
    z_score:        float | None
    interpretation: str    # "zone_sure" | "zone_grise" | "zone_detresse" | "DONNÉES_MANQUANTES"


class FScoreCriterion(BaseModel):
    nom:    str
    passe:  bool
    detail: str


class FScoreDetail(BaseModel):
    criteria:       list[FScoreCriterion]  # 9 critères
    f_score:        int = Field(ge=0, le=9)
    interpretation: str   # "forte_qualite" | "bonne_qualite" | "qualite_moyenne" | "value_trap"


class CScoreSignal(BaseModel):
    nom:     str
    present: bool
    detail:  str


class CScoreDetail(BaseModel):
    signaux:        list[CScoreSignal]  # 6 signaux
    c_score:        int = Field(ge=0, le=6)
    interpretation: str   # "propre" | "signaux_mineurs" | "signaux_multiples"


class SloanDetail(BaseModel):
    accrual_ratio:  float | None
    interpretation: str   # "qualite_elevee" | "neutre" | "qualite_degradee" | "DONNÉES_MANQUANTES"
```

**`EarningsQualityOutput`** avec `@model_validator` sur les listes :

```python
from pydantic import model_validator

class EarningsQualityOutput(BaseModel):
    ticker:            str
    is_financial:      bool = Field(False, description="Banque/assureur — certains scores inapplicables")
    m_score:           MScoreDetail
    z_score:           ZScoreDetail
    f_score:           FScoreDetail
    c_score:           CScoreDetail
    sloan:             SloanDetail
    drapeaux_rouges:   list[str]
    verdict:           str = Field(description="AUCUN_SIGNAL | ATTENTION | WATCHLIST | REJETER")
    verdict_detail:    str
    recommandation_prochaine_etape: list[str]
    citations:         list[Citation] = Field(default_factory=list)
    cost_usd:          float = 0.0

    @model_validator(mode="after")
    def valider_comptes_cadres(self) -> "EarningsQualityOutput":
        if len(self.f_score.criteria) != 9:
            raise ValueError(
                f"f_score.criteria : attendu 9, reçu {len(self.f_score.criteria)}"
            )
        if len(self.c_score.signaux) != 6:
            raise ValueError(
                f"c_score.signaux : attendu 6, reçu {len(self.c_score.signaux)}"
            )
        if self.verdict not in {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}:
            raise ValueError(f"verdict invalide : {self.verdict}")
        return self
```

---

### `prompts/system.md` — system prompt du skill

Le fichier doit dépasser **1 024 tokens** pour que le caching soit rentable.
Il doit couvrir **exactement** (dans cet ordre) :

1. **Rôle** — analyste en détection de manipulation comptable et risque de faillite
2. **M-Score (Beneish 1999)** — formule complète, 8 variables (DSRI, GMI, AQI, SGI, DEPI,
   SGAI, TATA, LVGI), seuils (-2.22 / -1.78), cas d'inapplicabilité
3. **Z-Score (Altman)** — 3 variantes (Z, Z', Z''), seuils par variante, sélection de variante
   selon profil (coté/privé/non-industriel), inapplicabilité aux banques
4. **F-Score (Piotroski 2000)** — 9 critères binaires (4 profitabilité, 3 levier/liquidité,
   2 efficacité), seuils (0-3 / 4-6 / 7 / 8-9), applicable uniquement aux actions value (bas P/B)
5. **C-Score (Montier)** — 6 signaux binaires (divergence NI-CFO, DSO, DIO, autres actifs
   courants, dépréciation, émission d'actions), interprétation 0-1/2-3/4-6
6. **Sloan Accruals** — formule `(NI - CFO) / TA_moyens`, interprétation par décile sectoriel
7. **Verdict combiné** — matrice (0 signal = AUCUN_SIGNAL, 1 = ATTENTION, 2 = WATCHLIST,
   3+ cadres défaillants = REJETER), inapplicabilités sectorielles (banques, utilities, REITs)
8. **Context Graham** — si `graham_context` fourni, mentionner explicitement le verdict Graham
   et croiser les drapeaux rouges avec les signaux comptables détectés
9. **Format de sortie JSON strict** — reproduire exactement la structure de `EarningsQualityOutput`
   avec tous les sous-objets

---

### `skill.py`

Structure identique à `GrahamAnalysisSkill`. Points spécifiques :

```python
class EarningsQualitySkill(SkillBase):
    skill_id:    ClassVar[str] = "earnings_quality"
    tier:        ClassVar[int] = 2
    description: ClassVar[str] = (
        "Détecte les manipulations comptables et le risque de faillite via "
        "M-Score (Beneish), Z-Score (Altman), F-Score (Piotroski), "
        "C-Score (Montier) et accruals (Sloan)."
    )

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model:  str,
        rag_service: RagService | None = None,
        top_k:  int = 5,
    ) -> None: ...

    def _build_user_message(
        self,
        input_data: EarningsQualityInput,
        citations:  list[Citation],
    ) -> str:
        """
        Construit le message utilisateur.
        Si graham_context fourni, l'inclure en tête avant les ratios :
        '## Contexte Graham\nVerdict : {verdict}, Score défensif : {score}/8 ...'
        """
        ...

    async def execute(
        self, input_data: EarningsQualityInput
    ) -> tuple[EarningsQualityOutput, UsageDetail]:
        """Même pattern que GrahamAnalysisSkill.execute() — timer, RAG, log structuré."""
        ...
```

La query RAG pour `get_citations()` :
```python
rag_query = (
    f"earnings quality fraud detection {input_data.ticker} "
    f"accruals M-Score Z-Score F-Score Beneish Piotroski"
)
```

---

## S3-2 — Ajouter `earnings_quality` au workflow

### Mise à jour `app/api/main.py`

1. Bumper la version : `_VERSION = "0.2.0"`
2. Instancier `EarningsQualitySkill` dans le lifespan :

```python
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill

# Dans lifespan, après graham_skill :
earnings_skill = EarningsQualitySkill(
    client=anthropic_client,
    model=model,
    rag_service=rag_service,
    top_k=top_k,
)
orchestrator = Orchestrator(
    db_pool=db_pool,
    graham_skill=graham_skill,
    earnings_skill=earnings_skill,
)
```

### Mise à jour `app/orchestrator/core.py`

**`AnalyzeRequest`** — ajouter le champ optionnel :

```python
class AnalyzeRequest(BaseModel):
    ticker:          str
    ratios:          GrahamRatios
    earnings_ratios: EarningsQualityRatios | None = None
    # Si None → earnings_quality ignoré, workflow reste ["graham_analysis"]
```

**`AnalyzeResponse`** — ajouter le champ optionnel :

```python
class AnalyzeResponse(BaseModel):
    analysis_id:      str
    ticker:           str
    workflow:         str
    skills_applied:   list[str]
    graham:           GrahamAnalysisOutput
    earnings_quality: EarningsQualityOutput | None = None
    cost_usd:         float
    created_at:       str
```

**`Orchestrator`** — nouveau constructeur et workflow :

```python
class Orchestrator:
    def __init__(
        self,
        db_pool:        asyncpg.Pool,
        graham_skill:   GrahamAnalysisSkill,
        earnings_skill: EarningsQualitySkill,
    ) -> None:
        self._db       = db_pool
        self._graham   = graham_skill
        self._earnings = earnings_skill
```

---

## S3-3 — Système de context enrichment

Le résultat de `graham_analysis` est passé en entrée de `earnings_quality`.
Le context enrichment se fait dans `run_company_analysis()` de l'orchestrateur.

**`run_company_analysis()` complet :**

```python
async def run_company_analysis(self, request: AnalyzeRequest) -> AnalyzeResponse:
    # --- Étape 1 : Graham ---
    graham_input = GrahamAnalysisInput(ticker=request.ticker, ratios=request.ratios)
    graham_output, graham_usage = await self._graham.execute(graham_input)

    skills_applied = ["graham_analysis"]
    total_cost     = graham_usage.cost_usd
    all_usages     = [graham_usage]

    # --- Étape 2 : Earnings quality (si données fournies) ---
    earnings_output: EarningsQualityOutput | None = None

    if request.earnings_ratios is not None:
        # Context enrichment — résultat Graham → input Earnings
        graham_ctx = GrahamContext(
            verdict=graham_output.verdict,
            defensive_score=graham_output.defensive_score,
            marge_securite=graham_output.marge_securite,
            drapeaux_rouges=graham_output.drapeaux_rouges,
        )
        earnings_input = EarningsQualityInput(
            ticker=request.ticker,
            ratios=request.earnings_ratios,
            graham_context=graham_ctx,
        )
        earnings_output, earnings_usage = await self._earnings.execute(earnings_input)
        skills_applied.append("earnings_quality")
        total_cost += earnings_usage.cost_usd
        all_usages.append(earnings_usage)

    analysis_id = await self._persist(request, graham_output, earnings_output, all_usages)

    return AnalyzeResponse(
        analysis_id=str(analysis_id),
        ticker=request.ticker,
        workflow="company_analysis",
        skills_applied=skills_applied,
        graham=graham_output,
        earnings_quality=earnings_output,
        cost_usd=total_cost,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
```

**`_persist()` mis à jour :**

```python
async def _persist(
    self,
    request:         AnalyzeRequest,
    graham_output:   GrahamAnalysisOutput,
    earnings_output: EarningsQualityOutput | None,
    usages:          list[UsageDetail],
) -> str:
    skills_used = json.dumps(
        ["graham_analysis"] + (["earnings_quality"] if earnings_output else [])
    )
    input_data = json.dumps(request.ratios.model_dump())

    # Résultat complet agrégé dans le champ JSONB
    result_dict: dict = {"graham": graham_output.model_dump()}
    if earnings_output:
        result_dict["earnings_quality"] = earnings_output.model_dump()
    result = json.dumps(result_dict)

    total_cost              = sum(u.cost_usd              for u in usages)
    total_tokens_input      = sum(u.tokens_input          for u in usages)
    total_tokens_output     = sum(u.tokens_output         for u in usages)
    total_tokens_cache_r    = sum(u.tokens_cache_read     for u in usages)
    total_tokens_cache_c    = sum(u.tokens_cache_creation for u in usages)

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
        request.ticker, "company_analysis",
        skills_used, input_data, result,
        total_cost,
        total_tokens_input, total_tokens_output,
        total_tokens_cache_r, total_tokens_cache_c,
    )
    return str(row["id"])
```

---

## S3-4 — Endpoint `GET /history`

### Design de l'endpoint

Pagination cursor-based par `created_at` (ISO 8601). Permet une pagination stable
même si de nouvelles analyses sont insérées entre les appels.

```
GET /history?ticker=BNS                          → 10 dernières analyses
GET /history?ticker=BNS&limit=5                  → 5 dernières
GET /history?ticker=BNS&before=2026-05-07T14:32:00Z  → page suivante
```

### Modèles de réponse dans `core.py`

```python
class HistoryEntry(BaseModel):
    analysis_id:    str
    ticker:         str
    workflow:       str
    skills_applied: list[str]
    cost_usd:       float
    defensive_score: int | None    # extrait du JSONB result
    earnings_verdict: str | None   # extrait du JSONB result, None si skill absent
    graham_verdict:  str | None
    created_at:     str


class HistoryResponse(BaseModel):
    ticker:      str
    entries:     list[HistoryEntry]
    next_before: str | None   # cursor ISO 8601 pour la page suivante, None si fin
```

### Méthode dans `Orchestrator`

```python
async def get_history(
    self,
    ticker: str,
    limit:  int = 10,
    before: datetime | None = None,
) -> HistoryResponse:
    """
    Retourne les analyses passées pour un ticker, triées par date décroissante.
    Utilise un cursor sur created_at pour la pagination.
    """
    rows = await self._db.fetch(
        """
        SELECT id, ticker, workflow_name, skills_used, cost_usd, result, created_at
        FROM analysis_history
        WHERE ticker = $1
          AND ($2::timestamptz IS NULL OR created_at < $2)
        ORDER BY created_at DESC
        LIMIT $3
        """,
        ticker,
        before,
        limit + 1,  # +1 pour détecter s'il y a une page suivante
    )

    has_more = len(rows) > limit
    rows = rows[:limit]

    entries = [
        HistoryEntry(
            analysis_id=str(row["id"]),
            ticker=row["ticker"],
            workflow=row["workflow_name"],
            skills_applied=json.loads(row["skills_used"]),
            cost_usd=float(row["cost_usd"]),
            defensive_score=_extract_int(row["result"], "graham", "defensive_score"),
            graham_verdict=_extract_str(row["result"], "graham", "verdict"),
            earnings_verdict=_extract_str(row["result"], "earnings_quality", "verdict"),
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]

    next_before = entries[-1].created_at if has_more and entries else None

    return HistoryResponse(ticker=ticker, entries=entries, next_before=next_before)
```

**Fonctions utilitaires privées dans `core.py` :**

```python
import json as _json

def _extract_int(result_json: str, *keys: str) -> int | None:
    """Navigue dans un JSONB imbriqué et retourne un int ou None."""
    try:
        obj = _json.loads(result_json)
        for key in keys:
            obj = obj[key]
        return int(obj)
    except (KeyError, TypeError, ValueError):
        return None


def _extract_str(result_json: str, *keys: str) -> str | None:
    """Navigue dans un JSONB imbriqué et retourne une str ou None."""
    try:
        obj = _json.loads(result_json)
        for key in keys:
            obj = obj[key]
        return str(obj)
    except (KeyError, TypeError, ValueError):
        return None
```

### Endpoint dans `app/api/main.py`

```python
from datetime import datetime

@app.get(
    "/history",
    response_model=HistoryResponse,
    summary="Historique des analyses par ticker",
)
async def history(
    request: Request,
    ticker:  str,
    limit:   int = 10,
    before:  str | None = None,
) -> HistoryResponse:
    """
    Retourne les analyses passées pour un ticker (max 50 par page).
    `before` : cursor ISO 8601 (valeur de `next_before` de la page précédente).
    """
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="limit doit être entre 1 et 50")

    before_dt: datetime | None = None
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(status_code=422, detail="before : format ISO 8601 requis")

    orchestrator: Orchestrator = request.app.state.orchestrator
    return await orchestrator.get_history(ticker=ticker, limit=limit, before=before_dt)
```

**Ajouter `HistoryResponse` dans l'import de `core.py` dans `main.py`.**

---

# MISE À JOUR DES TESTS

## Nouvelles fixtures dans `tests/conftest.py`

```python
from app.skills.tier2.earnings_quality.schemas import (
    EarningsQualityRatios, EarningsQualityInput, EarningsQualityOutput,
    GrahamContext, MScoreDetail, ZScoreDetail, FScoreDetail, FScoreCriterion,
    CScoreDetail, CScoreSignal, SloanDetail,
)

def _make_f_criteria(scores: list[bool]) -> list[FScoreCriterion]:
    """Génère exactement 9 FScoreCriterion."""
    noms = [
        "ROA > 0", "CFO > 0", "ROA en hausse", "CFO > bénéfice net",
        "Désendettement", "Current ratio en hausse", "Pas d'émission d'actions",
        "Marge brute en hausse", "Asset turnover en hausse",
    ]
    return [
        FScoreCriterion(nom=noms[i], passe=scores[i], detail="test")
        for i in range(9)
    ]

def _make_c_signaux(present: list[bool]) -> list[CScoreSignal]:
    """Génère exactement 6 CScoreSignal."""
    noms = [
        "Divergence NI-CFO", "DSO en hausse", "DIO en hausse",
        "Autres actifs courants", "Dépréciation réduite", "Émission d'actions",
    ]
    return [
        CScoreSignal(nom=noms[i], present=present[i], detail="test")
        for i in range(6)
    ]

@pytest.fixture
def ratios_earnings_msft():
    return EarningsQualityRatios(
        sales_t=211_915_000_000, sales_t1=198_270_000_000,
        cogs_t=74_114_000_000,  cogs_t1=65_863_000_000,
        net_income_t=72_361_000_000,
        cfo_t=87_582_000_000,
        ebit_t=88_523_000_000,
        receivables_t=48_688_000_000, receivables_t1=44_261_000_000,
        current_assets_t=184_257_000_000, current_liabilities_t=95_082_000_000,
        total_assets_t=512_163_000_000, total_assets_t1=484_275_000_000,
        retained_earnings_t=118_848_000_000,
        total_liabilities_t=205_753_000_000,
        market_cap_t=3_100_000_000_000,
        book_equity_t=206_223_000_000,
        ltd_t=49_800_000_000,
        sga_t=24_456_000_000,    sga_t1=22_759_000_000,
        depreciation_t=13_900_000_000, depreciation_t1=12_900_000_000,
    )

@pytest.fixture
def earnings_output_msft():
    return EarningsQualityOutput(
        ticker="MSFT",
        is_financial=False,
        m_score=MScoreDetail(
            dsri=None, gmi=None, aqi=None, sgi=1.07, depi=None,
            sgai=None, tata=-0.028, lvgi=None,
            m_score=None, interpretation="DONNÉES_MANQUANTES",
        ),
        z_score=ZScoreDetail(
            variante="Z_original",
            z_score=4.12,
            interpretation="zone_sure",
        ),
        f_score=FScoreDetail(
            criteria=_make_f_criteria([True]*8 + [False]),
            f_score=8,
            interpretation="forte_qualite",
        ),
        c_score=CScoreDetail(
            signaux=_make_c_signaux([False]*6),
            c_score=0,
            interpretation="propre",
        ),
        sloan=SloanDetail(accrual_ratio=-0.029, interpretation="qualite_elevee"),
        drapeaux_rouges=[],
        verdict="AUCUN_SIGNAL",
        verdict_detail="Aucun signal de manipulation ou de détresse.",
        recommandation_prochaine_etape=["dorsey_moat", "buffett_quality"],
    )
```

## Créer `tests/test_earnings_quality.py`

### `TestEarningsQualitySchemas`

```python
class TestEarningsQualitySchemas:
    def test_output_valide_se_construit(self, earnings_output_msft):
        assert earnings_output_msft.ticker == "MSFT"

    def test_f_score_8_criteres_leve_erreur(self, earnings_output_msft):
        """@model_validator rejette si f_score.criteria != 9."""
        data = earnings_output_msft.model_dump()
        data["f_score"]["criteria"] = data["f_score"]["criteria"][:8]
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_c_score_5_signaux_leve_erreur(self, earnings_output_msft):
        """@model_validator rejette si c_score.signaux != 6."""
        data = earnings_output_msft.model_dump()
        data["c_score"]["signaux"] = data["c_score"]["signaux"][:5]
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_verdict_invalide_leve_erreur(self, earnings_output_msft):
        data = earnings_output_msft.model_dump()
        data["verdict"] = "INCONNU"
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_graham_context_optionnel(self, ratios_earnings_msft):
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        assert inp.graham_context is None

    def test_graham_context_peuple(self, ratios_earnings_msft):
        ctx = GrahamContext(
            verdict="CANDIDAT_SOLIDE", defensive_score=6,
            marge_securite=0.18, drapeaux_rouges=[],
        )
        inp = EarningsQualityInput(
            ticker="MSFT", ratios=ratios_earnings_msft, graham_context=ctx
        )
        assert inp.graham_context.defensive_score == 6
```

### `TestEarningsQualitySkill`

```python
class TestEarningsQualitySkill:
    @pytest.fixture
    def skill(self):
        return EarningsQualitySkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill):
        assert skill.skill_id == "earnings_quality"

    def test_tier(self, skill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    @pytest.mark.asyncio
    async def test_execute_retourne_tuple(self, ratios_earnings_msft, earnings_output_msft):
        """execute() retourne (EarningsQualityOutput, UsageDetail)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=earnings_output_msft.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=1200, cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, usage = await skill.execute(inp)

        assert isinstance(output, EarningsQualityOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.tokens_cache_read == 1200

    @pytest.mark.asyncio
    async def test_user_message_contient_contexte_graham(
        self, ratios_earnings_msft, earnings_output_msft
    ):
        """Si graham_context fourni, le message utilisateur le mentionne."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=earnings_output_msft.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = GrahamContext(
            verdict="CANDIDAT_SOLIDE", defensive_score=6,
            marge_securite=0.18, drapeaux_rouges=["P/E élevé"],
        )
        inp = EarningsQualityInput(
            ticker="MSFT", ratios=ratios_earnings_msft, graham_context=ctx
        )
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "CANDIDAT_SOLIDE" in user_content
        assert "P/E élevé" in user_content
```

### `TestOrchestrateur` — ajouts

```python
class TestContextEnrichment:
    @pytest.mark.asyncio
    async def test_earnings_skill_recoit_graham_context(
        self, db_pool_mock, graham_output_msft, earnings_output_msft,
        ratios_msft, ratios_earnings_msft,
    ):
        """L'orchestrateur passe le verdict Graham à earnings_quality."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, mock_usage())

        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, mock_usage())

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(
            ticker="MSFT", ratios=ratios_msft, earnings_ratios=ratios_earnings_msft
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_earnings.execute.call_args
        earnings_input: EarningsQualityInput = call_args.args[0]
        assert earnings_input.graham_context is not None
        assert earnings_input.graham_context.verdict == graham_output_msft.verdict

    @pytest.mark.asyncio
    async def test_sans_earnings_ratios_workflow_reste_graham(
        self, db_pool_mock, graham_output_msft, ratios_msft
    ):
        """Sans earnings_ratios, earnings_quality n'est pas appelé."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, mock_usage())
        mock_earnings = AsyncMock()

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(ticker="MSFT", ratios=ratios_msft)  # earnings_ratios=None
        response = await orchestrator.run_company_analysis(req)

        mock_earnings.execute.assert_not_called()
        assert response.earnings_quality is None
        assert "earnings_quality" not in response.skills_applied
```

### `TestHistory` dans `tests/test_api.py`

```python
class TestHistory:
    @pytest.mark.asyncio
    async def test_history_ticker_existant_retourne_200(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        r = await async_client.get("/history?ticker=BNS")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_history_sans_ticker_retourne_422(self, async_client):
        r = await async_client.get("/history")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_limit_superieur_50_retourne_422(self, async_client):
        r = await async_client.get("/history?ticker=BNS&limit=100")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_before_invalide_retourne_422(self, async_client):
        r = await async_client.get("/history?ticker=BNS&before=pas-une-date")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_history_retourne_entries(self, async_client):
        entry = HistoryEntry(
            analysis_id="uuid-1", ticker="BNS", workflow="company_analysis",
            skills_applied=["graham_analysis"], cost_usd=0.0042,
            defensive_score=5, graham_verdict="CANDIDAT_SOLIDE",
            earnings_verdict=None, created_at="2026-05-07T14:00:00+00:00",
        )
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(
                ticker="BNS", entries=[entry], next_before=None
            )
        )
        r = await async_client.get("/history?ticker=BNS")
        data = r.json()
        assert data["ticker"] == "BNS"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["graham_verdict"] == "CANDIDAT_SOLIDE"

    @pytest.mark.asyncio
    async def test_history_next_before_present_si_page_suivante(self, async_client):
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(
                ticker="BNS", entries=[], next_before="2026-05-01T00:00:00+00:00"
            )
        )
        r = await async_client.get("/history?ticker=BNS")
        assert r.json()["next_before"] == "2026-05-01T00:00:00+00:00"
```

---

# CONTRAINTES NON-NÉGOCIABLES

- `AnalyzeRequest` sans `earnings_ratios` → comportement Phase 0 intact
- `EarningsQualitySkill(rag_service=None)` doit fonctionner
- La méthode `get_history` doit être testée sans connexion PostgreSQL réelle
- Ne pas modifier l'interface `/analyze` existante au-delà de l'ajout de `earnings_ratios`
- `skills_applied` dans `AnalyzeResponse` reflète les skills réellement exécutés
- `cost_usd` de `AnalyzeResponse` = somme de tous les skills exécutés
- Chaque fichier fourni est complet et autonome — pas de diff partiel

---

# CRITÈRE DE SUCCÈS UNIQUE

```bash
# 1. Tous les tests passent
pytest tests/ -v

# 2. Analyse Graham seule (backward compat)
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,
       "debt_equity":0.45,"eps_growth_10y":0.27,"price":80,"book_value":61.5}}'
# Attendu : skills_applied=["graham_analysis"], earnings_quality=null

# 3. Analyse complète Graham + Earnings Quality
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "MSFT",
    "ratios": {"pe":34.2,"pb":12.1,"current_ratio":1.34,"debt_equity":0.28,
               "eps_growth_10y":0.85,"price":420,"book_value":35},
    "earnings_ratios": {
      "sales_t":211915000000, "sales_t1":198270000000,
      "cogs_t":74114000000,   "cogs_t1":65863000000,
      "net_income_t":72361000000, "cfo_t":87582000000,
      "receivables_t":48688000000, "receivables_t1":44261000000,
      "current_assets_t":184257000000, "current_liabilities_t":95082000000,
      "total_assets_t":512163000000,   "total_assets_t1":484275000000
    }
  }'
# Attendu :
# - skills_applied = ["graham_analysis", "earnings_quality"]
# - earnings_quality.verdict ∈ {AUCUN_SIGNAL, ATTENTION, WATCHLIST, REJETER}
# - cost_usd = somme des deux appels Claude
# - earnings_quality.f_score.criteria compte 9 entrées
# - earnings_quality.c_score.signaux compte 6 entrées

# 4. Historique
curl "localhost:8000/history?ticker=MSFT&limit=5"
# Attendu : {"ticker":"MSFT","entries":[...],"next_before":null|"<iso_date>"}

# 5. Version mise à jour
curl localhost:8000/healthz
# Attendu : {"status":"ok","version":"0.2.0",...}
```

---

# FORMAT DE SORTIE

**Fichiers à CRÉER :**

| Fichier | Description |
|---------|-------------|
| `app/skills/tier2/earnings_quality/__init__.py` | Package marker (vide) |
| `app/skills/tier2/earnings_quality/schemas.py` | Tous les modèles Pydantic du skill |
| `app/skills/tier2/earnings_quality/skill.py` | `EarningsQualitySkill` |
| `app/skills/tier2/earnings_quality/prompts/system.md` | System prompt > 1 024 tokens |
| `tests/test_earnings_quality.py` | Tests schemas, skill, context enrichment |

**Fichiers à MODIFIER :**

| Fichier | Changement |
|---------|-----------|
| `app/orchestrator/core.py` | `AnalyzeRequest` + `AnalyzeResponse` + `Orchestrator` + `get_history()` + `_persist()` agrégé |
| `app/api/main.py` | Version 0.2.0, instanciation `EarningsQualitySkill`, endpoint `/history` |
| `tests/conftest.py` | Fixtures earnings quality + `_make_f_criteria` + `_make_c_signaux` |
| `tests/test_orchestrator.py` | Constructeur `Orchestrator` mis à jour, tests context enrichment |
| `tests/test_api.py` | Fixture `async_client` mise à jour, classe `TestHistory` |

---

# MODE DE RÉPONSE

1. Lire `.claude/skills/earnings-quality-fraud-detection/SKILL.md` et les 5 fichiers
   `references/*.md` AVANT de rédiger `prompts/system.md` — le prompt doit reproduire
   fidèlement les formules et seuils des références
2. Lire `architecture-copilote-financier.md` section 4.1 pour la composition du workflow
3. Traiter dans l'ordre S3-1 → S3-4
4. Pas de commentaires décoratifs, pas de TODO, pas de placeholders
5. Après les fichiers, donner uniquement :
   - Liste des fichiers créés/modifiés (path + 1 ligne de description)
   - Commande de validation (`pytest tests/ -v` + curl)
   - Points d'attention si applicable

---

*Sprint 3 — à exécuter après complétion et validation du Sprint 2.*
*Réviser ce prompt si l'architecture ou les schémas changent entre la rédaction et l'exécution.*
