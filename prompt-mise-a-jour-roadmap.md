# Sprint 202 — Frontend : carte « Quota mensuel » sur la page Facturation

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.88.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (201) a ajouté `tests/integration/test_stripe_plan_to_quota.py` : 2 tests prouvant qu'après un webhook Stripe signé (upgrade/downgrade), le `QuotaService` du même process voit la nouvelle borne sans redémarrage — chaînon manquant de la boucle de facturation E5. État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FRONTEND seul, additif pur** (zéro backend à créer, pas d'eval, pas de migration) : la page `/facturation` est le lieu naturel de gestion d'abonnement mais n'affiche pas l'état du quota mensuel — l'utilisateur doit deviner depuis le badge du header. Ce sprint ajoute une carte « Quota mensuel » alimentée par `GET /quota` (existant, S184).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.88.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TypeScript strict zéro `any`, structure pages/composants).
3. `.claude/rules/tests-pyramide.md` (niveau **composant** ; happy path + cas d'erreur minimum ; `vi.mock` des clients API).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `frontend/src/api/quota.ts` — client typé `getQuota()` (`:5`) → `GET /quota` ; type `QuotaStatus` importé (`:2`) — vérifié `grep` S201.
   - `frontend/src/types/index.ts` — `interface QuotaStatus` (`:906`) : `plan`, `used`, `limit`, `remaining`, `reset_at` (miroir de `QuotaStatusResponse`) — vérifié S201.
   - `frontend/src/pages/BillingPage.tsx` — page cible : deux `useQuery` existants (`['usage',30]` `:82`, `['usage-reporting']` `:87`), cartes avec `data-testid` (`billing-plan-badge` `:141`, `billing-usage-loading` `:174`, `billing-usage` `:189`) — patron de carte à imiter ; vérifié S201.
   - `frontend/src/components/QuotaBadge.tsx` + `QuotaBanner.tsx` — composants quota existants (header + bandeau) ; le badge utilise `getQuota()` avec `queryKey` scopé au tenant (S184) — **réutiliser le même patron de query, pas le composant lui-même** (la carte est un affichage détaillé, pas un badge).
   - `frontend/src/__tests__/BillingPage.test.tsx` — tests composant existants de la page (mock `useAuth`) ; patron d'extension.
   - Backend (contexte seulement, rien à modifier) : `GET /quota` → `app/api/endpoints/quota.py` (`get_quota` `:19`) ; fail-open `plan="unknown"` + `limit`/`remaining` `null` (jamais de 500).

---

## TÂCHE — Sprint 202 : carte « Quota mensuel » sur `/facturation`

**Objectif** : afficher l'état courant du quota mensuel d'analyses du tenant (plan, `used`/`limit`/`remaining`, date de réinitialisation `reset_at`) dans une carte dédiée de la page Facturation, en réutilisant le client `getQuota()` et le patron de carte existant de la page. Additif pur : aucune route, aucun backend, aucun type API à créer.

### Spécification

1. **Nouvelle carte « Quota mensuel »** dans `BillingPage.tsx`, après la carte du plan (avant ou après la conso 30 j — choisir le plus lisible) : `useQuery` sur `getQuota()` (clé scopée au tenant, même patron que le `QuotaBadge`), affichant :
   - plan (badge réutilisant le style `billing-plan-badge`),
   - `used` / `limit` avec barre de progression (ou fraction texte si plus simple — pas de nouvelle dépendance),
   - `remaining` analyses restantes,
   - `reset_at` formaté `fr-CA` (« Réinitialisation le … »).
2. **États obligatoires** : chargement (skeleton, `data-testid="billing-quota-loading"`), erreur (`billing-quota-error`), **fail-open neutre** : `plan="unknown"` ou `limit=null` → afficher le plan/compteur disponibles sans barre ni chiffres inventés (le backend garantit ce cas — S184) ; non authentifié → la page est déjà derrière l'auth, pas de cas à part.
3. **`data-testid`** : `billing-quota-card`, `billing-quota-remaining`, `billing-quota-reset` (+ états ci-dessus) — nécessaires aux tests.
4. **Conventions** : TypeScript strict zéro `any`, types depuis `types/index.ts` (le type `QuotaStatus` existe), commentaires FR du WHY uniquement, Tailwind + tokens existants de la page.

### Tests / validation
- **Vitest** : étendre `BillingPage.test.tsx` (ou fichier frère auto-portant si plus lisible) — happy path (quota rendu : plan, fraction, restantes, date), cas erreur (`billing-quota-error`), cas fail-open (`plan="unknown"`, `limit=null` → rendu neutre sans NaN). Mock de `../api/quota` (`vi.mock`), jamais d'appel réseau réel.
- **Gates frontend** : `npm test` (Vitest), `npm run typecheck` (`tsc --noEmit`, 0 erreur), ESLint (0 erreur / 0 warning).
- **Backend non touché** : pytest/ruff inchangés par construction — ne pas re-mesurer, le dire.
- **Preuve d'acceptation observable** : le test happy path **échoue** si la carte est retirée de la page (vérifier en commentant le bloc JSX puis en le restaurant) ; le cas fail-open ne rend **ni `NaN` ni barre pleine** quand `limit=null`.

### Note environnement conteneur web
`frontend/node_modules` peut manquer au clone (S198 : réinstallé via `npm ci` puis `npm install @rollup/rollup-linux-x64-gnu --no-save` — sans quoi Vitest ne démarre pas). Le hook `SessionStart` s'en charge normalement ; sinon relancer ces deux commandes.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — voir plan directeur §7-§8)

### Sprint 203 — Ops : test d'isolation RLS `usage_events` sur le chemin orchestrateur métré
**Objectif** : prouver que `_emit_usage_events` (orchestrateur) ne peut pas écrire un événement `usage_events` sous un tenant B depuis un contexte tenant A — gap couvert par la RLS PostgreSQL mais sans test d'intégration ciblé sur le chemin d'émission.
**Complexité** : Moyenne.
**Justification** : `usage_events` est la table de facturation (S166) ; une fuite cross-tenant serait une anomalie de facturation silencieuse. Les tests RLS S163-S165 couvrent la policy, pas l'émission depuis l'orchestrateur sous un tenant scopé.
**Référence** : `app/orchestrator/core.py` — `_emit_usage_events` (`:462`, sites d'appel `:1098` et `:1677`) — vérifié `grep` S200 ; `app/db/tenant_context.py` — `tenant_scope` (`:65`) — vérifié S200 ; le test est **à créer**.

### Sprint 204 — Frontend : page d'administration des tenants (super-admin)
**Objectif** : page `/admin/tenants` listant les tenants (nom, plan, `stripe_customer_id` tronqué, date de création) via un endpoint `GET /admin/tenants` à créer, accessible admin uniquement.
**Complexité** : Moyenne.
**Justification** : aucune UI n'expose la liste des tenants — l'administrateur doit inspecter la DB. Utile pour l'onboarding B2B et le support.
**Référence** : `app/api/endpoints/admin.py` — `_require_admin` (`:58`) — vérifié `grep` S200 ; `app/services/user_service.py` — `UserService` (`:22`) — vérifié S200 ; la route et la page sont **à créer**.

### Sprint 205 — Ops : étendre le garde anti-contournement asyncpg à `app/` entier (allowlist)
**Objectif** : généraliser le meta-test S200 de `app/workers/` à tout `app/`, avec allowlist explicite des deux usages légitimes — le chokepoint lui-même et le provisioning admin.
**Complexité** : Faible.
**Justification** : S200 verrouille les workers ; un endpoint ou service pourrait encore créer un pool direct (contournant garde insecure-creds + hook RLS). L'allowlist rend l'invariant global vérifiable sans faux positif. Alternative à évaluer en session : règle lint `ruff` banned-api (couverture équivalente, per-file-ignores) — trancher AVANT d'implémenter.
**Référence** : scan AST réutilisable `tests/meta/test_no_direct_asyncpg_in_workers.py` (`_scan_violations`) — livré S200 ; usages légitimes à allowlister : `app/db/pool.py:25` (`asyncpg.create_pool` du chokepoint) et `app/db/provision_app_runtime.py:47` (`asyncpg.connect(admin_url)`, provisioning admin) — vérifiés `grep` S200 ; l'extension est **à créer**.

### Sprint 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI »
**Objectif** : verrouiller par un meta-test (patron S200) que chaque `tests/integration/test_*.py` apparaît dans la liste explicite de fichiers du job CI « Migrations — Alembic + RLS » — un fichier oublié de la liste est aujourd'hui skippé localement (pas de PG) ET jamais exécuté en CI : couverture zéro silencieuse.
**Complexité** : Faible.
**Justification** : finding d'altitude de la revue S201 — la liste explicite est un choix assumé (auditabilité), mais sans garde-fou chaque nouveau fichier dépend de la discipline manuelle (S201 a dû éditer `ci.yml` à la main). Le meta-test lit `ci.yml` + `tests/integration/*.py` et échoue avec la liste des absents (allowlist pour exclusions volontaires, ex. `_rls_fixtures.py`).
**Référence** : liste explicite actuelle `.github/workflows/ci.yml:235-247` (13 fichiers, `pytest tests/integration/…`) — vérifié `grep` S201 ; patron meta-test filesystem `tests/meta/test_no_direct_asyncpg_in_workers.py` — livré S200 ; le meta-test est **à créer**.

---

## Template de démarrage

```
Tu es un développeur React/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.88.0),
.claude/rules/conventions-frontend.md, .claude/rules/tests-pyramide.md.
Sprint actif : 202 — Frontend : carte « Quota mensuel » sur la page Facturation.
COMMENCE PAR RE-GREP : frontend/src/api/quota.ts (getQuota :5), types/index.ts (QuotaStatus :906),
pages/BillingPage.tsx (useQuery :82/:87, testids :141/:174/:189), components/QuotaBadge.tsx (patron queryKey).
LIVRABLE : carte « Quota mensuel » (plan, used/limit, remaining, reset_at fr-CA) sur /facturation via
getQuota() ; états loading/error/fail-open (plan="unknown", limit=null → rendu neutre sans NaN) ;
data-testid billing-quota-*. Aucun backend.
GATES : Vitest + tsc --noEmit + ESLint (0/0). Backend non touché par construction.
PREUVE : test happy path rouge si la carte est retirée du JSX → restaurer ; fail-open sans NaN.
```
