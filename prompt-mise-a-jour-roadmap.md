# Sprint 93 -- Streaming SSE dans ComparePage (opt-in)

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
4. `app/api/endpoints/analyze_stream.py` -- endpoint SSE existant (`POST /analyze-stream`) et generateur `_sse_generator`
5. `frontend/src/pages/AnalyzePage.tsx` -- implementation streaming SSE cote frontend (pattern a reutiliser)
6. `frontend/src/pages/ComparePage.tsx` -- page actuelle, bouton "Analyser" + `handleAnalyze()` (Sprint 87)
7. `frontend/src/api/analyze.ts` -- `streamAnalyze()` ou equivalent (SSE client)

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                  |
| ----------------------- | ------------------------------------------------------- |
| Version                 | 8.5.0                                                   |
| Phase active            | Phase 3 -- Pipeline de synthese                         |
| Sprint actif            | **Sprint 93 -- Streaming SSE dans ComparePage (opt-in)** |
| Dernier sprint complete | Sprint 92 -- Annotations dans l'export Excel watchlist ✅ |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- `POST /analyze-stream` -- streaming SSE skill par skill (utilise dans AnalyzePage)
- `PATCH /watchlist/{id}/price-threshold` -- seuil alerte prix configurable par ticker (Sprint 91)
- `PATCH /watchlist/{id}/esg-threshold` -- seuil alerte ESG configurable par ticker (Sprint 84)
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit avec total_count (Sprint 90)
- `EsgHistoryService` + table `esg_score_history` + `GET /esg-history/{ticker}` -- historique ESG (Sprint 89)
- `app/utils/esg_utils.py` -- helper `esg_verdict()` partage (Sprint 88)
- `MonthlyReportService` -- section ESG en fin de PDF (Sprint 88)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary (Sprint 86)
- `GET /annotations/export.csv` + `GET /annotations/export.xlsx` -- export annotations depuis HistoryPage (Sprint 85)
- `AnnotationService.get_all_with_ticker()` -- toutes les annotations avec ticker (Sprint 85)
- `GET /watchlist/export.xlsx` -- export Excel watchlist avec Score ESG + Verdict ESG + Annotation (Sprint 83/92)
- `get_all_with_composite()` -- LEFT JOIN LATERAL composite_score_history + annotations (Sprint 82/83/92)
- 1374 tests au total (1372 CI verts hors e2e et evals)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 9 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG
- **ComparePage** -- bouton "Analyser" (opt-in, `analysis_id===null`) + `handleAnalyze()` Promise.race 60s (Sprint 87)
- **AnalyzePage** -- streaming SSE skill par skill via `POST /analyze-stream` (pattern de reference)
- **WatchlistTable** -- colonnes Seuil ESG (Sprint 84) et Seuil Prix (%) (Sprint 91) avec edition inline
- **HistoryPage** -- pagination numerotee (Sprint 90) + export annotations CSV/Excel (Sprint 85)
- Vitest + @testing-library/react -- 192 tests verts

## Corpus RAG complet (Sprint 75)

- 16/16 skills tier2 documentes -- ~67 documents references/ dans le corpus RAG Qdrant

---

# TACHE -- SPRINT 93

## Objectif

Ajouter une option "Streaming" (toggle ou checkbox) dans `ComparePage` qui utilise
`POST /analyze-stream` au lieu de `POST /analyze` -- affichage progressif skill par skill
pendant l'analyse. L'infrastructure SSE existe deja (AnalyzePage) -- l'appliquer a
ComparePage ameliore l'UX pour les analyses longues (> 30s). Le mode non-streaming
reste disponible (opt-in, pas de changement de comportement par defaut).

## Livrables attendus

### 1. Frontend

- `frontend/src/pages/ComparePage.tsx` -- ajouter un toggle `streamingEnabled` (boolean, defaut false) ;
  quand coché, `handleAnalyze()` utilise `streamAnalyze()` (SSE) au lieu de `postAnalyze()` ; afficher
  les tokens/skills recus progressivement dans la cellule correspondante (meme colonne, meme ticker) ;
  conserver le bouton "Analyser" et la logique Promise.race 60s existante

- `frontend/src/api/analyze.ts` -- verifier que `streamAnalyze(request, onChunk)` existe deja ou
  l'ajouter (callback invoque a chaque evenement SSE recu, parse le JSON du chunk, retourne la
  reponse finale complete quand le stream se ferme)

### 2. Tests Vitest

- `frontend/src/__tests__/CompareStreaming.test.tsx` -- 5 tests Vitest :
  - Toggle "Streaming" present et initialement desactive
  - Cocher le toggle appelle `streamAnalyze()` et non `postAnalyze()` lors du clic "Analyser"
  - Sans toggle, `postAnalyze()` est toujours appele (retrocompatibilite)
  - Les chunks recus sont affiches progressivement (spy sur le callback)
  - Erreur stream (rejet Promise) affichee inline 5s

### 3. Tests CI backend

Pas de changement backend -- aucun test CI requis pour ce sprint.
Objectif : +5 Vitest (total >= 197)

## Contraintes techniques

- Ne pas casser `handleAnalyze()` et le comportement actuel (Sprint 87) -- le mode non-streaming
  reste le defaut (toggle off = comportement identique a avant ce sprint)
- `Promise.race 60s` doit s'appliquer aussi en mode streaming
- Le toggle doit etre visuellement clair (label "Streaming en direct" ou equivalent)
- Pas de changement du backend -- `POST /analyze-stream` existe deja

---

# SPRINTS SUGGERES (94-98)

### Sprint 94 -- Alerte ESG sur degradation historique

**Objectif** : Comparer le `last_esg_score` au precedent enregistrement de `esg_score_history`.
Si la baisse est superieure au `esg_alert_threshold` (en valeur absolue), declencher une alerte
Slack/webhook -- pattern identique aux alertes composite Sprint 57.
**Complexite** : Moyenne
**Justification** : Repose sur le Sprint 89 (historique persiste) -- ferme la boucle
"detection -> alerte" deja en place pour le composite_score.

### Sprint 95 -- Suppression des analyses obsoletes (DELETE /history)

**Objectif** : Endpoint `DELETE /history/{analysis_id}` (admin only) pour nettoyer
les analyses test ou les anciennes versions. Bouton "Supprimer" dans HistoryPage avec confirmation.
**Complexite** : Faible-Moyenne
**Justification** : Au bout de 90+ sprints, l'historique contient beaucoup de bruit de developpement.
Permet a Yves de nettoyer manuellement sans toucher la DB.

### Sprint 96 -- Estimation rapide total_count via pg_class

**Objectif** : Quand `analysis_history` depasse 100k lignes, remplacer `SELECT COUNT(*)` par
une estimation `pg_class.reltuples` (option `?fast_count=true` sur `/history-paged`).
**Complexite** : Faible
**Justification** : Le `COUNT(*)` exact dans `get_history_paged()` (Sprint 90) devient couteux
au-dela de 100k analyses -- prevoir l'echappatoire avant d'y arriver.

### Sprint 97 -- Score composite historique dans WatchlistPage

**Objectif** : Ajouter un mini-graphique sparkline recharts dans WatchlistTable pour chaque ticker
montrant l'evolution du composite_score sur 30 jours, en utilisant `GET /composite-history/{ticker}`.
**Complexite** : Moyenne
**Justification** : Les donnees existent deja (Sprint 57/60) -- les rendre visibles directement dans
la watchlist sans naviguer vers le Dashboard.

### Sprint 98 -- Professionnalisation GitHub (CI complet + qualite code)

**Objectif** : Rendre le depot GitHub professionnel et pret pour des contributeurs exterieurs :
linting/formatage automatique, type-checking CI, templates GitHub, fichiers de gouvernance.

**Livrables concrets :**
- `.github/ISSUE_TEMPLATE/` -- 2 templates : `bug_report.yml` et `feature_request.yml`
- `.github/pull_request_template.md` -- checklist PR standard (tests, types, CLAUDE.md)
- `CONTRIBUTING.md` -- guide de contribution (setup local, conventions, pyramide de tests)
- `LICENSE` -- MIT (projet portfolio public)
- `.github/workflows/ci.yml` -- ajouter 2 jobs supplementaires :
  - `lint` : `ruff check app/ tests/` + `ruff format --check` (Python) ; `npm run lint` (frontend)
  - `typecheck` : `mypy app/ --ignore-missing-imports` (Python) ; `npx tsc --noEmit` (frontend)
- `pyproject.toml` -- configuration ruff (line-length 100, select E/W/F/I) + mypy (strict=False)
- `.github/dependabot.yml` -- mises a jour auto pip + npm (weekly)
- `SECURITY.md` -- politique de divulgation responsable (contact ivess49@gmail.com)

**Complexite** : Moyenne
**Justification** : Le depot est maintenant public. Sans ces fichiers, le projet parait abandonne.
Ces artefacts sont la norme pour tout depot open-source serieux.

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
- **Comparaison live Sprint 87** : bouton "Analyser" + `handleAnalyze()` dans `ComparePage.tsx` -- ne pas modifier ; ajouter le toggle SSE sans casser ce comportement
- **Section ESG mensuelle Sprint 88** : `MonthlyReportService.generate()` accepte `watchlist_service` kwarg -- ne pas modifier
- **Helper ESG Sprint 88** : `esg_verdict()` dans `app/utils/esg_utils.py` -- alias `_esg_verdict` conserve dans `app/api/endpoints/watchlist.py` pour retrocompat
- **Historique ESG Sprint 89** : table `esg_score_history` + `EsgHistoryService` dans `app.state.esg_history_service` + `GET /esg-history/{ticker}` + `record(ticker, score)` appele apres `EsgSimplifiedSkill` dans orchestrator -- ne pas modifier
- **Pagination Sprint 90** : `PagedHistoryResponse` + `Orchestrator.get_history_paged()` + `GET /history-paged` + `getHistoryPaged()` (frontend) + `HistoryPage.tsx` boutons `history-pagination-prev/next` + `history-page-label` -- ne pas modifier ; `GET /history` (cursor) preserve pour retrocompat
- **Seuil Prix Sprint 91** : `PATCH /watchlist/{id}/price-threshold` + `update_price_threshold()` + colonne "Seuil Prix (%)" WatchlistTable -- ne pas modifier ; l'endpoint divise la valeur % par 100 avant stockage NUMERIC(5,4)
- **Annotations XLSX Sprint 92** : `get_all_with_composite()` retourne `derniere_annotation` (COALESCE '') ; colonne "Annotation" position 9 dans `_XLSX_HEADERS` -- ne pas modifier
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-22 -- Yves / TradingClaude_
_Sprint 92 complete : Annotations dans l'export Excel watchlist -- second LEFT JOIN LATERAL dans get_all_with_composite() sur annotations+analysis_history (derniere_annotation COALESCE '') + colonne "Annotation" position 9 dans _XLSX_HEADERS/_XLSX_COL_WIDTHS + _generate_watchlist_xlsx() lit derniere_annotation + 3 tests CI (SQL, en-tete, valeur presente/absente) -- 1374 tests au total (1372 CI verts) -- version 8.5.0_
_Sprints 93-98 suggeres : Streaming SSE ComparePage -> Alerte degradation ESG -> DELETE /history -> Estimation rapide total_count -> Sparkline composite watchlist -> Professionnalisation GitHub (CI lint/typecheck, templates, LICENSE, CONTRIBUTING, Dependabot)_
