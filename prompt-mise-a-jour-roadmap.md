# Sprint 166 — E4-S1 : metering (`usage_events` append-only)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.52.0 — transformation B2B/SaaS, phase P0→P1)

**Épic E3 (isolation multi-tenant) CLOS** au Sprint 165 : l'isolation RLS des 6 tables métier est prouvée table par table en **rouge→vert** sous rôle NOSUPERUSER (matrice paramétrée `tests/integration/test_rls_isolation.py`, gate CI), et la policy a passé une **revue OWASP** (`docs/revue-owasp-rls-2026-06.md` — 2 risques résiduels hors code suivis : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS`, scoping tenant de `/report`). Démarre **E4 (facturation/SaaS)** par **E4-S1 metering** : une table `usage_events` append-only, émise par l'orchestrateur à granularité **par skill**, source de vérité unique de la consommation par tenant. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-165 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration.
> ⚠️ **`usage_events` portera `tenant_id NOT NULL` → elle entre dans le périmètre RLS.** Suivre le pattern des 6 tables (migration `0005_business_rls.py`) : `ENABLE`+`FORCE ROW LEVEL SECURITY` + policy `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`. Sinon un pool sans GUC verrait 0 ligne et ses INSERT échoueraient au `WITH CHECK`. Si tu prouves l'isolation en intégration, **étendre le `GRANT` du rôle `rls_tester`** (`.github/workflows/ci.yml`) à `usage_events` (+ séquence si BIGSERIAL).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.52.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7-§8 épic E4 ligne `E4-S1`** (metering) et **jalon M4** (facturation)
3. `.claude/rules/api-orchestrator.md` (point d'émission dans l'orchestrateur, pattern WORKFLOWS, `optional=True`) et `.claude/rules/tests-pyramide.md` (niveau intégration, marqueur `@pytest.mark.integration`, patch `call_claude_with_retry` — l'orchestrateur ne doit jamais appeler Claude réel en test)
4. `app/services/audit_log_service.py` (pattern **append-only** `record(...)` à cloner) · `app/orchestrator/core.py:1706` (`_persist`, déjà tenant-aware via `resolve_tenant`, import `:15`) et le hook par-skill `observability.record_skill_execution(SkillTrace(...))` (~`core.py:616`, `cost_usd`/`tokens_input`/`tokens_output` par skill déjà disponibles) · `alembic/versions/0005_business_rls.py` (dernière révision — chaîner après)

---

## TÂCHE — Sprint 166 (E4-S1) : metering `usage_events`

**Objectif** : poser une table **`usage_events` append-only** qui enregistre, **par skill exécuté** (pas seulement par analyse), la consommation facturable d'un tenant — fondation unique de l'agrégation de facturation (E4-S2 quotas, E4-S4 export). Ouvre l'épic E4.

### Spécification
1. **Migration `alembic/versions/0006_usage_events.py`** (chaînée après `0005_business_rls`) : table `usage_events(id, tenant_id UUID NOT NULL REFERENCES tenants(id), skill TEXT NOT NULL, workflow TEXT NOT NULL, cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0, tokens_input INTEGER NOT NULL DEFAULT 0, tokens_output INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())` + index `(tenant_id, created_at DESC)`. **Pas de FK vers `analysis_history`** (append-only, doit survivre à la purge d'une analyse) — décision à documenter. **RLS obligatoire** : `ENABLE`+`FORCE` + policy `usage_events_tenant_isolation` (USING + WITH CHECK sur le prédicat tenant standard). Downgrade idempotent (DROP POLICY → DISABLE → DROP TABLE). Choisir `id` UUID (`gen_random_uuid()`) **ou** BIGSERIAL — si BIGSERIAL, penser au `GRANT USAGE` séquence en CI.
2. **`app/services/usage_event_service.py`** (nouveau) — `UsageEventService` **append-only** calqué sur `AuditLogService` : `record(tenant_id, skill, workflow, cost_usd, tokens_input, tokens_output)` (INSERT pur, jamais UPDATE/DELETE) + helper `record_usage_safe(...)` **best-effort** (un échec de metering n'avorte JAMAIS l'analyse — log + continue, comme `record_audit_safe`). `tenant_id` défaut `resolve_tenant(...)` (idiome partagé).
3. **Émission depuis l'orchestrateur** (`app/orchestrator/core.py`) : à chaque skill exécuté avec succès (là où `observability.record_skill_execution(SkillTrace(...))` est déjà appelé), émettre **en parallèle** un `usage_events` best-effort. Réutiliser le `workflow` de la requête et le `cost_usd`/`tokens_*` de l'`UsageDetail`/usage du skill. **Un cache hit (`cost_usd=0`) n'émet rien** (rien n'est consommé) — décision à documenter. Le service est injecté optionnellement (constructeur/`app.state`, rétrocompat : workers/tests qui ne le fournissent pas restent verts).
4. **Lifespan** (`app/api/main.py`) : instancier `UsageEventService` et l'injecter à l'orchestrateur + exposer sur `app.state` (suivre le câblage d'`AuditLogService`, Sprint 160).

### Tests / validation
- **Unitaires** (`tests/services/`) : `record` construit l'INSERT attendu ; `record_usage_safe` avale une exception DB sans la propager (best-effort) ; défaut `resolve_tenant`.
- **Migration** (`tests/test_alembic_usage_events.py`, sans DB) : forme/chaînage de révision, présence colonne/index/RLS `ENABLE`+`FORCE`+policy USING+WITH CHECK, downgrade ordre inverse. Modèle : `tests/test_alembic_business_rls.py`.
- **Intégration** (`@pytest.mark.integration`, PG local migré) : un skill exécuté émet exactement 1 ligne `usage_events` pour le tenant courant ; un cache hit n'en émet aucune ; **isolation RLS** d'`usage_events` (réutiliser/étendre la matrice `test_rls_isolation.py` — `usage_events` est une 7ᵉ table RLS).
- **Orchestrateur** : l'émission ne doit pas appeler Claude réel — `call_claude_with_retry` patché (cf. `tests-pyramide.md`). Un test orchestrateur existant vérifie que l'analyse réussit même si `UsageEventService` lève (best-effort).
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts. **Eval** : l'orchestrateur est touché mais aucun **prompt de skill** ne change — émission de metering uniquement. Lancer une eval ciblée seulement si le routing/parallélisme des skills est modifié ; sinon le dire explicitement (pas de changement de prompt → pas d'eval).

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 167 — E4-S2 : quotas par plan + quotas screener par tenant
**Objectif** : table `plan_limits` (analyses/mois, taille screener, rétention) + compteur Redis ; `429` clair au dépassement ; **inclut les quotas screener par tenant différés de l'E3-S4** (borne tickers/analyses par tenant).
**Complexité** : Moyenne.
**Justification** : transforme la multi-tenance en offre commerciale ; consomme le metering `usage_events` (Sprint 166) pour compter, et absorbe le quota screener explicitement reporté au Sprint 164.
**Référence** : rate-limit Redis existant `app/middleware/rate_limit.py`, monté `app/api/main.py:478` (à étendre par tenant/plan) ; le `ContextVar` tenant (`app/db/tenant_context.py`, Sprint 164) fournit déjà le tenant courant pour cléer le compteur. `plan_limits` et l'agrégation de `usage_events` sont **à créer**.

### Sprint 168 — E4-S3 : clés API rattachées au tenant
**Objectif** : `api_keys.tenant_id` (FK) + résolution du tenant pour chaque appel programmatique (chemin Bearer), pour que les clés API entrent dans la tenance (M4).
**Complexité** : Faible.
**Justification** : ferme le dernier trou de la multi-tenance — aujourd'hui une requête par clé API retombe sur le tenant legacy (`BearerTokenMiddleware` ne pose pas `tenant_id` sur le chemin Bearer, `app/middleware/auth.py:111-147`).
**Référence** : table `api_keys` gérée par `app/services/api_key_service.py` (**sans** colonne `tenant_id` aujourd'hui — `grep -ni tenant app/services/api_key_service.py` vide, vérifié) ; la colonne `tenant_id` sur `api_keys` est **à créer** (migration chaînée après `0006_usage_events`). Le `ContextVar`/middleware tenant (Sprint 164) est en place : il suffira de poser `request.state.tenant_id` depuis l'enregistrement de clé sur le chemin Bearer de `app/middleware/auth.py`.

### Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me`
**Objectif** : exposer le `tenant_id` (et le nom du tenant) dans la réponse `/auth/me`, désormais pertinent puisque le contexte tenant est threadé.
**Complexité** : Faible.
**Justification** : le Sprint 161 avait **délibérément omis** `tenant_id` de la réponse publique tant que le threading n'existait pas (`app/models/auth.py:64`) — E3-S4 l'a livré, l'exposition devient cohérente (préparation UI multi-tenant).
**Référence** : `tenant_id` absent de la réponse publique — commenté `app/models/auth.py:64` ; `users.tenant_id` déjà lu par `user_service.get_by_id` (`SELECT … tenant_id …`, `app/services/user_service.py:81`).

### Sprint 170 — E4-S5 : endpoint d'agrégation de consommation (`GET /usage`)
**Objectif** : exposer la consommation agrégée du tenant courant (coût/tokens par skill, par jour, total période) à partir de `usage_events`, pour le futur tableau de bord de facturation.
**Complexité** : Moyenne.
**Justification** : rend le metering (Sprint 166) actionnable côté produit et alimente l'UI facturation/quotas (M4) ; prérequis d'une page « Facturation » frontend.
**Référence** : `usage_events` est **à créer** au Sprint 166 (cf. TÂCHE ci-dessus) ; le pattern d'agrégation par jour/skill existe déjà pour les coûts globaux (`GET /metrics` → `daily_cost`/`skills_cost`, `app/api/endpoints/` — à adapter en version **scopée tenant** via la RLS). L'endpoint `/usage` et son agrégation par tenant sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.52.0),
docs/plan-directeur-fintech-2026.md (§7-§8 E4-S1 + jalon M4), .claude/rules/api-orchestrator.md
et tests-pyramide.md.
Sprint actif : 166 — E4-S1 (metering). Créer la migration 0006_usage_events (table append-only
tenant/skill/workflow/cost_usd/tokens/created_at + index (tenant_id, created_at) + RLS ENABLE/FORCE
+ policy tenant standard), un UsageEventService append-only best-effort calqué sur AuditLogService,
et l'émission par-skill depuis l'orchestrateur (au hook record_skill_execution, core.py ~616) —
un cache hit (cost 0) n'émet rien. Câbler dans le lifespan (app/api/main.py). Étendre la matrice
RLS et le GRANT CI à usage_events. Best-effort : un échec de metering n'avorte jamais l'analyse.
Démarre un Postgres local (recette dans ce fichier ; installer alembic dans .venv) et PROUVE
l'émission + l'isolation RLS d'usage_events sous rôle NOSUPERUSER.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; émission par-skill vérifiée + cache hit = 0 ligne
+ isolation RLS d'usage_events (lecture isolée + WITH CHECK + fail-closed).
```
