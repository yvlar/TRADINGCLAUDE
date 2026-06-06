# Sprint 165 — E3-S5 : preuve d'isolation rouge→vert

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.51.0 — transformation B2B/SaaS, phase P0)

La roadmap exécute le **plan directeur `docs/plan-directeur-fintech-2026.md`** (44 sprints `E#-S#`, P0→P3). **Sprint 164 (E3-S4) complété** : le tenant **authentifié** est désormais threadé de bout en bout — un `ContextVar` `current_tenant` (`app/db/tenant_context.py`), posé par un middleware ASGI à partir du claim JWT, alimente **à la fois** le GUC RLS et la colonne `tenant_id` des 6 sites d'écriture (colonne == GUC → `WITH CHECK` satisfait), et préfixe la clé cache Redis. Isolation de deux tenants réels prouvée en runtime (Postgres local, rôle NOSUPERUSER). Démarre **E3-S5** : transformer la preuve d'isolation minimale (1 table) en **matrice cross-tenant rouge→vert exhaustive sur les 6 tables** + revue OWASP de la policy RLS, pour clore l'épic E3 (bloqueur n°1). État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-164 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> # Rôle NOSUPERUSER pour exercer la RLS (un superuser la contourne) :
> #   CREATE ROLE rls_tester LOGIN PASSWORD 'rlspass' NOSUPERUSER; GRANT … ON ALL TABLES IN SCHEMA public TO rls_tester;
> # puis RLS_TEST_DATABASE_URL=postgresql://rls_tester:rlspass@127.0.0.1:5433/copilote pytest tests/integration/test_rls_isolation.py -m integration
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration/RLS.
> ⚠️ **Le gate CI ne couvre aujourd'hui que `watchlist` + `tenants`** : `.github/workflows/ci.yml:201` ne `GRANT` les droits du rôle NOSUPERUSER `rls_tester` que sur ces deux tables. Étendre la matrice aux 6 tables impose d'élargir ce `GRANT` (sinon le test échoue sur permission, pas sur isolation).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.51.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7 épic E3 ligne `E3-S5`** (ce sprint) et **jalon M3** (preuve d'isolation exigée)
3. `.claude/rules/tests-pyramide.md` (niveau intégration, marqueur `@pytest.mark.integration`, patch `call_claude_with_retry`) et `.claude/rules/securite.md` (revue OWASP — pas de secret loggé, fail-closed)
4. `tests/integration/test_rls_isolation.py` (la preuve minimale 1 table à **étendre** aux 6) · `alembic/versions/0005_business_rls.py:47` (tuple `_TABLES` des 6 tables RLS) · `.github/workflows/ci.yml:151` (job `migrations`, rôle NOSUPERUSER `rls_tester`, `GRANT` à élargir)

---

## TÂCHE — Sprint 165 (E3-S5) : preuve d'isolation rouge→vert

**Objectif** : prouver — table par table, en **rouge→vert** — qu'un tenant A ne lit/écrit JAMAIS les lignes d'un tenant B sur les **6** tables métier, et documenter une revue OWASP de la policy RLS. Clôt l'épic E3.

### Spécification
1. **Matrice d'isolation 6 tables** (`tests/integration/test_rls_isolation.py`, marqueur `@pytest.mark.integration`, rôle NOSUPERUSER) : pour chacune des 6 tables (`analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`) — insertion sous tenant A et sous tenant B, puis : (a) A ne voit que A en lecture (`SELECT`) ; (b) `WITH CHECK` refuse à A d'écrire une ligne de B ; (c) fail-closed (GUC vide → 0 ligne). Paramétrer sur le tuple `_TABLES` plutôt que dupliquer (attention aux contraintes propres : ex. `watchlist` a un index unique **global** `(ticker, workflow)` non tenant-scoped → utiliser des clés distinctes par tenant ; `analysis_history`/`annotations` exigent des colonnes NOT NULL — fournir un payload minimal valide par table).
2. **Aspect rouge→vert** : démontrer que le test échouerait SANS la RLS (ex. un cas témoin documenté, ou une assertion qui ne passe que parce que la policy filtre) — la valeur du sprint est la preuve, pas juste un test vert de plus.
3. **Gate CI étendu** : élargir le `GRANT` du rôle `rls_tester` (`.github/workflows/ci.yml:201`) aux 6 tables (+ `tenants`) pour que la matrice tourne en CI, pas seulement en local.
4. **Revue OWASP de la policy** (`docs/` — note de sécurité) : passer la policy RLS au crible (contournement par fonction `SECURITY DEFINER` ? `BYPASSRLS` sur un rôle ? injection via le GUC ? `FORCE RLS` couvre-t-il le propriétaire ? les 6 tables ont-elles bien `ENABLE`+`FORCE` ?). Conclusions + risques résiduels documentés.
   - **Gap connu à traiter/documenter (hérité du Sprint 164, revue indépendante)** : les chemins **auth-exemptés** (`BearerTokenMiddleware.EXEMPT_PREFIXES` = `/report`, `/telemetry`, `/ws` — `app/middleware/auth.py:46`) ne résolvent AUCUN tenant → GUC legacy. `app/api/endpoints/report.py` lit `analysis_history WHERE id=$1` sous la RLS : une fois de vrais tenants émis, la ligne d'un tenant non-legacy devient invisible (404 parasite) et les lignes legacy restent lisibles par quiconque détient l'UUID. Décider : scoper le **token de rapport** au tenant, ou threader le tenant dans l'auth de rapport, ou documenter `/report` comme legacy-only. C'est de l'isolation **côté lecture** — hors du périmètre write-path/cache du Sprint 164, à trancher ici.

### Tests / validation
- Matrice 6 tables verte sous PostgreSQL local migré + rôle NOSUPERUSER ; chaque table prouve lecture isolée + `WITH CHECK` + fail-closed.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts. Aucun prompt skill/orchestrateur touché → pas d'eval (le dire).
- Le job CI `migrations` exécute la matrice 6 tables (gate, pas seulement preuve locale).

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 166 — E4-S1 : metering (`usage_events`)
**Objectif** : table `usage_events` append-only (tenant, skill, workflow, cost_usd, tokens, ts) émise depuis l'orchestrateur — source de vérité unique de la facturation.
**Complexité** : Moyenne.
**Justification** : ouvre l'épic E4 (facturation) ; agrège la consommation par tenant désormais correctement isolé (E3 clos).
**Référence** : `cost_usd`/`tokens_input`/`tokens_output` déjà persistés par analyse — colonnes présentes `alembic/versions/0001_baseline_schema.py:31-33` (table `analysis_history`). `usage_events` (granularité par skill, append-only) est **à créer** ; réutilise le **pattern append-only `AuditLogService`** posé au Sprint 160 (`app/services/audit_log_service.py`).

### Sprint 167 — E4-S2 : quotas par plan + quotas screener par tenant
**Objectif** : table `plan_limits` (analyses/mois, taille screener, rétention) + compteur Redis ; `429` clair au dépassement ; **inclut les quotas screener par tenant différés de l'E3-S4** (borne tickers/analyses par tenant).
**Complexité** : Moyenne.
**Justification** : transforme la multi-tenance en offre commerciale ; absorbe le quota screener explicitement reporté au Sprint 164.
**Référence** : rate-limit Redis existant `app/middleware/rate_limit.py`, monté `app/api/main.py:478` (à étendre par tenant/plan) ; le `ContextVar` tenant (`app/db/tenant_context.py`, Sprint 164) fournit déjà le tenant courant pour cléer le compteur. `plan_limits` et le metering `usage_events` (Sprint 166) sont **à créer**.

### Sprint 168 — E4-S3 : clés API rattachées au tenant
**Objectif** : `api_keys.tenant_id` (FK) + résolution du tenant pour chaque appel programmatique (chemin Bearer), pour que les clés API entrent dans la tenance (M4).
**Complexité** : Faible.
**Justification** : ferme le dernier trou de la multi-tenance — aujourd'hui une requête par clé API retombe sur le tenant legacy (`BearerTokenMiddleware` ne pose pas `tenant_id` sur le chemin Bearer).
**Référence** : table `api_keys` gérée par `app/services/api_key_service.py` (sans colonne `tenant_id` aujourd'hui — `grep tenant` vide) ; la colonne `tenant_id` sur `api_keys` est **à créer** (migration chaînée après `0005_business_rls`). Le `ContextVar`/middleware tenant (Sprint 164) est en place : il suffira de poser `request.state.tenant_id` depuis l'enregistrement de clé sur le chemin Bearer de `app/middleware/auth.py`.

### Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me`
**Objectif** : exposer le `tenant_id` (et le nom du tenant) dans la réponse `/auth/me`, désormais pertinent puisque le contexte tenant est threadé.
**Complexité** : Faible.
**Justification** : le Sprint 161 avait **délibérément omis** `tenant_id` de la réponse publique tant que le threading n'existait pas (`app/models/auth.py:64`) — E3-S4 l'a livré, l'exposition devient cohérente (préparation UI multi-tenant).
**Référence** : `tenant_id` absent de la réponse publique — commenté `app/models/auth.py:64` ; `users.tenant_id` déjà lu par `user_service.get_by_id` (`SELECT … tenant_id …`, `app/services/user_service.py:81`).

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.51.0),
docs/plan-directeur-fintech-2026.md (§7 E3-S5 + jalon M3), .claude/rules/tests-pyramide.md
et securite.md.
Sprint actif : 165 — E3-S5 (preuve d'isolation rouge→vert). Étendre tests/integration/test_rls_isolation.py
en une matrice cross-tenant paramétrée sur les 6 tables métier (tuple _TABLES, alembic 0005) : lecture isolée
(A ne voit que A) + WITH CHECK (A ne peut écrire B) + fail-closed (GUC vide → 0 ligne), sous rôle NOSUPERUSER.
Démontrer le rouge→vert (le test échouerait sans la RLS). Élargir le GRANT du rôle rls_tester aux 6 tables
dans .github/workflows/ci.yml:201 (gate CI). Rédiger une note OWASP de revue de la policy RLS dans docs/.
Démarre un Postgres local (recette dans ce fichier ; installer alembic dans .venv) et PROUVE la matrice
des 6 tables avec un rôle NOSUPERUSER.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; matrice 6 tables verte (lecture isolée + WITH CHECK + fail-closed).
```
