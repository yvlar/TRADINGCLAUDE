# Sprint 198 — E5 : test composant de bascule CTA Facturation cross-tenant

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.84.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (197) a statué « clos, NE PAS EXTRAIRE » sur le helper `asyncpg.connect` partagé : re-mesure = 7 sites `_APP_DB_URL` / `try/finally close` sur 3 fichiers, périmètre identique à S193 — gain marginal < coût d'abstraction. Seul livrable : note de décision dans `_rls_fixtures.py`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FRONTEND seul, test pur** (zéro `app/`, pas de backend, pas d'eval, pas de `mypy app/`) : prouver, au niveau **page**, qu'après la purge S190 la page `/facturation` re-fetch les données du nouveau tenant (et n'affiche pas le plan/conso de l'ancien) lors d'une re-connexion sans rechargement. Complémente S195 (flux cross-tenant au niveau `AuthContext`) en montant d'un niveau vers la page.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.84.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TypeScript strict, `@testing-library/react`, zéro `any`, fichiers de test auto-portants).
3. `.claude/rules/tests-pyramide.md` (niveau **composant** ; mock `fetch` ; pattern `renderWithProvider` + `QueryClientProvider`).
4. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `BillingPage` lit `user?.plan` (`frontend/src/pages/BillingPage.tsx:46`) et consomme `['usage', 30]` (`:83`) + `['usage-reporting']` (`:88`) — vérifiés `grep` S197.
   - `AuthContext` : `login` (`AuthContext.tsx:43`, `setUser(response.user)` `:45`), `logout` (`:58`, `queryClient.clear()` `:68`, `navigate('/login')` `:69`) — vérifiés S195.
   - **Tests existants** : `BillingPage.test.tsx` (plan free/pro, CTA, polling, portail, usage-reporting) + `AuthContextCrossTenant.test.tsx` (S195, flux login A→logout→login B au niveau `AuthContext`) — le test de **bascule CTA au niveau page** est **à créer** dans un nouveau fichier.

---

## TÂCHE — Sprint 198 : test de bascule CTA Facturation cross-tenant

**Objectif** : S190 + S195 verrouillent la purge du cache + le flux cross-tenant au niveau `AuthContext`. Reste à vérifier que la **page `/facturation`** reflète correctement le changement de tenant : après la bascule (logout tenant A → login tenant B), le CTA doit piloter sur le **plan de B** et les données `usage`/`usage-reporting` doivent être re-fetchées pour B, sans résidus de A.

### Spécification

1. **Nouveau fichier `frontend/src/__tests__/BillingPageCrossTenant.test.tsx`** (pas d'extension de `BillingPage.test.tsx`) — convention auto-portant (patron S195 : chaque fichier de test de flux cross-tenant est indépendant, les wrappers diffèrent par leur routing/provider).
2. **Scénario** : monter `BillingPage` avec un `QueryClient` partagé provider↔assertions, sous `AuthContext` avec deux utilisateurs (tenant A `free`, tenant B `pro`) ; simuler login A → pré-remplir `['usage', 30]` + `['usage-reporting']` avec données fictives de A → assertion de pré-condition non vacue → logout → login B → assertions :
   - les clés `['usage', 30]` et `['usage-reporting']` dans le `QueryClient` sont `undefined` (purge S190 effective).
   - le CTA affiché sur la page reflète le plan `pro` de B (portail, pas checkout) — sans rechargement.
3. **Mocks** : `authLogin`, `authLogout`, `authMe` (pas de vrai réseau) ; `createCheckout`/`openPortal` (`../api/billing`) mockés pour éviter les appels fetch ; `getUsage`/`getUsageReporting` mockés pour éviter les appels fetch. Type hints stricts, zéro `any`.
4. **Assertion de pré-condition non vacue** : avant le logout, vérifier explicitement que `['usage', 30]` contient bien les données de A — garantit que le test final n'est pas vacuous.

### Tests / validation
- **Frontend** : `tsc --noEmit` + ESLint (0 erreur / 0 warning) + Vitest suite complète (+1 test de flux cross-tenant).
- **Pas de backend, pas d'eval, pas de `mypy app/`** (aucun `app/` touché).
- **Preuve d'acceptation observable** : le test **échoue** quand `queryClient.clear()` est commenté dans `logout` (les données de A survivent, les assertions `undefined` échouent) ; il **passe** avec S190 en place. La pré-condition non vacue garantit l'assertion finale.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — voir plan directeur §7-§8)

### Sprint 199 — Ops : parité du garde insecure sur le boot API réel (compléter S196 côté API)
**Objectif** : prouver, en miroir de S196 (chemin worker), que le **boot API réel** refuse une DSN insecure en prod — le lifespan FastAPI doit lever `RuntimeError` **avant** `asyncpg.create_pool`.
**Complexité** : Faible.
**Justification** : S196 a verrouillé le chemin **worker** ; le chemin **API** repose sur le même chokepoint (`create_runtime_pool`) mais n'a pas de test exerçant le **lifespan** sous DSN insecure prod. La parité ferme le dernier site de boot non couvert par un test d'intégration ciblé.
**Référence** : `app/api/main.py` — `lifespan` (`:148`) appelle `create_runtime_pool(min_size=2, max_size=10)` (`:169`), garde appliqué dans le chokepoint (commentaire `:155`) — vérifiés `grep` S197 ; le test de lifespan insecure→`RuntimeError` est **à créer** (patron : mock `app.db.pool.asyncpg.create_pool`, `APP_ENV=production` + `APP_DATABASE_URL` insecure, exercer le lifespan).

### Sprint 200 — Ops : meta-test anti-contournement du chokepoint `create_runtime_pool`
**Objectif** : verrouiller par un test l'invariant architectural dont S192/S196 dépendent — **aucun** worker ne crée de pool via `asyncpg.create_pool`/`asyncpg.connect` en direct (tous passent par `create_runtime_pool`, donc par le garde).
**Complexité** : Faible.
**Justification** : S192 a centralisé le garde dans `create_runtime_pool` ; S196 a prouvé qu'il se déclenche sur un chemin worker. Mais rien n'empêche un futur worker d'appeler `asyncpg.create_pool` en direct (re-ouvrant le trou). Un meta-test (lecture du source / AST de `app/workers/tasks.py`) rend ce contournement impossible à introduire silencieusement.
**Référence** : `app/workers/tasks.py` — 0 occurrence de `asyncpg.create_pool`/`asyncpg.connect` en direct (confirmé `grep` S197), 10 matches `create_runtime_pool` (1 import + 9 usages — `grep -c` S197) ; le meta-test est **à créer**.

### Sprint 201 — E5 : test d'intégration de la bascule de plan Stripe (synchro webhook → quotas)
**Objectif** : prouver qu'après un événement Stripe `customer.subscription.updated` le plan du tenant est mis à jour dans `tenants.plan` ET que le `QuotaService` reflète la nouvelle limite sans redémarrage.
**Complexité** : Moyenne.
**Justification** : S172/S173 ont livré la facturation Stripe ; aucun test ne vérifie le chemin bout-en-bout webhook → mise à jour `tenants.plan` → lecture `QuotaService`. Un test d'intégration (mock webhook signé, vraie DB sous `app_runtime`) ferme ce gap.
**Référence** : `app/services/stripe_service.py` — `handle_event` synchro `tenants.plan` via `handle_subscription_updated` (à vérifier par `grep`) ; `app/services/quota_service.py` — lit `tenants.plan` via `_resolve_limits` (à vérifier par `grep`) ; le test est **à créer**.

### Sprint 202 — Frontend : page Quota avec historique visuel de consommation mensuelle
**Objectif** : ajouter une page `/quota` dédiée affichant l'historique de consommation mensuelle (analyses utilisées vs limite) sous forme de graphique barre, en réutilisant `DailyCostTrendChart` ou un composant recharts équivalent.
**Complexité** : Moyenne.
**Justification** : Le `GET /quota` existe depuis S184 (endpoint + `QuotaBadge`) mais aucune page n'offre une vue temporelle de la consommation. Utile pour l'utilisateur en approche de limite.
**Référence** : `GET /quota` endpoint (`app/api/endpoints/analyze_stream.py` — à vérifier par `grep`) ; `frontend/src/api/quota.ts` (client typé, S184) ; `DailyCostTrendChart` (`frontend/src/components/DailyCostTrendChart.tsx` — à vérifier par `grep`) ; la page est **à créer**.

---

## Template de démarrage

```
Tu es un développeur TypeScript senior (frontend React) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.84.0),
.claude/rules/conventions-frontend.md, .claude/rules/tests-pyramide.md.
Sprint actif : 198 — E5 : test composant de bascule CTA Facturation cross-tenant.
COMMENCE PAR RE-GREP : BillingPage.tsx (user?.plan, queryKeys usage/usage-reporting), AuthContext.tsx (login/logout/clear).
NOUVEAU FICHIER : frontend/src/__tests__/BillingPageCrossTenant.test.tsx — scénario login A (free) → logout → login B (pro) :
  1. QueryClient partagé provider↔assertions (même instance, sinon le test ne verrouille pas le flux réel).
  2. Pré-remplir ['usage', 30] + ['usage-reporting'] sous A → assertion non vacue.
  3. Logout → Login B → assertions: clés undefined (purge S190) + CTA portail (plan pro).
  4. Test échoue si queryClient.clear() est commenté dans logout — preuve d'acceptation.
Mocks: authLogin/authLogout/authMe (../contexts/AuthContext ou ../api/auth) + createCheckout/openPortal (../api/billing) + getUsage/getUsageReporting (../api/usage).
Type hints stricts, zéro any. Auto-portant (wrappers distincts de BillingPage.test.tsx et AuthContextCrossTenant.test.tsx).
GATES : tsc --noEmit + ESLint (0/0) + Vitest suite complète (+1). Pas de backend, pas d'eval, pas de mypy.
Confirmer avant git push.
```
