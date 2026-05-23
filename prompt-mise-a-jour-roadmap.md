# Sprint 100 — Export analyse individuelle en PDF enrichi

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
4. `.github/workflows/ci.yml` -- 4 jobs CI (test-backend, test-frontend, lint, typecheck)
5. `pyproject.toml` -- configuration ruff + mypy (Sprint 98)
6. `app/services/pdf_report_service.py` -- PdfReportService existant (Sprint 63)
7. `app/api/endpoints/ticker_report.py` -- endpoint GET /ticker-report/{ticker} existant

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                                  |
| ----------------------- | ----------------------------------------------------------------------- |
| Version                 | 9.4.0                                                                   |
| Phase active            | Phase 3 -- Pipeline de synthese                                         |
| Sprint actif            | **Sprint 100 -- Export analyse individuelle en PDF enrichi**            |
| Dernier sprint complete | Sprint 99 -- Tableau de bord alertes (AlertsPage) ✅                   |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- Systeme d'authentification complet (Sprint Login) :
  - `POST /auth/register|login|logout|refresh|forgot-password|reset-password`
  - `GET /auth/me` -- profil depuis cookie httpOnly JWT
  - Refresh token rotation + detection vol par famille (Redis + DB)
  - `CSRFMiddleware` double-submit cookie ; rate limiting login 5/15 min Redis
  - Services : `UserService`, `AuthTokenService`, `PasswordResetService` dans `app.state`
  - Tables : `users` + `refresh_tokens` (idempotentes lifespan)
  - Retro-compat Bearer API key complete
- `GET /alerts?limit=50` -- historique alertes Celery (ESG_DEGRADATION, SCREENER_FORT, PRIX_SEUIL) (Sprint 99)
- `GET /composite-history/{ticker}?limit=30` -- historique composite_score
- `GET /history-paged?fast_count=true` -- estimation rapide total_count pg_class (Sprint 96)
- `DELETE /history/{analysis_id}` -- suppression admin individuelle (Sprint 95)
- `POST /analyze-stream` -- streaming SSE skill par skill
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit
- `GET /ticker-report/{ticker}?days=90` -- rapport PDF multi-pages par ticker (Sprint 63)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary
- CI : 4 jobs (pytest + vitest + ruff/eslint lint + mypy/tsc typecheck)
- 1401 tests CI verts (hors e2e et evals)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 13 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG,
  Alerts, Register, ForgotPassword, ResetPassword
- Auth par cookie httpOnly JWT -- `authMe()` au montage pour restaurer la session
- CSRF double-submit cookie -- `X-CSRF-Token` dans `api/client.ts`
- `ProtectedRoute` attend `isLoading` avant de rediriger
- **AlertsPage** -- tableau alertes Celery (Sprint 99) -- route `/alerts`
- **WatchlistPage** -- colonne "Tendance" sparkline composite_score 30j (Sprint 97)
- 217 tests Vitest verts

## Infrastructure CI/qualite code (Sprint 98)

- `LICENSE` MIT + `CONTRIBUTING.md` + `SECURITY.md`
- `.github/ISSUE_TEMPLATE/` bug_report.yml + feature_request.yml
- `.github/pull_request_template.md`
- `pyproject.toml` -- ruff (line-length 100, E/W/F/I/N) + mypy (python_version 3.11)
- `frontend/.eslintrc.cjs` -- ESLint + @typescript-eslint + react-hooks
- `frontend/package.json` -- scripts `lint` + `typecheck`
- `.github/dependabot.yml` -- pip + npm weekly

---

# TACHE -- SPRINT 100

## Objectif

Ajouter un bouton "Exporter PDF" dans HistoryPage qui permet de telecharger le PDF d'une analyse
individuelle sans relancer l'analyse. Les donnees sont deja dans la base (result JSONB dans
`analysis_history`) -- les rendre exportables via `GET /history/{analysis_id}/pdf`.

## Livrables attendus

### 1. `Orchestrator.get_analysis_by_id(analysis_id: str)` (`app/orchestrator/core.py`)

Nouvelle methode :
```python
async def get_analysis_by_id(self, analysis_id: str) -> AnalyzeResponse | None:
    """Retourne une analyse complete depuis analysis_history par son UUID."""
```
Recupere la ligne `result JSONB` et reconstruit un `AnalyzeResponse` via `model_validate`.
Retourne None si l'UUID n'existe pas (ou InvalidTextRepresentationError asyncpg).

### 2. Endpoint `GET /history/{analysis_id}/pdf` (`app/api/main.py`)

- Appelle `orchestrator.get_analysis_by_id(analysis_id)`
- 404 si introuvable, 422 si UUID invalide (automatique FastAPI via `UUID` param)
- Instancie `PdfReportService` (deja dans `app.state.pdf_report_service`)
- Genere un PDF via `PdfReportService.generate_ticker_report()` (Sprint 63)
- Retourne `Response(content=pdf_bytes, media_type="application/pdf")`
- Header : `Content-Disposition: attachment; filename="{ticker}-{date}.pdf"`

### 3. Frontend -- couche API + bouton HistoryPage

- `frontend/src/api/analyze.ts` -- `downloadAnalysisPdf(analysisId: string): Promise<void>`
  via `apiClient.requestBlob` + creation `<a>` temporaire pour telechargement
- `frontend/src/pages/HistoryPage.tsx` -- bouton "PDF" par analyse dans le tableau
  (data-testid="download-analysis-pdf-{analysis_id}") ; etat loading par id + gestion 404

### 4. Tests backend

- `tests/test_analysis_pdf_endpoint.py` -- 3 tests CI :
  1. `get_analysis_by_id()` retourne None si UUID inconnu
  2. `get_analysis_by_id()` reconstruit un `AnalyzeResponse` valide depuis le JSONB
  3. endpoint `GET /history/{id}/pdf` retourne 200 + content-type application/pdf

### 5. Tests frontend

- `frontend/src/__tests__/AnalysisPdf.test.tsx` -- 5 tests Vitest :
  bouton present, telechargement appele avec bon id, etat loading pendant le telechargement,
  bouton desactive pendant loading, gestion erreur 404

## Tests attendus

+3 tests CI (backend) + 5 tests Vitest (frontend) = 1404 CI verts, 222 Vitest verts.

---

# SPRINTS SUGGERES (101-105)

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

### Sprint 104 -- Score Graham dans le screener batch

**Objectif** : Afficher le score Graham (defensive_score / enterprising_score) directement dans
le tableau du ScreenerPage en plus du composite_score, pour une lecture comparative immediate.
**Complexite** : Faible
**Justification** : La colonne Graham est la plus utilisee dans les decisions d'achat ; la rendre
visible sans cliquer vers le detail de chaque ticker.

### Sprint 105 -- Graphique distribution des alertes dans AlertsPage

**Objectif** : Ajouter un mini-graphique en barres recharts dans AlertsPage montrant la
distribution des alertes par type (ESG_DEGRADATION / SCREENER_FORT / PRIX_SEUIL) sur les 30
derniers jours. Les donnees viennent du meme endpoint `GET /alerts`.
**Complexite** : Faible
**Justification** : Rendre le tableau de bord alertes actionnable d'un coup d'oeil.

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
- **CI Sprint 98** : 4 jobs (test-backend, test-frontend, lint, typecheck) -- `.github/workflows/ci.yml` -- ne pas modifier ; `pyproject.toml` ruff+mypy + `frontend/.eslintrc.cjs` ESLint -- ne pas modifier
- **Auth Sprint Login** : `UserService/AuthTokenService/PasswordResetService` dans `app.state` ; tables `users` + `refresh_tokens` ; `CSRFMiddleware` ; proxy `/auth` dans `vite.config.ts` ; `authMe()` dans `AuthContext` ; `isLoading` dans `ProtectedRoute` -- ne pas modifier ; retro-compat Bearer API key obligatoire
- **AlertsPage Sprint 99** : `alert_history` table + `AlertHistoryService` dans `app.state.alert_history_service` + `GET /alerts?limit=50` + `AlertsPage.tsx` + route `/alerts` + lien "Alertes" nav -- ne pas modifier ; `tasks.py` persiste en best-effort (ESG_DEGRADATION dans `_execute_esg_degradation_check`, SCREENER_FORT dans `_execute_scheduled_screener`)
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-23 -- Yves / TradingClaude_
_Sprint 99 complete : Tableau de bord alertes -- AlertHistoryService + table alert_history + GET /alerts + AlertsPage.tsx + route /alerts + lien nav + persistance Celery ESG/screener -- +3 CI + 5 Vitest -- version 9.4.0_
_Sprints 100-105 suggeres : Export PDF analyse -> Recherche watchlist -> Web Push alertes -> Sparkline ESG -> Score Graham screener -> Distribution alertes_
