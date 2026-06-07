# Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me`

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.55.0 — transformation B2B/SaaS, phase P0→P1)

L'épic **E4 (facturation/SaaS)** a posé son socle : metering `usage_events` (S166), quotas par plan (S167) et — dernier sprint — **clés API rattachées au tenant** (S168 : `api_keys.tenant_id`, le chemin Bearer s'exécute désormais sous le tenant propriétaire). Le threading tenant est donc complet (web JWT **et** clés API) et borné. Démarre **E4-S4 : exposer le tenant dans la réponse publique `/auth/me`** — aujourd'hui `UserPublic` omet délibérément `tenant_id` (décision Sprint 161, prise quand le threading n'existait pas encore). État courant complet (version, endpoints, compteurs, fonctionnalités actives) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Validation DB en session web** : un PostgreSQL 16 local peut être démarré (binaires dans `/usr/lib/postgresql/16/bin`). Postgres refuse de tourner en root → user dédié. Recette validée aux sprints 158-168 :
> ```bash
> useradd -m pguser 2>/dev/null || true; mkdir -p /tmp/pgdata /tmp/pgrun; chown pguser /tmp/pgdata /tmp/pgrun
> runuser -u pguser -- /usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -U copilote --auth=trust -A trust
> runuser -u pguser -- /usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log -w start
> runuser -u pguser -- /usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 5433 -U copilote copilote
> DATABASE_URL=postgresql://copilote@127.0.0.1:5433/copilote .venv/bin/alembic upgrade head
> ```
> ⚠️ `alembic`/`sqlalchemy[asyncio]`/`mypy` sont dans `requirements.txt` mais **pas toujours installés dans `.venv`** : `.venv/bin/pip install "alembic>=1.13.0" "sqlalchemy[asyncio]>=2.0.0" mypy` avant les tests de migration. Le frontend peut nécessiter `cd frontend && npm install` (node_modules absent du conteneur).
> ⚠️ **Sprint sans migration ?** E4-S4 n'ajoute *a priori* aucune colonne (`users.tenant_id` existe déjà depuis le Sprint 161 ; le nom du tenant vit dans `tenants.name`). Vérifier avant d'écrire une migration — ce sprint est probablement **lecture + enrichissement de réponse uniquement**.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.55.0)
2. `.claude/rules/api-architecture.md` (endpoints, modèle de réponse, contraintes infra) et `.claude/rules/conventions-frontend.md` (TS strict zéro `any`, types `frontend/src/types/index.ts`, test composant happy + erreur)
3. `app/models/auth.py` — `UserPublic` (`:63`, `tenant_id` **volontairement absent**, raison commentée `:64`) · `app/api/endpoints/auth.py` — endpoint `/me` (`:288`, construit `UserPublic` `:297` ; deux autres constructions login/register `:143`/`:206`) · `app/services/user_service.py` — `get_by_id` (`:78`) **retourne déjà `tenant_id`** dans son `SELECT` (`:81`, vérifié) · `frontend/src/contexts/AuthContext.tsx` + le type miroir de `UserPublic` dans `frontend/src/types/index.ts`

---

## TÂCHE — Sprint 169 (E4-S4) : exposition du tenant dans `/auth/me`

**Objectif** : rendre le tenant **visible côté client** maintenant que le contexte tenant est threadé (E3-S4) et borné (E4-S2/S3). Exposer `tenant_id` **et le nom du tenant** dans `UserPublic` → préparation UI multi-tenant (affichage « espace : <nom> », futur sélecteur, affichage du plan). Lève la restriction délibérée du Sprint 161, désormais cohérente.

### Spécification
1. **`UserPublic`** (`app/models/auth.py`) : ajouter `tenant_id: UUID` et `tenant_name: str` (retirer/mettre à jour le commentaire `:64` qui justifie l'omission — la raison ne tient plus). Décider du nommage exact (`tenant_name` vs `tenant`) et le refléter côté TS.
2. **Lookup du nom de tenant** : `get_by_id` retourne déjà `tenant_id` ; ajouter le **nom** du tenant — soit par un `JOIN tenants` dans `get_by_id` (`SELECT … t.name AS tenant_name … FROM users u JOIN tenants t ON u.tenant_id = t.id`), soit un lookup dédié dans un `tenant`/`user` service. **Décider/documenter** le choix (un seul round-trip via JOIN est préférable). Attention RLS : `tenants` est lue par `id` dérivé du contexte serveur (pas une isolation par tenant — `tenants` n'est PAS sous RLS, c'est la table parent).
3. **Endpoint `/me`** (`app/api/endpoints/auth.py:288`) : threader les deux nouveaux champs dans la construction `UserPublic` (`:297`). Vérifier les **deux autres sites** de construction (`:143` login, `:206` register) — soit les enrichir aussi, soit confirmer qu'ils n'ont pas besoin du nom de tenant (ils peuvent le lire depuis `user.tenant_id` connu au moment de l'auth).
4. **Frontend** : enrichir le type miroir de `UserPublic` (`frontend/src/types/index.ts`, **zéro `any`**), propager dans `AuthContext`, et afficher le nom du tenant (ex. dans le header / menu utilisateur). Léger — pas de nouvelle page.

### Tests / validation
- **Unitaires** (`tests/services/`) : `get_by_id` (ou le service de lookup) retourne `tenant_name` (JOIN correct) ; cas tenant legacy → nom « Legacy ».
- **Intégration** (`tests/api/` ou `tests/`) : `GET /auth/me` authentifié → réponse contient `tenant_id` + `tenant_name` corrects ; un utilisateur du tenant legacy voit « Legacy ».
- **Frontend** (Vitest) : `AuthContext`/header affiche le nom du tenant ; happy path + cas où le champ est absent (rétrocompat / fallback).
- Suite `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts ; `cd frontend && npm run typecheck` + Vitest + ESLint verts. **Eval** : aucun prompt de skill touché → pas d'eval (le dire explicitement).
- **Preuve d'acceptation observable** : appeler `GET /auth/me` (test d'intégration) et **constater la forme** de la réponse enrichie (`tenant_id` + `tenant_name`), pas seulement « vert ».

---

## SPRINTS SUGGÉRÉS (suite E4 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 170 — E4-S5 : endpoint d'agrégation de consommation (`GET /usage`)
**Objectif** : exposer la consommation agrégée du tenant courant (coût/tokens par skill, par jour, total période) à partir de `usage_events`, pour le futur tableau de bord de facturation + l'affichage « N/N analyses ce mois » (quota Sprint 167).
**Complexité** : Moyenne.
**Justification** : rend le metering (166) + quotas (167) actionnables côté produit ; prérequis d'une page « Facturation » frontend.
**Référence** : `usage_events` existe (`alembic/versions/0006_usage_events.py`, `app/services/usage_event_service.py`) ; pattern d'agrégation par jour déjà présent pour les coûts globaux (`get_metrics` → `daily_cost`, `app/orchestrator/core.py:1981`, vérifié cette session — à adapter en version **scopée tenant** via la RLS d'`usage_events`). L'endpoint `/usage` et son agrégation par tenant sont **à créer**.

### Sprint 171 — E4-S6 : purge de rétention par plan (`retention_days`)
**Objectif** : appliquer `plan_limits.retention_days` (posé au Sprint 167 mais inappliqué) — tâche Celery qui purge les analyses/événements au-delà de la rétention du plan de chaque tenant.
**Complexité** : Moyenne.
**Justification** : transforme `retention_days` d'une colonne dormante en politique réelle (différenciation plan free/pro + conformité données) ; complète les quotas par une borne temporelle.
**Référence** : `retention_days` existe (`alembic/versions/0007_plan_limits.py:58`, seedé free=30/pro=365, vérifié cette session) ; le scheduler Celery beat existe (`run_scheduled_screener`, `app/workers/tasks.py:757`, vérifié). La tâche de purge scopée par plan/tenant est **à créer**.

### Sprint 172 — E4-S7 : intégration Stripe Billing (abonnements + usage)
**Objectif** : brancher Stripe (abonnement par plan + facturation à l'usage depuis `usage_events`), webhooks de cycle de vie (souscription, paiement, dunning), mapping plan↔price.
**Complexité** : Élevée.
**Justification** : convertit le socle metering+quotas+clés-tenant (166-168) en revenu réel (B1/B2 du plan directeur) ; dernière marche de M4.
**Référence** : `usage_events` (166), `plan_limits`/`tenants.plan` (167) et `api_keys.tenant_id` (168) sont les socles ; toute l'intégration Stripe (SDK, webhooks, mapping plan↔price, `.env` clés Stripe) est **à créer**.

### Sprint 173 — E4-S8 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant via le ContextVar, mais une clé env-admin retombe sur legacy — cf. NIT Sprint 168).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (168) pilotable côté produit, prérequis d'un onboarding multi-tenant ; lève l'angle mort « clé créée via clé env admin = legacy ».
**Référence** : `create_key(..., tenant_id=None)` rattache au tenant courant (`app/services/api_key_service.py`, Sprint 168, vérifié) ; l'endpoint `POST /admin/keys` (`app/api/endpoints/admin.py:90`) ne passe **pas** de `tenant_id` explicite. L'ajout d'un champ `tenant_id` optionnel à `CreateKeyRequest` + sa validation (admin ne crée que pour son tenant) sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.55.0), .claude/rules/api-architecture.md et conventions-frontend.md.
Sprint actif : 169 — E4-S4 (exposition du tenant dans /auth/me). Ajouter tenant_id + tenant_name
à UserPublic (lever la restriction délibérée du Sprint 161, commentée app/models/auth.py:64),
enrichir get_by_id d'un JOIN tenants pour le nom (users.tenant_id existe déjà, SELECT le retourne
user_service.py:81), threader les champs dans /auth/me (auth.py:297) et afficher le nom du tenant
côté frontend (type miroir + AuthContext, zéro any).
Vérifier AVANT d'écrire une migration : ce sprint est probablement lecture/enrichissement seul
(aucune colonne nouvelle attendue). Démarre un Postgres local (recette dans ce fichier) et PROUVE
la forme enrichie de GET /auth/me (tenant_id + tenant_name) via un test d'intégration.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ + frontend typecheck/Vitest/ESLint ;
forme de /auth/me constatée.
```
