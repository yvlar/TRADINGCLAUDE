# Sprint 168 — E4-S3 : clés API rattachées au tenant

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.54.0 — transformation B2B/SaaS, phase P0→P1)

L'épic **E4 (facturation/SaaS)** avance : le Sprint 166 (E4-S1) a posé `usage_events` (metering par skill), le Sprint 167 (E4-S2) les **quotas par plan** (`plan_limits` + `tenants.plan`, `QuotaService`, `429` au dépassement, borne screener par tenant). Démarre **E4-S3 : faire entrer les clés API dans la tenance** — aujourd'hui une requête authentifiée par clé API (chemin Bearer) retombe sur le tenant legacy car le claim `tenant_id` n'est posé que sur le chemin JWT. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-167 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration. Le frontend peut nécessiter `cd frontend && npm install` (node_modules absent du conteneur).
> ⚠️ **`api_keys` sous RLS ?** `api_keys` n'est PAS dans les 7 tables RLS (Sprint 165/166). Ajouter `api_keys.tenant_id` n'impose PAS la RLS sur cette table (elle est lue par le middleware AVANT que le contexte tenant existe — c'est elle qui le pose). Décider/documenter explicitement : `tenant_id` sert à **résoudre** le tenant à poser dans le ContextVar, pas à isoler `api_keys` par tenant. Suivre le pattern d'écriture `tenant_id or LEGACY_TENANT_ID` des Sprints 162/164.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.54.0)
2. `.claude/rules/api-architecture.md` (middlewares auth/`BearerTokenMiddleware`, contraintes infra) et `.claude/rules/securite.md` (clés API, jamais de secret en clair/log)
3. `app/middleware/auth.py` — `BearerTokenMiddleware` (`:20`), pose `request.state.tenant_id` depuis le claim JWT (`:165`) **mais pas** sur le chemin clé API · `app/services/api_key_service.py` (table `api_keys`, **aucune** colonne `tenant_id` aujourd'hui — `grep -ni tenant` vide, vérifié) · `app/db/tenant_context.py` (`set_current_tenant`/`TenantContextMiddleware` consommateur de `request.state.tenant_id`)

---

## TÂCHE — Sprint 168 (E4-S3) : clés API rattachées au tenant

**Objectif** : fermer le dernier trou de la multi-tenance — une requête authentifiée par **clé API** doit s'exécuter sous le tenant **propriétaire de la clé**, pas le tenant legacy. Prérequis pour facturer/quota-borner les appels programmatiques (M4).

### Spécification
1. **Migration `alembic/versions/0008_api_keys_tenant_id.py`** (chaînée après `0007_plan_limits`) : `ALTER TABLE api_keys ADD COLUMN tenant_id UUID REFERENCES tenants(id)` (nullable → backfill legacy → `SET NOT NULL`, pattern Sprint 162) + index `idx_api_keys_tenant`. **Décider/documenter** : `api_keys` reste **hors RLS** (c'est la table d'authn lue avant le contexte tenant ; sa colonne `tenant_id` sert à *résoudre* le tenant, pas à isoler la table). Downgrade : index → colonne.
2. **`api_key_service`** : exposer `tenant_id` sur `ApiKeyRecord`, le `SELECT` de validation de clé le retourne ; création de clé (`POST /admin/keys`) rattache la clé au tenant courant (`get_current_tenant()` ou `tenant_id or LEGACY_TENANT_ID`).
3. **`BearerTokenMiddleware`** (`app/middleware/auth.py`) : sur le chemin clé API (validation réussie), poser `request.state.tenant_id = record.tenant_id` — symétrique au chemin JWT (`:165`). Le `TenantContextMiddleware` (déjà en place, E3-S4) pose alors le ContextVar → RLS + quotas + écritures défaultent au bon tenant.
4. **Cohérence quota/metering** : une analyse lancée via clé API consomme désormais le quota (Sprint 167) et émet `usage_events` (Sprint 166) **sous le tenant de la clé** — vérifier que le threading atteint bien `QuotaService`/`UsageEventService`.

### Tests / validation
- **Migration** (`tests/test_alembic_api_keys_tenant.py`, sans DB) : chaînage après `0007`, colonne `tenant_id` + FK + backfill legacy + `SET NOT NULL`, index, downgrade ordre inverse. Modèle : `tests/test_alembic_*`.
- **Unitaires** (`tests/services/`) : `api_key_service` retourne `tenant_id` ; création rattache au tenant courant ; défaut legacy.
- **Middleware** (`tests/`) : chemin clé API valide → `request.state.tenant_id` = tenant de la clé ; clé legacy → tenant legacy.
- **Intégration** (`@pytest.mark.integration`, PG migré) : requête via clé API d'un tenant B → écritures/quota sous B, pas legacy (prouver via le chemin réel middleware → ContextVar → RLS).
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts ; `cd frontend && npm run typecheck` + Vitest verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me`
**Objectif** : exposer `tenant_id` (et le nom du tenant) dans la réponse `/auth/me`, désormais cohérent puisque le contexte tenant est threadé (E3-S4) et borné (E4-S2/S3).
**Complexité** : Faible.
**Justification** : le Sprint 161 avait **délibérément omis** `tenant_id` de la réponse publique tant que le threading n'existait pas — l'exposition devient cohérente (préparation UI multi-tenant + affichage du plan).
**Référence** : `tenant_id` absent de `UserPublic` — commenté `app/models/auth.py:64` (vérifié cette session) ; `users.tenant_id` déjà lu par `user_service.get_by_id` (`SELECT … tenant_id …`, `app/services/user_service.py:81`, vérifié). L'enrichissement de `UserPublic` + le `JOIN`/lookup du nom de tenant sont **à créer**.

### Sprint 170 — E4-S5 : endpoint d'agrégation de consommation (`GET /usage`)
**Objectif** : exposer la consommation agrégée du tenant courant (coût/tokens par skill, par jour, total période) à partir de `usage_events`, pour le futur tableau de bord de facturation + l'affichage « N/N analyses ce mois » (quota Sprint 167).
**Complexité** : Moyenne.
**Justification** : rend le metering (166) + quotas (167) actionnables côté produit ; prérequis d'une page « Facturation » frontend.
**Référence** : `usage_events` existe (`alembic/versions/0006_usage_events.py`, `app/services/usage_event_service.py`) ; pattern d'agrégation par jour/skill déjà présent pour les coûts globaux (`get_metrics` → `daily_cost`, `app/orchestrator/core.py:1981`, vérifié — à adapter en version **scopée tenant** via la RLS d'`usage_events`). L'endpoint `/usage` et son agrégation par tenant sont **à créer**.

### Sprint 171 — E4-S6 : purge de rétention par plan (`retention_days`)
**Objectif** : appliquer `plan_limits.retention_days` (posé au Sprint 167 mais inappliqué) — tâche Celery qui purge les analyses/événements au-delà de la rétention du plan de chaque tenant.
**Complexité** : Moyenne.
**Justification** : transforme `retention_days` d'une colonne dormante en politique réelle (différenciation plan free/pro + conformité données) ; complète les quotas par une borne temporelle.
**Référence** : `retention_days` existe (`alembic/versions/0007_plan_limits.py`, seedé free=30/pro=365, vérifié cette session) ; le scheduler Celery beat existe (`run_scheduled_screener`, cf. ROADMAP « Celery beat »). La tâche de purge scopée par plan/tenant est **à créer**.

### Sprint 172 — E4-S7 : intégration Stripe Billing (abonnements + usage)
**Objectif** : brancher Stripe (abonnement par plan + facturation à l'usage depuis `usage_events`), webhooks de cycle de vie (souscription, paiement, dunning), mapping plan↔price.
**Complexité** : Élevée.
**Justification** : convertit le socle metering+quotas+clés-tenant (166-168) en revenu réel (B1/B2 du plan directeur) ; dernière marche de M4.
**Référence** : `usage_events` (166), `plan_limits`/`tenants.plan` (167) et `api_keys.tenant_id` (168) sont les socles ; toute l'intégration Stripe (SDK, webhooks, mapping plan↔price, `.env` clés Stripe) est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.54.0),
.claude/rules/api-architecture.md et securite.md.
Sprint actif : 168 — E4-S3 (clés API rattachées au tenant). Créer la migration
0008_api_keys_tenant_id (colonne tenant_id + FK + backfill legacy + SET NOT NULL + index ;
api_keys reste hors RLS — documenter pourquoi : table d'authn lue avant le contexte tenant),
exposer tenant_id sur ApiKeyRecord et le rattacher à la création de clé, et poser
request.state.tenant_id depuis la clé dans BearerTokenMiddleware (symétrique au chemin JWT)
pour que le ContextVar/RLS/quota/metering ciblent le tenant de la clé.
Démarre un Postgres local (recette dans ce fichier ; installer alembic dans .venv) et PROUVE
qu'une requête par clé API d'un tenant B écrit/quota sous B (pas legacy) via le chemin réel.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ + frontend typecheck/Vitest ; tenant de la
clé threadé bout-en-bout vérifié.
```
