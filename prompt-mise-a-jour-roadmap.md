# Sprint 204 — Frontend : page d'administration des tenants (super-admin)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.90.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (203) a ajouté `tests/integration/test_orchestrator_metering_rls.py` : preuve que l'émission `usage_events` par l'orchestrateur est scopée tenant (USING) et qu'un INSERT forgé cross-tenant est rejeté par la DB (WITH CHECK). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FULL-STACK (backend + frontend)** : aucune UI n'expose la liste des tenants — l'administrateur doit inspecter la DB à la main pour l'onboarding B2B et le support. Ce sprint livre `GET /admin/tenants` (admin only) + une section « Tenants » sur la page Admin existante.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.90.0)
2. `.claude/rules/api-architecture.md` (contraintes endpoints) + `.claude/rules/conventions-frontend.md` (React 18, TS strict).
3. `.claude/rules/tests-pyramide.md` (endpoint → test d'intégration obligatoire ; composant → happy path + erreur).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `app/api/endpoints/admin.py` — `_require_admin` (`:58`, fail-closed JWT admin S175) ; patron d'endpoint GET admin : `GET /admin/keys` (`@router.get` `:129`), `GET /admin/audit-log` (`:158`) — vérifiés `grep` S203.
   - Table `tenants` : `id`, `name`, `slug`, `created_at` (`alembic/versions/0003_tenants.py:33-38`) + `plan` (ajouté par `0007_plan_limits`) — vérifié S203. **`stripe_customer_id` vit dans `subscriptions`** (S172, table HORS RLS) → LEFT JOIN requis pour l'afficher.
   - `frontend/src/pages/AdminPage.tsx` — page existante (clés API + section « Journal d'audit » S180, filtre client `:74-80`) — patron de section à imiter ; vérifié S203.
   - `frontend/src/api/` — clients admin existants (`admin.ts` ou équivalent — re-grep le nom exact du fichier portant `getAuditLog`/`listKeys`).

---

## TÂCHE — Sprint 204 : lister les tenants pour l'admin

**Objectif** : endpoint `GET /admin/tenants` (admin only, fail-closed) retournant la liste des tenants (`id`, `name`, `slug`, `plan`, `stripe_customer_id` éventuel, `created_at`), et section « Tenants » sur la page Admin (tableau trié par date de création, customer Stripe tronqué, badge plan).

### Spécification

1. **Backend — `GET /admin/tenants`** (`app/api/endpoints/admin.py`) : protégé par `_require_admin` (même dépendance que les 3 endpoints existants) ; requête `SELECT t.id, t.name, t.slug, t.plan, t.created_at, s.stripe_customer_id FROM tenants t LEFT JOIN subscriptions s ON s.tenant_id = t.id ORDER BY t.created_at DESC` — **attention RLS** : `tenants` et `subscriptions` sont HORS RLS (vérifié S201/S203), la requête passe sur le pool standard sans scope ; modèle Pydantic `TenantAdminEntry` (+ réponse liste) dans `app/models/` ; limite raisonnable (`?limit=100` borné).
2. **Frontend — section « Tenants »** sur `AdminPage.tsx` (patron de la section Journal d'audit) : tableau (nom, slug, badge plan, customer Stripe tronqué `cus_…` ou « — », date `fr-CA`), états chargement / erreur / vide ; client typé dans `frontend/src/api/` + type dans `types/index.ts` ; `data-testid` `admin-tenants-*`.
3. **Conventions** : type hints/docstrings FR backend ; TS strict zéro `any` ; pas de pagination complexe (liste bornée — l'onboarding B2B compte des dizaines de tenants, pas des milliers).

### Tests / validation
- **Backend** : test d'intégration endpoint (`tests/api/`) — 401/403 non-admin (parité avec les tests `_require_admin` existants — re-grep `tests/api/test_admin_auth.py`), 200 admin avec forme de réponse ; mock DB (pas de PG local).
- **Frontend** : Vitest section Tenants — happy path, erreur, vide ; mock du client.
- **Gates** : pytest (hors e2e/evals) + ruff + Vitest + `tsc --noEmit` + ESLint (0/0).
- **Preuve d'acceptation observable** : section retirée du JSX → test rouge → restaurer ; endpoint sans cookie admin → 401/403 asserté.

### Note environnement conteneur web
`.venv` via hook `SessionStart` (sinon `pip install -r requirements.txt`) ; `frontend/node_modules` : `npm ci` + `npm install @rollup/rollup-linux-x64-gnu --no-save` si absent.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops)

### Sprint 205 — Ops : étendre le garde anti-contournement asyncpg à `app/` entier (allowlist)
**Objectif** : généraliser le meta-test S200 de `app/workers/` à tout `app/`, avec allowlist explicite des deux usages légitimes — le chokepoint lui-même et le provisioning admin.
**Complexité** : Faible.
**Justification** : S200 verrouille les workers ; un endpoint ou service pourrait encore créer un pool direct (contournant garde insecure-creds + hook RLS). Alternative à évaluer en session : règle lint `ruff` banned-api — trancher AVANT d'implémenter.
**Référence** : scan AST réutilisable `tests/meta/test_no_direct_asyncpg_in_workers.py` (`_scan_violations`) — livré S200 ; à allowlister : `app/db/pool.py:25` et `app/db/provision_app_runtime.py:47` — vérifiés `grep` S200 ; l'extension est **à créer**.

### Sprint 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI »
**Objectif** : verrouiller par un meta-test (patron S200) que chaque `tests/integration/test_*.py` apparaît dans la liste explicite du job CI « Migrations — Alembic + RLS » — un fichier oublié est skippé localement ET jamais exécuté en CI : couverture zéro silencieuse.
**Complexité** : Faible.
**Justification** : finding d'altitude S201 ; S201 et S203 ont chacun dû éditer `ci.yml` à la main — la discipline manuelle ne se prouve pas.
**Référence** : liste explicite `.github/workflows/ci.yml` (14 fichiers après S203 — re-grep les lignes exactes) — vérifié S203 ; patron `tests/meta/` — livré S200 ; le meta-test est **à créer**.

### Sprint 207 — Frontend : hook partagé `useQuota` + CTA contextuel à quota épuisé
**Objectif** : extraire un hook `useQuota(tenantId)` consommé par `QuotaBadge` ET la carte Quota de `/facturation` (mêmes clé/options, logique fail-open unique), et afficher un CTA « Passer à Pro » contextuel dans la carte quand `remaining === 0` et plan `free`.
**Complexité** : Faible.
**Justification** : findings écartés-YAGNI de la revue S202 — dès qu'un 3ᵉ consommateur apparaît, la duplication clé/options/fail-open devient un risque de divergence réel.
**Référence** : `frontend/src/components/QuotaBadge.tsx` (query `:12-20`) — vérifié S202 ; carte Quota `BillingPage.tsx` — livrée S202 ; le hook et le CTA sont **à créer**.

### Sprint 208 — Ops : nettoyage du test frère E4-S7 (cleanup non protégé)
**Objectif** : aligner `tests/integration/test_stripe_billing_webhook.py` sur le patron `finally` imbriqué de S201 (un échec du DELETE de cleanup ne doit ni masquer l'échec d'origine ni laisser le pool ouvert).
**Complexité** : Faible.
**Justification** : finding hors-diff de la revue S201 (le fichier frère a un cleanup inline non protégé) — micro-sprint d'hygiène, zéro comportement.
**Référence** : `tests/integration/test_stripe_billing_webhook.py:134-138` (cleanup inline) — observé revue S201 ; patron cible : `test_stripe_plan_to_quota.py` (finally imbriqué) — livré S201.

---

## Template de démarrage

```
Tu es un développeur full-stack senior (FastAPI + React/TS) sur TradingClaude. Lis CLAUDE.md,
ROADMAP.md (v10.90.0), .claude/rules/api-architecture.md, .claude/rules/conventions-frontend.md,
.claude/rules/tests-pyramide.md.
Sprint actif : 204 — Frontend : page d'administration des tenants (super-admin).
COMMENCE PAR RE-GREP : admin.py _require_admin (:58) + patron GET (:129/:158), DDL tenants
(0003 + plan 0007), subscriptions.stripe_customer_id (S172, LEFT JOIN), AdminPage.tsx section audit.
LIVRABLE : GET /admin/tenants (admin only, LEFT JOIN subscriptions, TenantAdminEntry Pydantic)
+ section « Tenants » sur AdminPage (tableau nom/slug/plan/customer tronqué/date fr-CA,
états chargement/erreur/vide, testids admin-tenants-*) + client typé + types TS.
GATES : pytest + ruff + Vitest + tsc + ESLint. Tests : 401/403 non-admin + 200 forme ; happy/erreur/vide.
PREUVE : section retirée → test rouge → restaurer ; accès sans admin → 401/403.
```
