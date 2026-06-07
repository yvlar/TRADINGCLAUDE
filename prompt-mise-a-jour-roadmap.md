# Sprint 172 — E4-S7 : intégration Stripe Billing (abonnements + facturation à l'usage)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.58.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (171, E4-S6) a rendu `plan_limits.retention_days` **actionnable** : une tâche Celery quotidienne (`run_retention_purge`, 03h00 UTC) purge, pour chaque tenant **sous son contexte RLS** (`tenant_scope`), les tables historiques au-delà de la rétention de son plan (free=30/pro=365) ; `usage_events` (facturation), `watchlist` et `annotations` exclus. L'épic **E4** dispose maintenant du socle complet côté infra : metering (S166), quotas (S167), clés-tenant (S168), tenant exposé (S169), agrégation `GET /usage` (S170) et **rétention par plan** (S171). Prochaine marche : **convertir ce socle en revenu réel** — brancher Stripe. État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-171 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant tests de migration/mypy. Le SDK Stripe (`stripe`) devra être ajouté à `requirements.txt` et installé.
> ⚠️ **Webhooks Stripe = entrée non authentifiée** : la signature `Stripe-Signature` (HMAC via `STRIPE_WEBHOOK_SECRET`) est la SEULE authentification — vérifier la signature **avant** tout traitement, sinon n'importe qui peut forger un événement de paiement. L'endpoint webhook doit être exempté de l'auth middleware (cf. `EXEMPT_PREFIXES`, `app/middleware/auth.py:46`) MAIS sa sécurité repose entièrement sur la vérification de signature.
> ⚠️ **Aucune clé Stripe en dur** : `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET`/price IDs via `.env` + `.env.example` (valeurs factices) — cf. `.claude/rules/securite.md`.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.58.0)
2. `.claude/rules/securite.md` (clés Stripe dans `.env`/`.env.example`, pas de secret dans les logs/traces — central pour un sprint d'intégration de paiement) et `.claude/rules/api-architecture.md` (nouveau routeur `1 router par domaine`, async/`httpx`, montage dans `app/api/main.py`, `cost_usd` — édition `app/**`)
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `usage_events` (S166) = source de vérité de la conso à facturer ; `GET /usage` (`app/api/endpoints/usage.py:9-12`, créé S170) agrège déjà cost/tokens par tenant ; `plan_limits(plan, …, retention_days)` + FK `tenants.plan` (`alembic/versions/0007_plan_limits.py:58,65`) = mapping plan↔borne ; `api_keys.tenant_id` (S168). **Toute l'intégration Stripe (SDK, table d'abonnement, webhooks, mapping plan↔price, clés `.env`) est à CRÉER.**

---

## TÂCHE — Sprint 172 (E4-S7) : intégration Stripe Billing

**Objectif** : convertir le socle metering+quotas+agrégation (S166-S171) en **revenu réel** — brancher Stripe pour (a) l'abonnement d'un tenant à un plan (`free`/`pro`) et (b) la facturation à l'usage à partir de `usage_events`, avec les webhooks de cycle de vie. Dernière marche de M4 (monétisation).

### Spécification
1. **SDK + configuration** — ajouter `stripe` à `requirements.txt` ; clés `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, et le mapping plan↔price (`STRIPE_PRICE_FREE`/`STRIPE_PRICE_PRO` ou table de correspondance) dans `.env` + `.env.example` (valeurs factices). Client Stripe initialisé via env, jamais hardcodé.
2. **Migration** — table `subscriptions` (ou colonnes sur `tenants`) reliant un tenant à son `stripe_customer_id` / `stripe_subscription_id` / statut (`active`/`past_due`/`canceled`) + `plan` courant. **Décider/documenter** : table d'association vs colonnes sur `tenants` (cohérent avec la décision « option a » du S167 pour `tenants.plan`). RLS : `subscriptions` est-elle scopée tenant (entre dans la matrice) ou table de référence d'authn comme `api_keys` (hors RLS) ? Trancher explicitement.
3. **Service `StripeService`** (`app/services/`) — création de session de checkout (souscription à un plan), résolution `tenant ↔ customer`, et **synchronisation du plan** : à la réception d'un événement d'abonnement, mettre à jour `tenants.plan` (le `QuotaService`/purge en dépendent déjà). Facturation à l'usage : pousser la conso agrégée (`GET /usage` / `UsageEventService.aggregate`) vers Stripe (metered usage records) — ou documenter le report de la partie metered si trop large pour ce sprint.
4. **Endpoint webhook** (`app/api/endpoints/`, nouveau routeur, monté dans `main.py`) — `POST /billing/webhook` : **vérifier la signature `Stripe-Signature`** (`STRIPE_WEBHOOK_SECRET`) AVANT tout traitement (rejet 400 si invalide), puis router les événements (`customer.subscription.created/updated/deleted`, `invoice.paid`, `invoice.payment_failed` → dunning). Exempté de l'auth middleware (`EXEMPT_PREFIXES`) — sécurité = signature uniquement. Idempotence : un même `event.id` ne doit pas être traité deux fois.
5. **Sécurité/observabilité** — aucune clé/secret Stripe dans les logs JSON ni les traces Langfuse ; erreurs 500 assainies (corrélation_id), `str(exc)` jamais exposé.

### Tests / validation
- **Unitaires** (`tests/services/`) : `StripeService` avec le SDK mocké — checkout session créée, mapping plan↔price, synchro `tenants.plan` sur événement d'abonnement, idempotence par `event.id`.
- **Intégration** (`tests/api/` ou `tests/integration/`) : `POST /billing/webhook` — **signature invalide → 400 sans effet** ; signature valide → traitement (mocke la vérification SDK ou utilise un secret de test) ; `tenants.plan` mis à jour ; double livraison du même event → idempotent.
- **Migration** (`tests/`) : forme de la table `subscriptions`/colonnes, chaînage Alembic, décision RLS prouvée (dans ou hors matrice selon le choix), downgrade.
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).
- **Preuve d'acceptation observable** : sur PG migré, simuler un événement `customer.subscription.updated` (plan free→pro) signé et **constater** `tenants.plan='pro'` ; webhook à signature forgée → 400 et aucune mutation.

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 173 — E4-S8 : page « Facturation » frontend
**Objectif** : page React consolidant la consommation (`GET /usage`), le plan courant (`tenant.plan`) et le quota restant du mois en un tableau de bord de facturation lisible, avec bouton « Gérer l'abonnement » (Stripe portal).
**Complexité** : Moyenne.
**Justification** : donne une surface produit au socle E4 + à l'intégration Stripe (S172) ; transforme la facturation en self-service.
**Référence** : `GET /usage` créé au S170 (`app/api/endpoints/usage.py:9-12`, vérifié) ; `UsageResponse`/`UsageBySkill` dans `app/models/usage.py` ; `QuotaBanner` existe (`frontend/src/components/QuotaBanner.tsx`, vérifié) ; `SkillCostPieChart`/`DailyCostTrendChart` existent (`frontend/src/components/`, vérifié via `ls`). La page `BillingPage` + son **client typé `frontend/src/api/usage.ts`** (absent, vérifié via `ls` → **à créer**) sont à créer.

### Sprint 174 — E4-S9 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via un champ `tenant_id` optionnel sur `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant via le ContextVar ; une clé env-admin retombe sur legacy).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (S168) pilotable côté produit, prérequis d'un onboarding multi-tenant.
**Référence** : `create_key(...)` rattache au tenant courant (`app/services/api_key_service.py:82`, S168, vérifié) ; l'endpoint `POST /admin/keys` (`app/api/endpoints/admin.py:82`) délègue à `service.create_key(...)` (`:90`) **sans** `tenant_id` explicite (vérifié). L'ajout d'un champ `tenant_id` optionnel à `CreateKeyRequest` + sa validation (admin ne crée que pour son tenant) sont **à créer**.

### Sprint 175 — E4-S10 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy via GUC par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté (`docs/revue-owasp-rls-2026-06.md`) — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` est exempté de l'auth middleware (`app/middleware/auth.py:46` `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")`, vérifié) → GUC legacy par défaut ; la décision « legacy-only documentée » est tracée dans `docs/revue-owasp-rls-2026-06.md` (existe, vérifié). Un token de rapport portant le tenant + le threading du contexte (réutilisant `tenant_scope`, `app/db/tenant_context.py`, créé S171) sont **à créer**.

### Sprint 176 — E5-S1 : threading tenant des analyses planifiées (workers metrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que sous legacy, afin de les metrer dans `usage_events` (aujourd'hui chemin worker non metré, déféré au S166).
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ; réutilise la primitive `tenant_scope` posée au S171.
**Référence** : le chemin worker tourne sous legacy (commentaire `app/workers/tasks.py` `_build_orchestrator` « analyses planifiées sous tenant legacy — déféré », vérifié S166) ; `tenant_scope` (`app/db/tenant_context.py`, créé S171, vérifié) est la primitive d'exécution par-tenant ; `watchlist` porte déjà `tenant_id` (RLS, S163-165). Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.58.0), .claude/rules/securite.md et api-architecture.md.
Sprint actif : 172 — E4-S7 (intégration Stripe Billing). Brancher Stripe : SDK + clés .env
(STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET/price IDs, + .env.example factice), migration
subscriptions (trancher RLS in/out), StripeService (checkout + synchro tenants.plan), endpoint
POST /billing/webhook VÉRIFIANT la signature Stripe-Signature AVANT traitement (exempté auth,
EXEMPT_PREFIXES auth.py:46) + idempotence par event.id, facturation à l'usage depuis usage_events
(GET /usage, S170) ou report documenté de la partie metered.
Démarre un Postgres local (recette dans ce fichier) et PROUVE : webhook signé free→pro met
tenants.plan='pro' ; signature forgée → 400 sans mutation.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; signature vérifiée avant traitement +
idempotence event.id + synchro tenants.plan prouvée + aucune clé Stripe dans les logs/traces.
```
