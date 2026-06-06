# Sprint 159 — E2-S2 : sortir les `CREATE TABLE` du lifespan

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.45.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Épic E1 (sécurité fail-closed, 154-157) complet**, + **E9-S1 disclaimer inline (168)** + **E2-S1 socle Alembic (158)**. État courant complet (version, endpoints, compteurs) : **`ROADMAP.md`** (source unique).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires présents dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → créer un user dédié. Recette validée au sprint 158 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata; chown pguser /tmp/pgdata
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote
> ```
> `alembic upgrade head` fonctionne ainsi (env async asyncpg). C'est ce qui permet de valider E2/E3/E4 (RLS, metering) pour de vrai.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.45.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E2** (ce sprint = E2-S2 ; suite E2-S3, puis E3)
3. `.claude/rules/api-architecture.md` — lire `architecture-copilote-financier.md` avant toute modif du lifespan/schéma DB
4. `alembic/versions/0001_baseline_schema.py` — le baseline qui reproduit déjà le schéma courant (10 tables)

---

## TÂCHE — Sprint 159 (E2-S2) : le lifespan ne crée plus de table

**Objectif** : retirer le DDL inline du lifespan (`app/api/main.py:160-324` — tous les `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN` / `CREATE INDEX`) maintenant qu'Alembic (sprint 158) porte le schéma. Le boot ne fait plus de DDL ; le schéma est appliqué par `alembic upgrade head` (déploiement / entrée Docker).

### Spécification
1. **Supprimer** le bloc de migrations inline du lifespan (lignes ~160-324). Le `db_pool` reste créé ; aucune création/altération de table au boot.
2. **`alembic upgrade head` au démarrage** : soit via l'entrypoint Docker (recommandé — découple le schéma du process API), soit un appel optionnel gardé par `RUN_MIGRATIONS_ON_BOOT` (par défaut off en prod, le déploiement lance la migration). Documenter le choix.
3. **`infra/postgres/init.sql`** : conserver pour rétrocompat Docker OU le réduire à un commentaire pointant vers Alembic — décider et documenter (ne pas laisser deux sources de vérité divergentes).
4. **Boot read-only DB** : vérifier que l'app démarre contre une DB déjà migrée sans tenter de DDL (un rôle en lecture seule sur le schéma ne doit pas faire échouer le boot).
5. **Périmètre** : `app/api/main.py` (lifespan) + entrypoint/compose + doc. Pas de changement de schéma (le baseline 158 est la référence).

### Tests / validation
- **Runtime (Postgres local, voir recette ci-dessus)** : `alembic upgrade head` puis démarrer le lifespan → confirmer **zéro DDL émis** (ex. révoquer CREATE au rôle, ou inspecter qu'aucune table n'est (re)créée). Rollback : `alembic downgrade base` testé.
- **CI** : le job `migrations` (ajouté en 158) couvre déjà upgrade/downgrade ; ajouter au besoin un smoke « boot sans DDL ».
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.

---

## SPRINTS SUGGÉRÉS (suite P0 — voir plan directeur §7)

### Sprint 160 — E2-S3 : `audit_log` append-only
**Objectif** : table `audit_log(tenant, user, action, cible, ts)` + traçage de chaque mutation (watchlist/annotation/clé) ; consultable admin. Migration Alembic + service. Prérequis conformité Loi 25.
**Complexité** : Moyenne. **Référence** : mutations dans `app/services/watchlist_service.py`, `app/services/annotation_service.py`, `app/api/endpoints/admin.py`.

### Sprints 161-165 — E3 : multi-tenance + RLS *(bloqueur n°1)*
**Objectif** : `tenants` + `users.tenant_id` ; `tenant_id` sur les 6 tables (analysis_history, watchlist, composite_score_history, esg_score_history, alert_history, annotations) ; **RLS PostgreSQL** (`SET app.tenant_id` par requête) ; threading tenant endpoints→orchestrateur→services ; **preuve d'isolation rouge→vert** (test cross-tenant). VALIDABLE pour de vrai avec le Postgres local.
**Complexité** : Élevée. **Référence** : migrations Alembic (chaîner après 0001) ; middleware `app/middleware/` ; `app/orchestrator/core.py`.

### Sprints 166-167 — E4 : metering & quotas
**Objectif** : `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) depuis `core.py` ; `plan_limits` + compteur Redis → 429 au dépassement.
**Complexité** : Moyenne.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.45.0),
docs/plan-directeur-fintech-2026.md (§7 E2), .claude/rules/api-architecture.md.
Sprint actif : 159 — E2-S2 (sortir les CREATE TABLE du lifespan ; Alembic porte le schéma depuis 158).
Démarre un Postgres local (recette dans ce fichier) pour valider runtime.
Branche : claude/blissful-brown-qNf8y (PR #106). Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; alembic upgrade/downgrade sur Postgres local.
```
