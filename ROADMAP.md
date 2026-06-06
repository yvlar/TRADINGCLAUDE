# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-06 — Sprint 162 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.49.0 |
| **Phase active** | Transformation B2B/SaaS — P0 Fondations (plan directeur FinTech) |
| **Sprint actif** | Sprint 163 — E3-S3 RLS PostgreSQL (policy `tenant_id = current_setting`) |
| **Dernier sprint complété** | Sprint 162 — E3-S2 rattacher les 6 tables métier au tenant (`tenant_id NOT NULL` + index + backfill legacy) ✅ |

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
- `GET /admin/audit-log?limit=50` — journal d'audit append-only des mutations métier (watchlist, annotation, clé API), admin only (Sprint 160 — traçage best-effort côté service via `AuditLogService.record`, table `audit_log` posée par Alembic, `tenant_id` nullable en forward-compat E3)
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

### Sprint 162 — E3-S2 : rattacher les 6 tables métier au tenant ✅

**Objectif :** Propager la dimension tenant aux **données** — `tenant_id UUID NOT NULL` (FK → `tenants`) + index sur chacune des 6 tables métier, avec backfill vers le tenant « legacy » (constante `LEGACY_TENANT_ID` posée au Sprint 161). Aucune RLS ni middleware de contexte ici (E3-S3/S4) ; le tenant legacy reste le défaut des écritures tant que le threading n'est pas câblé. 2ᵉ marche de l'épic E3.

**Livrables :**
- `alembic/versions/0004_business_tenant_id.py` (nouveau) — révision chaînée après `0003_tenants`. Pour les 6 tables (`analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`) : `ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)` (nullable) → backfill legacy (`WHERE tenant_id IS NULL`) → `SET NOT NULL` → index `idx_<table>_tenant`. DDL bâti par template sur un tuple `_TABLES` (uniformité prouvable, zéro copier-coller). Downgrade en ordre FK inverse (index → colonne) par table, idempotent. Littéral UUID legacy figé (parité ↔ `LEGACY_TENANT_ID` verrouillée par test).
- **Politique `ON DELETE` documentée** : `NO ACTION` (restrict, défaut PostgreSQL — comme `users.tenant_id` au Sprint 161). Supprimer un tenant **échoue** tant qu'il porte des données métier ; le hard-delete relève d'un sprint dédié, jamais d'un `CASCADE` silencieux.
- **Écritures applicatives** (6 sites d'INSERT) : `core.py::_persist` (analysis_history), `watchlist_service`, `annotation_service`, `esg_history_service`, `composite_history_service`, `alert_history_service` — chacun accepte un `tenant_id: UUID | None = None` (défaut legacy via `tenant_id or LEGACY_TENANT_ID`, idiome partagé avec `user_service`), `tenant_id` ajouté en dernier binding de l'INSERT. `annotation.upsert` : tenant posé à l'INSERT seulement, **non** réécrit en `ON CONFLICT` (ré-annoter ne déplace pas le tenant). Décision d'altitude : **service-level explicit sans DB `DEFAULT`** → tout futur INSERT oubliant le tenant échoue franchement (NOT NULL) au lieu de mal-rattacher silencieusement (prépare le threading E3-S4).

**Validation runtime (Postgres 16 local)** : `upgrade head` → les 6 tables portent `tenant_id NOT NULL` + index `idx_<table>_tenant` + FK `confdeltype=NO ACTION` ; une ligne insérée **avant** la migration dans chaque table est backfillée au legacy ; `DELETE` du tenant legacy **refusé** (données référencées) ; `downgrade 0003` → colonnes/index retirés (0 colonne) ; re-`upgrade head` idempotent ; cycle CI `downgrade base → upgrade head` vert.

**Version** : 10.49.0
**Tests** : 2 002 backend collectés (1 988 passés, 13 skipped, 1 xfailed — +14 : forme de migration paramétrée sur 6 tables [colonne/FK/backfill/ordre backfill-avant-NOT-NULL/index/parité littéral↔constante], écritures défaut-legacy/tenant-explicite des 5 services, défaut legacy de `_persist`) ; `ruff`/`mypy app/` verts ; frontend inchangé ; pas d'eval (aucun prompt skill ni orchestrateur de skills touché). Revue indépendante à contexte frais : **correctness CLEAN** (split DDL sûr, placeholders `$n` alignés aux args aux 6 sites, ON CONFLICT préserve le tenant, binding asyncpg `uuid.UUID`, aucun appelant cassé — défauts présents) ; **qualité** : 1 finding traité (tests d'écriture paramétrés legacy/explicite, 10→5 fonctions), 1 écarté (helper `_load` triplé dans les tests de migration = convention pré-existante, refactor hors périmètre de ce sprint).

### Sprint 161 — E3-S1 : socle tenant (`tenants` + `users.tenant_id`) ✅

**Objectif :** Poser les fondations de la multi-tenance — table `tenants`, colonne `users.tenant_id` (FK), tenant « legacy » de backfill — sans isolation RLS ni rattachement des 6 tables métier (E3-S2/S3), en gardant l'auth 100 % rétrocompatible. 1ʳᵉ marche de l'épic E3 (bloqueur n°1).

**Livrables :**
- `alembic/versions/0003_tenants.py` (nouveau) — révision chaînée après `0002_audit_log` : table `tenants(id, name, slug UNIQUE, created_at)` + tenant legacy déterministe (UUID fixe, slug `legacy`, `ON CONFLICT DO NOTHING`) ; `users.tenant_id` ajouté nullable → backfill legacy (`WHERE tenant_id IS NULL`) → `SET NOT NULL` → index `idx_users_tenant`. Downgrade en ordre FK inverse (index → colonne → table), idempotent.
- `app/models/tenant.py` (nouveau) — source unique des valeurs du tenant legacy (`LEGACY_TENANT_ID`/`SLUG`/`NAME`) ; la migration en garde une copie littérale (artefact figé), parité verrouillée par test.
- `app/services/user_service.py` — `create_user` accepte un `tenant_id` optionnel (défaut = legacy) ; `tenant_id` exposé dans le `RETURNING` et les `SELECT` (`authenticate`/`get_by_id`).
- `app/models/auth.py` — décision documentée : `tenant_id` **absent** de la réponse publique `/auth/me` ce sprint (exposition pertinente seulement avec le threading de contexte tenant, E3-S4).
- Rétrocompat auth : `POST /auth/register` et `/auth/login` inchangés côté API ; nouvel inscrit rattaché au legacy par défaut.

**Validation runtime (Postgres 16 local)** : `upgrade head` → table `tenants` + tenant legacy présent + un `users` inséré **avant** la migration backfillé au legacy + `tenant_id NOT NULL` + index + FK `users_tenant_id_fkey` ; `downgrade 0002` → colonne/index/table retirés ; re-`upgrade head` idempotent (legacy + backfill préservés).

**Version** : 10.48.0
**Tests** : 1 951 backend collectés (1 937 passés, 13 skipped, 1 xfailed — +17 : forme/chaînage/ordre de migration, parité littéraux↔constantes, `create_user` legacy/explicite/dict) ; `ruff`/`mypy app/` verts ; frontend inchangé ; pas d'eval (aucun prompt skill ni orchestrateur touché). Revue indépendante à contexte frais : **correctness CLEAN** (split DDL sûr, ordre backfill-avant-NOT-NULL, downgrade ordre FK inverse, binding asyncpg `uuid.UUID`, `RETURNING` rétrocompatible) ; **qualité** : 2 findings traités (modèle Pydantic `Tenant` mort retiré ; constantes slug/name verrouillées par test au lieu de rester orphelines), 3 écartés (triplication `_execute_each`/`_load` = artefacts figés hors périmètre ; FK `ON DELETE` = décision délibérée E3-S2/S3).

### Sprint 160 — E2-S3 : journal d'audit `audit_log` append-only ✅

**Objectif :** Créer une table `audit_log` append-only et y tracer chaque mutation métier (watchlist, annotation, clé API), consultable par un admin. Prérequis conformité Loi 25 (traçabilité des accès/modifications). Clôt l'épic E2.

**Livrables :**
- `alembic/versions/0002_audit_log.py` (nouveau) — révision chaînée après `0001_baseline` : table `audit_log(id, tenant_id UUID NULL, user_id UUID NULL, action, cible_type, cible_id, metadata JSONB, created_at)` + index `(created_at DESC)` et `(cible_type, cible_id)`. `tenant_id` nullable en **forward-compat E3** (pas de table `tenants` ici) ; `user_id` sans FK (l'audit survit à la suppression d'un compte ; mutations clé API sans utilisateur).
- `app/services/audit_log_service.py` (nouveau) — `AuditLogService` append-only : `record(...)` (INSERT pur, aucun UPDATE/DELETE) + `list_recent(limit)` (tri `created_at DESC`). Helper `record_audit_safe(audit, …)` — traçage **best-effort** : un échec d'audit n'avorte jamais la mutation métier (log + continue).
- Traçage aux 3 sites de mutation (best-effort) : `watchlist_service.py` (`add_entry`/`delete_entry`), `annotation_service.py` (`upsert`), `api_key_service.py` (`create_key`/`revoke_key`) — `audit_log` injecté en kwarg optionnel (rétrocompat des constructeurs existants : workers/tests inchangés).
- `app/api/endpoints/admin.py` — `GET /admin/audit-log?limit=50` (admin only via `_require_admin`, 401/403 non-admin).
- `app/api/main.py` — `AuditLogService` instancié dans le lifespan et injecté aux 3 services + exposé sur `app.state`.

**Validation runtime (Postgres 16 local)** : `alembic upgrade head` → table `audit_log` + 2 index présents ; `downgrade base` → table supprimée ; re-`upgrade head` idempotent (couvert aussi par le job CI `migrations`).

**Version** : 10.47.0
**Tests** : 1 934 backend collectés (1 920 passés, 13 skipped, 1 xfailed — +40 : service append-only, traçage 3 sites + best-effort, endpoint admin 200/401/403/422, forme de migration) ; `ruff`/`mypy app/` verts ; frontend inchangé. Revue indépendante à contexte frais : **correctness CLEAN** (binding asyncpg `$n::uuid` NULL-safe, sérialisation JSONB, contrat append-only, garantie best-effort vérifiée, aucune régression de constructeur) ; **qualité** : 1 finding traité (test d'introspection source `getsource` retiré — fragile, redondant avec le test de contrat `dir()`).

### Sprint 159 — E2-S2 : le lifespan n'émet plus de DDL ✅

**Objectif :** Retirer le DDL inline du lifespan (`app/api/main.py:160-324` — tous les `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN` / `CREATE INDEX`) maintenant qu'Alembic (Sprint 158) porte le schéma. Le boot ne fait plus de DDL ; le schéma est appliqué par `alembic upgrade head`. **Sprint backend + infra, aucun changement de schéma.**

**Livrables :**
- `app/api/main.py` — bloc de migrations inline supprimé (−165 lignes) ; le lifespan ne crée que le pool asyncpg, zéro `db_pool.execute`. Commentaire : schéma porté par Alembic, appliqué hors du process API.
- `infra/docker-entrypoint.sh` (nouveau) — `alembic upgrade head` avant uvicorn, gardé par `RUN_MIGRATIONS_ON_BOOT` (défaut `true`) ; `set -e` + `exec "$@"` (PID 1 / signaux préservés).
- `Dockerfile` — embarque `alembic.ini` + `alembic/` + l'entrypoint (`ENTRYPOINT` → entrypoint, `CMD` → uvicorn).
- `docker-compose.yml` — le worker fixe `RUN_MIGRATIONS_ON_BOOT=false` (une seule migration concurrente, portée par `copilote`).
- `infra/postgres/init.sql` — réduit à un commentaire pointant vers Alembic (source de vérité unique ; no-op gardé pour rétrocompat du mount initdb).
- `.env.example` + `docs/architecture/…` (§6.3 + §7.3) — `RUN_MIGRATIONS_ON_BOOT` documenté ; choix entrypoint expliqué.
- `tests/api/test_boot_no_ddl.py` (nouveau) — le lifespan ne fait ni `execute` ni `executemany` (zéro DDL au boot) ; liste de skills importée de `conftest` (source unique anti-dérive).

**Validation runtime (Postgres 16 local)** : `alembic upgrade head` → 10 tables ; **boot du lifespan via un rôle EN LECTURE SEULE** (CREATE refusé) → succès, preuve directe du zéro-DDL ; `alembic downgrade base` → schéma supprimé ; re-upgrade idempotent.

**Version** : 10.46.0
**Tests** : 1 894 backend collectés (1 880 passés, 13 skipped, 1 xfailed — +1 boot no-DDL) ; `ruff`/`mypy app/` verts ; frontend inchangé. Revue indépendante à contexte frais : **correctness CLEAN** (couverture de schéma vérifiée — chaque table/index/colonne retirée est dans le baseline `0001` ; critère read-only satisfait) ; **qualité** : 3 findings traités (liste de skills consolidée sur `conftest`, commentaire lifespan corrigé, `init.sql` allégé).

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
