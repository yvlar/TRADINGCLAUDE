# Sprint 94 -- Alerte ESG sur dégradation historique

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
4. `app/services/watchlist_service.py` -- `WatchlistEntry` (champs `esg_alert_threshold`, `last_esg_score`) et methode `get_all()`
5. `app/services/esg_history_service.py` -- `EsgHistoryService.record()` et `get_history()` ; table `esg_score_history`
6. `app/services/slack_service.py` + `app/services/webhook_service.py` -- `send_esg_alert()` existant (Sprint 77/86)
7. `app/workers/tasks.py` -- taches Celery existantes (pattern `run_scheduled_screener`, `send_monthly_report`, etc.)
8. `frontend/src/pages/EsgPage.tsx` -- page ESG existante (Sprint 82)

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                  |
| ----------------------- | ------------------------------------------------------- |
| Version                 | 8.6.0                                                   |
| Phase active            | Phase 3 -- Pipeline de synthese                         |
| Sprint actif            | **Sprint 94 -- Alerte ESG sur degradation historique**  |
| Dernier sprint complete | Sprint 93 -- Streaming SSE dans ComparePage (opt-in) ✅ |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- `POST /analyze-stream` -- streaming SSE skill par skill (utilise dans AnalyzePage + ComparePage Sprint 93)
- `PATCH /watchlist/{id}/price-threshold` -- seuil alerte prix configurable par ticker (Sprint 91)
- `PATCH /watchlist/{id}/esg-threshold` -- seuil alerte ESG configurable par ticker (Sprint 84)
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit avec total_count (Sprint 90)
- `EsgHistoryService` + table `esg_score_history` + `GET /esg-history/{ticker}` -- historique ESG (Sprint 89)
- `app/utils/esg_utils.py` -- helper `esg_verdict()` partage (Sprint 88)
- `MonthlyReportService` -- section ESG en fin de PDF (Sprint 88)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary (Sprint 86)
- `WebhookService.send_esg_alert()` -- envoie alerte ESG via webhook (Sprint 77)
- `GET /annotations/export.csv` + `GET /annotations/export.xlsx` -- export annotations depuis HistoryPage (Sprint 85)
- `GET /watchlist/export.xlsx` -- export Excel watchlist avec Score ESG + Verdict ESG + Annotation (Sprint 83/92)
- `get_all_with_composite()` -- LEFT JOIN LATERAL composite_score_history + annotations (Sprint 82/83/92)
- 1374 tests au total (1372 CI verts hors e2e et evals)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 9 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG
- **ComparePage** -- toggle "Streaming en direct" SSE + handleAnalyze() bifurquant postAnalyze/streamAnalyze (Sprint 93)
- **AnalyzePage** -- streaming SSE skill par skill via `POST /analyze-stream` (pattern de reference)
- **EsgPage** -- tableau tritable, badges FORT/MODERE/FAIBLE, route /esg (Sprint 82)
- **WatchlistTable** -- colonnes Seuil ESG (Sprint 84) et Seuil Prix (%) (Sprint 91) avec edition inline
- **HistoryPage** -- pagination numerotee (Sprint 90) + export annotations CSV/Excel (Sprint 85)
- Vitest + @testing-library/react -- 197 tests verts

## Corpus RAG complet (Sprint 75)

- 16/16 skills tier2 documentes -- ~67 documents references/ dans le corpus RAG Qdrant

---

# TACHE -- SPRINT 94

## Objectif

Detecter automatiquement une degradation du score ESG d'un ticker de la watchlist et declencher
une alerte Slack/webhook quand la baisse depasse le seuil `esg_alert_threshold`.
Le mecanisme compare `last_esg_score` au dernier enregistrement de `esg_score_history` -- si
la difference est superieure au seuil (en valeur absolue), l'alerte est envoyee.
Ferme la boucle "detection -> alerte" deja en place pour le composite_score (Sprint 57).

## Livrables attendus

### 1. Backend Python

- `app/services/esg_history_service.py` -- nouvelle methode `get_latest_previous(ticker: str) -> float | None` :
  retourne le score ESG avant la derniere entree (2e enregistrement le plus recent) ; renvoie None
  si moins de 2 entrees pour ce ticker

- `app/services/watchlist_service.py` -- nouvelle methode `check_esg_degradation(entry: WatchlistEntry, previous_score: float | None) -> bool` :
  retourne True si `entry.last_esg_score is not None` et `previous_score is not None` et la
  degradation `(previous_score - entry.last_esg_score)` depasse `entry.esg_alert_threshold`

- `app/workers/tasks.py` -- nouvelle tache Celery `run_esg_degradation_check()` :
  itere toutes les entrees watchlist ; pour chacune ayant un `last_esg_score`, appelle
  `esg_history_service.get_latest_previous(ticker)` ; si `check_esg_degradation()` retourne True,
  appelle `webhook_service.send_esg_alert(ticker, last_esg_score)` ET
  `slack_service.send_esg_alert(ticker, last_esg_score, ...)` (meme pattern que Sprint 77/86)

- `app/api/main.py` -- Celery beat : ajouter `run_esg_degradation_check` dans le scheduler,
  execute chaque dimanche a 12h00 UTC (apres le screener 11h00 UTC de Sprint 64)

- `app/api/endpoints/watchlist.py` -- nouveau endpoint `POST /watchlist/check-esg-degradation`
  (admin only) pour declenchement manuel de la verification (meme pattern que les autres endpoints admin)

### 2. Tests CI backend

- `tests/test_esg_degradation.py` -- 5 tests :
  - `get_latest_previous` retourne None si moins de 2 entrees
  - `get_latest_previous` retourne le 2e enregistrement le plus recent
  - `check_esg_degradation` retourne False si degradation inferieure au seuil
  - `check_esg_degradation` retourne True si degradation superieure au seuil
  - `POST /watchlist/check-esg-degradation` retourne 200 avec `{"triggered": N}` (N alertes)

### 3. Tests CI et Vitest

Objectif : +5 tests CI (total >= 1379) -- pas de nouveau composant React, donc pas de Vitest requis.

## Contraintes techniques

- `esg_alert_threshold: float = 5.0` dans `WatchlistEntry` -- seuil en points absolus (ex. : score
  passe de 12 a 6 = baisse de 6 points > seuil 5.0 -> alerte)
- `SlackService` et `WebhookService` sont optionnels -- si absent, la tache ne leve pas d'exception
- Ne pas modifier `record()` dans `EsgHistoryService` -- Sprint 89 preserve
- Ne pas modifier `send_esg_alert()` dans `WebhookService` / `SlackService` -- Sprint 77/86 preserves
- Pattern Celery beat existant dans `app/api/main.py` (Sprint 64/81) -- suivre exactement le meme
- Autorisation admin only sur `POST /watchlist/check-esg-degradation` : verifier Bearer token
  comme les autres endpoints admin (Sprint 62)

---

# SPRINTS SUGGERES (95-99)

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

### Sprint 99 -- Tableau de bord alertes (AlertsPage)

**Objectif** : Nouvelle page `/alerts` listant les alertes recentes (ESG + composite + prix) avec
horodatage, ticker, type d'alerte et valeur. Persistance dans une nouvelle table `alert_history`.
**Complexite** : Moyenne-Elevee
**Justification** : Yves ne voit pas les alertes sans consulter Slack/webhook. Une page centrale
permet de retrouver l'historique des alertes passees.

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
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-22 -- Yves / TradingClaude_
_Sprint 93 complete : Streaming SSE dans ComparePage (opt-in) -- toggle "Streaming en direct" (streamingEnabled defaut false) + handleAnalyze() bifurquant streamAnalyze/postAnalyze + Promise.race 60s dans les deux branches + affichage skill courant data-testid="stream-skill-{ticker}" + erreur SSE inline -- 0 CI ajoutes + 5 Vitest ajoutes (CompareStreaming.test.tsx) -- 1374 CI verts, 197 Vitest verts -- version 8.6.0_
_Sprints 94-99 suggeres : Alerte degradation ESG -> DELETE /history -> Estimation rapide total_count -> Sparkline composite watchlist -> Professionnalisation GitHub -> AlertsPage tableau historique alertes_
