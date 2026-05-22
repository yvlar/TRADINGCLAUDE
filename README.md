# TradingClaude — Copilote Financier IA

[![Backend — pytest](https://github.com/yvlar/TRADINGCLAUDE/actions/workflows/ci.yml/badge.svg?branch=master&job=Backend+—+pytest)](https://github.com/yvlar/TRADINGCLAUDE/actions/workflows/ci.yml)
[![Frontend — Vitest](https://github.com/yvlar/TRADINGCLAUDE/actions/workflows/ci.yml/badge.svg?branch=master&job=Frontend+—+Vitest)](https://github.com/yvlar/TRADINGCLAUDE/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Version](https://img.shields.io/badge/version-8.4.0-green)

API d'analyse d'investissement multi-frameworks construite avec FastAPI, Claude (Anthropic),
PostgreSQL, Redis et un frontend React 18.

Analyse les actions selon **18 frameworks académiques** (Graham, Buffett, Dorsey, Lynch, ESG, etc.),
expose une API REST complète avec watchlist, screener, alertes, exports PDF/Excel et un tableau
de bord en temps réel.

**Version :** 8.4.0 — Phase 3 (Pipeline de synthèse)  
**Tests :** 1 371 CI verts · 192 Vitest verts

---

## Démarrage rapide

### Prérequis

- Docker + Docker Compose
- Node.js 18+ (frontend)
- Clé API Anthropic (`ANTHROPIC_API_KEY`)

### Installation

```bash
# 1. Copier et remplir les variables d'environnement
cp .env.example .env
# Éditer .env — au minimum : ANTHROPIC_API_KEY=sk-ant-...

# 2. Démarrer l'infrastructure (5 services)
docker-compose up -d

# 3. Vérifier l'API
curl localhost:8000/healthz
# → {"status": "ok", "postgres": "ok", "qdrant": "ok"}

# 4. Démarrer le frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

---

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Clé API Claude |
| `CLAUDE_MODEL` | — | Défaut : `claude-sonnet-4-6` |
| `DATABASE_URL` | — | PostgreSQL (défaut Docker Compose) |
| `REDIS_URL` | — | Redis (défaut Docker Compose) |
| `API_KEY` | — | Bearer token auth (vide = pas d'auth) |
| `QDRANT_URL` | — | Vector store RAG (optionnel) |
| `OPENAI_API_KEY` | — | Embeddings RAG (optionnel) |
| `LANGFUSE_SECRET_KEY` | — | Traces LLM (optionnel) |
| `WEBHOOK_URL` | — | Notifications webhook (optionnel) |
| `SLACK_WEBHOOK_URL` | — | Alertes Slack (optionnel) |
| `CLAUDE_TIMEOUT_S` | — | Timeout appels Claude, défaut `60` |

Voir `.env.example` pour la liste complète.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Frontend React 18 + TypeScript  :5173       │
│  9 pages : Analyze · Screener · History      │
│            Watchlist · Dashboard · Admin     │
│            Comparer · ESG · Login            │
└─────────────────┬───────────────────────────┘
                  │ proxy Vite → :8000
┌─────────────────▼───────────────────────────┐
│  FastAPI  :8000                              │
│  ┌──────────────────────────────────────┐   │
│  │  Orchestrator (workflows multi-steps) │   │
│  │  18 Skills : 16 Tier2 + 2 Tier1      │   │
│  │  Cache Redis · RAG Qdrant (opt.)     │   │
│  └──────────────────────────────────────┘   │
│  Celery workers (tâches planifiées)          │
└──────┬──────────────────────┬───────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────┐
│ PostgreSQL  │    │  Redis + Qdrant  │
│ (analyses,  │    │  (cache, broker, │
│  watchlist, │    │   vectors RAG)   │
│  history…)  │    └─────────────────┘
└─────────────┘
```

**Services Docker Compose :** `copilote` · `postgres` · `redis` · `qdrant` · `celery`

---

## Les 18 skills d'analyse

### Tier 2 — Frameworks académiques (appels Claude)

| Skill | Auteur / Source |
|-------|----------------|
| `graham_analysis` | Benjamin Graham — *The Intelligent Investor* |
| `earnings_quality` | Beneish M-Score · Altman Z-Score · Piotroski F-Score |
| `dorsey_moat` | Pat Dorsey — *The Little Book That Builds Wealth* |
| `buffett_quality` | Warren Buffett — 4 filtres + owner earnings |
| `stock_valuation_triangulation` | DCF + multiples comparables + SOTP |
| `investment_thesis_builder` | Synthèse multi-frameworks + kill criteria |
| `munger_mental_models` | Charlie Munger — 25 biais + inversion |
| `canadian_tax_considerations` | CELI · REER · CELIAPP · fiscalité QC/CA |
| `lynch_categories` | Peter Lynch — 6 catégories + PEG ratio |
| `fisher_scuttlebutt` | Phil Fisher — 15 points + scuttlebutt |
| `klarman_margin` | Seth Klarman — marge de sécurité absolue |
| `greenblatt` | Joel Greenblatt — Magic Formula (ROC + Earnings Yield) |
| `damodaran_narrative` | Aswath Damodaran — narrative vs numbers |
| `marks_cycles` | Howard Marks — pendule sentiment + cycles |
| `pabrai_dhandho` | Mohnish Pabrai — 9 principes Dhandho |
| `esg_simplified` | 15 critères ESG proxy (5E + 5S + 5G) |

### Tier 1 — Extracteurs de données (sans Claude)

| Skill | Source |
|-------|--------|
| `yahoo_finance_extractor` | Yahoo Finance (yfinance) |
| `sedar_plus_extractor` | SEDAR+ (documents canadiens) |

---

## Endpoints principaux

### Analyse

```bash
POST /analyze          # Analyse complète (sync)
POST /analyze-stream   # Analyse en streaming SSE skill par skill
POST /screen           # Screener multi-tickers (2–20 tickers)
GET  /extract?ticker=  # Extraction automatique ratios Yahoo Finance
```

### Watchlist

```bash
GET    /watchlist                           # Lister les positions
POST   /watchlist                           # Ajouter un ticker
DELETE /watchlist/{id}                      # Supprimer
PATCH  /watchlist/{id}/esg-threshold        # Configurer seuil ESG
PATCH  /watchlist/{id}/price-threshold      # Configurer seuil de prix (%)
GET    /watchlist/esg-scores                # Scores ESG triés
GET    /watchlist/export.xlsx               # Export Excel enrichi
GET    /watchlist/export.pdf                # Export PDF
```

### Historique et annotations

```bash
GET  /history                    # Historique cursor (rétrocompat)
GET  /history-paged              # Pagination offset/limit + total_count
POST /annotations                # Annoter une analyse
GET  /annotations                # Lire annotations par ticker
GET  /annotations/export.csv     # Export CSV
GET  /annotations/export.xlsx    # Export Excel
```

### Comparaison et ESG

```bash
POST /compare                    # Comparer 2–5 tickers (sans appel Claude)
GET  /esg-history/{ticker}       # Historique scores ESG
GET  /monthly-report             # Rapport PDF mensuel
GET  /screener-report            # Rapport PDF screener
GET  /ticker-report/{ticker}     # Rapport PDF par ticker (90 jours)
```

### Observabilité

```bash
GET /healthz
GET /telemetry/summary|costs|cache|latency
GET /telemetry/eval-drift
GET /metrics?days=30
```

### Administration

```bash
POST   /admin/keys      # Créer une clé API
GET    /admin/keys      # Lister les clés
DELETE /admin/keys/{id} # Révoquer une clé
```

---

## Tâches planifiées (Celery beat)

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| Screener watchlist | Dimanche 11h00 UTC | Analyse tous les tickers + webhook |
| Rapport mensuel PDF | 1er du mois 08h00 UTC | PDF global + section ESG + Slack |
| Alerte prix | En continu | Alerte si écart > `price_alert_threshold_pct` |
| Alerte ESG | En continu | Alerte si baisse > `esg_alert_threshold` |

---

## Frontend React

**SPA React 18 + TypeScript strict** — port 5173

| Page | Fonctionnalité |
|------|---------------|
| Analyze | Saisie ticker, auto-fill Yahoo Finance, streaming SSE skill par skill |
| Screener | Batch 2–20 tickers, tableau trié par composite score |
| History | Historique paginé, filtre dates, recherche full-text, export PDF |
| Watchlist | Positions surveillées, seuils ESG/Prix configurables inline, exports |
| Dashboard | Métriques WebSocket, graphique composite multi-tickers, eval drift |
| ESG | Scores ESG watchlist, graphique historique par ticker |
| Comparer | Tableau multi-skills côte à côte pour 2–5 tickers |
| Admin | Gestion clés API |
| Login | Auth Bearer token |

```bash
cd frontend
npm install
npm run dev      # dev :5173
npm run build    # production
npx vitest run   # 192 tests
```

---

## Développement et tests

```bash
# Tests backend (sans Docker, sans clé Claude)
python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
# → 1 371 passed

# Tests frontend
cd frontend && npx vitest run
# → 192 passed

# Logs Docker
docker-compose logs -f copilote

# Rebuild après modification
docker-compose up -d --build copilote
```

---

## Authentification

Si `API_KEY` est défini dans `.env`, toutes les routes (sauf `/healthz`, `/docs`, `/telemetry/*`)
nécessitent :

```bash
curl -H "Authorization: Bearer <api_key>" -X POST localhost:8000/analyze ...
```

Multi-utilisateurs supporté via `POST /admin/keys` (Sprint 62).  
Rétrocompatibilité : la variable `API_KEY` env reste fonctionnelle.

---

## RAG (Base de connaissances)

Si `OPENAI_API_KEY` est présent, le service active la recherche vectorielle dans Qdrant.
Le corpus contient ~67 documents de référence couvrant les 16 frameworks Tier 2.

```bash
# Ingestion des documents
python scripts/ingest_rag.py --path .claude/skills/
```

---

*Dernière mise à jour : 2026-05-22 — Yves Larivière / TradingClaude — v8.4.0*
