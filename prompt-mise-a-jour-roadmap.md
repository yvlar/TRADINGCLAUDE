# Sprint 96 -- Estimation rapide total_count via pg_class

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
4. `app/orchestrator/core.py` -- `Orchestrator.get_history_paged()` et `get_history()`
5. `app/api/main.py` -- endpoint `/history-paged` existant
6. `frontend/src/pages/HistoryPage.tsx` -- page historique existante (pagination Sprint 90, suppression Sprint 95)
7. `frontend/src/api/analyze.ts` -- `getHistoryPaged()` et `deleteAnalysis()` existants

---

# ETAT DU PROJET A CE JOUR

| Champ                   | Valeur                                                       |
| ----------------------- | ------------------------------------------------------------ |
| Version                 | 8.8.0                                                        |
| Phase active            | Phase 3 -- Pipeline de synthese                              |
| Sprint actif            | **Sprint 96 -- Estimation rapide total_count via pg_class**  |
| Dernier sprint complete | Sprint 95 -- Suppression des analyses obsoletes ✅           |

## Infrastructure backend (operationnelle)

- 18 skills en production (16 Tier2 + 2 Tier1) -- tous documentes dans `.claude/skills/`
- `DELETE /history/{analysis_id}` -- suppression admin individuelle (Sprint 95)
- `Orchestrator.delete_analysis()` -- supprime annotation orpheline puis analyse, True/False (Sprint 95)
- `POST /analyze-stream` -- streaming SSE skill par skill (Sprint 93)
- `POST /watchlist/check-esg-degradation` -- verif manuelle degradation ESG (admin, Sprint 94)
- `run_esg_degradation_check` Celery beat dimanche 12h00 UTC (Sprint 94)
- `GET /history-paged?ticker=&q=&page=1&page_size=10` -- pagination offset/limit (Sprint 90)
- `EsgHistoryService` + table `esg_score_history` + `GET /esg-history/{ticker}` (Sprint 89)
- `SlackService` -- send_text/send_esg_alert/send_screener_summary/send_monthly_report_summary (Sprint 86)
- 1382 tests au total (1382 CI verts hors e2e et evals)

## Frontend React (operationnel)

- SPA React 18 + TypeScript strict -- port 5173
- 9 pages : Analyze, Screener, History, Watchlist, Dashboard, Login, Admin, Comparer, ESG
- **HistoryPage** -- pagination numerotee (Sprint 90) + export annotations CSV/Excel (Sprint 85) + bouton Supprimer par analyse avec confirmation (Sprint 95)
- 200 tests Vitest verts

---

# TACHE -- SPRINT 96

## Objectif

Ajouter un parametre optionnel `?fast_count=true` a `GET /history-paged` qui remplace le
`SELECT COUNT(*)` exact par une estimation rapide via `pg_class.reltuples`. Indolore tant que
la table est petite ; prevu pour eviter un goulot d'etranglement quand `analysis_history`
depassera 100k lignes.

## Livrables attendus

### 1. Backend Python

- `app/orchestrator/core.py` -- modifier `Orchestrator.get_history_paged()` :
  accepter un parametre `fast_count: bool = False` ; quand True et sans filtre ticker/q/dates,
  utiliser `SELECT reltuples::bigint FROM pg_class WHERE relname = 'analysis_history'` au lieu de
  `SELECT COUNT(*)` ; sinon retomber sur COUNT(*) exact (le fast_count est seulement utile
  sans filtres car `pg_class` donne un total global, pas un count filtre)

- `app/api/main.py` -- modifier l'endpoint `GET /history-paged` :
  ajouter `fast_count: bool = False` comme query parameter ; le passer a `orchestrator.get_history_paged()`

### 2. Tests CI backend

- `tests/test_history_paged_fast_count.py` -- 3 tests :
  - `fast_count=False` (defaut) appelle `fetchval` avec `SELECT COUNT(*)`
  - `fast_count=True` sans filtre appelle `fetchval` avec `pg_class` au lieu de COUNT(*)
  - `fast_count=True` avec filtre ticker => retombe sur COUNT(*) exact (securite coherence)

---

# SPRINTS SUGGERES (97-101)

### Sprint 97 -- Score composite historique dans WatchlistPage

**Objectif** : Ajouter un mini-graphique sparkline recharts dans WatchlistTable pour chaque ticker
montrant l'evolution du composite_score sur 30 jours, en utilisant `GET /composite-history/{ticker}`.
**Complexite** : Moyenne
**Justification** : Les donnees existent deja (Sprint 57/60) -- les rendre visibles directement dans
la watchlist sans naviguer vers le Dashboard.

### Sprint 98 -- Professionnalisation GitHub (CI complet + qualite code)

**Objectif** : Rendre le depot GitHub professionnel et pret pour des contributeurs exterieurs :
linting/formatage automatique, type-checking CI, templates GitHub, fichiers de gouvernance.
**Complexite** : Moyenne
**Justification** : Le depot est maintenant public. Sans ces fichiers, le projet parait abandonne.

### Sprint 99 -- Tableau de bord alertes (AlertsPage)

**Objectif** : Nouvelle page `/alerts` listant les alertes recentes (ESG + composite + prix) avec
horodatage, ticker, type d'alerte et valeur. Persistance dans une nouvelle table `alert_history`.
**Complexite** : Moyenne-Elevee
**Justification** : Yves ne voit pas les alertes sans consulter Slack/webhook.

### Sprint 100 -- Export analyse individuelle en PDF enrichi

**Objectif** : Bouton "Exporter cette analyse" dans la vue detail d'une analyse historique
(HistoryPage), generant un PDF complet sur une page avec tous les skills executes, les verdicts
et les recommandations. Reutilise `PdfReportService` (Sprint 63).
**Complexite** : Moyenne
**Justification** : Les donnees existent deja dans `GET /history?ticker=X` ; les rendre
exportables directement sans re-executer une analyse.

### Sprint 101 -- Notification browser (Web Push) pour les alertes Celery

**Objectif** : Envoyer une notification navigateur (Web Push API) quand Celery detecte une
alerte ESG ou composite, sans dependance a Slack ni webhook externe.
**Complexite** : Elevee
**Justification** : Alternative self-hosted a Slack pour les alertes temps reel.

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
- **Degradation ESG Sprint 94** : `get_latest_previous()` + `check_esg_degradation()` + `run_esg_degradation_check` Celery beat dimanche 12h00 + `POST /watchlist/check-esg-degradation` (admin) -- ne pas modifier
- **Suppression analyses Sprint 95** : `Orchestrator.delete_analysis()` + `DELETE /history/{analysis_id}` (admin, 204/404/422) + `deleteAnalysis()` frontend + bouton 🗑 HistoryPage `data-testid="delete-analysis-{id}"` -- ne pas modifier
- **Robustesse OneDrive** : si la synchro OneDrive coupe une edition (fichier tronque a mi-contenu), restaurer en appendant la queue manquante via `python3 ... open(path, 'ab')` en chunks de ~600 bytes maximum ; toujours verifier `wc -l` + balance braces/parens apres une edition critique

---

_Roadmap mise a jour le 2026-05-22 -- Yves / TradingClaude_
_Sprint 95 complete : Suppression des analyses obsoletes -- Orchestrator.delete_analysis() + DELETE /history/{id} admin 204/404/422 + deleteAnalysis() frontend + bouton 🗑 HistoryPage + 3 tests CI (test_delete_history.py) + 3 tests Vitest (DeleteAnalysis.test.tsx) -- 1382 CI verts, 200 Vitest verts -- version 8.8.0_
_Sprints 96-101 suggeres : Estimation rapide total_count → Sparkline composite watchlist → Professionnalisation GitHub → AlertsPage → Export PDF analyse individuelle → Web Push alertes_
