# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-05 — Sprint 153 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.45.0 |
| **Phase active** | Transformation B2B/SaaS — P0 Fondations (plan directeur FinTech) |
| **Sprint actif** | Sprint 159 — E2-S2 sortir les `CREATE TABLE` du lifespan |
| **Dernier sprint complété** | Sprint 158 — E2-S1 socle Alembic (baseline fidèle, upgrade/downgrade validés sur Postgres réel) ✅ |

> **Pivot stratégique 2026-06-05** — la roadmap adopte la **transformation B2B/SaaS** : plan directeur `docs/plan-directeur-fintech-2026.md` (audit FinTech → 44 sprints `E#-S#`, phases P0→P3). Les sprints **154+ exécutent ce backlog** (154 = E1-S1, sécurité fail-closed). Le backlog analyse-tool antérieur (provenance PDF…) est parqué (historique git).

> **Sprint 137 exécuté (2026-05-31, evals Claude réelles)** — clé API temporaire fournie en session. `stock_valuation` (Sonnet, golden 5 cas) : **15 passed / 5 skipped / 0 failed** (8m50s) — la **substitution DCF déterministe (Sprint 132) survit à l'aller-retour tool-use réel** (valeur DCF + matrice = ossature Python), gate sectoriel financières/REIT correct. `earnings_quality` (Haiku, golden 20 cas) : **81 passed / 10 failed / 10 skipped** (33m45s) — **tous les scores déterministes M/Z/F/C/Sloan passent** (Sprints 128/131) et la concordance verdict globale ≥ 80 % tient ; les 10 échecs portent **uniquement sur des champs narratifs libres du LLM**, pas sur les calculs (voir « Drift earnings_quality » ci-dessous). Aucun lien avec le Sprint 140 (extraction tier1 uniquement).

> **Drift `earnings_quality` — état au Sprint 149** : la cause racine (contrat `drapeaux_rouges` sous-spécifié au Sprint 137) est désormais encadrée. Le prompt (`system.md` Cadre 6) porte une consigne de cardinalité **verrouillée par test** (Sprint 149) et **les 5 cadres d'interprétation sont déterministes** (M/Z Sprint 131, F/C Sprint 143, Sloan Sprint 148). Le **replay déterministe hors-ligne** (`tests/skills/test_earnings_deterministic_replay.py`, Sprint 149) confirme la cohérence golden des cadres substitués (Z 20/20, M 13/13, F 17/17 à ±1, Sloan 20/20). **Mesure live résiduelle différée** : la cardinalité `drapeaux_rouges` (champ libre du LLM) ne se mesure qu'avec `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min — absente du conteneur web, exclue du CI) → `ANTHROPIC_API_KEY=… pytest tests/evals/test_earnings_evals.py -m evals`.

> **Re-priorisation 2026-05-29** — La revue expert FinTech (`docs/revue-expert-fintech.md`) a identifié des correctifs P0 de sécurité, livrés au **Sprint 125** (complété). La suite de la file issue de la revue (déterminisme LLM, calculs déterministes, disclaimers, données multi-sources) est dans les sprints suggérés de `prompt-mise-a-jour-roadmap.md`.

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB) ; **scores financiers déterministes** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham) calculés en Python (`app/services/financial_calculations.py`) et substitués au bloc LLM — le modèle interprète, il ne produit plus les chiffres (Sprint 128) ; **sous-composantes auditables** (8 indices Beneish DSRI/GMI/… + termes X1-X5 Altman ; **+ critères détaillés F-Score (9 Piotroski) et signaux C-Score (6 Montier) — booléen `passe`/`present` par signal, Sprint 142** ; **+ libellés d'interprétation au niveau cadre F-Score / C-Score (`forte_qualite`/…/`value_trap` ; `propre`/`signaux_mineurs`/`signaux_multiples`) dérivés du score agrégé déterministe et substitués post-parse — parité avec M/Z déjà déterministes, Sprint 143 ; `sloan.interpretation` rejoint la parité (Sprint 148) — les 5 libellés de cadre sont déterministes**) également calculées en Python et persistées dans l'output — `sum(passe) == f_score` / `sum(present) == c_score` par construction, analyse entièrement rejouable (Sprint 131) ; **ossature DCF déterministe** (`stock_valuation`) — WACC (CMPC), valeur intrinsèque DCF par action et matrice de sensibilité WACC×g calculées en Python (`app/services/valuation_calculations.py`) et substituées au bloc LLM ; le modèle conserve comparables, sectoriel et verdict ; financières/REIT exclues du DCF (méthode sectorielle prime) (Sprint 132)
- `POST /screen` — screener multi-tickers (max 20, asyncio.gather + Semaphore) ; `ScreenEntry.analyzed_at` = date ISO de l'analyse sous-jacente (cache ou fraîche), None pour les échecs (Sprint 109)
- `DELETE /cache/{ticker}` — invalidation cache admin
- `GET /history?ticker=BNS` — historique paginé par cursor ; `?q=ACHAT` pour recherche cross-ticker (Sprint 73) ; `?tags=value,growth` filtre les analyses dont l'annotation porte TOUS les tags (`@>` sur `annotations.tags TEXT[]`, index GIN ; aussi sur `/history-paged`) (Sprint 126)
- `GET /metrics?days=30` — coûts cumulés, taux de cache, top tickers, `skills_cost` (coût USD réparti par skill) + `cache_by_workflow` (taux de cache par workflow) (Sprint 107) + `daily_cost` (coût USD total par jour, clé YYYY-MM-DD) (Sprint 112)
- `GET /metrics/skill-analyses?skill=&days=30` — drill-down : analyses ayant utilisé un skill donné sur la période (ticker / workflow / coût / date), filtre jsonb `skills_used @> [skill]`, 422 si `skill` absent (Sprint 112)
- `GET /telemetry/summary|costs|cache|latency` — métriques observabilité (Sprint 18)
- `GET /performance/{ticker}` — rendement rétrospectif par analyse (Sprint 39)
- `POST /auth/register` — inscription email/mot de passe, cookies JWT httpOnly + CSRF (Sprint Login)
- `POST /auth/login` — authentification cookie, rate limiting Redis 5/15 min (Sprint Login)
- `POST /auth/logout` — blacklist JWT jti + invalidation refresh token (Sprint Login)
- `POST /auth/refresh` — rotation refresh token avec détection de vol par famille (Sprint Login)
- `GET /auth/me` — profil utilisateur authentifié via cookie access_token (Sprint Login)
- `GET /alerts?limit=50` — historique des alertes Celery (ESG + composite + prix) (Sprint 99)
- `GET /semantic-search?q=&k=5` — recherche sémantique RAG dans `investment_knowledge` ; `rag_enabled=false` + `results=[]` si `OPENAI_API_KEY` absente (Sprint 106)
- `GET`/`PUT /preferences/screener` — préférences Screener (tri + filtres) liées au compte authentifié, table `user_preferences` (JSONB, PK `(user_id, key)`) ; 401 si non authentifié, fallback localStorage côté client (Sprint 124)
- `POST /auth/forgot-password` — token réinitialisation itsdangerous 1h (anti-énumération) (Sprint Login)
- `POST /auth/reset-password` — réinitialisation mot de passe avec token signé (Sprint Login)
- `POST /admin/keys` — créer une clé API (admin only) (Sprint 62)
- `GET /admin/keys` — lister toutes les clés (admin only) (Sprint 62)
- `DELETE /admin/keys/{id}` — révoquer une clé (admin only) (Sprint 62)
- `DELETE /history/{analysis_id}` — supprimer une analyse individuelle (admin only, 204/404/422) (Sprint 95)
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible) ; **bloc « Sources des ratios complémentaires »** rendu via `_fmt_ratios_source` quand les ratios earnings/valuation reconstruits (Sprint 144) portent une source+date, ligne omise sinon — parité Graham (Sprint 145)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts
- **Sécurité auth durcie (Sprint 125)** — secret JWT fail-fast (`RuntimeError` au boot hors dev/test si `JWT_SECRET_KEY` absent), blacklist JTI fail-closed (panne Redis → token refusé), réponses 500 assainies (body générique + `correlation_id`, `str(exc)` jamais exposé — global handler + tous les endpoints + flux SSE), CORS durci (`CORS_ORIGINS` CSV via env, méthodes explicites)

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance (avec source + date de récupération affichées sous les ratios — Sprint 134, étendues aux ratios Qualité bénéfices auto-remplis — Sprint 138 ; ratio absent de la source = `None` honnête, jamais `0.0` trompeur — Sprint 135), streaming SSE skill par skill, badge « score depuis cache <24h » ; **source + date des ratios Graham aussi affichées sous la carte Graham de l'analyse rendue/rechargée** (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, threadées jusqu'à la réponse et reconstruites depuis l'historique — Sprint 139 ; **étendues aux cartes Qualité bénéfices et Valorisation** via quatre champs miroir `earnings_ratios_*`/`valuation_ratios_*`, threadés aux 4 sites de construction de `AnalyzeResponse` + reconstruction historique, `data-testid` `earnings-ratios-source`/`valuation-ratios-source` — Sprint 146) ; **provenance par ratio en signal-only** sous la carte Graham après auto-fill — badge discret « P/B via `clé` (repli) » uniquement quand la clé yfinance effective diffère de la clé primaire attendue (`ratios_provenance`, Sprint 141) ; **étendue à l'analyse rendue/rechargée** (`AnalysisResult`) via le composant partagé `RatiosProvenanceNote` en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (Sprint 150)
- **Screener** — batch 2-20 tickers, tri + filtres composite **persistés côté serveur** (continuité multi-appareils, fallback localStorage hors-ligne — Sprint 124) + colonne fraîcheur (badge frais/périmé >24h) + export CSV filtré
- **History** — historique par ticker, recherche full-text `q` cross-ticker (index GIN pg_trgm), filtre par plage de dates, suppression par analyse
- **Watchlist** — positions surveillées, analyses manuelles, seuils ESG + prix éditables inline, score composite historique, export Excel
- **Dashboard v2** — métriques live WebSocket + section détaillée (top tickers, coût par skill avec drill-down, cache par workflow, alertes/jour, tendance coût quotidien), grille responsive 12 colonnes, eval drift
- **Comparer** — 2-5 tickers multi-skills côte à côte (historique ou analyse live opt-in, streaming SSE)
- **ESG** `/esg` — scores ESG de la watchlist (tableau triable, badges ESG_FORT/MODERE/FAIBLE)
- **Alertes** `/alerts` — tableau des alertes Celery récentes
- **Recherche** `/recherche` — recherche sémantique RAG en langage naturel
- **Admin** — gestion des clés API (créer/lister/révoquer)
- **Auth** — pages register / forgot-password / reset-password, session restaurée au montage (authMe)
- **Rapports PDF** — par ticker (ou analyse précise `analysis_id`), screener, watchlist, mensuel (section ESG) ; **bloc d'avertissement réglementaire** (« recherche éducative — pas un conseil financier ») inséré dans chaque rapport (Sprint 129)
- **Avertissement de conformité** — composant `Disclaimer` (variantes `inline`/`footer`) affiché sous les résultats d'analyse, sous le tableau du Screener et sous la comparaison de tickers (Sprint 133), et en pied de page global ; texte centralisé (constante TS + constante Python) (Sprint 129)
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants React structurés et typés depuis les schemas Pydantic (plus aucun JSON brut ; `SkillSection` générique retiré) — Sprints 118-121 ; la carte Z-Score (Earnings Quality) affiche désormais ses termes auditables X1-X5 en grille, en parité avec les 8 indices du M-Score (Sprint 136)

#### Outillage & corpus
- `.claude/rules/` — 16 règles path-scoped (CLAUDE.md allégé) ; `docs/cheatsheet.md` — commandes opérationnelles ; `.gitignore` durci
- `.claude/skills/` — 16/16 skills tier2 documentés (SKILL.md + references) → corpus RAG `investment_knowledge` complet

### Skills opérationnels
18 skills en production (16 tier2 + 2 tier1). Catalogue détaillé (code API → chemin de code) : `.claude/rules/base-connaissances-skills.md` et `CLAUDE.md`.

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Sprint 153 — Mutualiser l'extraction source+date des ratios (`_ratios_trace`) ✅

**Objectif :** Condition du sprint conditionnel remplie — le formateur d'affichage `_fmt_ratios_source` était déjà partagé (Sprint 145) et le gate unifié au Sprint 151 ; restait la **triplication de l'extraction source+date** (`_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace`, clones byte-identiques conservés au Sprint 146). **Sprint backend pur.**

**Livrables :**
- `app/services/ratios_recon.py` — les trois clones fusionnés en un seul helper union-typé `_ratios_trace(ratios: GrahamRatios | EarningsQualityRatios | ValuationRatios | None) -> tuple[str | None, str | None]` (les trois schémas portent les mêmes champs `ratios_fetched_at`/`ratios_source`). Honnêteté None : source conservée même sans date.
- Sites mis à jour : `core.py::_request_ratios_traces` et `reconstruct_ratios_traces`. Import `core.py` réduit à `_ratios_trace`.
- Tests : 3 classes quasi-dupliquées fusionnées en `TestRatiosTraceHelper` (couverture superset — None, 3 types avec/sans date, + cas source-sans-date).

**Version** : 10.39.0
**Tests** : 1 809 backend collectés (1 795 passés, 13 skipped, 1 xfailed — net −1 par consolidation de tests) ; `ruff`/`mypy` verts ; frontend inchangé. Revue indépendante à contexte frais : **CLEAN** — équivalence comportementale vérifiée, condition correctement résolue, zéro référence pendante, aucune régression de typage.

### Sprint 152 — Couverture d'intégration de GET /report/{id} (cœur reconstruct Sprint 147) ✅

**Objectif :** Le chemin 200 du endpoint `GET /report/{analysis_id}` (DB → `reconstruct(require_graham=True)` → PDF) n'était couvert qu'au niveau unité (`_reconstruct_response`). Verrouiller le contrat au niveau endpoint. **Sprint tests pur.**

**Livrables :**
- `tests/services/test_report.py` — deux tests d'intégration HTTP : (1) 200 + `application/pdf` + magic number `%PDF`, reconstruction multi-skills (graham + earnings) ; (2) `result` sans graham → `ValueError` du cœur consolidé → **500 assaini**. Réutilise le helper `_make_result_row` des tests de reconstruction Sprint 147 (DRY).

**Version** : 10.38.0
**Tests** : +2 backend ; `ruff` vert ; frontend inchangé. Revue indépendante à contexte frais : **CLEAN** — les deux tests passent pour les bonnes raisons (500 issu du `ValueError` intentionnel vérifié par spy sur `sanitized_http_500` ; 200 = vrai PDF de bout en bout), aucune pollution (fixture `client` function-scoped réinitialise `db_pool`).

### Sprint 151 — Prédicat partagé `has_ratios_source` (consolidation reuse) ✅

**Objectif :** Le gate « ratio possède une source OU une date » était dupliqué aux deux sites de rendu PDF (`pdf_report_service.py:246` Graham et `:261` earnings/valuation — finding *reuse* écarté au Sprint 145, désormais répété). L'extraire dans un helper partagé. **Sprint backend pur** (gate frontend déjà unifié dans `RatiosSourceNote`).

**Livrables :**
- `app/services/ratios_recon.py` — helper `has_ratios_source(ratios) -> TypeGuard[...]` (union-typé Graham/earnings/valuation, `None` → False). `TypeGuard` pour restreindre l'objet en non-None au site d'appel (accès `ratios_source`/`ratios_fetched_at`).
- `app/services/pdf_report_service.py` — les deux gates remplacés par `has_ratios_source(r)`. Sortie PDF inchangée.
- Tests : +2 (table de vérité source/date/both/neither/None + transverse aux 3 schémas).

**Version** : 10.37.0
**Tests** : +2 backend ; `ruff`/`mypy` verts ; frontend inchangé. Revue indépendante à contexte frais : **CLEAN** — équivalence comportementale aux deux gates, `TypeGuard` correct, aucune autre duplication (grep), aucun cycle d'import.

### Sprint 150 — Provenance par ratio (repli yfinance) sur l'analyse rendue ✅

**Objectif :** Étendre l'affichage signal-only de la provenance par ratio Graham (clé yfinance de repli — posé sur `AnalyzeForm` au Sprint 141) à l'analyse rendue/rechargée (`AnalysisResult`), en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`. **Sprint backend (threading) + frontend (affichage).**

**Livrables :**
- `app/orchestrator/core.py` — champ `AnalyzeResponse.ratios_provenance: dict[str,str] | None` peuplé aux 4 sites live via `_request_ratios_traces` et à la reconstruction historique via `reconstruct_ratios_traces` (rétrocompat : champ absent → None ; exclu de la clé de cache).
- `frontend/src/components/RatiosProvenanceNote.tsx` (nouveau) — logique de repli (`ratiosEnRepli` + clés primaires + badges) **extraite** de `AnalyzeForm` (DRY) et réutilisée par `AnalyzeForm` **et** `AnalysisResult` (testId `result-ratios-provenance`).
- Tests : +2 backend (threading + reconstruction provenance), +10 Vitest (composant partagé + `ratiosEnRepli` + `AnalysisResult` repli/null/clés primaires).

**Version** : 10.36.0
**Tests** : 1 806 backend collectés (+2) ; 442 Vitest verts (+10) ; `tsc`/ESLint 0/0 ; `mypy` vert. Revue indépendante à contexte frais : **CLEAN** — 5 chemins de threading vérifiés, gate None correct, la clé de cache exclut bien `ratios_provenance` (`analysis_cache.py:74`), extraction frontend fidèle sans code mort.

---

## Sprints antérieurs (Sprint 121 → Sprint 0)

L'historique détaillé des sprints complétés est archivé dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) — il n'est **pas** lu à
l'amorçage d'un sprint, afin de réduire le coût en tokens. Seuls les ~4 derniers
sprints restent ici (section « Phases complétées » ci-dessus).

---

## Décisions d'architecture

Les décisions structurantes (choix d'embedding, Tool Use, multi-model routing,
streaming SSE, scoring composite, etc.) sont documentées au fil des sprints dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) et dans `.claude/rules/`
(`api-architecture.md`, `api-orchestrator.md`).

---

## Règles de mise à jour de ce fichier

1. **Après chaque sprint** : passer le sprint de 🔜 → ✅, mettre à jour le tableau
   « État courant » (Version, Sprint actif, Dernier sprint complété) et ajouter un
   bloc détaillé en tête de « Phases complétées ».
2. **Rotation vers l'archive** : ne garder ici que les **~4 derniers sprints** en
   détail. Déplacer les blocs plus anciens vers `docs/roadmap-archive.md`. Ce
   fichier doit rester court (cible < 200 lignes) — c'est lui qui est lu à chaque
   amorçage de session.
3. **Pas de doublon** : un sprint n'apparaît qu'une seule fois. Ne jamais recopier
   l'historique de mémoire — **déplacer**, pas réécrire.
4. **Chiffres de tests vérifiables** : les compteurs (« N CI verts », « N Vitest »)
   doivent provenir d'une commande réelle, pas d'une estimation
   (voir `.claude/rules/workflow-sprint.md`).
5. **Version** : semver — incrément mineur (`X.Y.0`) par sprint livré, patch
   (`X.Y.Z`) pour un correctif isolé.

---

*Roadmap mise à jour le 2026-05-28 — historique complet dans `docs/roadmap-archive.md`.*
