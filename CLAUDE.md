# TradingClaude — Instructions pour Claude Code

## Identité du projet

Je suis **Yves**, développeur C++/Java/React basé au Québec.  
Ce projet est mon **copilote financier IA** : un système d'analyse d'investissement multi-frameworks
construit autour de 15 skills d'analyse financière et d'une architecture RAG progressive.  
Il est **distinct** du bot de trading C++ (Interactive Brokers / QQQ).

---

## Contexte financier

### Portefeuille — 4 piliers
| Pilier | Description |
|--------|-------------|
| **ETF passif** | Core — diversification large (ex. XEQT, VFV) |
| **Thématique** | Uranium, énergie IA, secteurs ciblés |
| **Valeur** | Approche Graham/Buffett — screener fondamental |
| **Algo/Systématique** | Stratégies quantitatives backtestées |

### Comptes canadiens
- **CELI** — croissance libre d'impôt, priorité 1
- **REER** — déduction fiscale, horizon long terme
- **CELIAPP** — achat propriété
- **Marge Atout (Desjardins)** — HELOC pour Smith Manœuvre

### Cadre fiscal (Québec)
- Gains en capital : 50 % inclusion (particulier)
- Revenus de dividendes : crédit d'impôt canadien applicable
- Intérêts de marge déductibles si investis (Smith Manœuvre)
- Toujours distinguer compte enregistré vs non enregistré

---

## Base de connaissances — 15 skills d'analyse

Les skills sont dans `.claude/skills/`. Chaque skill a un `SKILL.md` (logique + workflow)
et des fichiers `references/*.md` (corpus de connaissances détaillé).

**Ces fichiers sont la source de vérité pour toute analyse financière.**  
Claude Code doit les consulter avant de générer du code ou des analyses.

```
.claude/skills/
  ├── graham-stock-screening/          # Critères Graham — P/E, P/B, current ratio, formule valeur
  ├── buffett-quality-investing/       # 4 filtres Buffett, owner earnings, compounders
  ├── stock-valuation-triangulation/   # DCF + comparables + sectoriel, matrice sensibilité
  ├── investment-thesis-builder/       # Synthèse multi-skills, scenarios bull/base/bear
  ├── earnings-quality-fraud-detection/ # M-Score, Z-Score, F-Score, C-Score, accruals
  ├── dorsey-moat-analysis/            # 5 sources de moat, ROIC durable
  ├── marks-cycles-and-risk/           # Pendule sentiment, second-level thinking
  ├── damodaran-narrative-and-numbers/ # Narrative vs chiffres, ERP, story stocks
  ├── pabrai-dhandho-and-cloning/      # 9 principes Dhandho, 13F, Kelly fractionnel
  ├── fisher-scuttlebutt/              # 15 points Fisher, méthode scuttlebutt
  ├── lynch-categories-and-tenbaggers/ # 6 catégories Lynch, PEG, tenbaggers
  ├── klarman-margin-of-safety/        # Marge de sécurité, distressed, absolute return
  ├── munger-mental-models/            # 25 biais cognitifs, inversion, lollapalooza
  ├── canadian-tax-considerations/     # CELI/REER/CELIAPP, fiscalité QC/CA
  └── greenblatt-magic-formula/        # ROC + Earnings Yield, situations spéciales
```

> Si un skill est absent ou incomplet, signale-le avant de continuer l'analyse.

### Fichiers de référence associés (~62 documents)
Chaque skill possède un répertoire `references/` contenant les détails opérationnels
(formules, seuils, tableaux, exemples). Ce sont les documents qui alimenteront
le RAG Qdrant en Phase 1. Consulte-les directement pour les calculs précis.

---

## Architecture du système (source de vérité : `architecture-copilote-financier.md`)

Le projet est en transition d'un outil d'analyse interactif Claude vers un **service RAG**
avec API FastAPI. Lire `architecture-copilote-financier.md` avant toute modification
de l'infrastructure.

### Phases d'implémentation
| Phase | État | Description |
|-------|------|-------------|
| **Phase 0** | ✅ | API FastAPI + graham_analysis skill + PostgreSQL |
| **Phase 1** | ✅ | Infrastructure RAG Qdrant, get_citations(), Langfuse, retry backoff |
| **Phase 2** | ✅ | 17 skills en production, extracteurs tier1, screener multi-tickers |
| **Phase 3** | 🔄 Sprint 36 | Eval framework qualité IA, sanitisation ticker, pipeline synthèse |

### Structure du projet
```
TradingClaude/
├── CLAUDE.md                          # Ce fichier
├── ROADMAP.md                         # Source de vérité des sprints (sprint actif, historique)
├── architecture-copilote-financier.md # Source de vérité technique (sections 3.2, 7.3, 8.2, 9.1, 10, 11.2)
├── docker-compose.yml                 # 5 services : copilote, postgres, qdrant, redis, celery
├── Dockerfile                         # Image Python 3.11 pour le service copilote
├── requirements.txt                   # Dépendances Python
├── .env                               # Variables d'environnement (NE PAS committer)
├── .env.example                       # Template des variables requises
│
├── app/
│   ├── api/
│   │   ├── main.py                    # Lifespan, CORS, middlewares, routeurs
│   │   └── endpoints/
│   │       ├── analyze_stream.py      # POST /analyze (SSE streaming)
│   │       ├── screen.py              # POST /screen (multi-tickers, max 20)
│   │       ├── extract.py             # POST /extract (ratios depuis ticker)
│   │       ├── jobs.py                # GET/POST /jobs (Celery async)
│   │       ├── report.py              # GET /report/{ticker}
│   │       ├── watchlist.py           # CRUD /watchlist
│   │       ├── telemetry.py           # GET /telemetry/summary|costs|cache|latency
│   │       └── ws_metrics.py          # WebSocket /ws/metrics
│   │
│   ├── orchestrator/
│   │   ├── core.py                    # Workflow company_analysis + persistance
│   │   └── router.py                  # Dispatche vers les skills selon la requête
│   │
│   ├── skills/
│   │   ├── base.py                    # SkillBase — classe parente de tous les skills
│   │   ├── tier1/                     # Extracteurs de données
│   │   │   ├── yahoo_finance.py       # Ratios depuis yfinance
│   │   │   └── sedar_plus.py          # Documents SEDAR+
│   │   └── tier2/                     # 15 skills d'analyse (chacun : skill.py + schemas.py + prompts/)
│   │       ├── graham_analysis/
│   │       ├── earnings_quality/
│   │       ├── dorsey_moat/
│   │       ├── buffett_quality/
│   │       ├── stock_valuation/
│   │       ├── thesis_builder/
│   │       ├── munger_mental/
│   │       ├── canadian_tax/
│   │       ├── lynch_categories/
│   │       ├── fisher_scuttlebutt/
│   │       ├── klarman_margin/
│   │       ├── greenblatt/
│   │       ├── damodaran_narrative/
│   │       ├── marks_cycles/
│   │       └── pabrai_dhandho/
│   │
│   ├── rag/                           # Phase 1 — RAG Qdrant
│   │   ├── client.py                  # Connexion Qdrant
│   │   ├── embeddings.py              # Génération embeddings (OpenAI)
│   │   └── service.py                 # RagService — get_citations()
│   │
│   ├── middleware/
│   │   ├── auth.py                    # BearerTokenMiddleware
│   │   └── rate_limit.py              # RateLimitMiddleware
│   │
│   ├── observability/
│   │   └── langfuse_client.py         # LangfuseTracer (optionnel si LANGFUSE_SECRET_KEY)
│   │
│   ├── services/
│   │   ├── analysis_cache.py          # Cache Redis pour les analyses
│   │   ├── screener.py                # Screener multi-tickers
│   │   ├── report.py                  # Génération de rapports
│   │   ├── watchlist_service.py       # Service watchlist
│   │   ├── price_alert_service.py     # Alertes de prix
│   │   └── email_service.py           # Envoi de rapports par courriel
│   │
│   ├── workers/
│   │   ├── celery_app.py              # Configuration Celery
│   │   └── tasks.py                   # Tâches async (analyses longues)
│   │
│   ├── models/
│   │   └── watchlist.py               # Modèle Pydantic watchlist
│   │
│   ├── utils/
│   │   ├── costs.py                   # Calcul cost_usd depuis usage tokens
│   │   ├── retry.py                   # Retry exponentiel 429/529
│   │   └── ticker_sanitizer.py        # Validation et normalisation des tickers
│   │
│   └── logging_config.py              # Logging structuré JSON
│
├── infra/
│   └── postgres/
│       └── init.sql                   # Table analysis_history
│
├── .claude/
│   └── skills/                        # Les 15 skills — base de connaissances (source de vérité)
│
└── analyses/                          # Analyses complètes générées (ex: BNS-2026-05.md)
```

---

## Stack technique

### Service copilote
- **Python 3.11** — runtime
- **FastAPI ≥ 0.115** — API REST async (SSE streaming, WebSocket)
- **Anthropic SDK ≥ 0.40** — API Claude avec prompt caching
- **asyncpg ≥ 0.29** — driver PostgreSQL async
- **Pydantic v2** — validation des données
- **Celery** — tâches asynchrones longues (analyses background)
- **Langfuse** — observabilité LLM (optionnel, activé si `LANGFUSE_SECRET_KEY`)
- **Docker Compose** — orchestration locale homelab

### Infrastructure
- **PostgreSQL 16** — historique des analyses (`analysis_history`)
- **Qdrant v1.9** — vecteurs RAG, collection `investment_knowledge`
- **Redis 7** — cache analyses + sessions Celery

### Outils d'analyse existants
- **React + TypeScript** — interfaces de screening interactives
- **Python** — backtesting (pandas, vectorbt, yfinance)
- **Jupyter** — analyses exploratoires
- **Markdown** — rapports et thèses d'investissement

---

## Conventions de code

### Général
- Langue des commentaires, docstrings et variables métier : **français**
- Langue du code (noms de fonctions, classes, modules) : **anglais**
- Typage strict partout — pas de `any` en TypeScript, type hints en Python
- Async/await obligatoire pour les appels I/O (DB, API)
- Commentaires uniquement si le WHY n'est pas évident — pas de paraphrase du code

### Python (service copilote)
```python
async def execute(self, input_data: GrahamAnalysisInput) -> GrahamAnalysisOutput:
    """Appelle Claude avec prompt caching et retourne l'analyse Graham validée."""
    response = await self._client.messages.create(
        model=self._model,
        system=self.get_system_prompt(),   # cache_control activé
        messages=[{"role": "user", "content": self._build_user_message(input_data)}],
        max_tokens=2048,
    )
    data = _parse_claude_json(response.content[0].text)
    data["cost_usd"] = _calculate_cost(response.usage, self._model)
    return GrahamAnalysisOutput.model_validate(data)
```

### React / TypeScript (screener)
```tsx
// ✅ Bon
const calculateGrahamNumber = (eps: number, bvps: number): number => {
  return Math.sqrt(22.5 * eps * bvps); // Formule Graham classique
};

// ❌ Éviter
const calc = (a: any, b: any) => Math.sqrt(22.5 * a * b);
```

### Métriques financières — noms standardisés
| Variable | Signification |
|----------|--------------|
| `eps` / `eps_ttm` | Bénéfice par action (12 derniers mois) |
| `bvps` / `book_value` | Valeur comptable par action |
| `pe` / `pb` | Price/Earnings, Price/Book |
| `fcf` | Free cash flow |
| `roic` | Return on invested capital |
| `roe` | Return on equity |
| `eps_growth_10y` | Croissance totale BPA sur 10 ans (fraction : 0.85 = 85 %) |
| `current_ratio` | Actif circulant / Passif circulant |
| `debt_equity` | Dette totale / Capitaux propres |
| `cost_usd` | Coût API Claude de l'appel en USD |
| `grahamNumber` | √(22.5 × EPS × BVPS) |
| `pegRatio` | P/E ÷ croissance bénéfices |
| `sharpeRatio` | Rendement excédentaire / volatilité |
| `maxDrawdown` | Perte max pic-à-creux |

---

## Comportement attendu de Claude Code

### Fin de sprint — mises à jour obligatoires

Un sprint n'est **pas terminé** tant que ces deux fichiers n'ont pas été mis à jour :

1. **`ROADMAP.md`** — passer le sprint complété de 🔜 → ✅, mettre à jour "Sprint actif", "Dernier sprint complété", version, et ajouter le sprint suivant
2. **`prompt-mise-a-jour-roadmap.md`** — réécrire pour le sprint suivant : titre, état du projet, LECTURE OBLIGATOIRE, section TÂCHE, SPRINTS SUGGÉRÉS, template

> Ces deux fichiers sont la source de vérité pour les conversations futures. Sans leur mise à jour, la prochaine session commence avec un contexte obsolète.

`prompt-mise-a-jour-roadmap.md` doit toujours inclure une section **SPRINTS SUGGÉRÉS** proposant 3-5 nouveaux sprints non encore planifiés, avec objectif, complexité et justification courte.

**Ces mises à jour sont automatiques — ne pas demander confirmation à Yves. Les exécuter dès que les livrables du sprint sont validés.**

### Autonomie pendant un sprint — actions sans confirmation requise

Durant l'exécution d'un sprint, Claude Code est autorisé à effectuer les actions suivantes **sans demander de confirmation** :

- **Modifier des fichiers existants** — éditer tout fichier Python, TypeScript, Markdown, JSON, YAML du projet
- **Créer de nouveaux fichiers** — nouveaux modules, schemas, tests, prompts, services
- **Exécuter des tests** — `pytest`, `vitest`, et toute commande de test du projet
- **Exécuter des commandes bash** — linting, formatage, vérifications statiques, inspection de fichiers

**Exceptions — confirmation obligatoire avant d'agir :**
- `git push` ou toute opération affectant le dépôt distant
- `docker-compose down` ou destruction d'infrastructure
- Suppression de fichiers (`rm`, `del`)
- Modification de `.env` ou de fichiers de secrets
- Toute opération irréversible sur la base de données (DROP, DELETE sans WHERE)

### Avant de coder ou analyser
1. Lire le skill concerné dans `.claude/skills/{skill-name}/SKILL.md`
2. Consulter les `references/*.md` du skill pour les formules et seuils précis
3. Si l'analyse implique l'infrastructure → lire `architecture-copilote-financier.md` d'abord
4. Signaler si une hypothèse financière est discutable ou si des données manquent

### Format des réponses
- **Toujours en français**
- Réponses orientées **décision** — pas de remplissage
- Pour les formules financières : montrer le calcul intermédiaire, pas juste le résultat final
- Pour les analyses d'actions : utiliser la structure des skills (voir `analyses/BNS-2026-05.md` comme exemple)

### Gestion de l'API copilote
- Modèle par défaut : `claude-sonnet-4-6` (variable `CLAUDE_MODEL`)
- Prompt caching **obligatoire** sur tous les system prompts de skills (section 8.2 architecture)
- Le `cost_usd` doit toujours être calculé et persisté (section 10 architecture)
- Les schemas Pydantic dans `schemas.py` font foi — ne pas contourner la validation

### Gestion des données financières
- Valider les données avant calcul (None, valeurs aberrantes, division par zéro)
- Toujours préciser la **source** et la **date** des données dans les analyses
- Distinguer clairement backtesting vs live trading
- `current_ratio` peut être `null` pour les institutions financières — adapter les critères Graham

### Sécurité
- Aucune clé API dans le code — utiliser `.env`
- `.env` est dans `.gitignore` — ne jamais le committer
- `.env.example` obligatoire avec toutes les clés requises et leurs valeurs exemples

### Stratégie de test — pyramide obligatoire

Tout code livré doit être couvert selon la pyramide de test suivante, du plus granulaire au plus large :

| Niveau | Portée | Outils | Exemples dans ce projet |
|--------|--------|--------|------------------------|
| **Test unitaire** | Fonctions / classes isolées, logique pure | `pytest`, `vitest` | calculs Graham, schemas Pydantic, formules financières |
| **Test composant** | Composant React isolé (avec mocks des dépendances) | `vitest` + `@testing-library/react` | `AnalyzeForm`, `ScreenerTable`, `LoginPage` |
| **Test d'intégration** | Plusieurs modules ensemble — endpoints FastAPI, orchestrateur + skills | `pytest` + `httpx.AsyncClient`, `fakeredis`, `asyncpg` mocké | `test_integration_sync.py`, `test_workflow_router.py` |
| **Test système** | Application complète démarrée, sans UI — API exercée de bout en bout | `pytest` + `httpx` contre uvicorn en thread | `test_healthz_prod.py`, smoke tests |
| **Test d'acceptation** | Scénarios utilisateur complets depuis le navigateur | `playwright` | `tests/e2e/test_e2e_*.py` |

**Règle absolue : les appels à l'API Claude ne doivent jamais être réels dans les tests.**  
`call_claude_with_retry()` doit être patché à chaque niveau de la pyramide — unitaire, intégration, système, acceptation.  
Utiliser `unittest.mock.patch` (backend) ou `vi.mock` (frontend) selon le contexte.

**Marqueurs pytest à utiliser :**
- `@pytest.mark.e2e` — tests Playwright (exclus du CI standard : `--ignore=tests/e2e`)
- `@pytest.mark.integration` — tests nécessitant une vraie DB ou un vrai Redis

**Couverture minimale attendue par type de livrable :**
- Nouveau skill (ex: `earnings_quality`) → tests unitaires sur les schemas + test d'intégration sur l'endpoint
- Nouveau endpoint FastAPI → test d'intégration obligatoire
- Nouveau composant React → test composant obligatoire (happy path + cas d'erreur)
- Nouveau workflow orchestrateur → test système via `test_workflow_router.py`

---

## Commandes fréquentes

```bash
# Démarrer l'infrastructure complète
docker-compose up -d

# Vérifier que le service est opérationnel
curl localhost:8000/healthz

# Analyse complète via SSE streaming (retourne les 15 skills progressivement)
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS"}'

# Screener multi-tickers (max 20)
curl -X POST localhost:8000/screen \
  -H "Content-Type: application/json" \
  -d '{"tickers":["BNS","TD","RY"]}'

# Extraire les ratios financiers depuis Yahoo Finance
curl -X POST localhost:8000/extract -H "Content-Type: application/json" \
  -d '{"ticker":"BNS"}'

# Historique des analyses
curl "localhost:8000/history?ticker=BNS"

# Métriques / observabilité
curl "localhost:8000/metrics?days=30"
curl "localhost:8000/telemetry/summary"

# Logs du service copilote
docker-compose logs -f copilote

# Arrêter l'infrastructure
docker-compose down

# Reconstruire après modification du code
docker-compose up -d --build copilote

# Connexion directe à PostgreSQL
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT ticker, defensive_score, cost_usd, created_at FROM analysis_history ORDER BY created_at DESC LIMIT 10;"
```

### Outils d'analyse existants (hors API)
```bash
# Screener React
cd screener && npm run dev

# Backtesting Python
python backtests/run_backtest.py --strategy swing --ticker QQQ

# Tests
cd screener && npm test
python -m pytest backtests/tests/
```

---

## Ajout d'un nouveau skill (Phase 2+)

Pour implémenter un nouveau skill dans l'API :

1. Créer `app/skills/tier2/{skill_name}/` avec `skill.py`, `schemas.py`, `prompts/system.md`
2. Hériter de `SkillBase` dans `skill.py` (`app/skills/base.py`)
3. Le system prompt doit dépasser **1 024 tokens** pour bénéficier du prompt caching
4. Ajouter le skill au workflow dans `app/orchestrator/core.py` et `router.py`
5. Le skill source de vérité est dans `.claude/skills/{skill-name}/SKILL.md` — le prompt doit être fidèle à ce contenu
6. Couvrir selon la pyramide de tests : schemas (unitaire) + endpoint (intégration)

---

## Ce projet N'est PAS

- ❌ Le bot C++ Interactive Brokers (EMA/RSI sur QQQ) — projet séparé
- ❌ CoRoute (carpooling Java/GLO-2004) — projet séparé
- ❌ Ninja Sasquatch Games (React board games) — projet séparé

---

*Dernière mise à jour : 2026-05-13 — Yves / TradingClaude*  
*Phase 3 active — Sprint 38 — 17 skills en production, RAG Qdrant, Celery, Langfuse, SSE streaming*
