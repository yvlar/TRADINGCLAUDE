# Copilote Financier IA

![CI](https://github.com/ylariviere/tradingClaude/actions/workflows/ci.yml/badge.svg)

API d'analyse d'investissement multi-frameworks construite avec FastAPI, Claude (Anthropic) et Redis.
Analyse des actions selon 15 cadres académiques (Graham, Buffett, Dorsey, Lynch, etc.) et expose
une API REST complète avec cache, screener multi-tickers et observabilité avancée.

**Version :** 2.6.0 — Phase 3 (Pipeline de synthèse complet + CI/CD GitHub Actions)

---

## Démarrage rapide

### Prérequis
- Docker + Docker Compose
- Clé API Anthropic (`ANTHROPIC_API_KEY`)

### Installation

```bash
# 1. Copier et remplir les variables d'environnement
cp .env.example .env
# Éditer .env et ajouter ANTHROPIC_API_KEY=sk-ant-...

# 2. Démarrer l'infrastructure complète
docker-compose up -d

# 3. Vérifier que le service est opérationnel
curl localhost:8000/healthz
# → {"status": "ok", "version": "2.0.0", "postgres": "ok", "qdrant": "ok"}
```

---

## Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|----------|-------------|--------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | — | Clé API Claude |
| `DATABASE_URL` | — | `postgresql://copilote:copilote@postgres:5432/copilote` | PostgreSQL |
| `REDIS_URL` | — | `redis://redis:6379/0` | Broker Celery + cache + observabilité |
| `API_KEY` | — | *(vide = pas d'auth)* | Bearer token pour sécuriser l'API |
| `CLAUDE_MODEL` | — | `claude-sonnet-4-6` | Modèle Anthropic |
| `QDRANT_URL` | — | `http://qdrant:6333` | Vector store RAG (optionnel) |
| `OPENAI_API_KEY` | — | — | Embeddings RAG (optionnel) |
| `LANGFUSE_SECRET_KEY` | — | — | Traces Langfuse (optionnel) |
| `LANGFUSE_PUBLIC_KEY` | — | — | Requis si `LANGFUSE_SECRET_KEY` présent |
| `ANALYSIS_CACHE_TTL` | — | `86400` | TTL cache analyses Redis (secondes) |
| `COST_ALERT_THRESHOLD_USD` | — | `1.0` | Seuil d'alerte coût journalier (USD) |
| `CLAUDE_TIMEOUT_S` | — | `60` | Timeout appels Claude (secondes) |
| `CLAUDE_MAX_RETRIES` | — | `3` | Retries sur erreur 429/529 |

---

## Endpoints API

### Santé

```bash
GET /healthz
# → {"status": "ok", "version": "2.0.0", "postgres": "ok", "qdrant": "ok"}
```

### Analyse d'action (sync)

```bash
POST /analyze
Content-Type: application/json

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
    "revenue_bn": 38,
    "dividend_years": 190
  },
  "workflow": "value_graham"
}
```

**Champs optionnels pour activer des skills supplémentaires :**
- `earnings_ratios` → skill `earnings_quality`
- `dorsey_ratios` → skill `dorsey_moat`
- `buffett_ratios` → skill `buffett_quality`
- `valuation_ratios` → skill `stock_valuation_triangulation`
- `thesis_ratios: true` → skill `investment_thesis_builder`
- `munger_ratios: true` → skill `munger_mental_models` (nécessite `thesis_ratios`)
- `tax_input` → skill `canadian_tax_considerations`
- `lynch_ratios` → skill `lynch_categories`
- `fisher_input` → skill `fisher_scuttlebutt`
- `klarman_input` → skill `klarman_margin`
- `greenblatt_input` → skill `greenblatt_magic_formula`
- `damodaran_input` → skill `damodaran_narrative`
- `marks_input` → skill `marks_cycles_risk`
- `pabrai_input` → skill `pabrai_dhandho`

### Analyse async (Celery)

```bash
POST /analyze-async   → {"job_id": "uuid"}
GET  /jobs/{job_id}   → {"status": "done", "result": {...}}
```

### Screener multi-tickers

```bash
POST /screen
{
  "tickers": ["BNS", "TD", "RY"],
  "workflow": "value_graham",
  "ratios_map": {
    "BNS": {"pe": 11.0, "pb": 1.3, ...},
    "TD":  {"pe": 12.5, "pb": 1.4, ...},
    "RY":  {"pe": 13.0, "pb": 1.8, ...}
  },
  "max_parallel": 5
}
# → classement par defensive_score décroissant
```

### Extraction automatique de ratios

```bash
GET /extract?ticker=BNS
# → GrahamRatios extraits de Yahoo Finance
```

### Historique et métriques

```bash
GET /history?ticker=BNS&limit=10
GET /metrics?days=30
```

### Invalidation du cache

```bash
DELETE /cache/{ticker}
# → {"invalidated": 3}
```

### Observabilité (Sprint 18)

```bash
# Résumé global
GET /telemetry/summary?days=30
# → {"cost_total_usd": 0.42, "analyses_count": 18,
#    "cache_hit_ratio": 0.73, "latency_p95_ms": 3200,
#    "alerte_cout_active": false}

# Coûts journaliers
GET /telemetry/costs?days=7
# → [{"date": "2026-05-08", "cost_usd": 0.12}, ...]

# Statistiques cache Redis
GET /telemetry/cache
# → {"hits": 54, "misses": 20, "hit_ratio": 0.73, "keys_count": 12}

# Latences par skill
GET /telemetry/latency?skill_id=graham_analysis
# → {"skill_id": "graham_analysis", "p50_ms": 1800, "p95_ms": 3200,
#    "p99_ms": 4100, "sample_count": 42}
```

> Les endpoints `/telemetry/*` sont exemptés d'authentification (lecture seule).

---

## CLI en ligne de commande

```bash
# Analyse avec ratios en ligne de commande
python scripts/analyze_cli.py BNS \
    --pe 11.0 --pb 1.3 --price 80.0 \
    --debt-equity 0.45 --eps-growth-10y 0.27

# Analyse depuis un fichier JSON
python scripts/analyze_cli.py BNS \
    --ratios-file data/bns_ratios.json

# Avec thesis et Munger
python scripts/analyze_cli.py BNS \
    --ratios-file data/bns_full.json --thesis --munger

# Sortie stdout (pour redirection)
python scripts/analyze_cli.py BNS \
    --ratios-file data/bns.json --stdout > rapport.md
```

Le rapport est sauvegardé dans `analyses/{TICKER}-{YYYY-MM}.md`.

---

## Les 15 skills d'analyse

| Skill | Source académique | Input requis |
|-------|------------------|-------------|
| `graham_analysis` | Benjamin Graham — *The Intelligent Investor* | `ratios` (GrahamRatios) |
| `earnings_quality` | Beneish M-Score, Altman Z-Score, Piotroski F-Score | `earnings_ratios` |
| `dorsey_moat` | Pat Dorsey — *The Little Book That Builds Wealth* | `dorsey_ratios` |
| `buffett_quality` | Warren Buffett — 4 filtres + owner earnings | `buffett_ratios` |
| `stock_valuation_triangulation` | DCF + comparables + sectoriel | `valuation_ratios` |
| `investment_thesis_builder` | Synthèse multi-frameworks | `thesis_ratios: true` |
| `munger_mental_models` | Charlie Munger — 25 biais cognitifs + inversion | `munger_ratios: true` |
| `canadian_tax_considerations` | CELI/REER/CELIAPP, fiscalité QC/CA | `tax_input` |
| `lynch_categories` | Peter Lynch — 6 catégories + PEG | `lynch_ratios` |
| `fisher_scuttlebutt` | Phil Fisher — 15 points + scuttlebutt | `fisher_input` |
| `klarman_margin` | Seth Klarman — marge de sécurité absolue | `klarman_input` |
| `greenblatt_magic_formula` | Joel Greenblatt — ROC + Earnings Yield | `greenblatt_input` |
| `damodaran_narrative` | Aswath Damodaran — narrative vs chiffres | `damodaran_input` |
| `marks_cycles_risk` | Howard Marks — pendule sentiment + cycles | `marks_input` |
| `pabrai_dhandho` | Mohnish Pabrai — 9 principes Dhandho | `pabrai_input` |

---

## Architecture

```
[Client] → POST /analyze
              ↓
         [Cache Redis]  →  hit → réponse immédiate
              ↓ miss
         [Orchestrator]
              ↓
         [Skills Tier 2]  →  [Claude API] (prompt caching)
              ↓                    ↓
         [Observabilité]     [RAG Qdrant] (optionnel)
              ↓
         [PostgreSQL]  →  analysis_history
```

**Services Docker :**
- `copilote` : API FastAPI + workers Celery
- `postgres` : historique des analyses
- `qdrant` : vecteurs RAG (optionnel)
- `redis` : broker Celery + cache analyses + rate limiting + observabilité

---

## Développement et tests

```bash
# Installation des dépendances de développement
pip install -r requirements-dev.txt

# Lancer la suite de tests complète (sans Docker)
pytest tests/ -v --tb=short -q
# → 751+ passed, 1 xfail

# Tests smoke tests de charge (sans service réel)
pytest tests/test_load_smoke.py -v
# → 6 tests verts

# Tests d'observabilité uniquement
pytest tests/test_observability.py tests/test_telemetry.py -v

# Tests de schémas Pydantic
pytest tests/test_schemas.py -v

# Reconstruire l'image après modification du code
docker-compose up -d --build copilote

# Logs en temps réel
docker-compose logs -f copilote

# Consulter les dernières analyses persistées
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT ticker, workflow_name, cost_usd, created_at
      FROM analysis_history ORDER BY created_at DESC LIMIT 10;"
```

---

## Rapports PDF (Sprint 20)

Génération automatique d'un rapport PDF structuré depuis le résultat d'une analyse.

### Générer un rapport PDF

```bash
# Déclenche une analyse et télécharge directement le PDF
curl -X POST localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "BNS",
    "ratios": {
      "pe": 11.0,
      "pb": 1.3,
      "current_ratio": null,
      "debt_equity": 0.45,
      "eps_growth_10y": 0.27,
      "price": 80.0,
      "book_value": 61.5
    }
  }' \
  --output BNS-rapport.pdf
# → BNS-rapport.pdf créé, lisible dans n'importe quel lecteur PDF
```

### Régénérer depuis l'historique

```bash
# Récupère une analyse déjà persistée et génère son PDF
curl localhost:8000/report/550e8400-e29b-41d4-a716-446655440000 \
  --output BNS-archive.pdf
# → 404 si l'analysis_id est inconnu
```

### Structure du rapport

Le PDF inclut dans l'ordre : page de garde, résumé exécutif, section Graham (toujours présente), puis les sections optionnelles pour chaque skill appliqué (Earnings Quality, Dorsey Moat, Buffett, Valorisation, Thèse, Fiscalité, Lynch, Fisher, Klarman, Greenblatt, Damodaran, Marks, Pabrai).

**Couleurs sémantiques :** vert (#2E7D32) pour les verdicts positifs, rouge (#C62828) pour les négatifs, gris (#616161) pour les neutres.

> L'endpoint `/report` est exempté d'authentification (même politique que `/telemetry`).

---

## Tests de charge (Sprint 19)

Validation de la capacité de l'API sous charge réaliste avec [Locust](https://locust.io/).

### Prérequis

```bash
pip install -r requirements-dev.txt   # locust >= 2.20.0 inclus
docker-compose up -d                  # API + Redis + PostgreSQL
curl localhost:8000/healthz           # vérifier {"status": "ok"}
```

### Lancer les tests de charge

```bash
# Palier 10 utilisateurs — test de référence (p95 /analyze < 5 000 ms)
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 10 -r 2 --run-time 2m \
  --csv tests/load/results_10u

# Palier 50 utilisateurs — test de stress (p95 /analyze < 15 000 ms)
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 50 -r 5 --run-time 2m \
  --csv tests/load/results_50u

# Interface web interactive
locust -f tests/load/locustfile.py --host http://localhost:8000
# → ouvrir http://localhost:8089
```

### Critères de succès

| Utilisateurs | p95 /analyze | p95 /screen | Taux erreur |
|-------------|-------------|-------------|-------------|
| 10 | < 5 000 ms | < 15 000 ms | < 1 % |
| 25 | < 8 000 ms | < 20 000 ms | < 2 % |
| 50 | < 15 000 ms | < 30 000 ms | < 5 % |

Voir [tests/load/README.md](tests/load/README.md) pour les instructions complètes.

---

## Authentification

Si `API_KEY` est défini dans `.env`, toutes les requêtes (sauf `/healthz`, `/docs`, `/telemetry/*`)
nécessitent un header :

```bash
curl -H "Authorization: Bearer <votre_api_key>" \
     -X POST localhost:8000/analyze ...
```

Rate limiting : 10 requêtes/minute par IP (configurable via Redis).

---

## RAG (Knowledge Base)

Si `OPENAI_API_KEY` est présent, le service active la recherche RAG dans Qdrant.
Les 15 skills chargent automatiquement leurs références depuis la collection `investment_knowledge`.

```bash
# Ingestion des documents de référence dans Qdrant
python scripts/ingest_rag.py --path .claude/skills/
```

---

## Historique des sprints

| Sprint | Fonctionnalité | Statut |
|--------|---------------|--------|
| Phase 0 | API FastAPI + graham_analysis + PostgreSQL | ✅ |
| Sprint 1-4 | Infrastructure RAG, earnings_quality, métriques | ✅ |
| Sprint 5 | dorsey_moat | ✅ |
| Sprint 6 | buffett_quality | ✅ |
| Sprint 7 | stock_valuation_triangulation | ✅ |
| Sprint 8 | Extracteurs Tier 1 (Yahoo Finance, SEDAR+) | ✅ |
| Sprint 9 | investment_thesis_builder | ✅ |
| Sprint 10 | munger_mental_models + canadian_tax | ✅ |
| Sprint 11 | Robustesse production (Celery, auth, rate limit) | ✅ |
| Sprint 12 | CLI Markdown + décisions embedding | ✅ |
| Sprint 13 | Suite de tests pytest complète | ✅ |
| Sprint 14 | lynch_categories + fisher_scuttlebutt + klarman_margin | ✅ |
| Sprint 15 | greenblatt + damodaran + marks_cycles + pabrai_dhandho | ✅ |
| Sprint 17 | Screener multi-tickers + Cache Redis analyses | ✅ |
| Sprint 18 | Observabilité avancée — /telemetry + alertes coût | ✅ |
| Sprint 19 | Tests de charge (locust) | ✅ |
| **Sprint 20** | **Rapport PDF automatique** | **✅** |

---

*Dernière mise à jour : 2026-05-09 — Yves Larivière / TradingClaude*
