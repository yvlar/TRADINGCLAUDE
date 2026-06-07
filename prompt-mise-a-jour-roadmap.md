# Sprint 170 — E4-S5 : endpoint d'agrégation de consommation (`GET /usage`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.56.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (169, E4-S4) a **exposé le tenant dans `/auth/me`** (`UserPublic.tenant_id` + `tenant_name`, badge header côté frontend). L'épic **E4 (facturation/SaaS)** dispose désormais du socle complet : metering par-skill (`usage_events`, S166), quotas par plan (S167), clés API rattachées au tenant (S168) et tenant visible côté client (S169). Prochaine marche : **rendre le metering actionnable côté produit** via un endpoint d'agrégation. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-169 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant tests de migration/mypy. Le frontend peut nécessiter `cd frontend && npm install` (node_modules absent du conteneur).
> ⚠️ **Sprint sans migration** : E4-S5 lit `usage_events` (déjà créée au S166) et agrège — **aucune table/colonne nouvelle attendue**. C'est un sprint **lecture + agrégation + endpoint** (+ frontend léger optionnel).
> ⚠️ **RLS** : `usage_events` est **sous RLS** (7ᵉ table, policy tenant `NULLIF(...)`). L'agrégation doit tourner **sous le contexte tenant** (ContextVar/GUC posé par `TenantContextMiddleware`) pour ne voir que les lignes du tenant courant — c'est l'isolation native, pas un `WHERE tenant_id=` applicatif. Tester l'isolation avec le rôle NOSUPERUSER.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.56.0)
2. `.claude/rules/api-architecture.md` (nouvel endpoint, `cost_usd` persisté, modèle de réponse Pydantic, contraintes infra) et `.claude/rules/tests-pyramide.md` (nouvel endpoint FastAPI → **test d'intégration obligatoire** ; patch `call_claude_with_retry` ; fixture `client`)
3. **Code de référence vérifié cette session** : `app/services/usage_event_service.py` — `UsageEventService` (`:33`), `record` (`:39`), INSERT `usage_events` (`:58`) **append-only** (pas encore de méthode d'agrégation/lecture — **à créer**) · `app/orchestrator/core.py` — `get_metrics` (`:1875`) et son agrégation **par jour** `daily_cost` (`:1981`) = patron d'agrégation à **adapter en version scopée tenant** sur `usage_events` (et non `analysis_history`) · `app/api/main.py` — route `GET /metrics` (`:672`) qui délègue à `orchestrator.get_metrics(days=...)` (`:687`) = patron d'endpoint+router à cloner pour `GET /usage`

---

## TÂCHE — Sprint 170 (E4-S5) : endpoint d'agrégation de consommation `GET /usage`

**Objectif** : exposer la **consommation agrégée du tenant courant** à partir de `usage_events`, pour alimenter un futur tableau de bord de facturation et l'affichage « N analyses / coût ce mois ». Rend le metering (S166) + quotas (S167) **actionnables côté produit**.

### Spécification
1. **Méthode de lecture/agrégation** — ajouter à `UsageEventService` (ou un service de reporting dédié) une méthode `aggregate(days: int)` qui, **sous le contexte tenant courant** (RLS), agrège `usage_events` : total `cost_usd` + `tokens_input`/`tokens_output`, **ventilation par skill** (coût/tokens/compte d'événements par `skill`), et **série par jour** (`YYYY-MM-DD` → coût, patron `daily_cost` de `core.py:1981`). `cost_usd` est `NUMERIC` → renvoyer un `float` arrondi côté API (cohérent avec `MetricsResponse`). Décider/documenter la fenêtre par défaut (`days=30`).
2. **Modèle de réponse Pydantic** (`app/models/` ou à côté de l'endpoint) — `UsageResponse` typé : `total_cost_usd`, `total_tokens_input/output`, `by_skill: list[UsageBySkill]`, `daily_cost: dict[str, float]`, `period_days`. Zéro `dict` non typé exposé.
3. **Endpoint `GET /usage?days=30`** — authentifié (cookie JWT) ; lit le tenant depuis le contexte serveur (PAS de `tenant_id` en query — l'isolation vient de la RLS via le ContextVar). Clôner le patron `GET /metrics` (`app/api/main.py:672`). 422 si `days` hors bornes raisonnables.
4. **Frontend (léger, optionnel selon temps)** — client `usage.ts` typé + affichage minimal (ex. carte « Consommation ce mois » réutilisant les composants existants `SkillCostPieChart`/`DailyCostTrendChart` si applicable). Si non livré ce sprint, le **dire explicitement** et le verser au sprint « page Facturation ».

### Tests / validation
- **Unitaires** (`tests/services/`) : l'agrégation calcule bien total/par-skill/par-jour sur un jeu d'événements mocké ; fenêtre `days` respectée.
- **Intégration** (`tests/api/` ou `tests/integration/`) : `GET /usage` authentifié → forme `UsageResponse` correcte ; **isolation RLS** prouvée sous rôle NOSUPERUSER (tenant A ne voit que sa consommation, B la sienne) sur Postgres migré.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts ; si frontend touché : `cd frontend && npm run typecheck` + Vitest + ESLint verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).
- **Preuve d'acceptation observable** : appeler `GET /usage` (test d'intégration) et **constater la forme agrégée** (total + by_skill + daily_cost), pas seulement « vert ».

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 171 — E4-S6 : purge de rétention par plan (`retention_days`)
**Objectif** : appliquer `plan_limits.retention_days` (posé au S167 mais inappliqué) — tâche Celery qui purge analyses/événements au-delà de la rétention du plan de chaque tenant.
**Complexité** : Moyenne.
**Justification** : transforme `retention_days` d'une colonne dormante en politique réelle (différenciation free/pro + conformité données) ; complète les quotas par une borne temporelle.
**Référence** : `retention_days` existe et est seedé (`alembic/versions/0007_plan_limits.py:58`, valeurs free=30/pro=365 lignes 44-45, vérifié cette session) ; le scheduler Celery beat existe (`run_scheduled_screener`, `app/workers/tasks.py:757-758`, vérifié). La tâche de purge scopée par plan/tenant est **à créer**.

### Sprint 172 — E4-S7 : intégration Stripe Billing (abonnements + usage)
**Objectif** : brancher Stripe (abonnement par plan + facturation à l'usage depuis `usage_events`), webhooks de cycle de vie (souscription, paiement, dunning), mapping plan↔price.
**Complexité** : Élevée.
**Justification** : convertit le socle metering+quotas+clés-tenant (166-168) + agrégation (170) en revenu réel (B1/B2 du plan directeur) ; dernière marche de M4.
**Référence** : `usage_events` (S166), `plan_limits`/`tenants.plan` (S167) et `api_keys.tenant_id` (S168) sont les socles ; toute l'intégration Stripe (SDK, webhooks, mapping plan↔price, `.env` clés Stripe) est **à créer**.

### Sprint 173 — E4-S8 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant via le ContextVar, mais une clé env-admin retombe sur legacy — NIT S168).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (S168) pilotable côté produit, prérequis d'un onboarding multi-tenant.
**Référence** : `create_key(...)` rattache au tenant courant (`app/services/api_key_service.py:75`, S168, vérifié) ; l'endpoint `POST /admin/keys` (`app/api/endpoints/admin.py:76`) ne passe **pas** de `tenant_id` explicite (`create_key(name=..., role=..., expires_at=...)`, lignes 92-94, vérifié). L'ajout d'un champ `tenant_id` optionnel à `CreateKeyRequest` + sa validation (admin ne crée que pour son tenant) sont **à créer**.

### Sprint 174 — E4-S9 : page « Facturation » frontend
**Objectif** : page React consolidant la consommation (`GET /usage`), le plan courant (`tenant.plan`) et le quota restant du mois (bandeau S167) en un tableau de bord de facturation lisible.
**Complexité** : Moyenne.
**Justification** : donne une surface produit au socle E4 (metering+quotas+agrégation) ; point d'entrée naturel avant l'intégration Stripe (S172).
**Référence** : `GET /usage` sera créé au S170 (ce sprint) ; `QuotaBanner` existe (`frontend/src/components/QuotaBanner.tsx`, S167) ; `SkillCostPieChart`/`DailyCostTrendChart` existent (`frontend/src/components/`, vérifié via `ls`). La page `BillingPage` + son client typé sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.56.0), .claude/rules/api-architecture.md et tests-pyramide.md.
Sprint actif : 170 — E4-S5 (endpoint d'agrégation de consommation GET /usage). Ajouter à
UsageEventService une agrégation scopée tenant (total + par skill + par jour) sur usage_events
(patron daily_cost de core.py:1981), exposer un GET /usage?days=30 typé (UsageResponse) clôné
sur le patron GET /metrics (app/api/main.py:672), authentifié, isolation par la RLS (ContextVar/GUC,
PAS de tenant_id en query). Aucune migration attendue (usage_events existe depuis S166).
Démarre un Postgres local (recette dans ce fichier) et PROUVE la forme agrégée de GET /usage
+ l'isolation RLS (rôle NOSUPERUSER, tenant A ne voit que sa conso) via un test d'intégration.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ (+ frontend typecheck/Vitest/ESLint si touché) ;
forme de GET /usage constatée + isolation RLS prouvée.
```
