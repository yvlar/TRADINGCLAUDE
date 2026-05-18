# Sprint 74 — à définir
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# ROLE

Tu es un developpeur full-stack senior specialiste React + FastAPI **ET ingenieur IA applique**.
Tu maitrises Python, FastAPI, asyncpg, Pydantic v2, Celery, Redis, PostgreSQL,
React 18, TypeScript strict, Vitest et les patterns de tests automatises.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

1. `ROADMAP.md` -- etat courant, sprint actif, historique des decisions
2. `app/skills/base.py` -- SkillBase, pattern commun a tous les skills tier2
3. `app/orchestrator/core.py` -- AnalyzeResponse (structure de reference)
4. `frontend/src/types/index.ts` -- types TS existants
5. `frontend/src/pages/HistoryPage.tsx` -- page History avec recherche q (Sprint 73)
6. `frontend/src/pages/WatchlistPage.tsx` -- page Watchlist existante
7. `app/api/endpoints/watchlist.py` -- endpoints watchlist (export.xlsx Sprint 59)
8. `app/services/report.py` -- ReportService (generate_watchlist_summary_pdf existant)

---

# ETAT DU PROJET A CE JOUR

| Champ | Valeur |
|-------|--------|
| Version | 6.6.0 |
| Phase active | Phase 3 -- Pipeline de synthese |
| Sprint actif | **Sprint 74 -- à définir** |
| Dernier sprint complete | Sprint 73 -- Recherche full-text dans l'historique |

## Infrastructure backend (operationnelle)
- 18 skills en production (16 Tier2 + 2 Tier1), dont `esg_simplified` (Sprint 70)
- Tous les skills utilisent `build_tool_schema()` + `tool_choice` force (Tool Use)
- Haiku uniquement : `earnings_quality`, `greenblatt_magic_formula`, `lynch_categories`
- `depuis_cache_composite: bool = False` dans `AnalyzeResponse` (Sprint 65)
- `GET /ticker-report/{ticker}?days=90` -- rapport PDF multi-pages par ticker (Sprint 63)
- `GET /screener-report?tickers=&workflow=` -- rapport PDF screener reportlab (Sprint 71)
- `GET /history?ticker=BNS&q=ACHAT` -- recherche ILIKE cross-ticker + index GIN pg_trgm (Sprint 73)
- `run_scheduled_screener` dimanche 11h00 UTC -- screener watchlist + webhook JSON + webhook PDF (Sprint 71)
- 1259 tests CI verts (`pytest -m "not e2e and not evals"`)

## Frontend React (operationnel)
- SPA React 18 + TypeScript strict, `frontend/` -- port 5173
- 8 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin
- `HistoryPage` -- champ `q` recherche ILIKE cross-ticker + notice résultats (Sprint 73)
- `TickerComparisonChart` -- composant recharts multi-lignes (Sprint 72)
- `downloadScreenerPdf()` dans `api/analyze.ts` -- appel GET /screener-report (Sprint 71)
- Vitest + @testing-library/react -- **133 tests verts** (Sprint 73)

## Suite de tests operationnelle
- Total backend CI : **1259 passes** (`pytest -m "not e2e and not evals"`), 3 skipped, 1 xfail
- Total frontend : **133 tests** (tous verts)

---

# TACHE -- SPRINT 74

Le sprint 74 n'est pas encore defini. Choisir parmi les sprints suggeres ci-dessous
ou proposer un sprint personnalise adapte aux besoins actuels.

---

# SPRINTS SUGGERES (74-79)

| Sprint | Objectif | Dependance | Complexite | Justification |
|--------|---------|-----------|-----------|--------------|
| **Sprint 74** | **Export PDF watchlist depuis l'interface** -- bouton "Exporter PDF global" dans WatchlistPage appelant `GET /watchlist/export.pdf` (endpoint PDF multi-tickers reportlab) | Sprints 63+68 | Moyenne | Rapport imprimable de toute la watchlist en un clic, coherent avec PDF ticker et screener |
| **Sprint 75** | **Alertes ESG** -- alertes webhook si esg_score < seuil configurable (dans watchlist) + affichage indicateur ESG dans WatchlistTable | Sprint 70 | Faible | Combine le skill ESG avec le systeme d'alertes existant -- valeur immediate |
| **Sprint 76** | **Historique ESG** -- table `esg_score_history`, `EsgHistoryService.record()/get_history()`, GET /esg-history/{ticker}, LineChart dans AnalyzePage | Sprint 70 | Moyenne | Suivre l'evolution du score ESG dans le temps comme le composite_score |
| **Sprint 77** | **Mode comparaison tickers** -- analyse parallele de 2-5 tickers avec tableau comparatif multi-skills (graham + dorsey + valuation), score difference highlighted | Screener | Moyenne | Aide a l'arbitrage et la selection finale -- use case frequent |
| **Sprint 78** | **Annotations d'analyses** -- champ `notes` libre par `analysis_id` (POST /annotations), affiché dans HistoryPage sous chaque analyse, persisté PostgreSQL | Aucune | Faible-Moyenne | Permet de conserver les reflexions d'investissement liees a chaque analyse |
| **Sprint 79** | **Filtre dates dans l'historique** -- `GET /history?from=&to=` plage ISO 8601 + selecteurs DatePicker dans HistoryPage | Sprint 73 | Faible | Complementaire a la recherche q -- filtrer par periode fiscale ou trimestre |

---

# CONTRAINTES ABSOLUES (rappel)

- Ne jamais appeler `client.messages.create()` directement -- utiliser `call_claude_with_retry()`
- Aucun `print()` -- `logging.getLogger(__name__)` partout (backend)
- **Les tests CI standard ne doivent consommer aucun token Claude reel**
- **CI standard** : `pytest -m "not e2e and not evals"` -- aucune cle Claude requise
- **composite_score** : calcule par `compute_composite_score()` -- jamais demande a Claude
- **depuis_cache_composite** : `bool = False` dans `AnalyzeResponse` -- ajout Sprint 65
- **Tool Use** : tous les skills utilisent `build_tool_schema()` + `tool_choice` force
- **Haiku** : `earnings_quality`, `greenblatt_magic_formula`, `lynch_categories` uniquement
- **Frontend** : `frontend/` (pas `screener/`) -- port 5173 -- `cd frontend && npm run dev`
- **Types TS** : `frontend/src/types/index.ts` doit rester synchronise avec les schemas Pydantic backend
- Nouveau composant React -> test composant Vitest obligatoire (happy path + cas d'erreur)
- **Webhook** : optionnel -- si WEBHOOK_URL absent, toutes les fonctions retournent False sans exception
- **composite_history_service** : disponible dans `app.state` -- toujours passe en parametre optionnel
- **Filtres screener Sprint 58** : `composite_label`, `min_composite_score`, `filter_workflow` dans `ScreenRequest`
- **Export Excel Sprint 59** : `GET /watchlist/export.xlsx` disponible -- openpyxl installe
- **recharts Sprint 60** : recharts 3.8.1 installe dans `frontend/`
- **eval_drift Sprint 61** : `EvalDriftService` dans `app.state.eval_drift_service`
- **API multi-users Sprint 62** : retrocompatibilite obligatoire -- `API_KEY` env doit rester fonctionnel
- **Admin endpoints Sprint 62** : `_require_admin()` accepte role="admin" OU cle env OU dev mode
- **PDF Sprint 63** : `PdfReportService` dans `app.state.pdf_report_service` -- `GET /ticker-report/{ticker}` -- 404 si pas d'historique composite
- **Screener planifie Sprint 64** : `run_scheduled_screener` dimanche 11h00 UTC -- 5 taches beat_schedule -- `send_screener_report()` + `send_screener_pdf_report()` dans WebhookService
- **Cache composite Sprint 65** : `CompositeHistoryService.get_recent()` -- circuit court Etape 0b avant les skills -- `depuis_cache_composite: bool = False` dans `AnalyzeResponse`
- **Eval drift Sprint 66** : `EvalDriftResult` dans `frontend/src/types/index.ts` -- `fetchEvalDrift()` dans `api/analyze.ts` -- `EvalDriftSection` dans `DashboardPage.tsx`
- **Admin Sprint 67** : `ApiKey` / `ApiKeyCreate` dans `frontend/src/types/index.ts` -- `api/admin.ts` -- `AdminPage.tsx` -- route `/admin` dans App.tsx
- **requestBlob Sprint 68** : utiliser `apiClient.requestBlob()` pour telecharger les PDFs -- URL.createObjectURL() + lien temporaire pour declencher le telechargement
- **PDF par ticker Sprint 68** : `downloadTickerPdf(ticker, days=90)` dans `api/analyze.ts` -- bouton "Telecharger PDF" dans HistoryPage (loading + gestion 404) -- bouton "PDF" par ticker WatchlistTable (data-testid="pdf-btn-{ticker}")
- **Badge cache Sprint 69** : `depuisCache` state dans AnalyzePage -- Badge shadcn/ui "Score depuis cache (<24h)" (data-testid="cache-badge") -- reset au lancement d'une nouvelle analyse
- **ESG Sprint 70** : `EsgSimplifiedSkill` dans `app.state` via `Orchestrator._esg` -- `esg_input: EsgInput | None` dans `AnalyzeRequest` -- `esg: EsgOutput | None` dans `AnalyzeResponse` -- `esg_simplified: 'esg'` dans SKILL_FIELD AnalyzePage
- **Screener PDF Sprint 71** : `ScreenerPdfService` dans `app/services/screener_pdf_service.py` -- `GET /screener-report?tickers=&workflow=` -- `downloadScreenerPdf()` dans `api/analyze.ts` -- bouton "Exporter PDF" ScreenerPage (data-testid="export-pdf") -- `send_screener_pdf_report()` multipart/form-data dans WebhookService -- 1250 tests CI verts -- 118 tests Vitest verts -- version 6.4.0
- **Comparaison Dashboard Sprint 72** : `TickerComparisonChart` dans `frontend/src/components/TickerComparisonChart.tsx` -- `ComparisonSection` dans `DashboardPage.tsx` -- saisie CSV 2-5 tickers -- `Promise.all(tickers.map(t => getCompositeHistory(t, 90)))` -- palette 5 couleurs TICKER_COLORS -- `data-testid="comparison-tickers-input"` + `data-testid="comparison-comparer-btn"` + `data-testid="ticker-comparison-chart"` -- 6 tests TickerComparisonChart + 4 tests ComparisonSection -- 128 tests Vitest verts -- version 6.5.0
- **Recherche historique Sprint 73** : `GET /history?q=` ILIKE cross-ticker sur ticker/workflow_name/(result->>'graham')/(result->>'earnings_quality') -- ticker optionnel -- `HistoryResponse.ticker: str | None` -- index GIN pg_trgm (ticker + workflow_name) -- `getHistory(ticker?, limit, before?, q?)` dans `api/analyze.ts` -- `data-testid="history-ticker-input"` + `data-testid="history-search-input"` + `data-testid="history-search-btn"` + `data-testid="search-cross-ticker-notice"` + `data-testid="history-empty"` -- 9 tests CI + 5 tests Vitest HistorySearch.test.tsx -- 1259 tests CI verts -- 133 tests Vitest verts -- version 6.6.0

---

*Roadmap mise a jour le 2026-05-17 -- Yves / TradingClaude*
*Sprint 73 complete : Recherche full-text dans l'historique -- GET /history?q= ILIKE cross-ticker (ticker partiel, workflow, verdicts JSONB) + ticker optionnel + HistoryResponse.ticker nullable + index GIN pg_trgm + HistoryPage champ Recherche + notice cross-ticker + 9 tests CI + 5 tests Vitest HistorySearch.test.tsx -- 1259 tests CI verts -- 133 tests Vitest verts -- version 6.6.0*
*Sprints 74-79 suggeres : Export PDF watchlist -> Alertes ESG -> Historique ESG -> Mode comparaison tickers -> Annotations analyses -> Filtre dates historique*
