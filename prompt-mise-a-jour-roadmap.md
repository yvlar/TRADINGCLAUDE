# Sprint 167 — E4-S2 : quotas par plan + quotas screener par tenant

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.53.0 — transformation B2B/SaaS, phase P0→P1)

L'épic **E4 (facturation/SaaS) est ouvert** : le Sprint 166 (E4-S1) a posé la table `usage_events` append-only (metering **par skill**, 7ᵉ table RLS) + son émission best-effort depuis l'orchestrateur. Démarre **E4-S2 quotas** : un plan tarifaire (`plan_limits`) borne la consommation d'un tenant (analyses/mois, taille screener, rétention), un compteur Redis applique la borne, un `429` clair signale le dépassement. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-166 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration.
> ⚠️ **Si `plan_limits` porte `tenant_id` (ou est lue par tenant) → décider de son périmètre RLS.** Si la table est rattachée au tenant, suivre le pattern des 7 tables RLS (migration `0006_usage_events.py`, `0005_business_rls.py`) : `ENABLE`+`FORCE` + policy `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` (USING + WITH CHECK), étendre la matrice `tests/integration/test_rls_isolation.py` (devient 8ᵉ table) et le `GRANT` du rôle `rls_tester` (`.github/workflows/ci.yml`). Si `plan_limits` est une **table de référence globale** (un plan = même borne pour tous les tenants, clé = nom de plan), justifier explicitement l'**absence** de tenant/RLS.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.53.0)
2. `docs/plan-directeur-fintech-2026.md` — **§7-§8 épic E4 ligne `E4-S2`** (quotas) et **jalon M3** (quotas screener) / **M4** (facturation)
3. `.claude/rules/api-architecture.md` (middleware, rate-limit Redis, contraintes infra) et `.claude/rules/gotchas-operationnels.md` (timeouts/parallélisme screener — la borne de taille screener par tenant vit ici)
4. `app/middleware/rate_limit.py` (`RateLimitMiddleware`, compteur Redis incr/expire à cloner pour le quota) · importé `app/api/main.py:46`, monté `app/api/main.py:482` (ordre des middlewares CSRF→BearerToken→RateLimit→TenantContext commenté `:478`) · `app/db/tenant_context.py:24` (`get_current_tenant()` → clé du compteur par tenant) · `app/services/usage_event_service.py` (Sprint 166 — `usage_events` à agréger pour le compteur mensuel)

---

## TÂCHE — Sprint 167 (E4-S2) : quotas par plan + quotas screener par tenant

**Objectif** : transformer la multi-tenance en **offre commerciale bornée** — un plan tarifaire limite la consommation d'un tenant, un compteur applique la borne, un `429` explicite signale le dépassement. Absorbe aussi le **quota screener par tenant** explicitement reporté de l'E3-S4 (Sprint 164).

### Spécification
1. **Migration `alembic/versions/0007_plan_limits.py`** (chaînée après `0006_usage_events`) : table `plan_limits` définissant, **par plan** (`plan TEXT` — `free`/`pro`/…), les bornes : `max_analyses_per_month INTEGER`, `max_screener_tickers INTEGER`, `retention_days INTEGER` (+ `created_at`). Seeder les plans de base. **Rattachement tenant→plan** : décider entre (a) `tenants.plan TEXT NOT NULL DEFAULT 'free'` (colonne sur `tenants`, simple) **ou** (b) table d'association — justifier le choix. Décider et **documenter** le périmètre RLS de `plan_limits` (table de référence globale → pas de tenant/RLS ; voir l'avertissement DB ci-dessus).
2. **`app/services/quota_service.py`** (nouveau) — `QuotaService` : (a) résout le plan du tenant courant (`get_current_tenant()`), lit ses bornes dans `plan_limits` ; (b) **compteur mensuel d'analyses** via Redis (`incr`/`expire` à la fenêtre mensuelle, clé `quota:{tenant}:{YYYY-MM}` — calquer `app/middleware/rate_limit.py`) **OU** agrégation `COUNT(*)` sur `usage_events` par tenant/mois (choisir et justifier : Redis = rapide mais éphémère, `usage_events` = source de vérité durable) ; (c) `check_and_increment()` lève une erreur quota (→ `429`) au dépassement, sinon incrémente. Best-effort **interdit ici** : un quota est une **borne dure** (au contraire du metering Sprint 166 qui est best-effort) — un échec d'infra de quota doit être tranché explicitement (fail-open documenté **ou** fail-closed `503`).
3. **Application du quota d'analyses** : au point d'entrée `/analyze` (et `/analyze/stream`), avant de lancer l'orchestrateur, appeler `QuotaService.check_and_increment()` ; réponse `429` claire (`Retry-After` ou message « quota mensuel atteint, plan `X` : N/N ») au dépassement. Ne pas compter un **cache hit** (rien n'est consommé — cohérent avec le metering).
4. **Quota screener par tenant (M3, reporté de E3-S4)** : borner `POST /screen` à `max_screener_tickers` du plan du tenant (en plus du plafond technique `max 20` existant) — `429`/`422` clair si la liste dépasse la borne du plan.
5. **Frontend (léger)** : surfacer le `429` quota proprement (toast/bandeau « quota atteint ») là où `/analyze` et `/screen` sont appelés — pas de page dédiée ce sprint.

### Tests / validation
- **Unitaires** (`tests/services/`) : `QuotaService` — sous la borne incrémente et autorise ; à la borne lève l'erreur quota ; fenêtre mensuelle (clé/expire) ; résolution plan→bornes ; cache hit ne consomme pas.
- **Migration** (`tests/test_alembic_plan_limits.py`, sans DB) : forme/chaînage de révision (après `0006_usage_events`), colonnes/seed, downgrade ordre inverse. Modèle : `tests/test_alembic_usage_events.py`.
- **Intégration** (`@pytest.mark.integration`, PG local migré) : `/analyze` au-delà du quota → `429` ; sous quota → `200` ; `/screen` au-delà de `max_screener_tickers` → `429`/`422`. Si `plan_limits` est rattachée au tenant et sous RLS, l'ajouter à la matrice `test_rls_isolation.py` (8ᵉ table) + GRANT CI.
- **Composant** (`frontend/src/__tests__/`) : le `429` quota rend le bandeau/toast attendu (happy path + dépassement).
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts ; `cd frontend && npm run typecheck` + Vitest verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 168 — E4-S3 : clés API rattachées au tenant
**Objectif** : `api_keys.tenant_id` (FK) + résolution du tenant pour chaque appel programmatique (chemin Bearer), pour que les clés API entrent dans la tenance (M4).
**Complexité** : Faible.
**Justification** : ferme le dernier trou de la multi-tenance — aujourd'hui une requête par clé API retombe sur le tenant legacy (le chemin Bearer ne pose pas `tenant_id`).
**Référence** : `BearerTokenMiddleware` existe (`app/middleware/auth.py:20`), thread déjà le claim `tenant_id` JWT (`app/middleware/auth.py:163`) mais **pas** sur le chemin clé API ; table `api_keys` gérée par `app/services/api_key_service.py` **sans** colonne `tenant_id` aujourd'hui (`grep -ni tenant app/services/api_key_service.py` vide, vérifié cette session). La colonne `api_keys.tenant_id` est **à créer** (migration chaînée après `0007_plan_limits`).

### Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me`
**Objectif** : exposer le `tenant_id` (et le nom du tenant) dans la réponse `/auth/me`, désormais cohérent puisque le contexte tenant est threadé (E3-S4) et borné (E4-S2).
**Complexité** : Faible.
**Justification** : le Sprint 161 avait **délibérément omis** `tenant_id` de la réponse publique tant que le threading n'existait pas — l'exposition devient cohérente (préparation UI multi-tenant + affichage du plan).
**Référence** : `tenant_id` absent de `UserPublic` — commenté dans `app/models/auth.py` (bloc `UserPublic`, vérifié cette session) ; `users.tenant_id` déjà lu par `user_service.get_by_id` (`SELECT … tenant_id …`, `app/services/user_service.py:81`, vérifié). L'enrichissement de `UserPublic` + le `JOIN`/lookup du nom de tenant sont **à créer**.

### Sprint 170 — E4-S5 : endpoint d'agrégation de consommation (`GET /usage`)
**Objectif** : exposer la consommation agrégée du tenant courant (coût/tokens par skill, par jour, total période) à partir de `usage_events`, pour le futur tableau de bord de facturation.
**Complexité** : Moyenne.
**Justification** : rend le metering (Sprint 166) actionnable côté produit et alimente l'UI facturation/quotas (M4) ; prérequis d'une page « Facturation » frontend.
**Référence** : `usage_events` existe (`alembic/versions/0006_usage_events.py`, `app/services/usage_event_service.py`, Sprint 166) ; le pattern d'agrégation par jour/skill existe déjà pour les coûts globaux (`get_metrics` → `daily_cost`/`skills_cost`, `app/orchestrator/core.py:1981` — à adapter en version **scopée tenant** via la RLS d'`usage_events`). L'endpoint `/usage` et son agrégation par tenant sont **à créer**.

### Sprint 171 — E4-S6 : intégration Stripe Billing (abonnements + usage)
**Objectif** : brancher Stripe (abonnement par plan + facturation à l'usage depuis `usage_events`), webhooks de cycle de vie (souscription, paiement, dunning).
**Complexité** : Élevée.
**Justification** : convertit le socle metering+quotas (Sprints 166-167) en revenu réel (B1/B2 du plan directeur) ; dernière marche de M4.
**Référence** : `usage_events` (Sprint 166) et `plan_limits` (Sprint 167) sont les socles ; toute l'intégration Stripe (SDK, webhooks, mapping plan↔price, `.env` clés Stripe) est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.53.0),
docs/plan-directeur-fintech-2026.md (§7-§8 E4-S2 + jalon M3/M4), .claude/rules/api-architecture.md
et gotchas-operationnels.md.
Sprint actif : 167 — E4-S2 (quotas). Créer la migration 0007_plan_limits (table de bornes par plan
+ rattachement tenant→plan ; décider/documenter le périmètre RLS), un QuotaService (résolution plan
→ bornes, compteur mensuel Redis OU agrégation usage_events, check_and_increment qui lève au
dépassement — borne DURE, pas best-effort), l'application du quota à /analyze et /analyze/stream
(429 clair, cache hit ne consomme pas), et la borne max_screener_tickers par tenant sur /screen
(quota screener reporté de E3-S4). Surfacer le 429 quota côté frontend (toast/bandeau).
Démarre un Postgres local (recette dans ce fichier ; installer alembic dans .venv) et PROUVE
le 429 au dépassement + l'autorisation sous quota ; si plan_limits est tenant-scoped sous RLS,
étendre la matrice (8ᵉ table) + GRANT CI.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ + frontend typecheck/Vitest ; 429 au dépassement
vérifié + sous-quota autorisé + borne screener par tenant.
```
