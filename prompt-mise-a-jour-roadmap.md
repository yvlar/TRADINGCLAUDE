# Sprint 98 -- Professionnalisation GitHub (CI complet + qualite code)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# ROLE

Tu es un developpeur full-stack senior specialiste React + FastAPI **ET ingenieur IA applique**.
Tu maitrises Python, FastAPI, asyncpg, Pydantic v2, Celery, Redis, PostgreSQL,
React 18, TypeScript strict, Vitest et les patterns de tests automatises.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

1. `CLAUDE.md` -- index slim (pointe vers `.claude/rules/`)
2. `.claude/rules/base-connaissances-skills.md` -- catalogue 16+2 skills
3. `ROADMAP.md` -- etat courant, sprint actif, historique des decisions
4. `.github/workflows/` (si present) -- workflows CI existants a ne pas ecraser
5. `pyproject.toml` (si present) -- configuration Python existante
6. `package.json` dans `frontend/` -- scripts npm existants (lint, typecheck)

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                              |
| ----------------------- | ------------------------------------------------------------------- |
| Version                 | 9.0.0                                                               |
| Phase active            | Phase 3 -- Pipeline de synthese                                     |
| Sprint actif            | **Sprint 98 -- Professionnalisation GitHub (CI complet + qualite code)** |
| Dernier sprint complete | Sprint 97 -- Score composite historique dans WatchlistPage ✅      |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- `GET /composite-history/{ticker}?limit=30` -- historique composite_score (Sprint 57/60)
- `GET /history-paged?fast_count=true` -- estimation rapide total_count pg_class (Sprint 96)
- `DELETE /history/{analysis_id}` -- suppression admin individuelle (Sprint 95)
- `POST /analyze-stream` -- streaming SSE skill par skill (Sprint 93)
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit (Sprint 90)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary (Sprint 86)
- 1383 tests CI verts (hors e2e et evals)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 9 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG
- **WatchlistPage** -- WatchlistTable avec colonne "Tendance" sparkline composite_score 30j (Sprint 97)
- **CompositeSparkline** -- `frontend/src/components/CompositeSparkline.tsx` -- recharts 120px sans axes
- 205 tests Vitest verts

---

# TACHE -- SPRINT 98

## Objectif

Rendre le depot GitHub public professionnel et pret pour des contributeurs exterieurs :
linting/formatage automatique dans le CI, type-checking, templates GitHub, fichiers de gouvernance.

## Livrables attendus

### 1. Fichiers de gouvernance

- `LICENSE` -- MIT (2026, Yves Lariviere)
- `CONTRIBUTING.md` -- setup local (Docker Compose + npm), conventions bilingues FR/EN,
  pyramide de tests (5 niveaux), workflow sprint, commandes essentielles
- `SECURITY.md` -- politique de divulgation responsable, contact ivess49@gmail.com

### 2. Templates GitHub

- `.github/ISSUE_TEMPLATE/bug_report.yml` -- template structure : titre, version, etapes
  de reproduction, comportement attendu/observe, logs
- `.github/ISSUE_TEMPLATE/feature_request.yml` -- template : titre, probleme, solution proposee,
  alternatives envisagees
- `.github/pull_request_template.md` -- checklist : tests verts, types stricts, CLAUDE.md a jour,
  `.env.example` a jour, pas de secret commite

### 3. Configuration qualite code

- `pyproject.toml` -- configuration `ruff` (line-length 100, select E/W/F/I/N, per-file-ignores
  pour tests) + `mypy` (python_version 3.11, ignore_missing_imports = true, strict = false)
- `frontend/package.json` -- verifier que les scripts `lint` et `typecheck` existent
  (ajouter si absents : `"lint": "eslint src"`, `"typecheck": "tsc --noEmit"`)

### 4. Workflow CI GitHub Actions

- `.github/workflows/ci.yml` -- 3 jobs :
  1. `test-backend` : `pip install -r requirements.txt && pytest tests/ --ignore=tests/e2e --ignore=tests/evals`
  2. `lint` : `pip install ruff && ruff check app/ tests/` + `cd frontend && npm ci && npm run lint`
  3. `typecheck` : `pip install mypy && mypy app/ --ignore-missing-imports` + `cd frontend && npx tsc --noEmit`
- Declenchement : `push` sur `master`/`main` et `pull_request`
- Python 3.11, Node.js 20

### 5. Dependabot

- `.github/dependabot.yml` -- mise a jour automatique pip (weekly, lundi) + npm (weekly, lundi)
  cible `master`

## Tests attendus

Pas de nouveaux tests CI/Vitest -- sprint infrastructure uniquement.
Verifier que le CI passe en local : `ruff check app/` + `cd frontend && npm run lint` (si applicable).

---

# SPRINTS SUGGERES (99-103)

### Sprint 99 -- Tableau de bord alertes (AlertsPage)

**Objectif** : Nouvelle page `/alerts` listant les alertes recentes (ESG + composite + prix) avec
horodatage, ticker, type d'alerte et valeur. Persistance dans une nouvelle table `alert_history`.
**Complexite** : Moyenne-Elevee
**Justification** : Yves ne voit pas les alertes sans consulter Slack/webhook.

### Sprint 100 -- Export analyse individuelle en PDF enrichi

**Objectif** : Bouton "Exporter cette analyse" dans la vue detail d'une analyse historique
(HistoryPage), generant un PDF complet avec tous les skills, verdicts et recommandations.
Reutilise `PdfReportService` (Sprint 63).
**Complexite** : Moyenne
**Justification** : Les donnees existent deja ; les rendre exportables sans re-executer.

### Sprint 101 -- Recherche full-text dans WatchlistPage

**Objectif** : Champ de recherche dans WatchlistPage filtrant les tickers en temps reel
(cote client, pas de nouvel endpoint). Pattern identique au champ `q` de HistoryPage.
**Complexite** : Faible
**Justification** : La watchlist grandit -- trouver un ticker parmi 20+ est fastidieux.

### Sprint 102 -- Notification browser (Web Push) pour les alertes Celery

**Objectif** : Envoyer une notification navigateur (Web Push API) quand Celery detecte une
alerte ESG ou composite, sans dependance a Slack ni webhook externe.
**Complexite** : Elevee
**Justification** : Alternative self-hosted a Slack pour les alertes temps reel.

### Sprint 103 -- Historique sparkline ESG dans WatchlistTable

**Objectif** : Ajouter un sparkline de l'evolution du score ESG (30j) dans WatchlistTable,
en miroir du sparkline composite_score (Sprint 97). Donnees via `GET /esg-history/{ticker}`.
**Complexite** : Faible
**Justification** : Coherence visuelle avec le sparkline composite_score ; donnees deja disponibles.

---

# CONTRAINTES ABSOLUES (rappel)

- Ne jamais appeler `client.messages.create()` directement -- utiliser `call_claude_with_retry()`
- Aucun `print()` -- `logging.getLogger(__name__)` partout (backend)
- **Les tests CI standard ne doivent consommer aucun token Claude reel**
- **CI standard** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` -- aucune cle Claude requise
- **Tool Use** : tous les skills utilisent `build_tool_schema()` + `tool_choice` force
- **Frontend** : `frontend/` -- port 5173 -- `cd frontend && npm run dev`
- **Types TS** : `frontend/src/types/index.ts` doit rester synchronise avec les schemas Pydantic backend
- Nouveau composant React -> test composant Vitest obligatoire (happy path + cas d'erreur)
- **Webhook** : optionnel -- si WEBHOOK_URL absent, toutes les fonctions retournent False sans exception
- **Slack** : optionnel -- si SLACK_WEBHOOK_URL absent, toutes les fonctions retournent False sans exception
- **API multi-users Sprint 62** : retrocompatibilite obligatoire -- `API_KEY` env doit rester fonctionnel
- **ESG Sprint 70** : `EsgSimplifiedSkill` dans `app.state` via `Orchestrator._esg`
- **PDF watchlist Sprint 76** : `WatchlistPdfService` dans `app.state.watchlist_pdf_service`
- **Alertes ESG Sprint 77** : `esg_alert_threshold: float = 5.0` + `last_esg_score: float | None` dans `WatchlistEntry`
- **Annotations Sprint 78** : `AnnotationService` dans `app.state.annotation_service`
- **Filtre dates Sprint 79** : `from_dt` et `to_dt` dans `get_history()` -- ne pas modifier
- **Comparaison Sprint 80** : `CompareService` dans `app.state.compare_service` -- `POST /compare` sans appel Claude
- **Rapport mensuel Sprint 81** : `MonthlyReportService` dans `app.state.monthly_report_service`
- **Page ESG Sprint 82** : `GET /watchlist/esg-scores` + `EsgPage.tsx` + route `/esg` -- ne pas modifier
- **Export Excel ESG Sprint 83** : helper `esg_verdict()` dans `app/utils/esg_utils.py` (Sprint 88) -- ne pas supprimer
- **Seuil ESG Sprint 84** : `PATCH /watchlist/{id}/esg-threshold` + colonne "Seuil ESG" WatchlistTable -- ne pas modifier
- **Export annotations Sprint 85** : `GET /annotations/export.csv` + `GET /annotations/export.xlsx` -- ne pas modifier
- **Slack Sprint 86** : `SlackService` dans `app.state.slack_service` + `app.services.slack_service` -- ne pas modifier
- **Comparaison live Sprint 87** : bouton "Analyser" + `handleAnalyze()` dans `ComparePage.tsx` -- ne pas modifier
- **Section ESG mensuelle Sprint 88** : `MonthlyReportService.generate()` accepte `watchlist_service` kwarg -- ne pas modifier
- **Helper ESG Sprint 88** : `esg_verdict()` dans `app/utils/esg_utils.py` -- alias `_esg_verdict` conserve dans `app/api/endpoints/watchlist.py` pour retrocompat
- **Historique ESG Sprint 89** : table `esg_score_history` + `EsgHistoryService` dans `app.state.esg_history_service` + `GET /esg-history/{ticker}` + `record(ticker, score)` appele apres `EsgSimplifiedSkill` dans orchestrator -- ne pas modifier
- **Pagination Sprint 90** : `PagedHistoryResponse` + `Orchestrator.get_history_paged()` + `GET /history-paged` + `getHistoryPaged()` (frontend) -- ne pas modifier ; `GET /history` (cursor) preserve pour retrocompat
- **Seuil Prix Sprint 91** : `PATCH /watchlist/{id}/price-threshold` + `update_price_threshold()` + colonne "Seuil Prix (%)" WatchlistTable -- ne pas modifier ; l'endpoint divise la valeur % par 100 avant stockage NUMERIC(5,4)
- **Annotations XLSX Sprint 92** : `get_all_with_composite()` retourne `derniere_annotation` (COALESCE '') ; colonne "Annotation" position 9 dans `_XLSX_HEADERS` -- ne pas modifier
- **Streaming SSE Sprint 93** : toggle `streamingEnabled` + `tickerStreamSkill` + `data-testid="streaming-toggle"` + `data-testid="stream-skill-{ticker}"` dans `ComparePage.tsx` -- ne pas modifier
- **Degradation ESG Sprint 94** : `get_latest_previous()` + `check_esg_degradation()` + `run_esg_degradation_check` Celery beat dimanche 12h UTC + `POST /watchlist/check-esg-degradation` (admin) -- ne pas modifier
- **Suppression analyses Sprint 95** : `Orchestrator.delete_analysis()` + `DELETE /history/{analysis_id}` (admin, 204/404/422) + `deleteAnalysis()` frontend + bouton 🗑 HistoryPage `data-testid="delete-analysis-{id}"` -- ne pas modifier
- **Fast count Sprint 96** : `Orchestrator.get_history_paged()` accepte `fast_count: bool = False` ; `GET /history-paged?fast_count=true` -- ne pas modifier
- **Sparkline Sprint 97** : `CompositeSparkline` dans `frontend/src/components/CompositeSparkline.tsx` ; colonne "Tendance" dans `WatchlistTable.tsx` entre "Score composite" et "ESG" -- ne pas modifier ; tests Watchlist* mockent `CompositeSparkline` pour eviter QueryClientProvider
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-22 -- Yves / TradingClaude_
_Sprint 97 complete : Score composite historique dans WatchlistPage -- CompositeSparkline recharts 120px + colonne "Tendance" WatchlistTable + 5 tests Vitest -- 1383 CI verts, 205 Vitest verts -- version 9.0.0_
_Sprints 98-103 suggeres : Professionnalisation GitHub → AlertsPage → Export PDF analyse → Recherche watchlist → Web Push alertes → Sparkline ESG_
