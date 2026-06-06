# Sprint 160 — E2-S3 : `audit_log` append-only

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.46.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Épic E2 quasi complet** : socle Alembic (158) + lifespan sans DDL (159, le schéma est porté par Alembic, boot read-only validé). Reste **E2-S3** (ce sprint) pour clore E2, puis E3 (multi-tenance + RLS). État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-159 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote ; alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `\.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0"` avant de lancer les tests `tests/test_alembic_baseline.py` (sinon `ImportError: cannot import name 'op' from 'alembic'`). Idem `mypy`.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.46.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E2 ligne `E2-S3`** (ce sprint) ; le **§9 conformité Loi 25** (l'audit_log est un prérequis)
3. `.claude/rules/api-architecture.md` — lire `docs/architecture/architecture-copilote-financier.md` avant toute modif de schéma DB
4. `alembic/versions/0001_baseline_schema.py` — baseline (head actuel, `down_revision = None`) : la nouvelle révision se chaîne **après** (`down_revision = "0001_baseline"`)

---

## TÂCHE — Sprint 160 (E2-S3) : journal d'audit append-only

**Objectif** : créer une table `audit_log` append-only et y tracer chaque mutation métier (watchlist, annotation, clé API), consultable par un admin. Prérequis conformité Loi 25 (traçabilité des accès/modifications).

### Spécification
1. **Migration Alembic** (nouvelle révision chaînée après `0001_baseline`) : table `audit_log(id, tenant_id, user_id, action, cible_type, cible_id, metadata JSONB, created_at TIMESTAMPTZ DEFAULT NOW())` + index sur `(created_at DESC)` et `(cible_type, cible_id)`.
   - ⚠️ **Pas de concept `tenant` avant E3** (161+) : `tenant_id UUID NULL` (colonne posée maintenant, peuplée à E3) — le documenter comme forward-compat, ne PAS créer de table `tenants` ici.
   - upgrade/downgrade idempotents validés sur Postgres local (recette ci-dessus) + couverts par le job CI `migrations`.
2. **`AuditLogService`** (`app/services/audit_log_service.py`) — `async def record(action, cible_type, cible_id, user_id=None, tenant_id=None, metadata=None)` (INSERT pur, append-only — aucun UPDATE/DELETE) + `async def list_recent(limit)` pour l'admin. Injection du `db_pool` par constructeur (pattern des services existants), enregistré dans le lifespan + `app.state`.
3. **Traçage des mutations** (3 sites — append best-effort, ne jamais faire échouer la mutation métier si l'audit échoue : log + continue) :
   - `app/services/watchlist_service.py:32` `add_entry` et `:90` `delete_entry`
   - `app/services/annotation_service.py:18` `upsert`
   - `app/api/endpoints/admin.py:74` `create_key` et `:106` `revoke_key` (ou au niveau `app/services/api_key_service.py:67`/`:93`)
4. **Endpoint admin** : `GET /admin/audit-log?limit=50` (admin only, pattern `_require_admin` déjà utilisé dans `admin.py`) → liste paginée des dernières entrées.
5. **Périmètre** : migration + service + 3 sites de traçage + endpoint + tests. Pas de frontend obligatoire (optionnel : page admin).

### Tests / validation
- **Migration** : upgrade/downgrade sur Postgres local ; vérifier la présence de `audit_log` + index.
- **Service** : unitaire `record` insère / `list_recent` ordonne par `created_at DESC` ; append-only (pas de méthode de mutation).
- **Intégration** : une mutation watchlist/annotation/clé produit une entrée d'audit ; échec d'audit n'avorte pas la mutation (best-effort).
- **Endpoint** : `GET /admin/audit-log` 200 admin / 401-403 non-admin.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.

---

## SPRINTS SUGGÉRÉS (suite P0 — voir plan directeur §7)

### Sprints 161-165 — E3 : multi-tenance + RLS *(bloqueur n°1)*
**Objectif** : `tenants` + `users.tenant_id` ; `tenant_id` sur les 6 tables métier ; **RLS PostgreSQL** (`SET app.tenant_id` par requête) ; threading tenant endpoints→orchestrateur→services ; **preuve d'isolation rouge→vert** (test cross-tenant). VALIDABLE pour de vrai avec le Postgres local.
**Complexité** : Élevée.
**Référence** : la colonne `audit_log.tenant_id` posée nullable au Sprint 160 sera peuplée ici ; migrations chaînées après la révision E2-S3 ; tables métier existantes confirmées dans `alembic/versions/0001_baseline_schema.py:43` (watchlist), `:64` (composite_score_history), `:74` (esg_score_history), `:96` (alert_history), `:111` (annotations), `:24` (analysis_history) ; middleware dans `app/middleware/` ; orchestrateur `app/orchestrator/core.py`.

### Sprints 166-167 — E4 : metering & quotas
**Objectif** : `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émis depuis l'orchestrateur ; `plan_limits` + compteur Redis → 429 au dépassement.
**Complexité** : Moyenne.
**Référence** : le `cost_usd` par appel est déjà calculé et persisté — colonnes `cost_usd`/`tokens_input`/`tokens_output` présentes dans `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`) ; `usage_events` est **à créer** (table distincte append-only, granularité par skill). Réutilise le pattern `AuditLogService` (append-only) du Sprint 160.

### Sprint 168 — E9-S1 : déjà livré ✅ (disclaimer inline) — ne pas replanifier
Mentionné ici uniquement pour cohérence du plan ; voir `ROADMAP.md`.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.46.0),
docs/plan-directeur-fintech-2026.md (§7 E2-S3 + §9 Loi 25), .claude/rules/api-architecture.md.
Sprint actif : 160 — E2-S3 (audit_log append-only : migration Alembic chaînée après 0001,
AuditLogService, traçage des 3 mutations, endpoint GET /admin/audit-log).
tenant_id nullable (pas de concept tenant avant E3). Démarre un Postgres local (recette
dans ce fichier ; installer alembic dans .venv) pour valider la migration.
Branche : claude/prompt-executer-sprint-S9b2U. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; alembic upgrade/downgrade sur Postgres local.
```
