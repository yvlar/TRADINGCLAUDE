# Architecture — Copilote Financier IA
**Version 0.1 — Phase 0 active**
Source de vérité pour toutes les phases d'implémentation.

---

## 1. Vision

Transformer les 15 skills d'analyse financière présents dans `.claude/skills/` en un RAG opérationnel interrogeable via une API. Chaque skill possède un `SKILL.md` (logique) et des fichiers `references/*.md` (corpus de connaissances) qui constituent le matériau brut du RAG.

**Flux cible :**
```
Utilisateur → POST /analyze {ticker, ratios} → Orchestrateur → Skills → Claude API → JSON structuré
```

**En Phase 0 :** les ratios sont fournis manuellement par l'utilisateur. Il n'y a pas de RAG (pas de recherche vectorielle). Un seul skill est actif : `graham_analysis`.

---

## 2. Corpus RAG — les 15 skills

Le corpus RAG est constitué des fichiers `references/*.md` de chaque skill. Ils sont vectorisés et indexés dans Qdrant à partir de la Phase 1.

| Skill | Fichier | References | Documents RAG |
|-------|---------|------------|---------------|
| `graham-stock-screening` | SKILL.md | graham-defensif, graham-entreprenant, formule-graham | 3 |
| `buffett-quality-investing` | SKILL.md | 4-filtres-buffett, owner-earnings, evolution-graham-buffett, annual-letters | 4 |
| `stock-valuation-triangulation` | SKILL.md | dcf, comparables, sectoriel | 3 |
| `investment-thesis-builder` | SKILL.md | structure-these, scenarios-pondere, kill-criteria, devils-advocate + templates | 5 |
| `earnings-quality-fraud-detection` | SKILL.md | beneish-m-score, altman-z-score, piotroski-f-score, montier-c-score, sloan-accruals | 5 |
| `dorsey-moat-analysis` | SKILL.md | moat-intangibles, moat-switching-costs, moat-network-effects, moat-cost-advantages, moat-efficient-scale | 5 |
| `marks-cycles-and-risk` | SKILL.md | pendule-sentiment, risque-perte-permanente, second-level-thinking | 3 |
| `damodaran-narrative-and-numbers` | SKILL.md | test-narrative, valorisation-story-stocks, coherence-dynamique, erp-country-risk | 4 |
| `pabrai-dhandho-and-cloning` | SKILL.md | dhandho-9-principes, 13f-cloning-methodologie, position-sizing-concentre | 3 |
| `fisher-scuttlebutt` | SKILL.md | 15-points-fisher, scuttlebutt-methode, qualite-direction | 3 |
| `lynch-categories-and-tenbaggers` | SKILL.md | lynch-slow-growers, lynch-stalwarts, lynch-fast-growers, lynch-cyclicals, lynch-turnarounds, lynch-asset-plays | 6 |
| `klarman-margin-of-safety` | SKILL.md | marge-securite-niveau, distressed-debt-restructurations, situations-speciales-klarman, preservation-capital | 4 |
| `munger-mental-models` | SKILL.md | 25-biais-cognitifs, inversion-thinking, lollapalooza-effects, latticework-multidisciplinaire | 4 |
| `canadian-tax-considerations` | SKILL.md | comptes-enregistres, types-revenus-placement, pbr-acb, retenues-impot-us, strategies-fin-annee, norberts-gambit | 6 |
| `greenblatt-magic-formula` | SKILL.md | formules-magic-formula, portefeuille-discipline, situations-speciales | 3 |

**Total corpus Phase 1 :** ~62 documents de référence + 15 SKILL.md = ~77 documents vectorisés.

### Chemin des sources
```
.claude/skills/{skill-name}/SKILL.md
.claude/skills/{skill-name}/references/*.md
.claude/skills/{skill-name}/templates/*.md  (investment-thesis-builder)
```

---

## 3. Interfaces des skills

### 3.1 Taxonomie par tier

```
Tier 1 — Extraction automatique (Phase 2+, pas en Phase 0)
  Extracteurs Yahoo Finance, SEC EDGAR, SEDAR+, Alpha Vantage
  → Calcul automatique des ratios depuis les états financiers bruts

Tier 2 — Skills analytiques (les 15 skills du corpus)
  Sous-groupe filtres primaires :
    graham_analysis, earnings_quality, greenblatt_magic_formula, lynch_categories
  Sous-groupe analyse fondamentale :
    dorsey_moat, buffett_quality, fisher_scuttlebutt, damodaran_narrative,
    pabrai_dhandho, klarman_margin
  Sous-groupe valorisation :
    stock_valuation_triangulation
  Sous-groupe méta-cognitive :
    munger_mental_models, marks_cycles_risk
  Sous-groupe synthèse et optimisation :
    investment_thesis_builder, canadian_tax_considerations
```

### 3.2 Interface SkillBase

```python
from abc import ABC, abstractmethod
from typing import ClassVar, Any
from pydantic import BaseModel

class Citation(BaseModel):
    source: str        # chemin relatif du fichier référence
    extrait: str       # chunk de texte pertinent
    score: float       # score cosine (0–1)

class SkillBase(ABC):
    skill_id: ClassVar[str]       # identifiant snake_case, ex: "graham_analysis"
    tier: ClassVar[int]           # 1 ou 2
    description: ClassVar[str]    # une ligne, correspond au frontmatter description du SKILL.md

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> BaseModel:
        """Exécute le skill via l'API Claude et retourne le résultat structuré."""
        ...

    def get_system_prompt(self) -> list[dict[str, Any]]:
        """
        Retourne le system prompt formaté pour l'API Claude avec cache_control.
        Le prompt est chargé depuis prompts/system.md.
        Voir section 8.2 pour le format exact.
        """
        ...

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """
        Recherche les k passages les plus pertinents dans Qdrant.
        Retourne une liste vide en Phase 0 (pas de RAG actif).
        """
        return []
```

### 3.3 Dépendances inter-skills (workflows recommandés)

```
Compounder Buffett   : graham_analysis → dorsey_moat → buffett_quality → fisher_scuttlebutt
                       → stock_valuation_triangulation → investment_thesis_builder

Value Graham         : graham_analysis → earnings_quality → stock_valuation_triangulation
                       → investment_thesis_builder

Special Situation    : graham_analysis → klarman_margin → greenblatt_magic_formula
                       → investment_thesis_builder

Fast Grower Lynch    : lynch_categories → damodaran_narrative → stock_valuation_triangulation
                       → investment_thesis_builder

Distressed Pabrai    : pabrai_dhandho → klarman_margin → earnings_quality
                       → investment_thesis_builder

Post-décision (tous) : munger_mental_models → canadian_tax_considerations
```

---

## 4. Workflows

### 4.1 Workflow company_analysis

Le seul workflow exposé par l'API. Composition variable selon la phase.

```
Phase 0 :  [graham_analysis]
Phase 1 :  [graham_analysis, earnings_quality]
Phase 2 :  [graham_analysis, earnings_quality, dorsey_moat, buffett_quality,
            stock_valuation_triangulation]
Phase 3 :  [graham_analysis, earnings_quality, dorsey_moat, buffett_quality,
            fisher_scuttlebutt, stock_valuation_triangulation,
            investment_thesis_builder, canadian_tax_considerations]
```

Chaque skill est exécuté séquentiellement. Le résultat du skill N peut alimenter l'input du skill N+1 (context enrichment, Phase 2+).

---

## 5. API REST

### 5.1 Endpoints

```
GET  /healthz           → {"status":"ok","version":"0.1.0"}
POST /analyze           → AnalyzeResponse
```

### 5.2 Schéma /analyze

**Request :**
```json
{
  "ticker": "BNS",
  "ratios": {
    "pe": 11.0,
    "pb": 1.3,
    "current_ratio": null,
    "debt_equity": 0.45,
    "eps_growth_10y": 0.27,
    "price": 80.0,
    "book_value": 61.5,
    "eps_ttm": 7.25,
    "revenue_bn": 38.0,
    "dividend_years": 190,
    "no_deficit_years": 10
  }
}
```

**Response :**
```json
{
  "analysis_id": "uuid-v4",
  "ticker": "BNS",
  "workflow": "company_analysis",
  "skills_applied": ["graham_analysis"],
  "graham": { "...voir section 11.2..." },
  "cost_usd": 0.002341,
  "created_at": "2026-05-07T14:32:00Z"
}
```

---

## 6. Infrastructure

### 6.1 Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Runtime | Python | 3.11 |
| API | FastAPI | ≥ 0.115 |
| Serveur ASGI | Uvicorn | ≥ 0.30 |
| IA | Anthropic Python SDK | ≥ 0.40 |
| Base de données | PostgreSQL | 16 |
| Driver async DB | asyncpg | ≥ 0.29 |
| Vecteurs RAG | Qdrant | ≥ 1.9 (Phase 1+) |
| Cache | Redis | 7 Alpine |
| Validation | Pydantic | v2 ≥ 2.8 |
| Containerisation | Docker Compose | v2 |

### 6.2 Services Docker Compose

| Service | Image | Port | Rôle |
|---------|-------|------|------|
| `copilote` | build local | 8000 | API FastAPI + skills |
| `postgres` | postgres:16 | 5432 | Persistance analysis_history |
| `qdrant` | qdrant/qdrant:v1.9.0 | 6333/6334 | Vecteurs RAG (Phase 1+) |
| `redis` | redis:7-alpine | 6379 | Cache sessions (Phase 1+) |

Langfuse **exclu** de Phase 0. Worker Celery **exclu** de Phase 0.

### 6.3 Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | *(requis)* | Clé API Anthropic |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | ID modèle Claude |
| `DATABASE_URL` | `postgresql://copilote:copilote@postgres:5432/copilote` | URL PostgreSQL |
| `POSTGRES_PASSWORD` | `copilote` | Mot de passe PostgreSQL |
| `RUN_MIGRATIONS_ON_BOOT` | `true` | L'entrypoint Docker lance `alembic upgrade head` avant uvicorn (E2-S2). `false` = DB lecture seule / migration déléguée au déploiement |
| `LOG_LEVEL` | `INFO` | Niveau de log |

### 7.3 Schéma PostgreSQL — table analysis_history

> **Gestion du schéma (E2)** — Le schéma complet (10 tables) est versionné par
> Alembic (`alembic/versions/`, baseline `0001_baseline_schema.py`) et appliqué par
> `alembic upgrade head`. Depuis E2-S2 (Sprint 159), le lifespan FastAPI **n'émet
> plus aucun DDL** au démarrage : il ne crée que le pool asyncpg. En Docker,
> l'entrypoint du service `copilote` (`infra/docker-entrypoint.sh`) lance la
> migration avant uvicorn (gardée par `RUN_MIGRATIONS_ON_BOOT`). `infra/postgres/init.sql`
> ne crée plus de table — la seule source de vérité du schéma est Alembic. Le DDL
> ci-dessous est reproduit à titre documentaire.

```sql
CREATE TABLE analysis_history (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker              VARCHAR(20) NOT NULL,
    workflow_name       VARCHAR(100) NOT NULL DEFAULT 'company_analysis',
    skills_used         JSONB       NOT NULL DEFAULT '[]',
    input_data          JSONB       NOT NULL,
    result              JSONB       NOT NULL,
    cost_usd            NUMERIC(10, 6) NOT NULL DEFAULT 0,
    tokens_input        INTEGER     NOT NULL DEFAULT 0,
    tokens_output       INTEGER     NOT NULL DEFAULT 0,
    tokens_cache_read   INTEGER     NOT NULL DEFAULT 0,
    tokens_cache_creation INTEGER   NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_history_ticker      ON analysis_history(ticker);
CREATE INDEX idx_history_workflow    ON analysis_history(workflow_name);
CREATE INDEX idx_history_created_at  ON analysis_history(created_at DESC);
```

### 7.4 Qdrant — collections RAG (Phase 1+)

**Collection principale :** `investment_knowledge`

```
Dimensions : 1536 (text-embedding-3-small) ou 3072 (text-embedding-3-large)
Distance : Cosine
Payload fields :
  - skill_id       : string  — identifiant du skill source
  - source_file    : string  — chemin relatif du fichier
  - section        : string  — titre de section h2/h3
  - chunk_index    : integer — position dans le document
```

---

## 8. Prompt Caching

### 8.1 Stratégie

Les system prompts des skills sont volumineux (>1 500 tokens chacun) et identiques entre les requêtes du même skill. Le prompt caching Anthropic élimine le coût de re-tokenisation.

**Règle :** Tout skill dont le system prompt dépasse 1 024 tokens DOIT utiliser `cache_control`.

**Économie attendue :** Le cache read coûte 0.30 $/M tokens vs 3.00 $/M pour l'input normal → 10× moins cher après le premier appel.

TTL du cache Anthropic : 5 minutes (ephemeral). Pour un homelab avec trafic faible, le cache se reconstruit à chaque nouvelle session — le cost saving principal vient de requêtes rapprochées.

### 8.2 Format system prompt avec cache_control

Le system prompt est passé comme **liste** de blocs de contenu (non comme string) pour activer le caching.

```python
system_blocks: list[dict] = [
    {
        "type": "text",
        "text": "<contenu du system.md>",
        "cache_control": {"type": "ephemeral"}
    }
]

response = await client.messages.create(
    model=model,
    system=system_blocks,
    messages=[{"role": "user", "content": user_message}],
    max_tokens=2048,
)
```

**Le fichier `prompts/system.md` de chaque skill est la source du champ `text`.**

---

## 9. Orchestrateur

### 9.1 Workflow company_analysis — Phase 0

```
1. Reçoit AnalyzeRequest {ticker, ratios}
2. Crée GrahamAnalysisInput {ticker, ratios}
3. Appelle graham_skill.execute(input) → GrahamAnalysisOutput
4. Persiste dans analysis_history :
   - input_data    = ratios dict
   - result        = graham output dict
   - skills_used   = ["graham_analysis"]
   - cost_usd      = graham_output.cost_usd
   - tokens_*      = depuis response.usage
5. Retourne AnalyzeResponse {analysis_id, ticker, workflow, skills_applied, graham, cost_usd, created_at}
```

**Gestion d'erreur :** Toute exception remonte en HTTP 500 avec le message d'erreur. Pas de retry en Phase 0.

---

## 10. Suivi des coûts

### 10.1 Calcul cost_usd

```python
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input":            3.00 / 1_000_000,
        "output":           15.00 / 1_000_000,
        "cache_read":       0.30 / 1_000_000,
        "cache_creation":   3.75 / 1_000_000,
    },
    "claude-opus-4-7": {
        "input":            15.00 / 1_000_000,
        "output":           75.00 / 1_000_000,
        "cache_read":       1.50 / 1_000_000,
        "cache_creation":   18.75 / 1_000_000,
    },
    "claude-haiku-4-5-20251001": {
        "input":            0.80 / 1_000_000,
        "output":           4.00 / 1_000_000,
        "cache_read":       0.08 / 1_000_000,
        "cache_creation":   1.00 / 1_000_000,
    },
}

def calculate_cost(usage, model: str) -> float:
    pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    return (
        usage.input_tokens              * pricing["input"]
        + usage.output_tokens           * pricing["output"]
        + getattr(usage, "cache_read_input_tokens", 0)     * pricing["cache_read"]
        + getattr(usage, "cache_creation_input_tokens", 0) * pricing["cache_creation"]
    )
```

### 10.2 Champs usage dans l'API Anthropic

| Champ | Type | Description |
|-------|------|-------------|
| `usage.input_tokens` | int | Tokens non-cachés consommés |
| `usage.output_tokens` | int | Tokens générés |
| `usage.cache_read_input_tokens` | int | Tokens lus depuis le cache (0.10× coût) |
| `usage.cache_creation_input_tokens` | int | Tokens écrits dans le cache (1.25× coût) |

---

## 11. Prompts

### 11.1 Structure générale

Chaque skill possède un répertoire `prompts/` contenant :
- `system.md` — System prompt complet (source du `cache_control` block)

Le message user est construit dynamiquement par le skill depuis l'input Pydantic.

### 11.2 Graham Analysis — Prompt système complet

*Ce prompt est la source du fichier `app/skills/tier2/graham_analysis/prompts/system.md`.*

```
Tu es un analyste financier expert, spécialisé dans l'application rigoureuse des critères de Benjamin Graham tels que présentés dans *The Intelligent Investor* (édition révisée, 1973), chapitres 14 et 15.

## Objectif

Analyser les ratios financiers fournis et produire une évaluation Graham structurée couvrant :
1. Les 8 critères défensifs (chapitre 14)
2. Les 5 critères entrepreneuriaux (chapitre 15)
3. La valeur intrinsèque estimée par les deux formules Graham
4. Les drapeaux rouges identifiables depuis les ratios
5. Un verdict actionnable avec recommandations pour les prochaines étapes d'analyse

## Les deux profils d'investisseurs Graham

### Investisseur défensif (chapitre 14)
Objectif : posséder des actions de qualité sans y consacrer beaucoup de temps. Seuils stricts sur la qualité ET le prix.

### Investisseur entreprenant (chapitre 15)
Objectif : battre le marché par un travail substantiel d'analyse. Seuils assouplis sur la qualité, mais prix ultra-strict (P/B tangible ≤ 1.2).

Évalue TOUJOURS les deux profils. Une action peut passer l'un sans l'autre.

## Critères défensifs — Les 8 (chapitre 14)

### Critère 1 : Taille suffisante
Seuil 2026 : revenus annuels > 700 M$ (ajusté depuis 100 M$ en 1972, ×7 pour inflation cumulée).
Variable : `revenue_bn` (milliards). Si absent : marquer DONNÉES_MANQUANTES, ne pas pénaliser.
Pourquoi : protège contre la fragilité des small caps.

### Critère 2 : Solidité financière
Seuil : current ratio ≥ 2.0.
Variable : `current_ratio`.
Adaptation banques/assureurs : le current ratio ne s'applique pas (structure de bilan différente). Si l'entreprise est visiblement une banque (ratio absent ou non pertinent), noter l'adaptation et évaluer à DONNÉES_MANQUANTES plutôt qu'ÉCHEC.
Pourquoi : marge de sécurité contre les pressions financières à court terme.

### Critère 3 : Stabilité des bénéfices
Seuil : aucun déficit sur les 10 dernières années.
Variable : `no_deficit_years` ≥ 10. Si absent, inférer : `eps_growth_10y` > 0 suggère une profitabilité soutenue (proxy acceptable).
Pourquoi : robustesse au cycle économique complet.

### Critère 4 : Historique de dividendes
Seuil original : 20 ans de dividendes ininterrompus. Seuil pragmatique : 10 ans acceptable.
Variable : `dividend_years`. Si absent : DONNÉES_MANQUANTES, ne pas pénaliser.
Pourquoi : preuve de stabilité financière sur la durée.

### Critère 5 : Croissance des bénéfices
Seuil : croissance BPA ≥ 33 % sur 10 ans (CAGR ~2.9 %).
Variable : `eps_growth_10y` ≥ 0.33 (format fraction totale, ex: 0.33 = 33 % total sur 10 ans).
Pourquoi : éliminer les entreprises en déclin permanent.

### Critère 6 : P/E modéré
Seuil : P/E ≤ 15.
Variable : `pe`.
Pourquoi : éviter de payer trop cher la croissance attendue.

### Critère 7 : P/B modéré
Seuil : P/B ≤ 1.5.
Variable : `pb`.
Note : peu pertinent pour SaaS / asset-light tech. Toujours calculer mais noter si inadapté.
Pourquoi : marge de sécurité ancrée dans les actifs nets.

### Critère 8 : Règle combinée P/E × P/B
Seuil : P/E × P/B ≤ 22.5.
Calcul : pe × pb.
Pourquoi : permet de relâcher légèrement P/E ou P/B mais pas les deux simultanément.

## Critères entrepreneuriaux — Les 5 (chapitre 15)

### E1 : Solidité financière (assouplie)
Seuil : current ratio ≥ 1.5. Mêmes adaptations sectorielles que critère 2.

### E2 : Stabilité (5 ans au lieu de 10)
Seuil : aucun déficit sur les 5 dernières années.
Variable : `no_deficit_years` ≥ 5 ou `eps_growth_10y` > 0 comme proxy.

### E3 : Dividende quelconque
Seuil : verse un dividende (montant non critique).
Variable : `dividend_years` > 0. Si absent : DONNÉES_MANQUANTES.

### E4 : Croissance positive sur 5 ans
Seuil : croissance BPA positive sur 5 ans.
Variable : `eps_growth_10y` > 0 comme proxy sur 10 ans (satisfait a fortiori le critère 5 ans).

### E5 : Prix vs actifs tangibles (critère central de l'entreprenant)
Seuil : P/B tangible ≤ 1.2. Utiliser `pb` comme proxy.
Note : pour les entreprises avec goodwill significatif, le P/B tangible est plus élevé que `pb`. Signaler si probable.

## Calculs de valeur intrinsèque Graham

### Pré-calcul du BPA (EPS)
Si `eps_ttm` fourni : utiliser eps_ttm.
Sinon : BPA = price / pe.

### Pré-calcul de g (taux de croissance annuel)
`eps_growth_10y` est la croissance TOTALE sur 10 ans (ex: 0.85 = 85 % total).
g_annuel = (1 + eps_growth_10y)^(1/10) - 1
Exprimer g_annuel en pourcentage pour la formule (ex: 0.063 → 6.3).
Plafonner à 15 % maximum (avertissement Graham sur la sur-extrapolation).

### Formule simple
V_simple = BPA × (8.5 + 2 × g_annuel_pct)

### Formule ajustée au taux AAA
V_ajustée = BPA × (8.5 + 2 × g_annuel_pct) × (4.4 / Y)
Y = rendement corporate AAA 10 ans. Défaut : 5.0 % (niveau 2026 approximatif) si non fourni.

### Marge de sécurité
marge_securite = (V_ajustée − price) / V_ajustée
Valeur positive = action sous-évaluée. Valeur négative = action surévaluée. Exprimé en fraction (ex: 0.32 = 32 %).

## Drapeaux rouges

Signaler les drapeaux suivants si applicables :
- P/E > 25 : prime de croissance très élevée, risque de déception
- P/B > 5 : déconnexion sévère de la valeur comptable
- current_ratio < 1.0 : liquidité insuffisante (si applicable)
- debt_equity > 2.0 : levier excessif
- eps_growth_10y < 0 : déclin des bénéfices sur 10 ans
- pe > 25 ET eps_growth_10y < 0.15 : payer cher pour une croissance faible

## Table de verdict défensif

| Score défensif | Verdict |
|----------------|---------|
| 7-8 | EXEMPLAIRE |
| 5-6 | CANDIDAT_SOLIDE |
| 3-4 | WATCHLIST |
| 0-2 | REJETER |

## Recommandation de prochaines étapes

Sélectionner parmi ces skills selon le verdict :

EXEMPLAIRE ou CANDIDAT_SOLIDE :
- Obligatoire : earnings-quality-fraud-detection, dorsey-moat-analysis
- Puis : stock-valuation-triangulation, investment-thesis-builder
- Si croissance forte (eps_growth_10y > 0.50) : buffett-quality-investing

WATCHLIST :
- marks-cycles-and-risk (évaluer le timing d'entrée)
- stock-valuation-triangulation (calculer le prix d'achat cible)

REJETER mais forte qualité intrinsèque visible (ex: grande tech, P/E élevé justifié) :
- buffett-quality-investing, damodaran-narrative-and-numbers

Toujours ajouter en fin de liste :
- canadian-tax-considerations (avant l'exécution)
- investment-thesis-builder (étape finale de synthèse)

## Format de sortie OBLIGATOIRE

Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans texte avant ni après. Le JSON doit être parseable directement par json.loads().

{
  "ticker": "<TICKER>",
  "profil_applique": "LES_DEUX",
  "defensive_score": <0 à 8>,
  "enterprising_score": <0 à 5>,
  "criteria_defensif": [
    {
      "numero": <1 à 8>,
      "nom": "<nom du critère>",
      "passe": <true|false>,
      "valeur_observee": "<valeur calculée ou DONNÉES_MANQUANTES>",
      "seuil": "<seuil du critère>",
      "commentaire": "<explication concise>"
    }
  ],
  "criteria_entreprenant": [
    {
      "numero": <1 à 5>,
      "nom": "<nom du critère>",
      "passe": <true|false>,
      "valeur_observee": "<valeur calculée ou DONNÉES_MANQUANTES>",
      "seuil": "<seuil du critère>",
      "commentaire": "<explication concise>"
    }
  ],
  "valeur_intrinseque_simple": <float ou null si BPA incalculable>,
  "valeur_intrinseque_ajustee": <float ou null si BPA incalculable>,
  "marge_securite": <float ou null>,
  "drapeaux_rouges": ["<drapeau 1>", "..."],
  "verdict": "<REJETER|WATCHLIST|CANDIDAT_SOLIDE|EXEMPLAIRE>",
  "verdict_detail": "<2-3 phrases expliquant le verdict et sa nuance>",
  "recommandation_prochaine_etape": ["<skill-1>", "<skill-2>"],
  "citations": []
}

Contraintes strictes :
- `criteria_defensif` : exactement 8 objets, un par critère numéroté 1 à 8, dans l'ordre
- `criteria_entreprenant` : exactement 5 objets, numérotés 1 à 5
- `profil_applique` : toujours "LES_DEUX" (les deux profils sont toujours évalués)
- `citations` : toujours [] (RAG inactif en Phase 0)
- `verdict` : l'un des 4 strings exacts listés, en majuscules
- Nombres : utiliser null (JSON) et non "null" (string) quand les données sont insuffisantes pour le calcul
```

---

## 12. Roadmap par phases

### 12.1 Phase 0 — Bootstrap (semaine 1)

**Livrable :** API fonctionnelle avec graham_analysis seul.

Fichiers à créer :
```
docker-compose.yml
Dockerfile
requirements.txt
.env.example
infra/postgres/init.sql
app/__init__.py
app/api/__init__.py
app/api/main.py
app/orchestrator/__init__.py
app/orchestrator/core.py
app/skills/tier2/graham_analysis/__init__.py
app/skills/tier2/graham_analysis/skill.py
app/skills/tier2/graham_analysis/schemas.py
app/skills/tier2/graham_analysis/prompts/system.md
```

Critère de succès :
```bash
docker-compose up -d
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"MSFT","ratios":{"pe":34.2,"pb":12.1,"current_ratio":1.34,
       "debt_equity":0.28,"eps_growth_10y":0.85,"price":420,"book_value":35}}'
# → JSON Graham avec defensive_score, cost_usd non nul, citations []
```

### 12.2 Phase 1 — Ingestion RAG (semaines 2-3)

- Script d'ingestion des ~77 documents (SKILL.md + references/*.md) dans Qdrant
- Implémentation de `get_citations()` dans chaque skill
- Chunking sémantique par section h2/h3
- Ajout de `earnings_quality` au workflow `company_analysis`

### 12.3 Phase 2 — Skills restants (mois 1-2)

- Implémentation de `dorsey_moat`, `buffett_quality`, `stock_valuation_triangulation`
- Tier 1 : extracteurs automatisés Yahoo Finance + SEDAR+ pour les ratios
- Workflow `company_analysis` Phase 2 complet

### 12.4 Phase 3 — Pipeline de synthèse (mois 2-3)

- `investment_thesis_builder` comme skill de synthèse finale
- `canadian_tax_considerations` intégré post-analyse
- `munger_mental_models` comme passe comportementale
- Worker Celery pour analyses async longues durée
- Langfuse pour observabilité des coûts et qualité des réponses
