# Sprint 195 — E5 : test de flux re-connexion cross-tenant (compléter S190)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.81.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (194) a extrait en **un seul** helper typé `extractDetailMessage` (`frontend/src/api/errorDetail.ts`, ordre array-first) la logique de parsing du corps `detail` d'une réponse d'erreur, jusque-là **répétée et divergente** entre `request` (`client.ts`), `streamAnalyze` (`analyze.ts`) et `authFetch` (`auth.ts`) — un **4ᵉ** site (`authFetch`) non prévu par la carte a été réconcilié par `grep`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FRONTEND seul** (TypeScript, zéro `app/`) : ajouter un test de **flux** qui simule « logout tenant A → login tenant B sans rechargement » et asserte qu'**aucune donnée de A** n'apparaît côté cache react-query. S190 a prouvé le **mécanisme** (`queryClient.clear()` au `logout`) ; ce sprint verrouille l'**intention applicative** bout-en-bout. GATES : `npm test` (Vitest) + `tsc --noEmit` + ESLint (0/0). **Pas de backend, pas d'eval, pas de `mypy`** (aucun fichier `app/` touché). ⚠️ **Sprint de test** → ne PAS modifier le comportement de `AuthContext` ; n'ajouter que des tests (et au plus un helper de test).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.81.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TypeScript strict zéro `any`, structure `__tests__/`).
3. `.claude/rules/tests-pyramide.md` (niveau **composant** = `@testing-library/react` ; règle absolue de mock des appels API ; happy path + cas d'erreur).
4. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `AuthContext` (`frontend/src/contexts/AuthContext.tsx`) : `login` (`:43`, `setUser(response.user)` `:45` — **vérifié cette session** ; NB : `:50-52` est `refreshUser`, pas `login`), `logout` (`:58`, `setUser(null)` `:64`, `queryClient.clear()` `:68`, `navigate('/login')` `:69`, vérifiés). `useQueryClient` injecté dans `AuthProvider`.
   - Test existant `frontend/src/__tests__/AuthContext.test.tsx` (S190) : `renderWithProvider` enveloppe d'un `QueryClientProvider` (client injectable) ; prouve déjà que `clear()` vide `['usage', 30]` + `['usage-reporting']` au `logout`. Le test de **flux** (login A → logout → login B, assertion d'absence de fuite) est **à créer** — distinct du test de mécanisme.
   - Clés de cache non scopées au tenant consommées par `BillingPage` (`['usage', 30]`, `['usage-reporting']`) — à pré-remplir pour simuler des données de A.

---

## TÂCHE — Sprint 195 : test de flux re-connexion cross-tenant

**Objectif** : compléter S190. S190 a fermé la fuite cross-tenant par la purge `queryClient.clear()` au `logout` et l'a prouvé au niveau **mécanisme** (les clés ciblées passent à `undefined`). Il reste à verrouiller l'**intention applicative** : un test de **flux** qui rejoue le scénario réel « un utilisateur du tenant A se déconnecte, un utilisateur du tenant B se connecte dans le même onglet (sans rechargement) » et asserte qu'aucune donnée mise en cache sous A ne survit à la bascule. Sans ce test, une régression future (ex. `clear()` déplacé après `navigate`, ou remplacé par une purge partielle) repasserait le mécanisme S190 mais casserait le flux.

### Spécification

1. **Nouveau test de flux** (proposition : étendre `AuthContext.test.tsx` ou nouveau `AuthContextCrossTenant.test.tsx`) : monter `AuthProvider` avec un `QueryClient` injecté ; mocker `authLogin`/`authLogout`/`authMe` (cf. `tests-pyramide.md` — jamais d'appel réel).
2. **Scénario** : (a) `login` tenant A (mock `authLogin` → user A) ; (b) pré-remplir le cache react-query avec des données « de A » sous les clés réelles (`['usage', 30]`, `['usage-reporting']`) ; (c) `logout` ; (d) `login` tenant B (mock `authLogin` → user B) ; (e) **assertions** : les clés de A renvoient `undefined` après la bascule (aucune fuite), et `user` reflète bien B.
3. **Zéro `any`**, mocks typés. Ne PAS modifier `AuthContext.tsx` (sprint de test pur). Si un helper de montage est utile, le garder local au fichier de test (convention projet = fichiers de test auto-portants — cf. décision S190).

### Tests / validation
- **Frontend** : `npm test` (Vitest) + `tsc --noEmit` + ESLint (0/0). **Pas de backend, pas d'eval, pas de `mypy`**.
- **Tests obligatoires** : le test de flux ci-dessus (login A → logout → login B → assertion d'absence de fuite + `user` = B). Les tests existants `AuthContext.test.tsx` (mécanisme `clear()`) restent **verts**.
- **Preuve d'acceptation observable** : le nouveau test échoue si on neutralise `queryClient.clear()` dans `logout` (preuve que le test verrouille bien le flux, pas juste l'appel) — le vérifier mentalement / par un essai local, puis l'asserter par le test.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 196 — Ops : test de boot worker réel sous DSN insecure (preuve d'intégration du garde S192)
**Objectif** : compléter la preuve unitaire S192 (mock `asyncpg.create_pool`) par un test ciblant la **construction réelle** d'un pool worker avec une DSN insecure et assertant le `RuntimeError` au boot — verrouille le changement de comportement S192 au niveau du chemin worker, pas seulement du helper isolé.
**Complexité** : Faible.
**Justification** : S192 a prouvé le garde au niveau de `create_runtime_pool` en isolation ; un test ciblant un `_execute_*` worker (ou le lifespan) confirme que le garde se déclenche bien **sur le chemin de boot réel**. À cadrer : sans PG dans le conteneur web, le test reste un mock ciblé du chemin worker (pas un boot Celery complet).
**Référence** : `create_runtime_pool` (`app/db/pool.py:9`, garde `require_secure_db_url(dsn)` `:24`, vérifié cette session), importé + appelé **10×** (avec l'import) dans `app/workers/tasks.py` (`grep -c` = 10, vérifié) ; le test de boot worker ciblé est **à créer**.

### Sprint 197 — Ops : fixture de connexion RLS partagée (suite S193, périmètre `connect` re-mesuré)
**Objectif** : reconsidérer l'extraction d'un helper de connexion `asyncpg.connect` partagé pour les tests d'intégration RLS, **explicitement différée** en S193 (décision « ne pas sur-abstraire »).
**Complexité** : Faible.
**Justification** : S193 a centralisé l'inventaire de tables + le skip harness mais a **laissé le motif `connect` en place**. Les sites `asyncpg.connect` se répartissent en deux familles : `_APP_DB_URL` (5 sites simples, `test_revoke_public_rls.py:28/47/62/83`, `test_force_rls.py:31`) et `_RLS_DB_URL` (≥5 sites en `create_pool`/probe, `test_retention_purge_rls.py:60`, `test_scheduled_metering_rls.py:54/149`…). **À valider d'abord** : le gain dépasse-t-il la fragilité (familles à reasons distinctes) ? Sinon, statuer « clos, ne pas extraire ».
**Référence** : module partagé `tests/integration/_rls_fixtures.py` (`RLS_TABLES:23`, `APP_DB_URL:35`, `app_runtime_pytestmark:37`, vérifiés cette session) existe déjà (S193) — une fixture de connexion y serait **ajoutée** ; sites `asyncpg.connect` vérifiés par `grep` cette session.

### Sprint 198 — E5 : test composant de bascule CTA Facturation cross-tenant
**Objectif** : prouver, au niveau **page**, qu'après la purge S190 la page `/facturation` re-fetch les données du nouveau tenant (et n'affiche pas le plan/conso de l'ancien) lors d'une re-connexion sans rechargement.
**Complexité** : Moyenne.
**Justification** : S190 + S195 verrouillent le cache au niveau `AuthContext` ; un test au niveau `BillingPage` confirme que l'**UI** reflète bien le nouveau tenant (CTA checkout↔portail repiloté sur `user.plan`). Complète la couverture cross-tenant du côté présentation.
**Référence** : `BillingPage` consomme `['usage', 30]` / `['usage-reporting']` et `user.plan` (clés vérifiées via les tests S190) ; le test de bascule au niveau page est **à créer** (à confirmer par `grep` sur `frontend/src/pages/BillingPage.tsx` en début de sprint — n° de ligne non figés ici).

---

## Template de démarrage

```
Tu es un développeur TypeScript/React senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.81.0),
.claude/rules/conventions-frontend.md, .claude/rules/tests-pyramide.md.
Sprint actif : 195 — E5 : test de flux re-connexion cross-tenant (compléter S190).
Ajouter un test de FLUX (login tenant A → pré-remplir le cache react-query sous ['usage',30]/['usage-reporting']
→ logout → login tenant B) assertant qu'aucune donnée de A ne survit (clés → undefined) et que user = B.
NE PAS modifier AuthContext.tsx (sprint de test pur). Mocks typés (authLogin/authLogout/authMe), zéro any
(cf. tests-pyramide.md — jamais d'appel réel). À VÉRIFIER AVANT D'ÉCRIRE : re-grep login (:43)/logout (:58)/
queryClient.clear() (:68) — les lignes dérivent. Réutiliser le pattern renderWithProvider + QueryClientProvider
de AuthContext.test.tsx (S190).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : npm test (Vitest) + tsc --noEmit + ESLint (0/0). Pas de backend, pas de mypy, pas d'eval.
Preuve : le test échoue si on neutralise queryClient.clear() dans logout (il verrouille le flux, pas l'appel).
```
