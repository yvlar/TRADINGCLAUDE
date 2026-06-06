# Sprint 163 — E3-S3 : RLS PostgreSQL sur les 6 tables métier

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.49.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Sprint 162 (E3-S2) complété** : les 6 tables métier (`analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`) portent désormais `tenant_id UUID NOT NULL` + index + backfill legacy (migration `0004_business_tenant_id`), et les 6 sites d'INSERT posent le tenant legacy par défaut. Démarre **E3-S3** : activer la **Row-Level Security** PostgreSQL pour qu'un tenant ne lise jamais les lignes d'un autre. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-162 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration (sinon `ImportError`).
> ⚠️ **RLS et rôle superuser** : le propriétaire de table (et tout superuser) **contourne la RLS** par défaut. Le rôle applicatif `copilote` créé par `initdb -U copilote` est superuser → pour PROUVER l'isolation en local, tester avec un rôle dédié `NOSUPERUSER` (ou `FORCE ROW LEVEL SECURITY` sur les tables). À cadrer dans ce sprint.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.49.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E3 ligne `E3-S3`** (ce sprint) ; **§3.2 M2** (justification RLS) et **§8.1 décision 1** (single-DB + RLS pour démarrer)
3. `.claude/rules/api-architecture.md` — lire `docs/architecture/architecture-copilote-financier.md` avant toute modif de schéma/pool DB
4. `alembic/versions/0004_business_tenant_id.py` — **head actuel** (`down_revision = "0003_tenants"`) : la nouvelle révision se chaîne **après** (`down_revision = "0004_business_tenant_id"`). Le `tenant_id` est déjà NOT NULL + indexé sur les 6 tables.

---

## TÂCHE — Sprint 163 (E3-S3) : activer la RLS PostgreSQL

**Objectif** : poser l'**isolation** au niveau base — `ENABLE ROW LEVEL SECURITY` + une policy `tenant_id = current_setting('app.tenant_id')::uuid` sur chacune des 6 tables métier, et injecter `SET app.tenant_id` par requête/connexion. **Ce sprint pose le mécanisme RLS + son câblage de contexte ; la preuve d'isolation cross-tenant rouge→vert exhaustive est E3-S5 (sprint 165)** — mais inclure ici au moins un test runtime d'isolation minimal (un rôle non-superuser ne voit que ses lignes) pour ne pas livrer une RLS non vérifiée.

### Spécification
1. **Migration Alembic** (révision chaînée après `0004_business_tenant_id`) — pour chacune des 6 tables :
   - `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
   - `CREATE POLICY <table>_tenant_isolation ON <table> USING (tenant_id = current_setting('app.tenant_id', true)::uuid);` — le 2ᵉ argument `true` de `current_setting` (missing_ok) évite l'erreur quand le GUC n'est pas posé ; **décider et documenter** le comportement quand `app.tenant_id` est absent (policy `USING` → ligne invisible) vs un défaut. Couvrir aussi la clause `WITH CHECK` pour les INSERT/UPDATE (un tenant ne peut pas écrire une ligne d'un autre tenant).
   - **Décider `FORCE ROW LEVEL SECURITY`** : sans lui, le propriétaire de table contourne la policy. À argumenter (le rôle applicatif en prod n'est pas propriétaire, mais le câblage local de test l'exige — cf. note superuser ci-dessus).
   - downgrade : `DROP POLICY` + `DISABLE ROW LEVEL SECURITY` par table, idempotent.
   - Réutiliser le **pattern template sur tuple `_TABLES`** posé au Sprint 162 (`0004_business_tenant_id.py:41-58`) — DDL uniforme bâti par boucle, pas 6 copies.
2. **Injection du contexte tenant par connexion** : poser `SET app.tenant_id = '<uuid>'` (ou `set_config('app.tenant_id', …, true)` transaction-scoped) sur chaque connexion empruntée au pool. Câbler au point d'acquisition asyncpg (`app/api/main.py:159` crée le pool, exposé `app.state.db_pool` `:371`) — soit via `init`/`setup` de connexion du pool, soit un wrapper d'acquisition. **Tant que le threading endpoint→service n'est pas fait (E3-S4, sprint 164), le contexte par défaut = `LEGACY_TENANT_ID`** — l'isolation est réelle mais tout le monde est « legacy » jusqu'au threading. Documenter ce palier.
3. **Périmètre** : RLS + policy + câblage du GUC `app.tenant_id` + tests. **PAS** de threading `current_user`/tenant depuis l'auth (E3-S4), **PAS** de clé cache préfixée tenant (E3-S4), **PAS** de quotas (E4).

### Tests / validation
- **Migration** (Postgres local) : `upgrade head` → `rowsecurity = true` + une policy par table (`pg_policies`) ; `downgrade` → policies retirées + `rowsecurity = false` ; re-`upgrade` idempotent.
- **Isolation runtime minimale** (Postgres local, rôle **NOSUPERUSER** ou `FORCE RLS`) : insérer des lignes sous 2 `tenant_id` distincts ; avec `SET app.tenant_id = '<A>'`, un `SELECT` ne renvoie que les lignes de A ; bascule sur B → seulement B ; sans GUC → 0 ligne (ou défaut documenté). (La matrice exhaustive 6 tables = E3-S5.)
- **Forme de migration** (sans DB) : test paramétré sur les 6 tables (ENABLE RLS + CREATE POLICY présents, nom de policy, downgrade DROP POLICY + DISABLE).
- **Non-régression** : la suite `pytest` (mocks asyncpg) reste verte — le câblage du GUC ne doit pas casser les services testés avec un pool mocké.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.

---

## SPRINTS SUGGÉRÉS (suite E3 → E4 — voir plan directeur §7)

### Sprint 164 — E3-S4 : threading tenant bout-en-bout
**Objectif** : threader `current_user`/tenant endpoints→orchestrateur→services ; clé cache Redis **préfixée tenant** ; quotas screener par tenant.
**Complexité** : Élevée.
**Référence** : `app/api/endpoints/analyze_stream.py` ne reçoit **aucun** tenant/`current_user` aujourd'hui (grep `tenant|current_user` vide — vérifié) ; clé de cache analyses construite par `_cache_key` `app/services/analysis_cache.py:67`, exclut déjà la traçabilité `:74` (préfixer le tenant ici). Les services d'écriture acceptent déjà un `tenant_id` (param posé au Sprint 162) — E3-S4 le **remplit** au lieu du défaut legacy.

### Sprint 165 — E3-S5 : preuve d'isolation rouge→vert
**Objectif** : test cross-tenant **rouge→vert** exhaustif (tenant A ne lit jamais les lignes de B) sur les 6 tables + revue OWASP de la policy RLS.
**Complexité** : Moyenne.
**Référence** : VALIDABLE pour de vrai avec le Postgres local (RLS réelle, rôle NOSUPERUSER). Dépend de la RLS posée au Sprint 163 et du threading au Sprint 164.

### Sprint 166 — E4-S1 : metering (`usage_events`)
**Objectif** : table `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émise depuis l'orchestrateur — base de facturation.
**Complexité** : Moyenne.
**Référence** : `cost_usd`/`tokens_input`/`tokens_output` déjà persistés par analyse — colonnes présentes `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`). `usage_events` est **à créer** (table distincte, granularité par skill). Réutilise le **pattern append-only `AuditLogService`** posé au Sprint 160 (`app/services/audit_log_service.py`).

### Sprint 167 — E4-S2 : quotas par plan (`plan_limits`)
**Objectif** : table `plan_limits` (analyses/mois, taille screener, rétention) + compteur Redis ; `429` clair au dépassement ; override admin.
**Complexité** : Moyenne.
**Référence** : rate-limit Redis existant `app/middleware/rate_limit.py` monté `app/api/main.py:468` (à étendre par tenant/plan). `plan_limits` et le metering `usage_events` (Sprint 166) sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.49.0),
docs/plan-directeur-fintech-2026.md (§7 E3-S3 + §3.2 M2 + §8.1), .claude/rules/api-architecture.md.
Sprint actif : 163 — E3-S3 (RLS PostgreSQL : migration chaînée après 0004_business_tenant_id,
ENABLE ROW LEVEL SECURITY + CREATE POLICY tenant_id = current_setting('app.tenant_id')::uuid +
WITH CHECK sur les 6 tables métier ; injecter SET app.tenant_id par connexion au pool asyncpg —
défaut LEGACY_TENANT_ID tant que le threading n'est pas câblé E3-S4 ; décider FORCE RLS et le
comportement GUC-absent). PAS de threading auth ni cache préfixé tenant (E3-S4). Réutilise le
template DDL sur tuple _TABLES du Sprint 162. Démarre un Postgres local (recette dans ce fichier ;
installer alembic dans .venv) et PROUVE l'isolation avec un rôle NOSUPERUSER (sinon la RLS est
contournée par le superuser copilote).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; alembic upgrade/downgrade + isolation runtime sur Postgres local.
```
