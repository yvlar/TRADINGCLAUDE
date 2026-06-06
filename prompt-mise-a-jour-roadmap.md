# Sprint 162 — E3-S2 : rattacher les 6 tables métier au tenant

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.48.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Sprint 161 (E3-S1) complété** : socle tenant posé — table `tenants`, tenant « legacy » déterministe, `users.tenant_id` FK NOT NULL après backfill, `UserService` rattache au legacy par défaut, auth 100 % rétrocompatible. Démarre **E3-S2** : propager `tenant_id` aux 6 tables métier. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-161 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration (sinon `ImportError`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.48.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E3 ligne `E3-S2`** (ce sprint) ; le **§5 M1** (justification `tenant_id` sur les données) et le **§8.1** (single-DB + RLS — E3-S3 suit)
3. `.claude/rules/api-architecture.md` — lire `docs/architecture/architecture-copilote-financier.md` avant toute modif de schéma DB
4. `alembic/versions/0003_tenants.py` — **head actuel** (`down_revision = "0002_audit_log"`) : la nouvelle révision se chaîne **après** (`down_revision = "0003_tenants"`). Réutiliser le pattern de backfill legacy (`app/models/tenant.py::LEGACY_TENANT_ID`, `ADD COLUMN nullable → UPDATE → SET NOT NULL → CREATE INDEX`).

---

## TÂCHE — Sprint 162 (E3-S2) : rattacher les 6 tables métier

**Objectif** : ajouter `tenant_id UUID NOT NULL` (FK → `tenants`) + index à chacune des **6 tables métier**, avec backfill vers le tenant « legacy » (constante `LEGACY_TENANT_ID` posée au Sprint 161). **Aucune RLS ni middleware de contexte ici** (E3-S3 / sprint 163) — ce sprint pose uniquement la colonne tenant sur les données, en gardant les écritures actuelles fonctionnelles (le tenant legacy sert de défaut tant que le threading tenant n'est pas câblé, E3-S4).

### Spécification
1. **Migration Alembic** (révision chaînée après `0003_tenants`) — pour chacune des 6 tables :
   - `analysis_history` (`alembic/versions/0001_baseline_schema.py:24`), `watchlist` (`:43`), `composite_score_history` (`:64`), `esg_score_history` (`:74`), `alert_history` (`:96`), `annotations` (`:111`).
   - Pattern par table : `ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)` (nullable) → `UPDATE … SET tenant_id = '<legacy>' WHERE tenant_id IS NULL` → `ALTER COLUMN tenant_id SET NOT NULL` → `CREATE INDEX IF NOT EXISTS idx_<table>_tenant ON <table> (tenant_id)`.
   - Réutiliser le **littéral UUID legacy figé** (cf. `0003_tenants.py:30`) — la migration n'importe pas de code applicatif ; verrouiller la parité littéral ↔ `LEGACY_TENANT_ID` par un test (pattern Sprint 161).
   - downgrade : pour chaque table, `DROP INDEX` → `DROP COLUMN` (ordre FK inverse). Idempotent.
   - **Décision `ON DELETE`** : le FK `users.tenant_id` du Sprint 161 est en `NO ACTION` (défaut). Choisir et **documenter** explicitement la politique pour les tables métier (probable `NO ACTION`/restrict — la suppression d'un tenant ne doit pas effacer silencieusement ses données ; le hard-delete tenant relève d'un sprint dédié).
2. **Écritures applicatives** : repérer les `INSERT` sur les 6 tables (services : `analysis_cache`/persistance historique, `watchlist_service`, `composite_score`/`esg_score` history, `alert`/alertes, `annotation_service`) et garantir qu'ils restent verts. Tant que le tenant n'est pas threadé (E3-S4), passer `LEGACY_TENANT_ID` par défaut au site d'INSERT (constante partagée) **ou** documenter un DB `DEFAULT` temporaire — décision à argumenter (le service-level explicite est préférable, cf. note d'altitude Sprint 161).
3. **Périmètre** : migration + colonnes + backfill + index + ajustement des INSERT + tests. **PAS** de RLS, **PAS** de policy, **PAS** de middleware de contexte ni de clé cache préfixée tenant (sprints 163-164).

### Tests / validation
- **Migration** (Postgres local) : `upgrade head` → les 6 tables portent `tenant_id NOT NULL` + index ; une ligne insérée **avant** la migration dans chaque table est backfillée au legacy ; `downgrade` → colonnes/index retirés ; re-`upgrade` idempotent.
- **Forme de migration** (sans DB) : test paramétré sur les 6 tables (présence colonne/index/backfill, ordre backfill-avant-NOT-NULL, parité littéral ↔ constante).
- **Écritures** : tests existants des services concernés toujours verts ; un INSERT sans tenant explicite atterrit sur le legacy.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.

---

## SPRINTS SUGGÉRÉS (suite E3 → E4 — voir plan directeur §7)

### Sprint 163 — E3-S3 : RLS PostgreSQL
**Objectif** : `ENABLE ROW LEVEL SECURITY` + policy `tenant_id = current_setting('app.tenant_id')::uuid` sur les 6 tables ; `SET app.tenant_id` injecté par requête via middleware + pool.
**Complexité** : Élevée.
**Référence** : middlewares montés `app/api/main.py:468-470` (RateLimit/Bearer/CSRF) ; pool asyncpg créé dans le lifespan `app/api/main.py:159` (exposé `app.state.db_pool` `:371`). La colonne `tenant_id` sur les 6 tables métier est **à créer** au Sprint 162.

### Sprint 164 — E3-S4 : threading tenant bout-en-bout
**Objectif** : threader `current_user`/tenant endpoints→orchestrateur→services ; clé cache Redis **préfixée tenant** ; quotas screener par tenant.
**Complexité** : Élevée.
**Référence** : `app/api/endpoints/analyze_stream.py` ne reçoit **aucun** tenant/`current_user` aujourd'hui (grep vide — vérifié) ; clé de cache analyses construite par `_cache_key` `app/services/analysis_cache.py:67`, exclut déjà la provenance `:74` (préfixer le tenant ici). Orchestrateur `app/orchestrator/core.py`.

### Sprint 165 — E3-S5 : preuve d'isolation rouge→vert
**Objectif** : test cross-tenant **rouge→vert** (tenant A ne lit jamais les lignes de B) sur les 6 tables + revue OWASP de la policy RLS.
**Complexité** : Moyenne.
**Référence** : VALIDABLE pour de vrai avec le Postgres local (RLS réelle). Dépend de l'isolation posée aux sprints 162-163.

### Sprint 166 — E4-S1 : metering (`usage_events`)
**Objectif** : table `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émise depuis l'orchestrateur — base de facturation.
**Complexité** : Moyenne.
**Référence** : `cost_usd`/`tokens_input`/`tokens_output` déjà persistés par analyse — colonnes présentes `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`). `usage_events` est **à créer** (table distincte, granularité par skill). Réutilise le **pattern append-only `AuditLogService`** posé au Sprint 160 (`app/services/audit_log_service.py`).

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.48.0),
docs/plan-directeur-fintech-2026.md (§7 E3-S2 + §5 M1 + §8.1), .claude/rules/api-architecture.md.
Sprint actif : 162 — E3-S2 (rattacher les 6 tables métier au tenant : migration Alembic chaînée
après 0003_tenants, tenant_id UUID NOT NULL + index + backfill legacy sur analysis_history,
watchlist, composite_score_history, esg_score_history, alert_history, annotations ; ajuster les
INSERT pour défaut legacy ; documenter la politique ON DELETE). PAS de RLS ni middleware de
contexte ici (E3-S3/S4). Réutilise LEGACY_TENANT_ID (app/models/tenant.py) et le pattern de
backfill du Sprint 161. Démarre un Postgres local (recette dans ce fichier ; installer alembic
dans .venv) pour valider la migration + le backfill des 6 tables.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; alembic upgrade/downgrade + backfill sur Postgres local.
```
