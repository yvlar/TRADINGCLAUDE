# Sprint 161 — E3-S1 : socle tenant (`tenants` + `users.tenant_id`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.47.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Épic E2 clos** au Sprint 160 (`audit_log` append-only : migration Alembic `0002`, `AuditLogService`, traçage best-effort de 3 mutations, `GET /admin/audit-log`). Démarre maintenant **E3 — multi-tenance + RLS** (bloqueur n°1), dont ce sprint est la 1ʳᵉ marche. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-160 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant de lancer les tests de migration (sinon `ImportError`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.47.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E3 ligne `E3-S1`** (ce sprint) ; le **§5 M1/M2** (justification multi-tenance) et le **§8.1** (choix single-DB + RLS)
3. `.claude/rules/api-architecture.md` — lire `docs/architecture/architecture-copilote-financier.md` avant toute modif de schéma DB
4. `alembic/versions/0002_audit_log.py` — **head actuel** (`down_revision = "0001_baseline"`) : la nouvelle révision se chaîne **après** (`down_revision = "0002_audit_log"`)

---

## TÂCHE — Sprint 161 (E3-S1) : socle tenant

**Objectif** : poser les fondations de la multi-tenance — table `tenants`, colonne `users.tenant_id` (FK), et un tenant « legacy » de backfill pour les comptes existants. **Aucune isolation RLS ni rattachement des 6 tables métier ici** (E3-S2/S3, sprints 162-163) — ce sprint pose uniquement la dimension tenant côté comptes, en gardant l'auth 100 % rétrocompatible.

### Spécification
1. **Migration Alembic** (révision chaînée après `0002_audit_log`) :
   - Table `tenants(id UUID PK DEFAULT gen_random_uuid(), name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())`.
   - Insérer un **tenant « legacy »** déterministe (slug `legacy`, UUID fixe en constante) pour rattacher les comptes pré-multi-tenance.
   - `ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id)` — **nullable d'abord**, puis backfill de tous les `users` existants vers le tenant legacy, puis (même migration) `SET NOT NULL` + index `idx_users_tenant`. (Le `users` baseline est en `0001_baseline_schema.py:121`.)
   - downgrade : retirer la colonne + l'index + la table (ordre FK inverse). Idempotent.
2. **`UserService`** (`app/services/user_service.py:20`, `create_user` en `:26`, `INSERT INTO users` en `:32`) — `create_user` accepte un `tenant_id` optionnel ; à défaut, rattacher au tenant legacy (constante partagée). Le `SELECT`/`_row_to_user` expose `tenant_id`.
3. **Modèle** (`app/models/auth.py`) — exposer `tenant_id` sur le modèle utilisateur interne (pas forcément dans la réponse publique `/auth/me` ce sprint — décision à documenter).
4. **Rétrocompat auth** : `POST /auth/register` (`app/api/endpoints/auth.py:114`, appelle `create_user` en `:121`) et `/auth/login` continuent de fonctionner sans changement d'API externe ; un nouvel inscrit est rattaché au tenant legacy par défaut (le provisioning d'un tenant dédié par signup arrive à E10-S3 / sprint 189).
5. **Périmètre** : migration + `tenants` + `users.tenant_id` + backfill legacy + `UserService` + tests. **PAS** de `tenant_id` sur les 6 tables métier, **PAS** de RLS, **PAS** de middleware de contexte (sprints 162-163).

### Tests / validation
- **Migration** : sur Postgres local, `upgrade head` → table `tenants` + tenant legacy présent + `users.tenant_id NOT NULL` peuplé ; `downgrade` → colonne/table retirées ; re-`upgrade` idempotent.
- **Backfill** : un `users` inséré avant la migration se retrouve rattaché au tenant legacy (test sur Postgres local ou test de forme de la migration).
- **Service** : `create_user` sans `tenant_id` → legacy ; avec `tenant_id` explicite → respecté ; `tenant_id` remonté dans le dict utilisateur.
- **Rétrocompat** : tests existants `tests/api/test_auth*.py` toujours verts ; register/login inchangés côté API.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.

---

## SPRINTS SUGGÉRÉS (suite E3 → E4 — voir plan directeur §7)

### Sprint 162 — E3-S2 : rattacher les 6 tables métier
**Objectif** : `tenant_id UUID NOT NULL` + index sur les 6 tables métier ; backfill « legacy ».
**Complexité** : Moyenne.
**Référence** : les 6 tables existent dans le baseline — `analysis_history` (`alembic/versions/0001_baseline_schema.py:24`), `watchlist` (`:43`), `composite_score_history` (`:64`), `esg_score_history` (`:74`), `alert_history` (`:96`), `annotations` (`:111`). Le tenant legacy + `tenants` sont **à créer** au Sprint 161 (ce sprint).

### Sprint 163 — E3-S3 : RLS PostgreSQL
**Objectif** : `ENABLE ROW LEVEL SECURITY` + policy `tenant_id = current_setting('app.tenant_id')` sur les 6 tables ; `SET app.tenant_id` injecté par requête via middleware + pool.
**Complexité** : Élevée.
**Référence** : middlewares existants dans `app/middleware/` (auth/csrf/rate_limit montés `app/api/main.py:468-470`) ; pool asyncpg créé dans le lifespan `app/api/main.py:159`. La colonne `tenant_id` sur les tables métier est **à créer** au Sprint 162.

### Sprint 164 — E3-S4 : threading tenant bout-en-bout
**Objectif** : threader `current_user`/tenant endpoints→orchestrateur→services ; clé cache Redis **préfixée tenant** ; quotas screener par tenant.
**Complexité** : Élevée.
**Référence** : `app/orchestrator/core.py` (orchestrateur) ; cache analyses `app/services/analysis_cache.py` (la clé de cache exclut déjà `ratios_provenance` — `analysis_cache.py:74`, cf. Sprint 150) ; endpoint `app/api/endpoints/analyze_stream.py` (ne reçoit aucun tenant aujourd'hui — à vérifier avant impl).

### Sprint 165 — E3-S5 : preuve d'isolation rouge→vert
**Objectif** : test cross-tenant **rouge→vert** (tenant A ne lit jamais les lignes de B) sur les 6 tables + revue OWASP de la policy RLS.
**Complexité** : Moyenne.
**Référence** : VALIDABLE pour de vrai avec le Postgres local (RLS réelle). Dépend de l'isolation posée aux sprints 162-163.

### Sprint 166 — E4-S1 : metering (`usage_events`)
**Objectif** : table `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émise depuis l'orchestrateur — base de facturation.
**Complexité** : Moyenne.
**Référence** : `cost_usd`/`tokens_input`/`tokens_output` déjà persistés par analyse — colonnes présentes dans `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`). `usage_events` est **à créer** (table distincte, granularité par skill). Réutilise le **pattern append-only `AuditLogService`** posé au Sprint 160 (`app/services/audit_log_service.py`).

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.47.0),
docs/plan-directeur-fintech-2026.md (§7 E3-S1 + §5 M1/M2 + §8.1), .claude/rules/api-architecture.md.
Sprint actif : 161 — E3-S1 (socle tenant : migration Alembic chaînée après 0002_audit_log,
table tenants + tenant « legacy » + users.tenant_id FK NOT NULL après backfill, UserService
rattache au legacy par défaut, auth 100 % rétrocompatible). PAS de tenant_id sur les 6 tables
métier ni de RLS ici (E3-S2/S3). Démarre un Postgres local (recette dans ce fichier ; installer
alembic dans .venv) pour valider la migration + le backfill.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; alembic upgrade/downgrade + backfill sur Postgres local.
```
