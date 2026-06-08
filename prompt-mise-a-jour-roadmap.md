# Sprint 190 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.76.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (189, E5-S8) a enrichi le `429` quota en corps structuré (`detail:{message,plan,used,limit,remaining}`) et transformé le `QuotaBanner` en point de conversion (plan + borne + lien `/facturation`, repli propre si le corps n'est pas structuré). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FRONTEND seul** (hygiène de cache cross-tenant) : purger le cache react-query au `logout` pour qu'une re-connexion sous un **autre tenant** sur la même session SPA (sans rechargement) ne serve jamais de données périmées du tenant précédent. GATES : frontend `npm test` (Vitest) + `npm run typecheck` (0 erreur) + ESLint (0/0). **Pas de backend, pas d'eval** (purge de cache client — aucun endpoint, prompt de skill ni orchestrateur touché). ⚠️ `node_modules` peut être absent du conteneur web → `cd frontend && npm ci` si Vitest/tsc échoue à se lancer.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.76.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TS strict zéro `any`, `data-testid`, test composant happy+erreur — c'est le cœur du sprint) **et** `.claude/rules/tests-pyramide.md` (le `logout` enrichi exige un test de contexte/`AuthContext` prouvant la purge — niveau « Composant » de la pyramide, mock des appels API).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **Le `logout` (à enrichir)** : `frontend/src/contexts/AuthContext.tsx:56` (vérifié cette session, `useCallback(async …, [navigate])`) — `await authLogout()` (try/catch best-effort) → `setUser(null)` → `navigate('/login', { replace: true })`. Il **n'importe pas** `useQueryClient`. C'est ici qu'il faut injecter `const queryClient = useQueryClient()` et appeler `queryClient.clear()` (ou `removeQueries`) après `setUser(null)`.
   - **Le `QueryClient` global** : instancié dans `frontend/src/main.tsx:7` (`new QueryClient({…})`) et fourni via `QueryClientProvider` à `frontend/src/main.tsx:21` (vérifié) → `useQueryClient()` est disponible dans tout l'arbre, donc dans `AuthProvider` (à condition que `AuthProvider` soit monté SOUS `QueryClientProvider` — **à VÉRIFIER** dans `main.tsx`/`App.tsx` avant d'écrire : si `AuthProvider` est au-dessus du provider react-query, `useQueryClient()` lèvera → il faudra soit réordonner, soit passer le client autrement).
   - **Les clés non scopées par tenant (la fuite à fermer)** : `['usage', 30]` (`frontend/src/pages/BillingPage.tsx:83`, vérifié), `['usage-reporting']` (`BillingPage.tsx:88`, vérifié) — **non scopées au tenant**, contrairement à `['quota', tenantId]` (`QuotaBadge.tsx:13`, scopé S184). Une purge unique au logout couvre **tout** le cache d'un coup (scopées ou non), sans avoir à scoper chaque clé une par une.

---

## TÂCHE — Sprint 190 : E5-S9, purge du cache react-query au logout

**Objectif** : garantir qu'après un `logout` puis une re-connexion sous un **autre tenant** (même onglet, sans rechargement de page), aucune donnée du tenant précédent (`usage`, `usage-reporting`, et toute autre requête en cache) ne soit servie depuis le cache react-query. Généralise le finding cross-tenant de la revue S184 (qui n'avait scopé que `['quota', tenantId]` au cas par cas).

### Spécification

1. **`AuthContext.tsx`** : injecter `useQueryClient()` dans `AuthProvider` et, dans `logout`, appeler `queryClient.clear()` **après** `setUser(null)` (et avant ou après `navigate`, mais la purge doit être inconditionnelle — même si `authLogout()` lève, le cache doit être vidé puisque `setUser(null)` est déjà inconditionnel). Mettre à jour le tableau de dépendances du `useCallback` (`[navigate, queryClient]`).
2. **VÉRIFIER l'ordre de montage des providers** (`main.tsx` / `App.tsx`) : `AuthProvider` doit être un descendant de `QueryClientProvider` pour que `useQueryClient()` résolve. Si ce n'est pas le cas, réordonner les providers (changement minimal, ne pas casser le routing ni le `BrowserRouter`).
3. **Choix `clear()` vs `removeQueries()`** : préférer `queryClient.clear()` (purge totale — la plus sûre contre la fuite cross-tenant, et la plus simple). Documenter le WHY en une ligne FR (purge totale au changement d'identité, pas de scope par clé à maintenir).

### Tests / validation
- **Frontend** : test de `AuthContext`/`logout` (niveau Composant, mock de `authLogout` + un `QueryClient` réel ou un spy sur `clear`) — prouver que `logout()` appelle bien la purge du cache (ex. pré-remplir le cache via `queryClient.setQueryData(['usage', 30], …)`, appeler `logout`, asserter que la donnée n'est plus servie / `clear` appelé). Conserver le test happy-path de login/logout existant vert.
- **Cas dégradé** : `authLogout()` qui rejette → le cache est **quand même** purgé (la purge ne dépend pas du succès réseau).
- Gates : frontend Vitest + `tsc --noEmit` + ESLint (0/0). **Pas de backend, pas d'eval**.
- **Preuve d'acceptation observable** : après `logout()`, `queryClient.getQueryData(['usage', 30])` (pré-rempli avant) renvoie `undefined` (cache vidé).

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 191 — Ops : `FORCE RLS` vérifié par test sur les 7 tables (verrou anti-régression)
**Objectif** : asserter en CI que les 7 tables RLS portent bien `relforcerowsecurity = true` (`pg_class`), pour qu'une future migration qui ajoute une table RLS sans `FORCE` (ou qui le retire) échoue immédiatement.
**Complexité** : Faible.
**Justification** : §2.3 d'OWASP repose sur `FORCE` ; aujourd'hui c'est prouvé indirectement (la matrice d'isolation échouerait), jamais asserté directement. Un test ciblé rend l'invariant explicite et auto-documenté.
**Référence** : `docs/revue-owasp-rls-2026-06.md` (cité ROADMAP) ; les 7 tables RLS sont énumérées dans `tests/integration/test_revoke_public_rls.py:30` (« 7 tables RLS », vérifié cette session). Le test d'assertion `relforcerowsecurity` est **à créer** (peut tourner en lecture catalogue sous le rôle `app_runtime`).

### Sprint 192 — Ops : garde `require_secure_db_url` uniformisé sur tous les pools runtime
**Objectif** : faire passer les **9 pools workers** par le même garde insecure-creds que le boot API, en l'absorbant dans `create_runtime_pool()` (ou un appel câblé dans le helper) — aujourd'hui seuls les pools API le portent.
**Complexité** : Faible.
**Justification** : finding d'altitude **différé** des revues S187 — laisser le garde API-only laisse un special-case permanent. Le rendre uniforme ferme un gap : un worker qui boote en prod avec des creds par défaut devrait échouer comme l'API. **Assumé comme changement de comportement** (d'où un sprint dédié avec tests de boot workers).
**Référence** : `require_secure_db_url` (`app/utils/security_config.py:41`, vérifié cette session) appelé **uniquement** à `app/api/main.py:158` (vérifié) ; `create_runtime_pool` (`app/db/pool.py:9`, vérifié) est le home naturel. L'absorption + les tests de boot workers sont **à créer**.

### Sprint 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration)
**Objectif** : extraire le harnais répété des tests d'intégration RLS (connexion sous rôle réel `app_runtime`/NOSUPERUSER, pose du GUC tenant, skip hors PG migré) en une fixture/helper partagé.
**Complexité** : Moyenne.
**Justification** : finding **écarté** en S185 (« refactor suite-wide ») et toujours ouvert — plusieurs `tests/integration/test_*_rls.py` répètent le même setup de connexion/skip. Un helper unique réduirait le bruit et rendrait l'ajout d'un nouveau test RLS trivial. À cadrer prudemment (ne pas casser la convention de skip existante).
**Référence** : les tests d'intégration RLS existent (ex. `tests/integration/test_revoke_public_rls.py`, `test_rls_isolation.py`, `test_app_runtime_rls.py` — cités dans `ROADMAP.md`, à re-`grep` pour le harnais exact). Le helper/fixture partagé est **à créer** ; le périmètre exact (combien de fichiers convergent) est **à mesurer** avant de s'engager.

### Sprint 194 — E5 : helper front partagé `extractDetailMessage` (dé-duplication des parseurs d'erreur)
**Objectif** : extraire la logique de parsing du corps `detail` (objet structuré / tableau de validation Pydantic / string) répétée entre `client.ts` (`request`), `analyze.ts` (`streamAnalyze` SSE) et `quotaDetailFromError` (`QuotaBanner.tsx`) en un helper unique, pour fermer le risque de dérive entre parseurs.
**Complexité** : Faible.
**Justification** : note qualité **écartée** à la revue S189 (split pré-existant, hors périmètre du delta). Les deux parseurs diffèrent déjà légèrement dans l'ordre des gardes (array-first dans `client.ts`, object-with-`!Array` dans `analyze.ts`) ; un helper partagé supprime la divergence.
**Référence** : `request` (`frontend/src/api/client.ts`, branche `if (!response.ok)`, vérifié cette session — distingue array/object/string), `streamAnalyze` (`frontend/src/api/analyze.ts`, même distinction, vérifié), `quotaDetailFromError` (`frontend/src/components/QuotaBanner.tsx`, vérifié). Le helper partagé est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.76.0),
.claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 190 — E5-S9 : purge du cache react-query au logout (hygiène cross-tenant). Injecter
useQueryClient() dans AuthProvider et appeler queryClient.clear() dans logout (AuthContext.tsx:56),
APRÈS setUser(null), purge inconditionnelle (même si authLogout() lève).
À VÉRIFIER AVANT D'ÉCRIRE : que AuthProvider est monté SOUS QueryClientProvider (main.tsx:21 instancie le
client à main.tsx:7) — sinon useQueryClient() lèvera, réordonner les providers.
Clés non scopées au tenant aujourd'hui : ['usage',30] et ['usage-reporting'] (BillingPage.tsx:83/88) ;
['quota',tenantId] est scopé (QuotaBadge.tsx:13). Une purge totale au logout couvre tout d'un coup.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : frontend Vitest + tsc --noEmit + ESLint (0/0). Pas de backend, pas d'eval.
Preuve : après logout(), queryClient.getQueryData(['usage',30]) (pré-rempli) renvoie undefined.
```
