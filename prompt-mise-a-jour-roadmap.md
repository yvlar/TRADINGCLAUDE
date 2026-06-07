# Sprint 171 — E4-S6 : purge de rétention par plan (`retention_days`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.57.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (170, E4-S5) a rendu le metering **actionnable** : `GET /usage?days=30` agrège `usage_events` scopé tenant (total coût/tokens + ventilation par skill + série quotidienne) via `UsageEventService.aggregate(days)`, sous la RLS (pas de `WHERE tenant_id`). L'épic **E4** dispose maintenant du socle complet : metering (S166), quotas (S167), clés-tenant (S168), tenant exposé (S169) et **agrégation de consommation** (S170). Prochaine marche : **appliquer `retention_days`** — la colonne posée au S167 mais jamais appliquée. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-170 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant tests de migration/mypy. Le frontend peut nécessiter `cd frontend && npm install` (node_modules absent du conteneur).
> ⚠️ **Sprint sans migration attendue** : `retention_days` existe déjà (`alembic/versions/0007_plan_limits.py:58`, seed free=30/pro=365 lignes 44-45). C'est un sprint **tâche Celery + service de purge** — lecture du plan de chaque tenant + DELETE scopé. **Aucune table/colonne nouvelle attendue.**
> ⚠️ **RLS + purge** : `analysis_history`, `usage_events`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`, `watchlist` sont **sous RLS**. Un DELETE doit tourner **sous le contexte tenant** (ContextVar/GUC posé par `apply_tenant_context`) pour ne purger que les lignes du tenant ciblé — sinon la policy fail-closed renvoie 0 ligne. La tâche doit **itérer tenant par tenant** en posant `set_current_tenant(tenant_id)` (cf. `tests/conftest.py` `as_tenant`). Décision à documenter : **`usage_events` est la rétention de FACTURATION** — faut-il la purger avec la même borne que les analyses, ou la conserver plus longtemps (la carte S166 note « rétention facturation ≠ rétention analyse ») ? Trancher explicitement.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.57.0)
2. `.claude/rules/gotchas-operationnels.md` (édition `app/workers/**` — tâches Celery, timeouts, parallélisme) et `.claude/rules/tests-pyramide.md` (nouvelle tâche worker → tests unitaires sur la logique de purge + intégration sous PG migré ; patch `call_claude_with_retry` si applicable ; rôle NOSUPERUSER pour prouver le scoping RLS de la purge)
3. **Code de référence vérifié cette session** : `alembic/versions/0007_plan_limits.py` — `retention_days INTEGER NOT NULL` (`:58`), seed `free`=30/`pro`=365 (`:44-45`), posé mais **inappliqué** (`:25`, à transformer en politique réelle) · `app/workers/celery_app.py` — `beat_schedule` (`:29`), patron `crontab(...)` (ex. `:48` `run_scheduled_screener` dimanche 11h00) où enregistrer la tâche planifiée de purge · `app/workers/tasks.py` — patron de tâche `@celery_app.task(name=..., bind=True)` (ex. `run_scheduled_screener` `:757-758`) à cloner · `app/db/tenant_context.py` — `set_current_tenant`/`apply_tenant_context` pour exécuter la purge **sous chaque tenant** · `tests/conftest.py` — `as_tenant` (`:56`) pour les tests de scoping

---

## TÂCHE — Sprint 171 (E4-S6) : purge de rétention par plan

**Objectif** : transformer `plan_limits.retention_days` (colonne dormante depuis S167) en **politique réelle** — une tâche Celery planifiée qui, pour chaque tenant, supprime les données au-delà de la fenêtre de rétention de **son plan**. Différenciation free (30 j) / pro (365 j) + hygiène/conformité des données.

### Spécification
1. **Service de purge** (`app/services/` — nouveau, ex. `retention_service.py`) — méthode qui, **pour un tenant donné et sous son contexte (RLS)**, supprime les lignes plus vieilles que `retention_days` de son plan. Borne temporelle : `created_at < NOW() - (retention_days || ' days')::interval` (cohérent avec le patron `interval` de `get_metrics`/`aggregate`). Résout le plan du tenant via le join `tenants ⨝ plan_limits` (patron `QuotaService._resolve_limits`). **Décider/documenter le périmètre des tables purgées** : `analysis_history` au minimum ; trancher explicitement le sort de `usage_events` (rétention facturation — candidate à une borne distincte / non purgée ce sprint) et des tables dérivées (`composite_score_history`, `esg_score_history`, `alert_history`, `annotations`).
2. **Tâche Celery planifiée** (`app/workers/tasks.py` + `app/workers/celery_app.py`) — `@celery_app.task` clonée sur le patron `run_scheduled_screener` : itère sur **tous les tenants** (lecture hors RLS de `tenants`, table parente), pose `set_current_tenant(tenant_id)` pour chacun, appelle le service de purge sous ce contexte, agrège un compte de lignes supprimées par tenant/table (retour structuré pour les logs). Enregistrer dans `beat_schedule` (`celery_app.py:29`) à une cadence raisonnable (ex. quotidienne, heure creuse). **Best-effort par tenant** : l'échec d'un tenant ne doit pas avorter la purge des autres.
3. **Borne de sécurité** : ne jamais purger si `retention_days` est `NULL`/absent (fail-safe — un plan mal configuré ne doit pas tout supprimer) ; DELETE toujours scopé par `created_at` ET par le contexte tenant (jamais de `DELETE FROM table` sans clause).

### Tests / validation
- **Unitaires** (`tests/services/`) : la borne `retention_days` est respectée (ligne à J-31 purgée pour free=30, ligne à J-29 conservée) ; plan absent/`NULL` → aucune purge ; résolution plan→bornes correcte (asyncpg mocké).
- **Intégration** (`tests/integration/`, gated `RLS_TEST_DATABASE_URL` + rôle NOSUPERUSER) : sur PG migré, la purge sous le contexte du tenant A ne supprime **que** les lignes périmées de A (lignes de B intactes, lignes récentes de A intactes) — prouver le scoping RLS de la purge. Ajouter au gate CI (`.github/workflows/ci.yml`).
- **Worker** (`tests/workers/`) : la tâche itère sur les tenants, pose le contexte, agrège les comptes ; best-effort (un tenant en échec n'interrompt pas les autres).
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).
- **Preuve d'acceptation observable** : exécuter la purge sur PG migré avec des lignes datées artificiellement et **constater** le nombre de lignes restantes par tenant (périmées supprimées, récentes conservées, isolation tenant respectée).

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 172 — E4-S7 : intégration Stripe Billing (abonnements + usage)
**Objectif** : brancher Stripe (abonnement par plan + facturation à l'usage depuis `usage_events`), webhooks de cycle de vie (souscription, paiement, dunning), mapping plan↔price.
**Complexité** : Élevée.
**Justification** : convertit le socle metering+quotas+clés-tenant (166-168) + agrégation (170) en revenu réel (B1/B2 du plan directeur) ; dernière marche de M4.
**Référence** : `usage_events` (S166), `plan_limits`/`tenants.plan` (`alembic/versions/0007_plan_limits.py:58,65`, vérifié) et `api_keys.tenant_id` (S168) sont les socles ; `GET /usage` (`app/api/endpoints/usage.py`, créé S170) fournit l'agrégation à facturer. Toute l'intégration Stripe (SDK, webhooks, mapping plan↔price, `.env` clés Stripe) est **à créer**.

### Sprint 173 — E4-S8 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant via le ContextVar, mais une clé env-admin retombe sur legacy — NIT S168).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (S168) pilotable côté produit, prérequis d'un onboarding multi-tenant.
**Référence** : `create_key(...)` rattache au tenant courant (`app/services/api_key_service.py:75`, S168, vérifié) ; l'endpoint `POST /admin/keys` (`app/api/endpoints/admin.py:76`) délègue à `service.create_key(...)` (`:90`) **sans** `tenant_id` explicite (vérifié). L'ajout d'un champ `tenant_id` optionnel à `CreateKeyRequest` + sa validation (admin ne crée que pour son tenant) sont **à créer**.

### Sprint 174 — E4-S9 : page « Facturation » frontend
**Objectif** : page React consolidant la consommation (`GET /usage`), le plan courant (`tenant.plan`) et le quota restant du mois (bandeau S167) en un tableau de bord de facturation lisible.
**Complexité** : Moyenne.
**Justification** : donne une surface produit au socle E4 (metering+quotas+agrégation) ; point d'entrée naturel avant l'intégration Stripe (S172).
**Référence** : `GET /usage` créé au S170 (`app/api/endpoints/usage.py`, `UsageResponse`/`UsageBySkill` dans `app/models/usage.py`, vérifié) ; `QuotaBanner` existe (`frontend/src/components/QuotaBanner.tsx`, vérifié) ; `SkillCostPieChart`/`DailyCostTrendChart` existent (`frontend/src/components/`, vérifié via `ls`). La page `BillingPage` + son client typé `usage.ts` (différé du S170) sont **à créer**.

### Sprint 175 — E4-S10 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy via GUC par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté (`docs/revue-owasp-rls-2026-06.md`) — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` est exempté de l'auth middleware (`app/middleware/auth.py` `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")`, vérifié) → GUC legacy par défaut ; la décision « legacy-only documentée » est tracée dans `docs/revue-owasp-rls-2026-06.md` (risque résiduel n°2). Un token de rapport portant le tenant + le threading du contexte sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.57.0), .claude/rules/gotchas-operationnels.md et tests-pyramide.md.
Sprint actif : 171 — E4-S6 (purge de rétention par plan). Créer un service de purge qui, sous le
contexte de chaque tenant (RLS, set_current_tenant), supprime les lignes au-delà de
plan_limits.retention_days (free=30/pro=365, 0007_plan_limits.py:58) ; borne created_at < NOW() -
(retention_days || ' days')::interval ; trancher le sort de usage_events (rétention facturation).
Tâche Celery planifiée clonée sur run_scheduled_screener (tasks.py:757) + beat_schedule
(celery_app.py:29), itérant tenant par tenant, best-effort. Aucune migration attendue.
Démarre un Postgres local (recette dans ce fichier) et PROUVE le scoping RLS de la purge (rôle
NOSUPERUSER, tenant A ne purge que ses lignes périmées, B intact) + la borne retention_days.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; borne retention_days respectée + isolation
RLS de la purge prouvée + fail-safe retention_days NULL (aucune purge).
```
