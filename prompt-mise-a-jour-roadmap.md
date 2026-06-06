# Sprint 164 — E3-S4 : threading tenant bout-en-bout

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.50.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Sprint 163 (E3-S3) complété** : la **Row-Level Security** PostgreSQL est active (`ENABLE`+`FORCE`) sur les 6 tables métier avec policy `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` (USING+WITH CHECK, fail-closed) ; le GUC `app.tenant_id` est posé par connexion au pool asyncpg (`app/db/tenant_context.py`) — mais **figé à `LEGACY_TENANT_ID`** tant que le tenant réel n'est pas threadé. Démarre **E3-S4** : threader le tenant authentifié de l'endpoint jusqu'aux services pour que la RLS isole les vrais tenants, et préfixer la clé cache Redis par tenant. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB possible en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-163 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> # DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration.
> ⚠️ **Crux RLS↔threading** : le GUC est aujourd'hui posé par le `setup` du pool à **chaque acquisition** (`app/db/tenant_context.py:25`), valeur constante `LEGACY_TENANT_ID`. Comme les services appellent `pool.fetch/execute` directement (acquire→release par requête, pas de connexion tenue), threader un tenant réel impose un mécanisme **par requête** : soit un `contextvars.ContextVar` lu par le `setup`, soit acquérir explicitement une connexion par requête et y poser le GUC. **Décider et cadrer ce mécanisme dans ce sprint** — c'est le cœur d'E3-S4. Prouver avec rôle NOSUPERUSER que deux tenants réels sont isolés (pas seulement « tout legacy »).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.50.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E3 ligne `E3-S4`** (ce sprint) ; **§3.2 M2 point 3** (« threader `current_user`/tenant depuis l'auth jusqu'à l'orchestrateur ») et **§3.2 M3** (quotas screener par tenant)
3. `.claude/rules/api-architecture.md` (contraintes `app/**`, modèle, cache) et `.claude/rules/gotchas-operationnels.md` (timeouts/parallélisme screener — touché par les quotas tenant)
4. `app/db/tenant_context.py` (le `setup` legacy posé au Sprint 163, à généraliser) · `app/services/analysis_cache.py:67-79` (`_cache_key`, à préfixer tenant) · `app/orchestrator/core.py:1726,1810` (le `tenant_id: UUID | None` à **remplir** au lieu du défaut legacy)

---

## TÂCHE — Sprint 164 (E3-S4) : threading tenant bout-en-bout

**Objectif** : faire circuler le tenant **authentifié** depuis l'endpoint jusqu'aux écritures DB et au cache, pour que l'isolation RLS (Sprint 163) protège les **vrais** tenants — pas seulement le palier legacy.

### Spécification
1. **Résolution du tenant en entrée de requête** : extraire le `tenant_id` de l'utilisateur authentifié (cookie JWT → `user.tenant_id`, présent depuis le Sprint 161 sur la table `users`) et le déposer dans un contexte de requête (recommandé : `contextvars.ContextVar`, propre à l'async). Pour les requêtes **non authentifiées** ou les workers/tâches planifiées : défaut explicite `LEGACY_TENANT_ID` (rétrocompat). Ce résolveur de requête est du **middleware ASGI** (`app/middleware/`) — distinct du setter de connexion `app/db/tenant_context.py` (couche DB), qui le **lit**.
2. **Pose du GUC par requête** : généraliser `app/db/tenant_context.py` pour que le `setup` du pool lise le `ContextVar` (défaut legacy) au lieu de la constante figée. Vérifier le piège de réutilisation de connexion : `setup` s'exécute à chaque acquisition → le GUC est réinitialisé au tenant courant à chaque `pool.fetch/execute` (pas de fuite du tenant d'une requête précédente).
3. **Threading jusqu'aux services d'écriture** : passer le `tenant_id` résolu aux 6 sites d'écriture qui acceptent déjà le param (Sprint 162 : `core.py::_persist`, watchlist/annotation/esg_history/composite_history/alert_history) — **remplir** la valeur réelle au lieu du défaut legacy. `analyze_stream.py` ne reçoit aucun tenant aujourd'hui (`grep` vide — vérifié) : le câbler.
4. **Clé cache Redis préfixée tenant** : `analysis_cache._cache_key` (`app/services/analysis_cache.py:79`) construit `analysis:{ticker}:{workflow}:{hash}` — préfixer par tenant (`analysis:{tenant}:{ticker}:…`) pour qu'un tenant ne serve jamais l'analyse cachée d'un autre. Adapter `invalidate()` (pattern `KEYS`) en conséquence.
5. **Quotas screener par tenant** (M3, si le périmètre tient) : borne du nombre de tickers / analyses par tenant — sinon, le **réduire à un sprint E4 dédié** et le dire explicitement.

### Tests / validation
- **Isolation runtime 2 tenants réels** (Postgres local, rôle NOSUPERUSER) : une requête sous tenant A n'écrit/ne lit que A, une sous B que B — étend `tests/integration/test_rls_isolation.py` (Sprint 163) au threading réel (pas le GUC legacy constant).
- **Cache** : deux tenants, même ticker/workflow/ratios → 2 clés distinctes, aucun hit croisé.
- **Rétrocompat** : requête non authentifiée / worker → défaut legacy, comportement inchangé ; la suite `pytest` (mocks asyncpg) reste verte.
- **Non-régression du `ContextVar`** sous concurrence : deux requêtes async simultanées avec tenants différents ne se contaminent pas.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts ; si un prompt skill/orchestrateur de skills est touché, lancer les `evals` ciblées (sinon le dire).

---

## SPRINTS SUGGÉRÉS (suite E3 → E4 — voir plan directeur §7)

### Sprint 165 — E3-S5 : preuve d'isolation rouge→vert
**Objectif** : test cross-tenant **rouge→vert** exhaustif (tenant A ne lit jamais les lignes de B) sur les **6** tables + revue OWASP de la policy RLS.
**Complexité** : Moyenne.
**Justification** : clôt l'épic E3 (bloqueur n°1) par la preuve d'isolation exigée au jalon investisseur M3.
**Référence** : la RLS est posée sur les 6 tables — `_TABLES` dans `alembic/versions/0005_business_rls.py:47`. Le test minimal actuel (`tests/integration/test_rls_isolation.py`) ne couvre que `watchlist` (1 table) et est câblé en gate CI (`.github/workflows/ci.yml`, job `migrations`, rôle NOSUPERUSER `rls_tester`) — E3-S5 **étend** la matrice aux 5 autres tables. Dépend du threading réel livré au Sprint 164.

### Sprint 166 — E4-S1 : metering (`usage_events`)
**Objectif** : table `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émise depuis l'orchestrateur — base de facturation.
**Complexité** : Moyenne.
**Justification** : ouvre l'épic E4 (facturation) ; source de vérité unique du metering (plan §8.1 décision 4).
**Référence** : `cost_usd`/`tokens_input`/`tokens_output` déjà persistés par analyse — colonnes présentes `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`). `usage_events` est **à créer** (table distincte, granularité par skill). Réutilise le **pattern append-only `AuditLogService`** posé au Sprint 160 (`app/services/audit_log_service.py`).

### Sprint 167 — E4-S2 : quotas par plan (`plan_limits`)
**Objectif** : table `plan_limits` (analyses/mois, taille screener, rétention) + compteur Redis ; `429` clair au dépassement ; override admin.
**Complexité** : Moyenne.
**Justification** : transforme la multi-tenance en offre commerciale (différenciation des plans) ; dépend du metering.
**Référence** : rate-limit Redis existant `app/middleware/rate_limit.py` monté `app/api/main.py:474` (à étendre par tenant/plan). `plan_limits` et le metering `usage_events` (Sprint 166) sont **à créer**.

### Sprint 168 — E4-S3 : clés API rattachées au tenant
**Objectif** : `api_keys.tenant_id` (FK) + attribution de chaque appel programmatique à un tenant (M4).
**Complexité** : Faible.
**Justification** : ferme le dernier trou de la multi-tenance (M4) — les clés API sont aujourd'hui hors tenance.
**Référence** : table `api_keys` gérée par `app/services/api_key_service.py` (audit déjà branché Sprint 160) ; la colonne `tenant_id` sur `api_keys` est **à créer** (migration chaînée après `0005_business_rls`).

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.50.0),
docs/plan-directeur-fintech-2026.md (§7 E3-S4 + §3.2 M2 point 3 + §3.2 M3), .claude/rules/api-architecture.md
et gotchas-operationnels.md.
Sprint actif : 164 — E3-S4 (threading tenant bout-en-bout). Résoudre le tenant authentifié
(JWT → users.tenant_id, Sprint 161) en entrée de requête via un contextvars.ContextVar (middleware
ASGI app/middleware/, défaut LEGACY_TENANT_ID pour non-auth/workers) ; généraliser le setup du pool
(app/db/tenant_context.py) pour LIRE ce ContextVar au lieu de la constante legacy ; remplir le tenant_id
réel aux 6 sites d'écriture (déjà paramétrés Sprint 162) + analyze_stream ; préfixer la clé cache Redis
par tenant (app/services/analysis_cache.py:79) et adapter invalidate(). Quotas screener par tenant si
le périmètre tient, sinon le différer à E4 explicitement.
Démarre un Postgres local (recette dans ce fichier ; installer alembic dans .venv) et PROUVE l'isolation
de DEUX tenants réels avec un rôle NOSUPERUSER (pas seulement le palier legacy).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; isolation runtime 2 tenants réels + non-hit cache croisé.
```
