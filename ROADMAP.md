# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-13 — Sprint 37 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 3.1.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 38 — Scoring composite unifié 🔜 |
| **Dernier sprint complété** | Sprint 37 — Validation anti-hallucination ✅ |

### Ce qui fonctionne aujourd'hui
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 15 skills + cache Redis (circuit court si analyse déjà en cache)
- `POST /screen` — screener multi-tickers (max 20, asyncio.gather + Semaphore)
- `DELETE /cache/{ticker}` — invalidation cache admin
- `GET /history?ticker=BNS` — historique paginé par cursor
- `GET /metrics?days=30` — coûts cumulés, taux de cache, top tickers
- `GET /telemetry/summary|costs|cache|latency` — métriques observabilité (Sprint 18)
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts

### Skills opérationnels
| Skill | Fichier | Statut |
|-------|---------|--------|
| `graham_analysis` | `app/skills/tier2/graham_analysis/` | ✅ Production |
| `earnings_quality` | `app/skills/tier2/earnings_quality/` | ✅ Production |
| `dorsey_moat` | `app/skills/tier2/dorsey_moat/` | ✅ Production |
| `buffett_quality` | `app/skills/tier2/buffett_quality/` | ✅ Production |
| `stock_valuation_triangulation` | `app/skills/tier2/stock_valuation/` | ✅ Production |
| `yahoo_finance_extractor` | `app/skills/tier1/yahoo_finance.py` | ✅ Production |
| `sedar_plus_extractor` | `app/skills/tier1/sedar_plus.py` | ✅ Production |
| `investment_thesis_builder` | `app/skills/tier2/thesis_builder/` | ✅ Production |
| `munger_mental_models` | `app/skills/tier2/munger_mental/` | ✅ Production |
| `canadian_tax_considerations` | `app/skills/tier2/canadian_tax/` | ✅ Production |
| `lynch_categories` | `app/skills/tier2/lynch_categories/` | ✅ Production |
| `fisher_scuttlebutt` | `app/skills/tier2/fisher_scuttlebutt/` | ✅ Production |
| `klarman_margin` | `app/skills/tier2/klarman_margin/` | ✅ Production |
| `greenblatt` | `app/skills/tier2/greenblatt/` | ✅ Production |
| `damodaran_narrative` | `app/skills/tier2/damodaran_narrative/` | ✅ Production |
| `marks_cycles` | `app/skills/tier2/marks_cycles/` | ✅ Production |
| `pabrai_dhandho` | `app/skills/tier2/pabrai_dhandho/` | ✅ Production |

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Phase 1 — Infrastructure RAG ✅ (Sprints 1–4)
- **Sprint 1** : `SkillBase` extrait dans `app/skills/base.py`, `UsageDetail` propagé, tokens persistés, `@model_validator` critères Graham, `/healthz` enrichi
- **Sprint 2** : `scripts/ingest_rag.py`, collection Qdrant `investment_knowledge`, `RagService`, `get_citations()`, logging structuré JSON
- **Sprint 3** : `earnings_quality` skill + context enrichment (`GrahamContext`), `GET /history`
- **Sprint 4** : `LangfuseTracer`, `GET /metrics`, timeout `CLAUDE_TIMEOUT_S`, retry backoff exponentiel

---

## Phase 2 — Skills restants (mois 1–2)

**Objectif :** Implémenter 3 skills Tier 2 + extracteurs automatiques de ratios.
**Workflow cible :**
```
graham_analysis → earnings_quality → dorsey_moat → buffett_quality → stock_valuation_triangulation
```

---

### Sprint 5 — dorsey_moat ✅

**Objectif :** Qualifier la durabilité de l'avantage concurrentiel selon Pat Dorsey.

#### Fichiers à créer
```
app/skills/tier2/dorsey_moat/__init__.py
app/skills/tier2/dorsey_moat/schemas.py
app/skills/tier2/dorsey_moat/skill.py
app/skills/tier2/dorsey_moat/prompts/system.md
tests/test_dorsey_moat.py
```

#### Spécifications
- Hériter de `SkillBase` (`app/skills/base.py`)
- Input : `DorseyMoatInput(ticker, ratios: DorseyRatios, earnings_context: EarningsContext | None)`
- `EarningsContext` = verdict + z_score + m_score depuis `EarningsQualityOutput` (context enrichment)
- Output : `DorseyMoatOutput` avec :
  - `moat_type` : `WIDE | NARROW | NONE`
  - `sources_identifiees` : list[MoatSource] (5 sources : intangibles, switching_costs, network_effects, cost_advantages, efficient_scale)
  - `roic_durability` : `FORTE | MODÉRÉE | FAIBLE` (basé sur ROIC fourni ou inféré)
  - `verdict_detail` : str
  - `recommandation_prochaine_etape` : list[str]
  - `citations` : list[Citation]
  - `cost_usd` intégré dans UsageDetail
- Source de vérité du prompt : `.claude/skills/dorsey-moat-analysis/SKILL.md` + `references/*.md`
- System prompt > 1 024 tokens (obligatoire pour prompt caching)

#### Intégration orchestrateur
- Ajouter `DorseyMoatSkill` dans `Orchestrator.__init__`
- Appeler après `earnings_quality` si `earnings_output` présent
- Ajouter `dorsey` dans `AnalyzeResponse`

#### Tests à écrire (`tests/test_dorsey_moat.py`)
```python
# Unitaires (pas d'appel réseau)
test_dorsey_ratios_validation_ok()          # DorseyRatios valide
test_dorsey_ratios_roic_negatif_accepte()   # ROIC négatif = pas d'erreur
test_dorsey_output_moat_type_enum()         # moat_type in {WIDE, NARROW, NONE}
test_dorsey_output_sources_count()          # len(sources_identifiees) == 5
test_dorsey_skill_build_user_message()      # message contient ticker + ratios
test_dorsey_execute_mock_claude()           # mock client.messages.create → GrahamAnalysisOutput valide
test_dorsey_get_citations_rag_absent()      # rag_service=None → citations == []

# Intégration orchestrateur
test_orchestrator_avec_dorsey()             # run_company_analysis avec earnings_ratios → dorsey présent dans response
test_orchestrator_sans_dorsey()             # sans earnings_ratios → dorsey absent
```

#### Critère de succès
```bash
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"BNS",
    "ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,"debt_equity":0.45,
              "eps_growth_10y":0.27,"price":80,"book_value":61.5,
              "eps_ttm":7.25,"revenue_bn":38,"dividend_years":190},
    "earnings_ratios":{...},
    "dorsey_ratios":{...}
  }'
# → JSON avec "dorsey": {"moat_type": "WIDE|NARROW|NONE", ...}
```

---

### Sprint 6 — buffett_quality ✅

**Objectif :** Appliquer les 4 filtres Buffett + calcul des owner earnings.

#### Fichiers à créer
```
app/skills/tier2/buffett_quality/__init__.py
app/skills/tier2/buffett_quality/schemas.py
app/skills/tier2/buffett_quality/skill.py
app/skills/tier2/buffett_quality/prompts/system.md
tests/test_buffett_quality.py
```

#### Spécifications
- Input : `BuffettQualityInput(ticker, ratios: BuffettRatios, dorsey_context: DorseyContext | None)`
- `DorseyContext` = moat_type + sources depuis `DorseyMoatOutput`
- Output : `BuffettQualityOutput` avec :
  - `filtres` : list[BuffettFiltre] — les 4 filtres ("compréhensible", "economics favorables", "management", "prix attractif")
  - `owner_earnings` : float | None — BPA + amortissement - capex maintenance
  - `quality_score` : int (0–4, nombre de filtres passés)
  - `verdict` : `COMPOUNDER | QUALITE_CORRECTE | REJETER`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Source du prompt : `.claude/skills/buffett-quality-investing/SKILL.md` + références

#### Tests à écrire (`tests/test_buffett_quality.py`)
```python
test_buffett_ratios_validation_ok()
test_buffett_output_filtres_count()          # len(filtres) == 4
test_buffett_output_quality_score_range()    # 0 <= quality_score <= 4
test_buffett_owner_earnings_calcul()         # owner_earnings = eps + d&a - maintenance_capex
test_buffett_execute_mock_claude()
test_buffett_get_citations_rag_absent()
test_orchestrator_avec_buffett()
```

#### Critère de succès
```bash
# → JSON avec "buffett": {"quality_score": 3, "owner_earnings": 8.50, ...}
```

---

### Sprint 7 — stock_valuation_triangulation ✅

**Objectif :** Valorisation par 3 méthodes indépendantes avec matrice de sensibilité.

#### Fichiers à créer
```
app/skills/tier2/stock_valuation/__init__.py
app/skills/tier2/stock_valuation/schemas.py
app/skills/tier2/stock_valuation/skill.py
app/skills/tier2/stock_valuation/prompts/system.md
tests/test_stock_valuation.py
```

#### Spécifications
- Input : `StockValuationInput(ticker, ratios, graham_context, earnings_context, dorsey_context, buffett_context)`
- Output : `StockValuationOutput` avec :
  - `valeur_dcf` : float | None
  - `valeur_comparables` : float | None
  - `valeur_sectorielle` : float | None
  - `fourchette_basse` / `fourchette_centrale` / `fourchette_haute` : float
  - `marge_securite_composite` : float (fraction)
  - `matrice_sensibilite` : list[list[float]] (WACC × taux_croissance)
  - `verdict` : `SOUS_EVALUE | JUSTE_VALEUR |_SUREVALUE`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Source du prompt : `.claude/skills/stock-valuation-triangulation/SKILL.md` + références

#### Tests à écrire
```python
test_valuation_fourchette_coherente()        # basse < centrale < haute
test_valuation_marge_securite_calcul()       # (centrale - price) / centrale
test_valuation_matrice_sensibilite_shape()   # 5×5 ou 4×4
test_valuation_execute_mock_claude()
test_orchestrator_workflow_complet_phase2()  # tous les skills enchaînés
```

#### Critère de succès
```bash
# → JSON avec "valuation": {"fourchette_centrale": 92.50, "marge_securite_composite": 0.14, ...}
```

---

### Sprint 8 — Extracteurs Tier 1 ✅

**Objectif :** Calculer les ratios automatiquement depuis les sources publiques (fin de la saisie manuelle).

#### Fichiers à créer
```
app/skills/tier1/__init__.py
app/skills/tier1/yahoo_finance.py        # YahooFinanceExtractor
app/skills/tier1/sedar_plus.py           # SedarPlusExtractor (SEDAR+ Canada)
app/api/endpoints/extract.py             # GET /extract?ticker=BNS
tests/test_yahoo_finance.py
tests/test_sedar_plus.py
```

#### Spécifications
- `YahooFinanceExtractor.extract(ticker: str) -> GrahamRatios` (async, via `httpx` + `yfinance`)
- `SedarPlusExtractor.extract(ticker: str) -> GrahamRatios | None` (TSX seulement, best-effort)
- Nouveau endpoint : `GET /extract?ticker=BNS` → `GrahamRatios` JSON
- Nouveau workflow automatique : `POST /analyze-auto?ticker=BNS` → extraction + analyse
- Timeout 10s sur les extracteurs, erreur explicite si source indisponible

#### Tests à écrire
```python
test_yahoo_finance_mock_response()        # httpx mock → GrahamRatios valide
test_yahoo_finance_ticker_inconnu()       # → HTTPException 404
test_yahoo_finance_valeur_none_toleree()  # current_ratio=None pour banques
test_sedar_plus_tsx_seulement()          # ticker NYSE → None, pas d'erreur
test_extract_endpoint_integration()       # GET /extract?ticker=BNS avec mock Yahoo
```

---

## Phase 3 — Pipeline de synthèse (mois 2–3)

**Objectif :** Workflow d'analyse complet Phase 3 + robustesse production.

**Workflow cible Phase 3 :**
```
[Tier 1] extraction automatique
  → graham → earnings_quality → dorsey_moat → buffett_quality
  → stock_valuation → munger_mental_models
  → investment_thesis_builder → canadian_tax_considerations
```

---

### Sprint 9 — investment_thesis_builder ✅

**Objectif :** Skill de synthèse finale — consolide tous les résultats en une thèse formelle.

#### Fichiers à créer
```
app/skills/tier2/thesis_builder/__init__.py
app/skills/tier2/thesis_builder/schemas.py
app/skills/tier2/thesis_builder/skill.py
app/skills/tier2/thesis_builder/prompts/system.md
tests/test_thesis_builder.py
```

#### Spécifications
- Input : `ThesisBuilderInput(ticker, all_contexts: AllSkillContexts)` — agrège tous les outputs précédents
- Output : `ThesisBuilderOutput` avec :
  - `scenario_bull` / `scenario_base` / `scenario_bear` : ThesisScenario (prob, rendement_cible, hypotheses)
  - `kill_criteria` : list[str] — conditions qui invalident la thèse
  - `devils_advocate` : str — argument le plus fort contre la thèse
  - `position_size_pct` : float (0–10) — allocation recommandée en % du portefeuille
  - `verdict_final` : `ACHETER | ACCUMULER | CONSERVER | VENDRE`
  - `synthese_narrative` : str — 3-5 paragraphes de thèse formelle
  - `citations`

#### Tests à écrire
```python
test_thesis_scenarios_probabilites_somme_100()    # bull + base + bear = 100 %
test_thesis_position_size_range()                 # 0 <= position_size_pct <= 10
test_thesis_kill_criteria_non_vide()
test_thesis_execute_mock_claude()
```

---

### Sprint 10 — Comportemental (munger + canadian_tax) ✅

**Objectif :** Passe comportementale + optimisation fiscale québécoise.

#### Fichiers à créer
```
app/skills/tier2/munger_mental/__init__.py
app/skills/tier2/munger_mental/schemas.py
app/skills/tier2/munger_mental/skill.py
app/skills/tier2/munger_mental/prompts/system.md
app/skills/tier2/canadian_tax/__init__.py
app/skills/tier2/canadian_tax/schemas.py
app/skills/tier2/canadian_tax/skill.py
app/skills/tier2/canadian_tax/prompts/system.md
tests/test_munger.py
tests/test_canadian_tax.py
```

#### Spécifications munger_mental
- Input : `MungerInput(ticker, thesis_context: ThesisContext)` — nourri par thesis_builder
- Output : `MungerOutput` avec :
  - `biais_detectes` : list[BiaisCognitif] (nom, description, impact_sur_these)
  - `inversion_analysis` : str — "qu'est-ce qui pourrait faire échouer cette thèse ?"
  - `lollapalooza_risk` : bool — convergence de plusieurs biais amplificateurs
  - `verdict_comportemental` : `CONFIANCE_JUSTIFIEE | BIAIS_DETECTE | ALERTE_ROUGE`

#### Spécifications canadian_tax
- Input : `CanadianTaxInput(ticker, position_size_pct, verdict_final, province: str = "QC")`
- Output : `CanadianTaxOutput` avec :
  - `compte_recommande` : `CELI | REER | CELIAPP | NON_ENREGISTRE`
  - `justification_fiscale` : str
  - `impact_retenue_us` : str | None (si dividende US)
  - `strategie_smith_manoeuvre` : bool — applicable si marge HELOC disponible

#### Tests à écrire
```python
test_munger_biais_non_vide()
test_munger_inversion_non_vide()
test_tax_compte_celi_priorite()           # action croissance → CELI recommandé
test_tax_dividende_us_retenue()           # ticker US avec dividende → retenue mentionnée
test_tax_province_validation()            # province invalide → ValidationError
```

---

### Sprint 11 — Robustesse production ✅

**Objectif :** Analyse async longue durée + Redis cache + sécurité minimale.

#### Fichiers à créer / modifier
```
app/api/endpoints/jobs.py                # POST /jobs + GET /jobs/{id}
app/workers/celery_app.py               # Worker Celery
app/workers/tasks.py                    # task: run_full_analysis
app/middleware/auth.py                   # API key middleware (Bearer token)
app/middleware/rate_limit.py             # Rate limiting via Redis
```

#### Spécifications
- `POST /analyze-async` → `{"job_id": "uuid"}` (réponse immédiate)
- `GET /jobs/{job_id}` → `{"status": "pending|running|done|failed", "result": ...}`
- Résultats stockés dans Redis 24h, puis dans PostgreSQL
- Authentification : Bearer token depuis `API_KEY` env var
- Rate limiting : 10 requêtes / minute par IP (via Redis)

#### Tests à écrire
```python
test_analyze_async_retourne_job_id()
test_job_status_pending_puis_done()       # mock Celery task
test_auth_missing_token_401()
test_auth_invalid_token_401()
test_rate_limit_depasse_429()
```

---

## Décisions d'architecture

| Décision | Choix retenu | Décidé lors de | Raison |
|----------|-------------|---------------|--------|
| **Modèle d'embedding** | `text-embedding-3-small` (OpenAI) | Sprint 12 | Coût négligeable (~$0.00002/1k tokens), pas de GPU local requis, simplicité d'infrastructure vs `nomic-embed-text` |
| **Chunking RAG** | Sections h2/h3 (actuel) | Sprint 2 | Découpage sémantique aligné avec la structure des SKILL.md |
| **Authentification** | Bearer token simple (`API_KEY` env) | Sprint 11 | Outil interne — OAuth2 inutilement complexe à ce stade |
| **Celery broker** | Redis | Sprint 11 | Redis déjà en stack, RabbitMQ = surcharge inutile pour volumes modérés |

---

---

### Sprint 12 — CLI + décision embedding ✅

**Objectif :** Interface CLI pour analyses manuelles + décisions d'architecture closes.

#### Fichiers créés
```
scripts/analyze_cli.py        # CLI principal — wrapping de POST /analyze
scripts/cli/__init__.py       # Package (vide)
scripts/cli/formatter.py      # Formatage AnalyzeResponse → Markdown
```

#### Spécifications `analyze_cli.py`
- Ticker en argument positionnel
- `--ratios-file FILE` : JSON complet (GrahamRatios plat ou corps `/analyze` complet)
- Ratios Graham inline : `--pe`, `--pb`, `--price`, `--eps`, `--book-value`, `--debt-equity`, `--eps-growth-10y`
  - `book_value` et `eps_ttm` dérivés automatiquement si absents (`price/pb`, `price/pe`)
- `--thesis` / `--munger` pour activer les skills optionnels
- `--api-url`, `--api-key` (ou var `API_KEY`), `--output-dir`
- `--stdout` pour afficher sans sauvegarder
- Rapport sauvegardé dans `analyses/{TICKER}-{YYYY-MM}.md`
- Messages d'erreur explicites : 401 / 422 / 429 / timeout / connexion refusée

#### Usage rapide
```bash
# Ratios inline (Graham seulement)
python scripts/analyze_cli.py BNS \
    --pe 11.0 --pb 1.3 --price 80.0 \
    --debt-equity 0.45 --eps-growth-10y 0.27

# Fichier JSON complet + thèse
python scripts/analyze_cli.py BNS \
    --ratios-file data/bns_full.json --thesis --munger

# Stdout (redirection possible)
python scripts/analyze_cli.py BNS --ratios-file data/bns.json --stdout > rapport.md
```

#### Décision embedding (Sprint 12)
- **Retenu : `text-embedding-3-small`** (OpenAI)
- **Chunking : sections h2/h3** (inchangé depuis Sprint 2)
- Voir section "Décisions d'architecture" ci-dessus pour le détail

#### Critère de succès
```bash
python scripts/analyze_cli.py BNS \
    --pe 11 --pb 1.3 --price 80 --debt-equity 0.45 --eps-growth-10y 0.27
# → analyses/BNS-2026-05.md généré avec sections Graham + résumé exécutif
```

---

### Sprint 13 — Tests d'intégration end-to-end ✅

**Objectif :** Suite pytest complète validant workflow sync + async sous Docker Compose, avant d'ajouter de nouveaux skills.

#### Fichiers à créer
```
tests/conftest.py                    # Fixtures : TestClient, mock Claude, cleanup DB
tests/test_schemas.py                # Validation Pydantic des 10 schemas (critères, ordres, plages)
tests/test_integration_sync.py       # POST /analyze, /history, /metrics, /healthz, /extract
tests/test_integration_async.py      # POST /analyze-async → poll /jobs/{id} → done
tests/test_middleware.py             # Auth 401, rate limit 429, EXEMPT_PATHS
requirements-dev.txt                 # pytest, pytest-asyncio, httpx[test], respx
```

#### Spécifications
- `conftest.py` :
  - `mock_claude` : fixture qui patch `anthropic.AsyncAnthropic.messages.create` → JSON minimal valide par skill
  - `app_client` : `httpx.AsyncClient(app=app, base_url="http://test")` (pas de docker nécessaire)
  - `db_cleanup` : `DELETE FROM analysis_history WHERE ticker = 'TEST'` après chaque test d'intégration
- `test_schemas.py` (unitaires, 0 appel réseau) :
  - Graham : exactement 8 `criteria_defensif`, 5 `criteria_entreprenant`, `defensive_score` in [0,8]
  - Earnings : exactement 9 `f_score.criteria`, 6 `c_score.signaux`
  - Valuation : `fourchette_basse <= fourchette_centrale <= fourchette_haute`
  - Thesis : `bull.probabilite + base.probabilite + bear.probabilite == 1.0` (± 0.01)
  - Munger : `impact_sur_these` in {"MINEUR", "MODERE", "MAJEUR"}
  - Tax : `compte_recommande` in {"CELI", "REER", "CELIAPP", "NON_ENREGISTRE"}
- `test_integration_sync.py` :
  - `test_healthz_200` : GET /healthz → {"status": "ok"}
  - `test_analyze_graham_seulement` : POST /analyze minimal → 200 + `graham.defensive_score` in [0,8]
  - `test_analyze_ratios_invalides_422` : POST /analyze sans `pe` → 422
  - `test_analyze_coute_non_nul` : `cost_usd > 0`
  - `test_history_pagination` : 2 analyses puis GET /history → `entries` non vide
  - `test_metrics_period_valide` : GET /metrics?days=30 → `total_analyses >= 0`
  - `test_extract_endpoint` : GET /extract?ticker=TEST → 200 ou 404 (mock Yahoo)
- `test_integration_async.py` :
  - `test_analyze_async_retourne_job_id` : POST /analyze-async → `{"job_id": "..."}` (UUID)
  - `test_job_status_progression` : mock Celery task → GET /jobs/{id} → status "done"
  - `test_job_inconnu_404` : GET /jobs/uuid-inconnu → 404
- `test_middleware.py` :
  - `test_auth_absent_401` (si `API_KEY` env non vide)
  - `test_auth_invalide_401`
  - `test_auth_valide_passe`
  - `test_rate_limit_429` : 11 requêtes rapides → 429 sur la 11e
  - `test_healthz_exempt_auth` : GET /healthz sans token → 200 (EXEMPT_PATH)

#### Critère de succès
```bash
pytest tests/ -v --tb=short
# → 0 failures, 0 errors sur les tests unitaires
# → Tests intégration passent avec mock Claude (pas de vraie clé API requise)
```

---

### Sprint 14 — Skills Lynch + Fisher + Klarman ✅

**Objectif :** 3 skills manquants pour les workflows croissance, analyse qualitative et situations spéciales.

#### Fichiers à créer
```
app/skills/tier2/lynch_categories/__init__.py
app/skills/tier2/lynch_categories/schemas.py
app/skills/tier2/lynch_categories/skill.py
app/skills/tier2/lynch_categories/prompts/system.md
app/skills/tier2/fisher_scuttlebutt/__init__.py
app/skills/tier2/fisher_scuttlebutt/schemas.py
app/skills/tier2/fisher_scuttlebutt/skill.py
app/skills/tier2/fisher_scuttlebutt/prompts/system.md
app/skills/tier2/klarman_margin/__init__.py
app/skills/tier2/klarman_margin/schemas.py
app/skills/tier2/klarman_margin/skill.py
app/skills/tier2/klarman_margin/prompts/system.md
tests/test_lynch_categories.py
tests/test_fisher_scuttlebutt.py
tests/test_klarman_margin.py
```

#### Spécifications `lynch_categories`
- Source de vérité : `.claude/skills/lynch-categories-and-tenbaggers/SKILL.md` + `references/`
- Input : `LynchRatios(pe, eps_growth_5y, revenue_growth_5y, net_margin, debt_equity, fcf_yield, dividend_yield | None, capex_intensity | None)`
- Output : `LynchOutput`
  - `categorie` : `"SLOW_GROWER" | "STALWART" | "FAST_GROWER" | "CYCLICAL" | "TURNAROUND" | "ASSET_PLAY"`
  - `peg_ratio` : `float | None` — pe / (eps_growth_5y × 100), null si eps_growth_5y ≤ 0
  - `tenbagger_potential` : `bool` — FAST_GROWER avec PEG < 1.0
  - `score_croissance` : `int` (0-5)
  - `verdict` : `"EXCELLENT" | "BON" | "MOYEN" | "EVITER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`

#### Spécifications `fisher_scuttlebutt`
- Source de vérité : `.claude/skills/fisher-scuttlebutt/SKILL.md` + `references/`
- Input : `FisherInput(ticker, fisher_answers: list[FisherAnswer], contexte_qualitatif: str | None)`
  - `FisherAnswer(point: int, score: int, commentaire: str)` — 15 points cotés 0/1/2
- Output : `FisherOutput`
  - `fisher_score` : `int` (0-30)
  - `points_evalues` : `list[FisherPoint]` — exactement 15 éléments
  - `management_quality` : `"EXCEPTIONNEL" | "BON" | "ADEQUAT" | "MEDIOCRE"`
  - `verdict` : `"ACHAT_FORT" | "ACHAT" | "CONSERVER" | "EVITER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Validation : `len(points_evalues) == 15`, `0 <= fisher_score <= 30`

#### Spécifications `klarman_margin_of_safety`
- Source de vérité : `.claude/skills/klarman-margin-of-safety/SKILL.md` + `references/`
- Input : `KlarmanInput(ticker, situation_type: str, klarman_ratios: KlarmanRatios)`
  - `KlarmanRatios(nav_per_share: float | None, price: float, liquidation_value: float | None, debt_equity: float | None, revenue_bn: float | None, catalyst: str | None)`
- Output : `KlarmanOutput`
  - `situation_type_qualifie` : `"NET_NET" | "ACTIFS_CACHES" | "DISTRESSED" | "SPECIAL_SITUATION" | "VALEUR_CLASSIQUE"`
  - `marge_securite_score` : `int` (0-10)
  - `preservation_capital_score` : `int` (0-10)
  - `discount_to_intrinsic` : `float | None`
  - `verdict` : `"OPPORTUNITE_FORTE" | "OPPORTUNITE_MODEREE" | "ATTENDRE" | "PASSER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`

#### Intégration orchestrateur
- Ajouter `lynch_ratios: LynchRatios | None`, `fisher_input: FisherInput | None`, `klarman_input: KlarmanInput | None` dans `AnalyzeRequest`
- Étapes 9, 10, 11 dans `run_company_analysis` — pattern identique aux étapes 1-8
- Champs correspondants dans `AnalyzeResponse`

#### Critère de succès
```bash
curl -X POST localhost:8000/analyze \
  -d '{"ticker":"BNS","ratios":{...},"lynch_ratios":{"pe":11,"eps_growth_5y":0.05,...}}'
# → JSON avec "lynch": {"categorie": "STALWART", "peg_ratio": 2.2, ...}
```

---

### Sprint 15 — Skills Greenblatt + Damodaran + Marks + Pabrai ✅

**Objectif :** Compléter les 15 skills de l'architecture — 4 derniers skills (screening systématique, valorisation growth, cycles marché, position sizing).

#### Fichiers à créer
```
app/skills/tier2/greenblatt/__init__.py
app/skills/tier2/greenblatt/schemas.py
app/skills/tier2/greenblatt/skill.py
app/skills/tier2/greenblatt/prompts/system.md
app/skills/tier2/damodaran_narrative/__init__.py
app/skills/tier2/damodaran_narrative/schemas.py
app/skills/tier2/damodaran_narrative/skill.py
app/skills/tier2/damodaran_narrative/prompts/system.md
app/skills/tier2/marks_cycles/__init__.py
app/skills/tier2/marks_cycles/schemas.py
app/skills/tier2/marks_cycles/skill.py
app/skills/tier2/marks_cycles/prompts/system.md
app/skills/tier2/pabrai_dhandho/__init__.py
app/skills/tier2/pabrai_dhandho/schemas.py
app/skills/tier2/pabrai_dhandho/skill.py
app/skills/tier2/pabrai_dhandho/prompts/system.md
tests/test_greenblatt.py
tests/test_damodaran.py
tests/test_marks_cycles.py
tests/test_pabrai_dhandho.py
```

#### Spécifications `greenblatt_magic_formula`
- Source : `.claude/skills/greenblatt-magic-formula/SKILL.md`
- Input : `GreenblattRatios(ebit: float, enterprise_value: float, net_working_capital: float, net_fixed_assets: float, sector: str | None)`
- Output : `GreenblattOutput`
  - `roc` : `float` — EBIT / (NWC + NFA)
  - `earnings_yield` : `float` — EBIT / EV
  - `verdict` : `"TOP_DECILE" | "BON" | "MOYEN" | "EVITER"`
  - `situations_speciales` : `list[str]` — spinoffs, arbitrage, restructuring identifiés
  - `verdict_detail`, `citations`

#### Spécifications `damodaran_narrative`
- Source : `.claude/skills/damodaran-narrative-and-numbers/SKILL.md`
- Input : `DamodararInput(ticker, narrative_text: str, damodaran_ratios: DamodararRatios)`
  - `DamodararRatios(revenue_bn, revenue_growth_5y, net_margin, roic, tam_bn: float | None, market_share_pct: float | None, sector: str | None)`
- Output : `DamodararOutput`
  - `test_coherence` : `"POSSIBLE" | "PLAUSIBLE" | "PROBABLE" | "INCOHERENT"`
  - `erp_implied` : `float | None`
  - `narrative_strength` : `int` (0-10)
  - `divergences_detectees` : `list[str]`
  - `verdict` : `"NARRATIVE_FORTE" | "NARRATIVE_ACCEPTABLE" | "NARRATIVE_FAIBLE" | "NARRATIVE_INCOHERENTE"`
  - `verdict_detail`, `citations`

#### Spécifications `marks_cycles_risk`
- Source : `.claude/skills/marks-cycles-and-risk/SKILL.md`
- Input : `MarksInput(market_context: str, marks_ratios: MarksRatios)`
  - `MarksRatios(pe_market: float | None, vix: float | None, credit_spreads_bps: float | None, insider_net_buying: float | None, bullish_sentiment_pct: float | None)`
- Output : `MarksOutput`
  - `position_cycle` : `"PESSIMISME_EXCESSIF" | "PESSIMISME" | "NEUTRE" | "OPTIMISME" | "EUPHORIE"`
  - `pendule_score` : `int` (-5 à +5, négatif = opportunité contrariante)
  - `second_level_insight` : `str`
  - `recommandation_timing` : `"ACHETER_AGRESSIF" | "ACHETER_PRUDEMMENT" | "ATTENDRE" | "REDUIRE" | "VENDRE"`
  - `verdict_detail`, `citations`
- Validation : `pendule_score` in [-5, 5]

#### Spécifications `pabrai_dhandho`
- Source : `.claude/skills/pabrai-dhandho-and-cloning/SKILL.md`
- Input : `PabraiInput(ticker, pabrai_ratios: PabraiRatios, cloning_source: str | None)`
  - `PabraiRatios(price, intrinsic_value_low, intrinsic_value_high, downside_pct, upside_pct, debt_equity, fcf_yield, business_quality_score: int)`
- Output : `PabraiOutput`
  - `principes_dhandho` : `list[DhandhoPrincipe]` — exactement 9 (nom, satisfait: bool, commentaire)
  - `heads_i_win_score` : `int` (0-9)
  - `asymetrie` : `float` — upside / abs(downside)
  - `kelly_fractionnel` : `float | None` — Kelly / 4
  - `verdict` : `"DHANDHO_FORT" | "DHANDHO_MOYEN" | "PAS_DHANDHO"`
  - `verdict_detail`, `citations`
- Validation : `len(principes_dhandho) == 9`, `asymetrie >= 0`

#### Critère de succès
Tous les 15 skills de l'architecture opérationnels. POST /analyze avec le payload complet retourne les 15 sections.

---

### Sprint 17 — Screener multi-tickers + Cache Redis ✅

**Objectif :** `POST /screen` (analyse parallèle avec asyncio.gather + Semaphore) + cache Redis sur `POST /analyze`.

#### Fichiers créés
```
app/services/__init__.py
app/services/analysis_cache.py    # AnalysisCacheService — clé analysis:{ticker}:{workflow}:{hash}
app/services/screener.py          # ScreenerService — asyncio.gather + Semaphore + timeout
app/api/endpoints/screen.py       # POST /screen + DELETE /cache/{ticker}
tests/test_analysis_cache.py      # 8 tests (get/set/invalidate/TTL/orchestrateur)
tests/test_screener.py            # 12 tests (validation, tri, déduplication, endpoint)
```

#### Fichiers modifiés
```
app/orchestrator/core.py          # AnalyzeRequest.workflow + run_company_analysis(cache=) + cache store
app/api/main.py                   # screen router + AnalysisCacheService + ScreenerService + version 2.0.0
tests/conftest.py                 # mocks analysis_cache + screener dans fixture client
tests/test_api.py                 # version 1.0.0 → 2.0.0
tests/test_orchestrator.py        # workflow "company_analysis" → "value_graham" (défaut Sprint 17)
```

#### Note architecture
Sprint 16 (WorkflowRouter + WebSocket) a été sauté — les fichiers `app/orchestrator/router.py`
et `app/api/endpoints/ws_metrics.py` ne sont pas encore implémentés. Le champ `workflow`
dans `AnalyzeRequest` prépare l'intégration future du WorkflowRouter sans le bloquer.

#### Critère de succès
```bash
pytest tests/test_screener.py tests/test_analysis_cache.py -v  # 20 tests verts
pytest tests/ -v -q                                             # 733 passed, 1 xfail
```

---

### Sprint 18 — Observabilité avancée ✅

**Objectif :** Dashboard Langfuse structuré : traces par skill avec coût et latence, alertes coût > seuil, endpoint `/telemetry` pour visualiser les métriques clés.

#### Fichiers à créer
```
app/services/observability.py        # ObservabilityService — traces Langfuse + compteurs Redis
app/api/endpoints/telemetry.py       # GET /telemetry/summary, /costs, /cache, /latency
tests/test_observability.py          # ~10 tests ObservabilityService
tests/test_telemetry.py              # ~8 tests endpoints /telemetry
```

#### Fichiers à modifier
```
app/orchestrator/core.py             # record_skill_execution après chaque skill (asyncio.create_task)
app/api/main.py                      # Inclure telemetry router + injecter ObservabilityService
```

#### Spécifications — `ObservabilityService`

```python
@dataclass
class SkillTrace:
    skill_id: str
    ticker: str
    cost_usd: float
    latency_ms: int
    cache_hit: bool
    tokens_input: int
    tokens_output: int
    created_at: datetime

class ObservabilityService:
    def __init__(self, langfuse_client: Langfuse | None, redis_client: Redis) -> None: ...

    async def record_skill_execution(self, trace: SkillTrace) -> None:
        # 1. Si Langfuse dispo → span avec metadata structurée (cost_usd, latency_ms, cache_hit)
        # 2. Redis INCRBYFLOAT obs:cost:{YYYY-MM-DD} cost_usd
        # 3. Redis INCR obs:cache:hits si cache_hit, sinon obs:cache:misses
        # 4. Redis ZADD skill_traces:{skill_id} score=timestamp value=latency_ms

    async def get_cost_summary(self, days: int = 30) -> CostSummary:
        """Coût total + breakdown par jour depuis Redis obs:cost:{date}."""

    async def get_cache_stats(self) -> CacheStats:
        """hits / (hits + misses) depuis Redis."""

    async def get_latency_p95(self, skill_id: str | None = None) -> float | None:
        """P95 latence via ZRANGE sur sorted set (skill_id précis ou tous les skills)."""

    async def check_cost_alert(self, daily_threshold_usd: float = 1.0) -> bool:
        """Coût du jour > seuil ? (lecture obs:cost:{today})"""
```

#### Spécifications — endpoints `/telemetry`

```python
GET /telemetry/summary?days=30
# → TelemetrySummary(cost_total_usd, cache_hit_ratio, analyses_count, latency_p95_ms, top_tickers)

GET /telemetry/costs?days=30
# → list[DailyCost(date, cost_usd)]

GET /telemetry/cache
# → CacheStats(hits, misses, hit_ratio, keys_count)

GET /telemetry/latency?skill_id=graham_analysis
# → LatencyStats(skill_id, p50_ms, p95_ms, p99_ms, sample_count)
```

- Endpoints **exemptés d'auth** (lecture seule, monitoring interne)
- `ObservabilityService` injecté via `app.state.observability` dans le lifespan
- Si Langfuse non configuré (`LANGFUSE_SECRET_KEY` absent), le service tourne en mode Redis-only sans erreur

#### Intégration orchestrateur

```python
# Dans run_company_analysis, après chaque skill exécuté avec succès :
asyncio.create_task(
    observability.record_skill_execution(SkillTrace(
        skill_id="graham_analysis",
        ticker=request.ticker,
        cost_usd=output.cost_usd,
        latency_ms=elapsed_ms,
        cache_hit=was_cached,
        tokens_input=output.usage.input_tokens,
        tokens_output=output.usage.output_tokens,
        created_at=datetime.utcnow(),
    ))
)
# asyncio.create_task → non-bloquant, ne ralentit pas l'analyse
```

#### Tests à écrire

**`tests/test_observability.py`**
```python
test_record_sans_langfuse_ok()               # langfuse=None → pas d'erreur
test_record_avec_langfuse_mock()             # span créé avec bons metadata
test_get_cost_summary_vide()                 # 0 enregistrements → cost_total=0.0
test_get_cost_summary_cumul_correct()        # 3 appels → somme exacte
test_get_cache_stats_hit_ratio()             # 3 hits + 1 miss → 0.75
test_get_latency_p95_calcul()               # 100 valeurs → p95 dans range attendu
test_check_cost_alert_depasse()              # coût > seuil → True
test_check_cost_alert_ok()                   # coût < seuil → False
test_record_cache_hit_incremente_hits()      # cache_hit=True → obs:cache:hits +1
test_record_cache_miss_incremente_misses()   # cache_hit=False → obs:cache:misses +1
```

**`tests/test_telemetry.py`**
```python
test_telemetry_summary_200()                 # GET /telemetry/summary → 200 + TelemetrySummary
test_telemetry_costs_200()                   # GET /telemetry/costs?days=7 → 200 + list[DailyCost]
test_telemetry_cache_200()                   # GET /telemetry/cache → 200 + CacheStats
test_telemetry_latency_200()                 # GET /telemetry/latency → 200 + LatencyStats
test_telemetry_latency_skill_filtre()        # ?skill_id=graham → résultat filtré
test_telemetry_sans_auth_200()              # endpoints /telemetry/* exemptés d'auth
test_telemetry_hit_ratio_entre_0_et_1()     # 0 <= hit_ratio <= 1.0
test_telemetry_cost_total_positif()          # cost_total_usd >= 0
```

#### Critère de succès
```bash
pytest tests/test_observability.py tests/test_telemetry.py -v  # tous verts
pytest tests/ -v -q                                             # 0 failures (751+ passed)

curl localhost:8000/telemetry/summary?days=7
# → {"cost_total_usd": 0.42, "cache_hit_ratio": 0.73, "analyses_count": 18, "latency_p95_ms": 3200}

curl localhost:8000/telemetry/cache
# → {"hits": 54, "misses": 20, "hit_ratio": 0.73, "keys_count": 12}
```

---

---

### Sprint 19 — Tests de charge ✅

**Objectif :** Valider la capacité de l'API sous charge réaliste — mesurer le débit de `/screen` et `/analyze` à 10/50 req/min, identifier les goulots d'étranglement avant tout déploiement.

#### Fichiers à créer
```
tests/load/locustfile.py             # Scénarios Locust : /analyze, /screen, /telemetry
tests/load/k6_basic.js               # Scénario k6 pour /analyze seul (alternative)
tests/load/README.md                 # Instructions d'exécution des tests de charge
```

#### Spécifications
- **Outil principal :** `locust` (Python, s'intègre bien avec FastAPI)
- **Scénarios :**
  - `AnalyzeUser` : POST /analyze avec ratios Graham (poids 70 %)
  - `ScreenUser` : POST /screen avec 5 tickers (poids 20 %)
  - `TelemetryUser` : GET /telemetry/summary (poids 10 %)
- **Niveaux testés :** 10, 25, 50 utilisateurs concurrents
- **Durée :** 2 minutes par palier
- **Métriques collectées :** p50, p95, p99 latence, débit (req/s), taux d'erreur
- **Critère de succès :** p95 < 5s à 10 utilisateurs avec cache Redis activé

#### Variables d'environnement pour les tests de charge
```bash
LOCUST_HOST=http://localhost:8000
LOCUST_USERS=50
LOCUST_SPAWN_RATE=5
LOCUST_RUN_TIME=2m
```

#### Tests à écrire
```python
# locustfile.py
class AnalyzeUser(HttpUser): ...      # POST /analyze avec payload Graham complet
class ScreenUser(HttpUser): ...       # POST /screen avec 5 tickers + ratios_map
class TelemetryUser(HttpUser): ...    # GET /telemetry/summary polling
```

#### Critère de succès
```bash
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 10 -r 2 --run-time 2m
# → p95 < 5000ms, taux erreur < 1%

locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 50 -r 5 --run-time 2m
# → p95 < 10000ms, taux erreur < 5%
```

---

### Sprint 20 — Rapport PDF automatique ✅

**Objectif :** Générer un PDF structuré depuis `AnalyzeResponse` via `reportlab`.
Exposer `POST /report` qui déclenche une analyse et retourne un PDF téléchargeable.

#### Fichiers à créer
```
app/services/report.py               # ReportService — génère PDF depuis AnalyzeResponse
app/api/endpoints/report.py          # POST /report, GET /report/{analysis_id}
tests/test_report.py                 # 10 tests (service + endpoint)
```

#### Fichiers à modifier
```
app/api/main.py                      # Inclure report_router
requirements.txt                     # Ajouter reportlab>=4.0.0
README.md                            # Ajouter section "Rapports PDF"
```

#### Critère de succès
```bash
pytest tests/test_report.py -v  # 10 tests verts

curl -X POST localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,
       "debt_equity":0.45,"eps_growth_10y":0.27,"price":80.0,"book_value":61.5}}' \
  --output BNS-rapport.pdf
# → BNS-rapport.pdf créé, lisible dans un lecteur PDF
```

---

### Sprint 21 — Workflows alternatifs + WebSocket dashboard ✅

**Objectif :** Implémenter le `WorkflowRouter` avec 5 workflows spécialisés + un dashboard WebSocket temps réel.
Ce sprint intègre le contenu prévu initialement en Sprint 16 (précédemment sauté).

#### Fichiers à créer
```
app/orchestrator/router.py           # WorkflowRouter — dispatch vers la bonne séquence de skills
app/api/endpoints/ws_metrics.py      # WebSocket /ws/metrics (Redis pub/sub)
tests/test_workflow_router.py        # Tests WorkflowRouter + workflows alternatifs
```

#### Fichiers à modifier
```
app/orchestrator/core.py             # Intégrer WorkflowRouter dans run_company_analysis
app/api/main.py                      # Inclure ws_metrics router, version 2.1.0
```

#### 5 workflows (section 3.3 de l'architecture)

| Workflow | Séquence de skills |
|----------|--------------------|
| `value_graham` | graham → earnings → valuation → thesis → tax *(existant, défaut)* |
| `compounder_buffett` | graham → earnings → dorsey → buffett → fisher → valuation → thesis → munger → tax |
| `fast_grower_lynch` | lynch → damodaran → valuation → thesis → munger → tax |
| `special_situation` | graham → klarman → greenblatt → thesis → tax |
| `distressed_pabrai` | pabrai → klarman → earnings → thesis → tax |

#### Spécifications `WorkflowRouter`
- `AnalyzeRequest` : le champ `workflow: str = "value_graham"` est **déjà présent** — ne pas le re-créer
- `WorkflowRouter.route(workflow: str) -> list[SkillStep]` : retourne la séquence ordonnée
- `SkillStep(skill_id: str, optional: bool = False)` — les skills sans ratios fournis sont sautés (pas d'erreur)
- `run_company_analysis` utilise `WorkflowRouter.route(workflow)` pour déterminer les étapes à exécuter

#### WebSocket `/ws/metrics`
- Connexion : `GET /ws/metrics` → WebSocket upgrade
- Push JSON toutes les 5 secondes :
  ```json
  {
    "jobs_en_cours": 2,
    "jobs_echoues_1h": 0,
    "cout_total_1h_usd": 0.042,
    "cache_hit_ratio": 0.73,
    "analyses_24h": 15,
    "timestamp": "2026-05-09T14:32:00Z"
  }
  ```
- Source : Redis `KEYS job:*:status` + compteurs observabilité existants (`obs:cost:*`, `obs:cache:*`)
- Fermeture propre si client déconnecté (`WebSocketDisconnect`)
- Pas d'auth requise (lecture seule, monitoring interne)

#### Version
- Passer `_VERSION = "2.1.0"` dans `app/api/main.py`

#### Tests à écrire (`tests/test_workflow_router.py`)
```python
test_workflow_value_graham_steps()         # défaut → 5 steps attendus
test_workflow_compounder_buffett_steps()   # 9 steps
test_workflow_fast_grower_lynch_steps()    # 6 steps
test_workflow_special_situation_steps()    # 4 steps
test_workflow_distressed_pabrai_steps()    # 5 steps
test_workflow_inconnu_raise_value_error()  # "foo" → ValueError
test_orchestrator_workflow_non_defaut()    # fast_grower_lynch → lynch présent, graham absent
test_ws_metrics_connect_disconnect()       # mock WebSocket → connect + data + disconnect propre
test_ws_metrics_payload_structure()        # JSON valide avec tous les champs attendus
```

#### Fichiers créés
```
app/orchestrator/router.py           # WorkflowRouter + WORKFLOWS dict (5 workflows)
app/api/endpoints/ws_metrics.py      # WebSocket /ws/metrics — push JSON toutes les 5s
tests/test_workflow_router.py        # 9 tests (7 router + 2 WebSocket)
```

#### Fichiers modifiés
```
app/orchestrator/core.py             # WorkflowRouter intégré, graham/ratios optionnels, _persist corrigé
app/api/main.py                      # ws_metrics_router inclus, version 2.1.0
app/middleware/auth.py               # /ws ajouté à EXEMPT_PREFIXES
```

#### Critère de succès
```bash
# Workflow Lynch
curl -X POST localhost:8000/analyze \
  -d '{"ticker":"NVDA","workflow":"fast_grower_lynch","lynch_ratios":{...},...}'
# → JSON avec sections lynch + damodaran + valuation + thesis (pas de graham)

# WebSocket
wscat -c ws://localhost:8000/ws/metrics
# → Push JSON toutes les 5s avec jobs_en_cours, cout_total_1h_usd, cache_hit_ratio

pytest tests/test_workflow_router.py -v   # 9 tests verts
pytest tests/ -v -q                        # 776+ passed, 1 xfail
```

---

### Sprint 22 — Interface web professionnelle ✅

**Objectif :** Dashboard React professionnel dans `frontend/` pour accéder au copilote sans CLI.

#### Fichiers créés
```
frontend/package.json                        # React 18, Vite 5, TS strict, shadcn/ui, Tanstack Query v5, React Router v6
frontend/vite.config.ts                      # Proxy API → localhost:8000, WebSocket ws:// proxy, Vitest jsdom
frontend/tsconfig.json                       # strict: true, jsx: react-jsx, types: [vitest/globals, jest-dom]
frontend/index.html                          # Entrée Vite
frontend/src/vite-env.d.ts                  # /// <reference types="vite/client" />
frontend/src/setupTests.ts                   # Polyfills Radix UI (hasPointerCapture, scrollIntoView)
frontend/src/types/index.ts                  # GrahamRatios, AnalyzeRequest/Response, ScreenEntry, MetricsPayload, WORKFLOWS
frontend/src/api/client.ts                   # fetch wrapper + ApiError (status, message, name)
frontend/src/api/analyze.ts                  # postAnalyze, postScreen, getHistory, postReport, getHealthz
frontend/src/api/ws.ts                       # useMetrics() — WebSocket /ws/metrics + auto-reconnect 3s
frontend/src/App.tsx                         # BrowserRouter + NavLink (/, /screener, /historique, /dashboard)
frontend/src/components/ui/button.tsx        # cva variants: default, destructive, outline, secondary, ghost, link
frontend/src/components/ui/badge.tsx         # cva variants: default, secondary, destructive, success, warning, danger
frontend/src/components/ui/select.tsx        # Radix @radix-ui/react-select wrapper stylé
frontend/src/components/ui/card.tsx          # Card, CardHeader, CardTitle, CardContent
frontend/src/components/ui/input.tsx         # Input stylé
frontend/src/components/ui/table.tsx         # Table, Thead, Tbody, Tr, Th, Td
frontend/src/components/WorkflowSelector.tsx # Dropdown 5 workflows avec description
frontend/src/components/AnalyzeForm.tsx      # Formulaire ticker + workflow + 10 ratios Graham + options
frontend/src/components/AnalysisResult.tsx   # Affichage 15 sections skills + score + verdict + coût
frontend/src/components/ScreenerTable.tsx    # Tableau trié par score, badges verdict colorés, badge cache
frontend/src/components/HistoryTable.tsx     # Historique paginé, bouton PDF par ligne
frontend/src/components/MetricsDashboard.tsx # 5 cards métriques temps réel via useMetrics
frontend/src/pages/AnalyzePage.tsx           # useMutation postAnalyze + PDF blob download
frontend/src/pages/ScreenerPage.tsx          # Textarea multi-tickers + WorkflowSelector + ScreenerTable
frontend/src/pages/HistoryPage.tsx           # useQuery initial + useMutation load-more cursor pagination
frontend/src/pages/DashboardPage.tsx         # Wrapper MetricsDashboard
frontend/src/__tests__/AnalyzeForm.test.tsx  # 6 tests (submit, uppercase ticker, ratios Graham, loading, munger)
frontend/src/__tests__/ScreenerTable.test.tsx # 6 tests (tickers, tri score, EXEMPLAIRE, REJETER, cache, tri ticker)
frontend/src/__tests__/WorkflowSelector.test.tsx # 5 tests (combobox, 5 workflows, valeurs, label/desc, aria-label)
frontend/src/__tests__/useMetrics.test.ts    # 5 tests (init, onopen, message, JSON invalide, onclose)
frontend/src/__tests__/api.test.ts           # 6 tests (BASE_URL, ApiError, fetch URL, headers, ApiError 422)
```

#### Résultat des tests
```bash
cd frontend && npm test
# ✓ api.test.ts             6 tests
# ✓ ScreenerTable.test.tsx  6 tests
# ✓ WorkflowSelector.test.tsx 5 tests
# ✓ useMetrics.test.ts      5 tests
# ✓ AnalyzeForm.test.tsx    6 tests
# → 5 fichiers, 28 tests — tous verts
```

#### Build
```bash
cd frontend && npm run build
# → vite v5.4.21 ✓ built in ~2s, dist/ généré sans erreurs TypeScript
```

#### Critère de succès
```bash
cd frontend && npm run dev   # http://localhost:5173 accessible
cd frontend && npm run build # dist/ sans erreur TS
cd frontend && npm test      # 28 tests verts
```

---

### Sprint 23 — Watchlist persistante ✅

**Objectif :** Sauvegarder une liste de tickers + workflow + alertes → re-analyse hebdomadaire via Celery beat.

#### Fichiers créés
```
app/models/__init__.py
app/models/watchlist.py                  # WatchlistEntry, WatchlistCreate (Pydantic)
app/services/watchlist_service.py        # WatchlistService — CRUD PostgreSQL
app/api/endpoints/watchlist.py           # POST/GET/DELETE /watchlist + POST /{id}/analyze
tests/test_watchlist.py                  # 7 tests verts
```

#### Fichiers modifiés
```
infra/postgres/init.sql                  # Table watchlist ajoutée
app/workers/tasks.py                     # run_watchlist_analysis + _execute_watchlist_analysis
app/workers/celery_app.py                # beat_schedule — dimanche 07h00 UTC
app/api/main.py                          # watchlist_router + WatchlistService + version 2.3.0
```

---

### Sprint 24 — Alertes prix ✅

**Objectif :** Surveiller le prix courant de chaque entrée watchlist et déclencher une re-analyse si l'écart vs `valeur_intrinseque_ajustee` dépasse ±10 %.

#### Fichiers créés
```
app/services/price_alert_service.py  # PriceAlertService.check_price_alerts()
tests/test_price_alert.py            # 7 tests verts
```

#### Fichiers modifiés
```
app/models/watchlist.py              # +3 champs : last_intrinsic_value, last_price_checked, price_alert_threshold_pct
infra/postgres/init.sql              # colonnes Sprint 24 + migration ALTER TABLE commentée
app/services/watchlist_service.py    # requêtes mises à jour, update_last_analyzed(intrinsic_value), update_price_checked
app/workers/tasks.py                 # _execute_watchlist_analysis → last_intrinsic_value ; _execute_price_alert_check + run_price_alert_check
app/workers/celery_app.py            # beat quotidien run_price_alert_check (08h00 UTC)
app/api/endpoints/watchlist.py       # GET /watchlist/{id}/price-status
```

#### Critère de succès
```bash
pytest tests/test_price_alert.py -v  # 7 tests verts
curl localhost:8000/watchlist/{id}/price-status
# → {"ticker": "BNS", "current_price": 72.50, "intrinsic_value": 80.00, "ecart_pct": -0.094, "alerte": false}
```

---

### Sprint 25 — Export hebdomadaire automatique ✅

**Objectif :** Générer chaque dimanche un rapport PDF synthétisant les positions de la watchlist et l'envoyer par email.

#### Fichiers créés
```
app/services/email_service.py        # EmailService — SMTP stdlib ou SendGrid (import conditionnel)
tests/test_email_service.py          # 4 tests (smtp_ok, sans_config, pdf_attache, sendgrid_priorite)
tests/test_weekly_report.py          # 3 tests (genere_pdf, envoie_email, watchlist_vide)
```

#### Fichiers modifiés
```
app/services/report.py               # +generate_watchlist_summary_pdf(entries) — tableau récapitulatif
app/workers/tasks.py                 # +_execute_weekly_watchlist_report + run_weekly_watchlist_report
app/workers/celery_app.py            # beat_schedule — dimanche 09h00 UTC
```

#### Version milestone : 2.5.0

---

### Sprint 26 — Déploiement homelab ✅

**Objectif :** Passer à un service accessible hors du réseau local avec TLS automatique, backup PostgreSQL journalier, et monitoring Uptime Kuma.

#### Fichiers créés
```
infra/caddy/Caddyfile                        # Reverse proxy Caddy — TLS automatique Let's Encrypt
infra/backup/backup_postgres.sh              # pg_dump + rotation 7 jours
infra/backup/README.md                       # Instructions cron système
infra/monitoring/docker-compose.monitoring.yml # Uptime Kuma service séparé
docker-compose.prod.yml                      # Override production (Caddy + ports internes)
tests/test_healthz_prod.py                   # 2 tests healthz (status ok + version)
```

#### Décisions d'architecture
- **Reverse proxy** : Caddy 2 (Alpine) — TLS Let's Encrypt automatique via variables `{env.DOMAIN}` et `{env.CADDY_EMAIL}`
- **Port isolation** : `copilote:8000` non exposé hors du réseau Docker en production
- **Backup** : cron système (pas Celery), rotation 7 jours via `find -mtime +7`
- **Monitoring** : Uptime Kuma dans compose séparé (`docker-compose.monitoring.yml`) — surveille `/healthz` toutes les 60s sur `:3001`

#### Nouvelles variables d'environnement (`.env`)
```
DOMAIN=copilote.example.com
CADDY_EMAIL=yves@example.com
BACKUP_DIR=/backups
```

#### Critère de succès
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
curl https://{DOMAIN}/healthz  # → {"status": "ok", "version": "2.5.0"}
bash infra/backup/backup_postgres.sh  # → copilote_YYYYMMDD_HHMMSS.sql.gz créé
```

---

### Sprint 27 — Watchlist dans le frontend ✅

**Objectif :** Exposer la watchlist persistante (backend Sprint 23-24) dans une page React dédiée.

#### Fichiers créés
```
frontend/src/api/watchlist.ts                  # getWatchlist, addToWatchlist, removeFromWatchlist, triggerWatchlistAnalysis, getWatchlistPriceStatus
frontend/src/pages/WatchlistPage.tsx           # Page principale — formulaire ajout + tableau + mutations
frontend/src/components/WatchlistTable.tsx     # Tableau shadcn/ui + badges Alerte/OK calculés depuis entry
frontend/src/__tests__/WatchlistPage.test.tsx  # 6 tests Vitest verts
```

#### Fichiers modifiés
```
frontend/src/types/index.ts    # +WatchlistEntry, +WatchlistCreate, +PriceStatus
frontend/src/App.tsx           # route /watchlist + NavLink "Watchlist"
frontend/src/api/client.ts     # +requestEmpty() pour DELETE 204 No Content
```

#### Décisions
- `WatchlistEntry.id` est `string` (UUID) côté frontend — backend renvoie des UUIDs
- Badge Alerte calculé localement depuis `last_price_checked` / `last_intrinsic_value` (pas d'appel /price-status par ligne)
- `requestEmpty` ajouté à `apiClient` pour gérer les réponses 204 sans body JSON

#### Critère de succès
```bash
cd frontend && npm test  # → 34 tests verts (28 existants + 6 WatchlistPage)
cd frontend && npm run build  # → dist/ sans erreur TS
```

---

### Sprint 16 — Workflows alternatifs + WebSocket dashboard

> **Note :** Ce sprint a été sauté lors de la séquence originale et est désormais implémenté comme **Sprint 21**.

---

### Sprint 29 — Fix WorkflowRouter ✅

**Objectif :** Corriger les 24 tests en échec dans `tests/test_workflow_router.py`.

**Cause :** Lors du Sprint 21, `dorsey_moat` et `buffett_quality` avaient été exclus du
workflow `value_graham`, alors que les tests supposaient leur présence.

**Correction apportée :** Ajout de `dorsey_moat` et `buffett_quality` dans la séquence
`value_graham` du `WorkflowRouter`. Rétrocompatibilité préservée — 806 tests verts.

---

### Sprint 30 — Tests E2E Frontend → Backend (Claude mocké) ✅

**Objectif :** Couvrir toutes les fonctionnalités par des tests end-to-end traversant
le vrai frontend React jusqu'au vrai backend FastAPI, en mockant uniquement
`call_claude_with_retry`. Aucun token Anthropic réel consommé.

#### Fichiers à créer
```
tests/e2e/__init__.py
tests/e2e/conftest.py                 # uvicorn thread + mock Claude + Playwright browser
tests/e2e/fixtures/__init__.py
tests/e2e/fixtures/claude_stubs.py   # JSON stubs par skill (déterministes)
tests/e2e/test_e2e_auth.py           # login / logout / redirect (4 tests)
tests/e2e/test_e2e_analyze.py        # analyse Graham complète + bug fixes (5 tests)
tests/e2e/test_e2e_screener.py       # screener multi-tickers (3 tests)
tests/e2e/test_e2e_watchlist.py      # CRUD watchlist (4 tests)
```

#### Fichiers à modifier
```
requirements-dev.txt          # +playwright>=1.44, +pytest-playwright>=0.5
frontend/src/components/      # +data-testid sur AnalysisResult, ScreenerTable, WatchlistTable
frontend/src/pages/AnalyzePage.tsx   # bug fix : setResult(null) avant mutation
frontend/src/components/AnalyzeForm.tsx  # bug fix : earnings_ratios vide → sous-formulaire ou désactivation
```

#### Architecture
```
Playwright (Chromium headless)
  │  HTTP via Vite proxy (port 5173 → 8000)
  ▼
FastAPI (port 8000, thread uvicorn, Claude patché)
  │  call_claude_with_retry() → claude_stubs.py (0 token réel)
  ▼
fixtures déterministes JSON
```

#### Scénarios couverts
| Fichier | Tests | Fonctionnalité |
|---------|-------|---------------|
| `test_e2e_auth.py` | 4 | Redirect /login, login, bouton désactivé, logout |
| `test_e2e_analyze.py` | 5 | Analyse BNS, reset ticker, workflow Lynch, earnings 422, ratios invalides |
| `test_e2e_screener.py` | 3 | 3 tickers, badges, majuscules |
| `test_e2e_watchlist.py` | 4 | Ajout, suppression, doublon refusé, liste vide |

#### Critère de succès
```bash
# Vite dev server actif sur port 5173
cd frontend && npm run dev &

API_KEY=test-key pytest tests/e2e/ -v -m e2e
# → 16 tests verts, 0 appel api.anthropic.com

pytest tests/ -v -q --ignore=tests/e2e
# → 806+ passed, 1 xfail, 0 failures
```

---

### Sprint 31 — CI/CD GitHub Actions ✅

**Objectif :** Pipeline automatisé qui exécute la suite de tests complète à chaque push et pull request.
Aucun service Docker requis — PostgreSQL, Redis et Claude sont tous mockés.

#### Fichiers à créer
```
.github/workflows/ci.yml    # 2 jobs en parallèle : backend + frontend
```

#### Fichiers à modifier
```
README.md                   # Badge CI en haut de page
```

#### Spécifications `.github/workflows/ci.yml`

2 jobs indépendants (parallèles) :

| Job | Environnement | Commande |
|-----|--------------|----------|
| `backend` | ubuntu-latest, Python 3.11 | `pytest tests/ --ignore=tests/e2e -q --tb=short` |
| `frontend` | ubuntu-latest, Node 20 | `cd frontend && npm ci && npm test` |

Variables d'environnement (aucun secret GitHub requis) :
```
ANTHROPIC_API_KEY: sk-ant-ci-dummy-key   # factice — tests mockent Claude
API_KEY: ci-test-key                      # factice — tests mockent auth
DATABASE_URL: postgresql://unused:5432/unused
REDIS_URL: redis://localhost:6379/0
QDRANT_URL: http://localhost:6333
```

#### Critère de succès
```bash
# Push sur master → GitHub Actions
# → job:backend : 806+ passed, 1 xfail, 0 failures
# → job:frontend : 39 passed
# → Badge CI vert dans README.md
```

---

### Sprint 32 — Extraction auto Yahoo Finance (frontend) ✅

**Objectif :** Bouton "Auto-fill" sur `AnalyzeForm` qui appelle `GET /extract?ticker=BNS`
et pré-remplit les 10 champs Graham — élimine la saisie manuelle des ratios.

#### Fichiers à créer
```
(aucun — uniquement des modifications)
```

#### Fichiers à modifier
```
frontend/src/api/analyze.ts               # +getExtract(ticker: string) → GrahamRatios
frontend/src/components/AnalyzeForm.tsx   # bouton "Auto-fill" + loading + erreur
frontend/src/__tests__/AnalyzeForm.test.tsx  # 3 nouveaux tests (bouton, pré-remplissage, erreur 404)
```

#### Spécifications

- Bouton "Auto-fill" à côté du champ ticker (désactivé si ticker vide)
- Au clic : `GET /extract?ticker={ticker}` (endpoint déjà implémenté en Sprint 8)
- Si 200 : pré-remplit les champs `pe`, `pb`, `price`, `book_value`, `eps_ttm`, `revenue_bn`,
  `debt_equity`, `eps_growth_10y`, `dividend_years` — `current_ratio` peut être `null`
- Si 404 : toast/message "Ticker introuvable — vérifiez le symbole"
- Pendant la requête : bouton désactivé avec spinner (état `loading`)
- Les valeurs pré-remplies restent éditables

#### Tests à ajouter (`frontend/src/__tests__/AnalyzeForm.test.tsx`)
```tsx
test_autofill_button_renders()          // bouton "Auto-fill" visible dans le formulaire
test_autofill_prefills_ratios()         // mock GET /extract → champs pré-remplis correctement
test_autofill_error_404_affiche_msg()   // GET /extract 404 → message d'erreur visible
```

#### Critère de succès
```bash
cd frontend && npm test
# → 42 tests verts (39 existants + 3 nouveaux)

cd frontend && npm run build
# → dist/ sans erreur TypeScript
```

---

### Sprint 33 — Qualité bénéfices fonctionnelle ✅

**Objectif :** Activer la checkbox "Qualité bénéfices" dans `AnalyzeForm` : Auto-fill alimente `EarningsQualityRatios` depuis `GET /extract` (états financiers Yahoo Finance), checkbox active uniquement si les données sont disponibles.

#### Fichiers modifiés
```
app/skills/tier1/yahoo_finance.py          # +_fetch_earnings_data() +extract_earnings_quality() → EarningsQualityRatios | None
app/api/endpoints/extract.py               # ExtractResponse (graham + earnings_quality) — breaking change GET /extract
frontend/src/types/index.ts                # +EarningsQualityRatios +ExtractResponse ; earnings_ratios typé
frontend/src/api/analyze.ts                # getExtract() → Promise<ExtractResponse>
frontend/src/components/AnalyzeForm.tsx    # earningsRatios state, checkbox activée post-Auto-fill, payload earnings_ratios
requirements.txt                           # +pandas>=2.0.0
```

#### Tests ajoutés
```
tests/test_yahoo_finance.py                # +TestYahooFinanceExtractEarningsQuality (5 tests) + 2 tests ExtractEndpoint mis à jour
frontend/src/__tests__/AnalyzeForm.test.tsx # +3 tests Sprint 33 (checkbox désactivée, activation, payload)
```

#### Résultats
```bash
pytest tests/test_yahoo_finance.py -v   # 22 passed
cd frontend && npm test                  # 45 passed (42 existants + 3 nouveaux)
```

#### Logique UX
- Checkbox "Qualité bénéfices" désactivée par défaut (`disabled`)
- Après Auto-fill réussi avec `earnings_quality != null` → checkbox active + badge "✓ chargé (Yahoo Finance)"
- Si Yahoo Finance ne retourne pas les états financiers détaillés → checkbox reste désactivée, message "(Auto-fill requis)"
- `earnings_ratios` inclus dans `POST /analyze` uniquement si checkbox cochée et données disponibles

#### Critère de succès
```bash
# Auto-fill BNS → checkbox active → analyse avec earnings_quality
curl GET /extract?ticker=BNS
# → {"graham": {...}, "earnings_quality": {"sales_t": 38e9, ...} ou null}

curl POST /analyze -d '{"ticker":"BNS","ratios":{...},"earnings_ratios":{...}}'
# → JSON avec "earnings_quality": {"verdict": "AUCUN_SIGNAL|ATTENTION|...", ...}
```

---

### Sprint 34 — Tests E2E Sprint 33 ✅

**Objectif :** Couvrir le flux Sprint 33 (Auto-fill + checkbox Qualité bénéfices → analyse) par des tests Playwright.

#### Fichiers créés
```
tests/e2e/test_e2e_sprint33.py    # 3 tests E2E (autofill champs, checkbox active, analyse complète)
```

#### Fichiers modifiés
```
tests/e2e/conftest.py             # _make_yahoo_mock() : +extract_earnings_quality mocqué
```

#### Tests ajoutés
- `test_autofill_remplit_champs_graham` — bouton désactivé sans ticker, Auto-fill → P/E=11, P/B=1.3
- `test_autofill_active_checkbox_earnings` — après Auto-fill, checkbox activée + badge "✓ chargé"
- `test_autofill_earnings_inclus_dans_analyse` — Auto-fill + cocher earnings + Analyser → résultat BNS

#### Résultats
```bash
API_KEY=test-key pytest tests/e2e/test_e2e_sprint33.py -v -m e2e
# → 3 tests verts, 0 appel api.anthropic.com
pytest tests/e2e/ -v -m e2e   # → 19 tests verts (16 existants + 3 nouveaux)
```

---

### Sprint 35 — SSE Streaming ✅

**Objectif :** Afficher chaque skill au fur et à mesure via Server-Sent Events — éliminer les 15-30s d'écran blanc lors d'une analyse multi-skills.

#### Fichiers créés
```
app/api/endpoints/analyze_stream.py      # POST /analyze-stream — StreamingResponse SSE
frontend/src/components/StreamingProgress.tsx  # Composant skill-par-skill (active/done/verdict)
frontend/src/__tests__/AnalyzePage.test.tsx    # 5 tests Vitest streaming (form, progress, résultat, erreur, payload)
tests/test_analyze_stream.py             # 8 tests d'intégration SSE
```

#### Fichiers modifiés
```
app/orchestrator/core.py       # +stream_company_analysis() async generator (skill_start/skill_result/complete/cached/error)
app/api/main.py                # +analyze_stream_router, version 3.0.0
frontend/src/types/index.ts    # +SSEEvent discriminated union (skill_start, skill_result, complete, error, cached)
frontend/src/api/analyze.ts    # +streamAnalyze() — fetch POST + ReadableStream + SSE parsing manuel
frontend/src/pages/AnalyzePage.tsx  # Refactorisé : for-await SSE + partialResult + activeSkill + completedSkills
```

#### Architecture SSE
- **Pourquoi POST et non EventSource :** `EventSource` ne supporte que GET ; le payload JSON + Bearer token impose `fetch()` + `ReadableStream` manuel
- **Parsing SSE** : buffer accumulé, split `\n`, tracking `event:` et `data:` cross-chunk, `currentEventType` réinitialisé après chaque data
- **Events émis** : `skill_start` → `skill_result` (×N) → `complete` ; `cached` si cache hit ; `error` si exception dans le générateur
- **State React** : `isStreaming`, `partialResult`, `activeSkill`, `completedSkills` mis à jour event-par-event

#### Tests
```python
# Backend (8 tests — tests/test_analyze_stream.py)
test_stream_content_type_sse()               # Content-Type: text/event-stream
test_stream_contient_skill_start()           # event skill_start présent
test_stream_skill_start_contient_skill_id()  # skill_id == "graham_analysis"
test_stream_skill_result_contient_result()   # skill_id + result présents
test_stream_complete_contient_analyze_response()  # analysis_id, ticker, cost_usd
test_stream_ordre_events()                   # start < result < complete (ordre garanti)
test_stream_cache_hit_retourne_cached()      # event cached, pas de skill_start
test_stream_erreur_skill_retourne_event_error()   # exception → event error {message}

# Frontend (5 tests — frontend/src/__tests__/AnalyzePage.test.tsx)
test_affiche_formulaire_et_titre()           # rendu initial
test_affiche_StreamingProgress_pendant_streaming()  # streaming-progress testid visible
test_affiche_resultat_final_apres_complete() # result-ticker = "BNS"
test_affiche_message_erreur_quand_rejet()    # error-message testid avec message
test_appelle_streamAnalyze_avec_ticker()     # payload {ticker: 'BNS'}
```

#### Critère de succès
```bash
pytest tests/test_analyze_stream.py -v         # 8 tests verts
cd frontend && npm test                         # 50 tests Vitest verts
```

---

### Sprint 36 — Eval framework qualité IA + Sanitisation ticker ✅

**Objectif :** Mesurer la qualité des sorties Claude via un dataset golden de 20 tickers calibrés,
détecter les dérives de verdict après chaque changement de prompt, et sécuriser les entrées ticker
avec validation et normalisation systématique.

#### Fichiers créés

```
app/utils/ticker_sanitizer.py                   # sanitize_ticker() — regex + HTTP 422
tests/test_ticker_sanitizer.py                   # 28 tests (11 valides + 14 invalides + 3 standalone)
tests/evals/__init__.py                          # Package evals
tests/evals/conftest.py                          # eval_client — AsyncClient réel, JAMAIS de mock Claude
tests/evals/fixtures/__init__.py                 # load_graham_golden() → list[dict]
tests/evals/eval_runner.py                       # EvalResult, EvalReport, EvalRunner.run_all()
tests/evals/fixtures/graham_golden.template.json # 20 tickers (PASSE×8, BORDERLINE×6, REJETER×6)
```

#### Fichiers modifiés

```
app/skills/tier2/graham_analysis/schemas.py  # defensive_verdict @computed_field + pe: float | None
tests/test_schemas.py                         # test_pe_null_accepte + test_pe_negatif_accepte (remplacement test_pe_manquant)
tests/test_api.py                             # test_body_sans_pb_retourne_422 (pb = champ requis restant)
tests/test_integration_sync.py               # BODY_SANS_PB (pe optionnel, pb requis)
tests/test_report.py                          # payload invalides → pb manquant (pas pe)
```

#### Décisions d'architecture prises

| Décision | Choix retenu | Raison |
|----------|-------------|--------|
| **`defensive_verdict`** | `@computed_field` dérivé de `defensive_score` (PASSE≥6, BORDERLINE 4-5, REJETER≤3) | Cible stable pour les evals — jamais générée par Claude, toujours déterministe |
| **`pe: float \| None`** | Nullable, défaut `None` | Sociétés déficitaires (NKLA, RIVN, AMC) — critère PE échoue automatiquement si `None` |
| **Format golden dataset** | Clé `inputs` (pas `ratios`), `defensive_score_range: [min, max]` | Distingue les entrées API des sorties attendues ; plage plutôt que valeur exacte pour tolérer la variabilité Claude |
| **`@pytest.mark.evals`** | `call_claude_with_retry` **JAMAIS patché** dans `tests/evals/` | Les evals mesurent le vrai comportement Claude — mocker Claude annulerait leur utilité |

#### Progression

| Livrable | Statut |
|----------|--------|
| `sanitize_ticker()` + 28 tests | ✅ Complété |
| `defensive_verdict` computed_field | ✅ Complété |
| `pe: float \| None` + 4 tests mis à jour | ✅ Complété |
| EvalRunner + conftest + fixtures infra | ✅ Complété |
| `graham_golden.template.json` (20 tickers) | ✅ Complété |
| Intégrer `sanitize_ticker()` dans 3 endpoints | ✅ Complété — core.py + screen.py + watchlist.py |
| `graham_golden.json` (données réelles Yahoo) | ✅ Complété — 20 cas calibrés par Yves |
| `tests/evals/test_graham_evals.py` | ✅ Complété |
| `pytest tests/evals/ -m evals` ≥ 18/20 | ✅ **20/20 PASS (100 %)** |

#### Intégration `sanitize_ticker()` restante

```python
# app/orchestrator/core.py — @field_validator sur AnalyzeRequest.ticker
@field_validator("ticker")
@classmethod
def validate_ticker(cls, v: str) -> str:
    return sanitize_ticker(v)

# app/api/endpoints/screen.py — avant ScreenerService.screen()
# app/api/endpoints/watchlist.py — avant PostgreSQL insert
```

#### Tests evals — structure attendue (`tests/evals/test_graham_evals.py`)

```python
@pytest.mark.evals
async def test_graham_golden_dataset(eval_client, graham_golden):
    """Exécute tous les cas du golden dataset contre l'API réelle."""
    runner = EvalRunner(client=eval_client)
    report = await runner.run_all(graham_golden)

    assert report.pass_rate >= 0.90, f"Taux de réussite {report.pass_rate:.0%} < 90%"
    assert report.verdict_drift_rate <= 0.10
    report.print_summary()
```

Note : le payload mappe `inputs → ratios` lors de l'appel `POST /analyze`.

#### Critères de succès

- [x] `pytest tests/test_ticker_sanitizer.py -v` → 28 tests verts
- [x] `pytest tests/ -v -q --ignore=tests/evals` → 817+ passés (pas de régression)
- [x] `graham_golden.json` rempli avec vrais ratios Yahoo Finance
- [x] `pytest tests/evals/ -m evals` → **20/20 (100 %)** — appels Claude réels ✅

---

### Sprint 37 — Validation anti-hallucination ✅

**Objectif :** Sanity checks financiers avant appel Claude + détection contradictions inter-skills +
extension du `confidence_score` déterministe aux skills Buffett, Earnings et Dorsey.

#### Livrables

| Livrable | Statut |
|----------|--------|
| `@model_validator` sur `GrahamRatios` : pe<0, pb<0, eps_growth_10y>5, triangle pe/price/eps_ttm | ✅ |
| `confidence_score` Graham (`@computed_field` valeur_observee) | ✅ |
| `confidence_score` Buffett (champ régulier, calculé dans execute() depuis ratios non-None) | ✅ |
| `confidence_score` EarningsQuality (`@computed_field` depuis cadres M/Z/F/C/Sloan) | ✅ |
| `confidence_score` Dorsey (champ régulier, calculé dans execute() depuis ratios non-None) | ✅ |
| `_detect_inter_skill_conflicts()` + `inter_skill_conflicts: list[str]` dans `AnalyzeResponse` | ✅ |
| 27 nouveaux tests (validators + confidence × 4 skills + inter-skill conflicts) | ✅ |

#### Critères de succès

- [x] `pytest tests/evals/ -m evals` → 20/20 toujours verts après ajout validateurs
- [x] `inter_skill_conflicts` détecté pour Buffett=COMPOUNDER + Graham=REJETER
- [x] `confidence_score` calculé de façon déterministe sur 4 skills (Graham, Buffett, Earnings, Dorsey)
- [x] `pytest -m "not e2e and not evals"` → 851 tests CI verts (pas de régression, 25 échecs pré-existants)

#### Décisions d'architecture
- **GrahamRatios validators** : WARNING log uniquement, jamais HTTP 422 — les données imparfaites passent
- **confidence_score stratégie** : `@computed_field` quand l'output encode la complétude (valeur_observee / None-able), champ régulier sinon (calculé dans execute() depuis les inputs)
- **inter_skill_conflicts** : `list[str]` dans AnalyzeResponse (pas `bool`) — messages explicites pour revue manuelle

---

### Sprint 38 — Scoring composite unifié 🔜

**Objectif :** Calculer un score global 0-100 agrégeant les 6 skills principaux avec pondération fixe.

#### Livrables prévus

| Livrable | Pondération |
|----------|------------|
| Graham : `defensive_score / 8` × 20 pts | 20 % |
| Buffett : `quality_score / 4` × 20 pts | 20 % |
| Dorsey : `moat_type` (WIDE=20, NARROW=13, NONE=0) × pondération | 15 % |
| EarningsQuality : `f_score / 9` × 15 pts | 15 % |
| Valuation : `marge_securite_composite` × 20 pts | 20 % |
| Marks cycles : pondération sentiment × 10 pts | 10 % |

#### Fichiers prévus
- `app/services/composite_score.py` — `CompositeScore`, `compute_composite_score(response: AnalyzeResponse)`
- `app/orchestrator/core.py` — ajouter `composite_score: CompositeScore | None` dans `AnalyzeResponse`
- `tests/test_composite_score.py` — tests unitaires (calculs, plages, None-safety)

#### Critères de succès
- [ ] Score 0-100 présent dans `AnalyzeResponse` si au moins 2 skills exécutés
- [ ] Tests unitaires couvrent toutes les combinaisons de skills présents/absents
- [ ] Aucune régression CI (851+ tests verts)

---

## Règles de mise à jour de ce fichier

1. **Après chaque sprint complété** : passer le statut `🔜` → `✅`, mettre à jour "Dernier sprint complété" et "Sprint actif"
2. **Quand un test est ajouté** : cocher la case dans la liste du sprint correspondant
3. **Quand une décision d'architecture est prise** : remplir la colonne Options et archiver la ligne
4. **Version** : incrémenter le patch (0.3.x) pour les corrections, le mineur (0.x.0) pour chaque sprint complété
5. **Ne jamais supprimer** les sprints complétés — ils servent de documentation de la progression

---

*Roadmap mise à jour le 2026-05-09 — à mettre à jour après chaque sprint.*
*Utiliser `prompt-mise-a-jour-roadmap.md` pour guider Claude lors des mises à jour.*
*Sprint 24 complété : Alertes prix — PriceAlertService + run_price_alert_check + GET /price-status + 7 tests verts — version 2.4.0*
*Sprint 25 complété : Export hebdomadaire automatique — EmailService + generate_watchlist_summary_pdf + run_weekly_watchlist_report + 7 tests verts — version 2.5.0*
*Sprint 26 complété : Déploiement homelab — Caddy + TLS Let's Encrypt + backup PostgreSQL + Uptime Kuma + docker-compose.prod.yml + 2 tests healthz — version 2.5.0*
*Sprint 27 complété : Watchlist dans le frontend — WatchlistPage React + WatchlistTable + api/watchlist.ts + requestEmpty() + 6 tests Vitest — total frontend 34 tests verts — version 2.5.0*
*Sprint 28 complété : Authentification frontend — AuthContext + ProtectedRoute + LoginPage + token localStorage + 5 tests Vitest — total frontend 39 tests verts — version 2.5.0*
*Sprint 29 complété : Fix WorkflowRouter — 24 échecs corrigés (dorsey_moat + buffett_quality dans value_graham) — total backend 806 passés — version 2.5.0*
*Sprint 30 complété : Tests E2E Frontend → Backend — 16 tests Playwright (auth×4, analyze×5, screener×3, watchlist×4) — InMemoryWatchlistService + stubs JSON 15 skills + mocks middleware — version 2.6.0*
*Sprint 31 complété : CI/CD GitHub Actions — .github/workflows/ci.yml — 2 jobs parallèles (backend pytest + frontend vitest) — badge CI README.md — version 2.6.0*
*Sprint 32 complété : Extraction auto Yahoo Finance (frontend) — bouton Auto-fill AnalyzeForm → GET /extract → ratios pré-remplis — 3 tests Vitest + fix LoginPage validation — total frontend 42 tests verts — version 2.7.0*
*Sprint 33 complété : Qualité bénéfices fonctionnelle — extract_earnings_quality() + ExtractResponse + checkbox AnalyzeForm + 5 tests backend + 3 tests frontend — 45 tests Vitest verts — version 2.8.0*
*Sprint 34 complété : Tests E2E Sprint 33 — 3 tests Playwright (autofill Graham, checkbox earnings active, analyse complète) + fix mock extract_earnings_quality dans conftest E2E — 19 tests E2E verts — version 2.9.0*
*Sprint 35 complété : SSE Streaming — POST /analyze-stream + stream_company_analysis() + StreamingProgress React + streamAnalyze() fetch/ReadableStream + 8 tests backend + 5 tests frontend — 50 tests Vitest verts — version 3.0.0*
*Sprint 36 complété : Eval framework qualité IA + Sanitisation ticker — defensive_verdict computed_field + defensive_score computed_field + pe nullable + sanitize_ticker() intégré dans 3 endpoints + EvalRunner + graham_golden.json 20 cas + test_graham_evals.py **20/20 PASS** — 817 tests CI verts*
*Sprint 37 complété : Validation anti-hallucination — @model_validator GrahamRatios (pe<0, pb<0, eps_growth>5, triangle pe/price/eps_ttm) + confidence_score sur 4 skills (Graham @computed_field, Buffett/Dorsey champ régulier, Earnings @computed_field) + _detect_inter_skill_conflicts() + inter_skill_conflicts dans AnalyzeResponse — 27 nouveaux tests — 851 tests CI verts — version 3.1.0*
