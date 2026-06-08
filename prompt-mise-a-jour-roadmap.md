# Sprint 194 — E5 : helper front partagé `extractDetailMessage` (dé-duplication des parseurs d'erreur)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.80.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (193) a extrait le harnais d'intégration RLS dupliqué dans **une** source partagée `tests/integration/_rls_fixtures.py` (inventaire unique des 7 tables `RLS_TABLES` + harnais de skip `APP_DATABASE_URL`), couplage inter-tests `test_force_rls → test_revoke_public_rls` brisé. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint FRONTEND seul** (TypeScript, zéro `app/`) : extraire la logique de parsing du corps `detail` d'une réponse d'erreur (objet structuré `{message,…}` / tableau de validation Pydantic / string brute) — aujourd'hui **répétée et divergente** entre `request` (`client.ts`), `streamAnalyze` (`analyze.ts`) et `quotaDetailFromError` (`QuotaBanner.tsx`) — en **un seul** helper typé. GATES : `npm test` (Vitest) + `tsc --noEmit` + ESLint (0/0). **Pas de backend, pas d'eval, pas de `mypy`** (aucun fichier `app/` touché). ⚠️ **Refactor front** → les tests Vitest existants (`QuotaBanner`, flux Analyze/Screener) doivent rester **verts** sans changer le comportement utilisateur observable (mêmes messages affichés).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.80.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TypeScript strict zéro `any`, structure `api/`/`components/` — cœur du sprint).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **3 parseurs `detail` divergents** : `request` (`frontend/src/api/client.ts:22`, branche `if (!response.ok)` + parsing `detail` `:54-75`, vérifié cette session) — **array-first** (`Array.isArray` `:58`) puis objet (`:66`) puis string (`:70`) ; `streamAnalyze` (`frontend/src/api/analyze.ts:147`, parsing `detail` `:173-187`, vérifié) — **objet-d'abord** (`typeof === 'object' && !Array.isArray` `:177`) puis string (`:180`), un tableau **retombe** sur `error`/`statusText` ; `quotaDetailFromError` (`frontend/src/components/QuotaBanner.tsx:14`, vérifié) — extrait le corps structuré 429.
   - **Le type miroir** : `QuotaErrorDetail` (`frontend/src/types/index.ts`) consommé par `QuotaBanner` (`:34`/`:52`/`:54`, vérifié). Le helper partagé `extractDetailMessage` est **à créer**.
   - **`ApiError.detail`** (`frontend/src/api/client.ts:9`, champ `detail?: unknown`, vérifié) — déjà le canal qui transporte le corps brut jusqu'au composant ; le helper ne change pas ce contrat.

---

## TÂCHE — Sprint 194 : helper front partagé `extractDetailMessage`

**Objectif** : fermer une note qualité **écartée aux revues S189/S192** (split pré-existant des parseurs `detail`, hors périmètre des deltas de l'époque) et toujours ouverte. Les trois sites parsent le même contrat (`detail` = objet structuré | tableau de validation Pydantic | string) mais **dans un ordre de gardes différent** (`client.ts` array-first vs `analyze.ts` object-with-`!Array`-first) — un risque de dérive silencieuse à chaque évolution du contrat d'erreur backend. Centraliser donne **un seul** point de décision « comment extraire un message lisible d'un corps `detail` ».

### Spécification

1. **Helper unique** : créer `extractDetailMessage` (proposition `frontend/src/api/errorDetail.ts` ou un module utilitaire `api/`) qui prend le corps brut (`unknown` ou `{ detail?: unknown; error?: string }`) + un fallback (`statusText`) et retourne `{ message: string; detail: unknown }` — gérant **les 3 formes** (tableau Pydantic → concatène `loc: msg` comme aujourd'hui dans `client.ts:60-65` ; objet structuré → `detail.message ?? error ?? fallback` ; string → `detail ?? error ?? fallback`). Zéro `any`.
2. **Réécrire les 3 appelants** pour déléguer au helper : `request` (`client.ts`), `streamAnalyze` (`analyze.ts`), et — si pertinent — réconcilier `quotaDetailFromError` (qui extrait le **sous-objet structuré**, pas le message ; décider s'il réutilise une primitive commune de garde « est-ce un objet détail structuré ? » ou reste distinct car finalité différente).
3. **Trancher l'ordre des gardes unifié** : choisir UN ordre canonique (recommandé : array-first comme `client.ts`, le plus complet) et l'appliquer aux deux chemins → supprime la divergence `analyze.ts` (où un tableau retombe aujourd'hui sur le fallback au lieu d'être aplati). **Documenter** ce choix : c'est un **changement de comportement** pour le chemin SSE sur un `detail` tableau (rare en pratique — le 429 quota porte un objet) → l'assumer et le tester.
4. **Préserver le comportement observable** : pour le cas dominant (429 quota = objet structuré, validation 422 = tableau sur `request`), les messages affichés doivent rester **identiques**. `ApiError(status, message, detail)` reçoit toujours le `detail` brut (contrat S189 inchangé) → `quotaDetailFromError` continue de fonctionner.

### Tests / validation
- **Frontend** : `npm test` (Vitest) + `tsc --noEmit` + ESLint (0/0). **Pas de backend, pas d'eval, pas de `mypy`**.
- **Tests obligatoires** : tests unitaires sur `extractDetailMessage` couvrant les 3 formes (objet `{message}`, tableau Pydantic `[{loc,msg}]`, string) + fallback `error`/`statusText` + corps vide/null → repli sûr. Les tests existants `QuotaBanner.test.tsx` (toutes branches de `quotaDetailFromError`) et les tests de flux Analyze/Screener restent **verts**.
- **Preuve d'acceptation observable** : `grep` prouve qu'il n'existe plus **qu'un** site implémentant l'aplatissement du tableau Pydantic (`loc: msg`) ; un `429` quota (objet) et une erreur 422 (tableau) produisent le **même message qu'avant** (assertion Vitest), et le chemin SSE aplatit désormais un `detail` tableau au lieu de le perdre.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 195 — E5 : test de flux re-connexion cross-tenant (compléter S190)
**Objectif** : ajouter un test qui simule le scénario complet « logout tenant A → login tenant B sans rechargement » et asserte qu'aucune donnée de A n'apparaît (vs S190 qui prouve le **mécanisme** `clear()`, pas le flux applicatif bout-en-bout).
**Complexité** : Moyenne.
**Justification** : S190 a fermé la fuite par la purge `queryClient.clear()` ; un test de flux verrouille l'**intention** (pas juste l'appel `clear()`). Note de couverture relevée à la revue S190.
**Référence** : `login` (`frontend/src/contexts/AuthContext.tsx:43`, vérifié cette session — `setUser(await authMe())` `:52`), `logout` (`:58`, vérifié — `queryClient.clear()` `:68`) ; le test de flux multi-tenant est **à créer** (composant avec deux `authMe`/`authLogin` mockés successifs + assertions sur le cache react-query, ou e2e Playwright si le périmètre le justifie).

### Sprint 196 — Ops : test de boot worker réel sous DSN insecure (preuve d'intégration du garde S192)
**Objectif** : compléter la preuve unitaire S192 (mock `asyncpg.create_pool`) par un test d'intégration qui invoque la **construction réelle** d'un pool worker avec une DSN insecure et asserte le `RuntimeError` au boot — verrouille le changement de comportement S192 au niveau du chemin worker, pas seulement du helper isolé.
**Complexité** : Faible.
**Justification** : S192 a prouvé le garde au niveau de `create_runtime_pool` en isolation ; un test ciblant un `_execute_*` worker (ou le lifespan) confirme que le garde se déclenche bien **sur le chemin de boot réel**. À cadrer : sans PG dans le conteneur web, le test reste un mock ciblé du chemin worker (pas un boot Celery complet).
**Référence** : `create_runtime_pool` (`app/db/pool.py:9`, garde `require_secure_db_url(dsn)` `:24`, vérifié cette session), importé + appelé **9×** dans `app/workers/tasks.py` (`grep -c` = 10 avec l'import, vérifié) ; le test de boot worker ciblé est **à créer**.

### Sprint 197 — Ops : fixture de connexion RLS partagée (suite S193, périmètre `connect` re-mesuré)
**Objectif** : reconsidérer l'extraction d'un helper de connexion `asyncpg.connect`/`create_pool` partagé pour les tests d'intégration RLS, **explicitement différée** en S193 (décision « ne pas sur-abstraire » — `test_rls_isolation.py` diverge par son `setup=apply_tenant_context` + casts par-table).
**Complexité** : Faible.
**Justification** : S193 a centralisé l'inventaire de tables + le skip harness mais a **laissé le motif `connect` en place** (mesuré : 7 sites simples vs pool divergent). Si un futur sprint ajoute d'autres tests `APP_DATABASE_URL`, re-mesurer la convergence pourrait justifier une fixture async. **À valider d'abord** : le gain dépasse-t-il la fragilité ? Sinon, statuer « clos, ne pas extraire ».
**Référence** : 7 sites `asyncpg.connect(_APP_DB_URL)` (`tests/integration/test_revoke_public_rls.py:28/47/62/83`, `test_force_rls.py:31`, `test_app_runtime_rls.py:33/63`, vérifiés cette session via grep `asyncpg.connect`) ; le module partagé `tests/integration/_rls_fixtures.py` (`RLS_TABLES`/`APP_DB_URL`/`app_runtime_pytestmark`) existe déjà (S193) — une fixture de connexion y serait **ajoutée**.

---

## Template de démarrage

```
Tu es un développeur TypeScript/React senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.80.0),
.claude/rules/conventions-frontend.md.
Sprint actif : 194 — E5 : helper front partagé extractDetailMessage (dé-duplication des parseurs d'erreur).
Extraire en UN helper typé (proposition frontend/src/api/errorDetail.ts) la logique de parsing du corps `detail`
(objet structuré {message} / tableau de validation Pydantic [{loc,msg}] / string), aujourd'hui répétée et
DIVERGENTE entre request (client.ts:22, parsing :54-75, array-first :58), streamAnalyze (analyze.ts:147,
parsing :173-187, object-first :177 — un tableau RETOMBE sur le fallback) et quotaDetailFromError (QuotaBanner.tsx:14).
À VÉRIFIER AVANT D'ÉCRIRE : re-grep ces lignes (elles dérivent). Trancher UN ordre de gardes canonique (recommandé
array-first) → assume le changement de comportement SSE sur un detail tableau (à tester). ApiError(status, message, detail)
conserve le detail brut (contrat S189 inchangé) → quotaDetailFromError continue de fonctionner.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : npm test (Vitest) + tsc --noEmit + ESLint (0/0). Pas de backend, pas de mypy, pas d'eval.
Preuve : grep = un seul site aplatissant le tableau Pydantic (loc: msg) ; 429 (objet) + 422 (tableau) → même message qu'avant (Vitest).
```
