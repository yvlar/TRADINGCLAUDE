# Sprint 192 — Ops : garde `require_secure_db_url` uniformisé sur tous les pools runtime

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.78.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (191) a rendu l'invariant `FORCE ROW LEVEL SECURITY` **explicite** par un test d'intégration direct (`tests/integration/test_force_rls.py` : sous `app_runtime`, `pg_class.relforcerowsecurity == true` sur les 7 tables RLS, ajouté au gate NOSUPERUSER). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul** (changement de comportement assumé) : faire passer **tous** les pools asyncpg runtime — y compris les **9 pools workers** — par le garde insecure-creds `require_secure_db_url`, aujourd'hui appliqué **uniquement** au boot API. L'absorber dans `create_runtime_pool()` (le chokepoint S187) ferme le special-case : un worker qui boote en prod avec des creds par défaut doit échouer **comme** l'API. GATES : `pytest` (hors e2e/evals) + `ruff check` + `mypy app/`. **Pas de frontend, pas d'eval** (plomberie de pool — aucun prompt de skill ni l'orchestrateur touché). ⚠️ **Changement de comportement** → tests de boot workers obligatoires (un pool avec DSN insecure doit lever).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.78.0)
2. `.claude/rules/securite.md` (garde sur les creds DB / secrets — cœur du sprint) **et** `.claude/rules/gotchas-operationnels.md` (conventions workers — c'est leur boot qui change de comportement).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **Le garde** : `require_secure_db_url` (`app/utils/security_config.py:41`, vérifié cette session) — appelé **uniquement** à `app/api/main.py:158` (vérifié, seul site `app/`). C'est ce mono-site qu'on généralise.
   - **Le chokepoint où l'absorber** : `create_runtime_pool(*, min_size, max_size)` (`app/db/pool.py:9`, vérifié) — résout déjà `resolve_app_database_url()` (`app/utils/security_config.py:17`, vérifié) et câble `setup=apply_tenant_context`. Le garde y trouverait son **home naturel** (la DSN runtime y est déjà résolue → un seul endroit où l'asserter).
   - **Les appelants** : `create_runtime_pool(` est appelé **1×** dans `app/api/main.py` et **9×** dans `app/workers/tasks.py` (vérifié `grep -c`) — ce sont ces 9 pools workers qui héritent du garde après absorption.

---

## TÂCHE — Sprint 192 : garde `require_secure_db_url` uniformisé

**Objectif** : fermer un special-case permanent **différé** des revues S187. Aujourd'hui `require_secure_db_url` ne protège que le boot API (`app/api/main.py:158`) ; les 9 pools workers bootent sans ce garde fail-closed. En l'absorbant dans `create_runtime_pool()`, **tout** pool runtime (API + workers) refuse de démarrer avec des creds par défaut/insecure — l'isolation de prod ne dépend plus du site d'appel.

### Spécification

1. **Absorber le garde dans le chokepoint** : `create_runtime_pool()` appelle `require_secure_db_url(dsn)` sur la DSN résolue (`resolve_app_database_url()`) **avant** de créer le pool. Décider : (a) retirer l'appel redondant de `app/api/main.py:158` (le helper le couvre désormais) **ou** (b) le conserver en double défensif au boot — **trancher et justifier** (le double coûte une lecture env, le retrait centralise ; cohérence avec la philosophie chokepoint de S187).
2. **Changement de comportement assumé** : un worker (ou l'API) avec une DSN insecure lève désormais au boot du pool. Le DIRE dans la doc de fin de sprint — ce n'est PAS une non-régression silencieuse.
3. **Tests de boot** : ajouter un test prouvant que `create_runtime_pool()` lève sur une DSN insecure (calquer le pattern de `tests/db/test_pool.py`, créé en S187) **avant** d'atteindre `asyncpg.create_pool` (mock pour ne pas toucher de DB réelle). Couvrir le happy-path (DSN secure → pool créé) ET le cas insecure (→ lève, pool jamais créé).
4. **Vérifier la sémantique exacte** de `require_secure_db_url` (lire son corps : que considère-t-il « insecure » ? mot de passe par défaut ? localhost ?) pour que le test cible la vraie condition, pas une supposition.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/` + `mypy app/ --ignore-missing-imports` (du code `app/` est touché).
- **Preuve d'acceptation observable** : `create_runtime_pool()` avec une DSN insecure lève (test unitaire, mock `asyncpg.create_pool` → asserter qu'il n'est jamais atteint) ; avec une DSN secure, le pool est créé (kwargs DSN+setup préservés de S187). **Pas de frontend, pas d'eval**.
- **Pas de Docker/PG dans le conteneur web** → preuve par tests unitaires (faux pool / mock), pas un boot réel.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration)
**Objectif** : extraire le harnais répété des tests d'intégration RLS (connexion sous rôle réel `app_runtime`/NOSUPERUSER, skip hors PG migré, et **l'inventaire des 7 tables RLS**) en une fixture/helper partagé, pour qu'il existe **une seule** source de l'ensemble des tables.
**Complexité** : Moyenne.
**Justification** : finding **écarté** en S185 (« refactor suite-wide ») et toujours ouvert. Après S191, l'inventaire des 7 tables vit en **2 définitions** (`_RLS_TABLES` + `_TABLES`) plus **1 import** (`test_force_rls.py`) ; un module partagé `tests/integration/_rls_fixtures.py` (ou conftest local) centraliserait l'ensemble + le skip. À cadrer prudemment (ne pas casser la convention de skip ni les casts par-table de `test_rls_isolation.py`).
**Référence** : `_RLS_TABLES` (`tests/integration/test_revoke_public_rls.py:31`, vérifié cette session), `_TABLES` (`tests/integration/test_rls_isolation.py:40`, vérifié), import (`tests/integration/test_force_rls.py:23`, vérifié). Le helper/fixture partagé est **à créer** ; le périmètre exact (combien de fichiers convergent) est **à mesurer** avant de s'engager.

### Sprint 194 — E5 : helper front partagé `extractDetailMessage` (dé-duplication des parseurs d'erreur)
**Objectif** : extraire la logique de parsing du corps `detail` (objet structuré / tableau de validation Pydantic / string) répétée entre `client.ts` (`request`), `analyze.ts` (`streamAnalyze` SSE) et `quotaDetailFromError` (`QuotaBanner.tsx`) en un helper unique, pour fermer le risque de dérive entre parseurs.
**Complexité** : Faible.
**Justification** : note qualité **écartée** à la revue S189 (split pré-existant, hors périmètre du delta). Les parseurs diffèrent déjà légèrement dans l'ordre des gardes (array-first vs object-with-`!Array`) ; un helper partagé supprime la divergence.
**Référence** : `request` (`frontend/src/api/client.ts:52`/`:99`/`:125`, branches `if (!response.ok)`, vérifié cette session), `streamAnalyze` (`frontend/src/api/analyze.ts`, même distinction — à re-grep), `quotaDetailFromError` (`frontend/src/components/QuotaBanner.tsx:14`, vérifié). Le helper partagé est **à créer**.

### Sprint 195 — E5 : test e2e/composant du flux re-connexion cross-tenant (compléter S190)
**Objectif** : ajouter un test qui simule le scénario complet « logout tenant A → login tenant B sans rechargement » et asserte qu'aucune donnée de A n'apparaît (vs S190 qui prouve le **mécanisme** `clear()`, pas le flux applicatif bout-en-bout).
**Complexité** : Moyenne.
**Justification** : S190 a fermé la fuite par la purge ; un test de flux verrouille l'**intention** (pas juste l'appel `clear()`). Note de couverture relevée à la revue S190.
**Référence** : `login` (`frontend/src/contexts/AuthContext.tsx:43`, vérifié), `logout` (`:58`, vérifié — `queryClient.clear()` à `:68`) ; le test de flux multi-tenant est **à créer** (composant avec deux `authMe`/`authLogin` mockés successifs + assertions sur le cache, ou e2e Playwright si le périmètre le justifie).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.78.0),
.claude/rules/securite.md et gotchas-operationnels.md.
Sprint actif : 192 — Ops : garde require_secure_db_url uniformisé sur tous les pools runtime.
Absorber require_secure_db_url(dsn) dans create_runtime_pool() (app/db/pool.py) AVANT asyncpg.create_pool,
pour que les 9 pools workers (en plus de l'API) refusent de booter avec des creds insecure.
À VÉRIFIER AVANT D'ÉCRIRE : require_secure_db_url (app/utils/security_config.py:41, seul site app/ = app/api/main.py:158),
create_runtime_pool (app/db/pool.py:9, appelé 1× main.py + 9× workers/tasks.py), resolve_app_database_url
(security_config.py:17). LIRE le corps de require_secure_db_url pour cibler la vraie condition « insecure ».
Trancher : retirer l'appel redondant de main.py:158 ou le garder en double défensif (justifier).
CHANGEMENT DE COMPORTEMENT assumé → tests de boot (DSN insecure → lève avant asyncpg.create_pool, mock).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check + mypy app/. Pas de frontend, pas d'eval.
Preuve : create_runtime_pool() lève sur DSN insecure (pool jamais créé) ; DSN secure → pool créé (kwargs S187 préservés).
```
