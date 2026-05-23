# Sprint 92 -- Annotations dans l'export Excel watchlist

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
4. `app/services/watchlist_service.py` -- methode `get_all_with_composite()` (LEFT JOIN LATERAL a enrichir avec les annotations)
5. `app/services/annotation_service.py` -- methode `get_all_with_ticker()` (pattern a utiliser pour le JOIN)
6. `app/api/endpoints/watchlist.py` -- fonction `_generate_watchlist_xlsx()` + colonnes actuelles
7. `app/models/annotation.py` -- schema `Annotation` (champs `ticker`, `content`)

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                  |
| ----------------------- | ------------------------------------------------------- |
| Version                 | 8.4.0                                                   |
| Phase active            | Phase 3 -- Pipeline de synthese                         |
| Sprint actif            | **Sprint 92 -- Annotations dans l'export Excel watchlist** |
| Dernier sprint complete | Sprint 91 -- Seuil de prix configurable par ticker ✅   |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- `PATCH /watchlist/{id}/price-threshold` -- seuil alerte prix configurable par ticker (Sprint 91)
- `PATCH /watchlist/{id}/esg-threshold` -- seuil alerte ESG configurable par ticker (Sprint 84)
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit avec total_count (Sprint 90)
- `EsgHistoryService` + table `esg_score_history` + `GET /esg-history/{ticker}` -- historique ESG (Sprint 89)
- `app/utils/esg_utils.py` -- helper `esg_verdict()` partage (Sprint 88)
- `MonthlyReportService` -- section ESG en fin de PDF (Sprint 88)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary (Sprint 86)
- `GET /annotations/export.csv` + `GET /annotations/export.xlsx` -- export annotations depuis HistoryPage (Sprint 85)
- `AnnotationService.get_all_with_ticker()` -- toutes les annotations avec ticker (Sprint 85)
- `GET /watchlist/export.xlsx` -- export Excel watchlist avec Score ESG + Verdict ESG, SANS annotation (Sprint 83)
- `get_all_with_composite()` -- LEFT JOIN LATERAL sur composite_score_history (Sprint 82/83)
- 1371 tests CI verts (`pytest tests/ --ignore=tests/e2e --ignore=tests/evals`)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 9 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG
- **WatchlistTable** -- colonnes Seuil ESG (Sprint 84) et Seuil Prix (%) (Sprint 91) avec edition inline
- **HistoryPage** -- pagination numerotee (Sprint 90) + export annotations CSV/Excel (Sprint 85)
- Vitest + @testing-library/react -- 192 tests verts

## Corpus RAG complet (Sprint 75)

- 16/16 skills tier2 documentes -- ~67 documents references/ dans le corpus RAG Qdrant

---

# TACHE -- SPRINT 92

## Objectif

Inclure la colonne "Annotation" dans `GET /watchlist/export.xlsx` en faisant un LEFT JOIN
sur la table `annotations` depuis `get_all_with_composite()`. Les annotations sont deja
exportables depuis HistoryPage (Sprint 85) mais pas depuis la watchlist. Ce sprint ferme
cette incoherence : un seul champ par ticker (la derniere annotation, ou vide si aucune).

## Livrables attendus

### 1. Backend

- `app/services/watchlist_service.py` -- enrichir `get_all_with_composite()` avec un deuxieme
  LEFT JOIN LATERAL sur la table `annotations` pour recuperer `content` de la derniere annotation
  par ticker (ORDER BY created_at DESC LIMIT 1) ; alias SQL : `derniere_annotation`
- `app/api/endpoints/watchlist.py` -- ajouter la colonne "Annotation" a `_XLSX_HEADERS` et
  `_XLSX_COL_WIDTHS` ; dans `_generate_watchlist_xlsx()`, recuperer `row.get("derniere_annotation", "")`
  et l'ecrire dans la colonne appropriee (apres "Notes" existant ou a la place)

### 2. Tests CI

- `tests/test_watchlist_xlsx_annotation.py` -- 3 tests CI :
  - `get_all_with_composite()` inclut la colonne `derniere_annotation` dans le SQL
  - `GET /watchlist/export.xlsx` contient la colonne "Annotation" dans la ligne d'en-tete
  - `GET /watchlist/export.xlsx` ecrit la valeur de l'annotation si presente, chaine vide si absente

Objectif : +3 CI (total >= 1374)

### 3. Tests Vitest

Pas de changement frontend -- aucun test Vitest requis pour ce sprint.

## Contraintes techniques

- Ne pas casser `get_all_with_composite()` -- les colonnes existantes doivent rester identiques
- Le champ "Notes" dans le XLSX actuel est toujours vide (`""`) -- remplacer par `derniere_annotation`
  ou ajouter "Annotation" comme colonne supplementaire apres "Notes" (au choix)
- Garder la retrocompatibilite : si la table `annotations` est vide pour un ticker, la cellule est `""`
- La requete SQL ne doit pas utiliser de sous-requete correllee non-indexed -- utiliser LEFT JOIN LATERAL

---

# SPRINTS SUGGERES (93-97)

### Sprint 93 -- Streaming SSE dans ComparePage (opt-in)

**Objectif** : Ajouter une option "streaming" dans ComparePage qui utilise
`POST /analyze-stream` au lieu de `POST /analyze` -- affichage progressif skill par skill.
**Complexite** : Moyenne
**Justification** : L'infrastructure SSE existe deja (AnalyzePage) -- l'appliquer a
ComparePage ameliore l'UX pour les analyses longues (> 30s).

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
**Justification** : Le depot est maintenant public (fait en session Sprint 91). Sans ces fichiers,
le projet parait abandonne ou non maintenu. Ces artefacts sont la norme pour tout depot open-source
serieux et ameliorent la confiance des recruteurs/contributeurs. Le linting CI catch les regressions
de style avant merge -- valeur immediate, effort faible.

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
- **Pagination Sprint 90** : `PagedHistoryResponse` + `Orchestrator.get_history_paged()` + `GET /history-paged` + `getHistoryPaged()` (frontend) + `HistoryPage.tsx` boutons `history-pagination-prev/next` + `history-page-label` -- ne pas modifier ; `GET /history` (cursor) preserve pour retrocompat
- **Seuil Prix Sprint 91** : `PATCH /watchlist/{id}/price-threshold` + `update_price_threshold()` + colonne "Seuil Prix (%)" WatchlistTable -- ne pas modifier ; l'endpoint divise la valeur % par 100 avant stockage NUMERIC(5,4)
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-22 -- Yves / TradingClaude_
_Sprint 91 complete : Seuil de prix configurable par ticker -- update_price_threshold() WatchlistService + PriceThresholdUpdate schema + PATCH /watchlist/{id}/price-threshold (422 si hors 0-100, division par 100 pour stockage NUMERIC(5,4)) + colonne "Seuil Prix (%)" WatchlistTable (edition inline, etats independants du seuil ESG) + patchPriceThreshold() API + 3 CI + 5 Vitest + bonus correction corruption OneDrive types/index.ts + accents HistoryPage.tsx + mock getHistoryPaged PdfDownload.test.tsx -- 1371 CI verts + 192 Vitest verts -- version 8.4.0_
_Sprints 92-98 suggeres : Annotations watchlist export -> Streaming SSE ComparePage -> Alerte degradation ESG -> DELETE /history -> Estimation rapide total_count -> Sparkline composite watchlist -> Professionnalisation GitHub (CI lint/typecheck, templates, LICENSE, CONTRIBUTING, Dependabot)_
