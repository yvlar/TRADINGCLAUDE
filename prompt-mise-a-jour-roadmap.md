# Sprint 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.79.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (192) a uniformisé le garde insecure-creds `require_secure_db_url` sur **tous** les pools runtime en l'absorbant dans le chokepoint `create_runtime_pool()` (`app/db/pool.py`) — les 9 pools workers (en plus de l'API) refusent désormais de booter avec des creds par défaut hors dev ; appel redondant retiré de `app/api/main.py` (centralisation complète). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint TEST/OPS seul** (refactor de tests, zéro `app/`) : extraire le harnais d'intégration RLS répété — connexion sous le rôle réel `app_runtime` via `APP_DATABASE_URL`, marqueurs `pytest.mark.integration` + `skipif(not _APP_DB_URL)`, et **l'inventaire des 7 tables RLS** — en **une seule** source partagée (fixture/helper ou conftest local), pour qu'il n'existe plus 2 définitions de l'ensemble des tables + 1 import dispersé. GATES : `pytest` (hors e2e/evals) + `ruff check`. **Pas de frontend, pas d'eval, pas de `mypy app/`** (aucun fichier `app/` touché). ⚠️ **Refactor de tests pur** → les tests d'intégration RLS existants doivent rester **verts** (skippés hors PG dans le conteneur web, passants en CI sous `app_runtime`) sans changer de sémantique de skip.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.79.0)
2. `.claude/rules/tests-pyramide.md` (pyramide de tests, marqueur `@pytest.mark.integration`, fixtures — cœur du sprint).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **L'inventaire des 7 tables RLS, en 2 définitions** : `_RLS_TABLES` (`tests/integration/test_revoke_public_rls.py:31`, vérifié cette session) et `_TABLES` (`tests/integration/test_rls_isolation.py:40`, vérifié) — **plus** 1 import inter-module `from tests.integration.test_revoke_public_rls import _RLS_TABLES` (`tests/integration/test_force_rls.py:23`, vérifié). C'est cette dispersion (2 défs + 1 import) qu'on centralise.
   - **Le harnais de skip dupliqué dans 4 fichiers** : `_APP_DB_URL = os.environ.get("APP_DATABASE_URL")` + `pytest.mark.integration` + `skipif(not _APP_DB_URL, reason=…)` apparaissent **verbatim** dans `test_revoke_public_rls.py:20-26`, `test_rls_isolation.py:28-29`, `test_force_rls.py:25-31` et `test_app_runtime_rls.py:22-28` (tous vérifiés cette session).
   - **Le pattern de connexion** : `conn = await asyncpg.connect(_APP_DB_URL)` répété (ex. `test_revoke_public_rls.py:45/64/79/100`, `test_force_rls.py:39`, `test_app_runtime_rls.py:39/63`) — candidat secondaire à un helper de connexion, **à mesurer** avant de s'engager (les casts par-table de `test_rls_isolation.py` divergent).

---

## TÂCHE — Sprint 193 : helper de test RLS partagé

**Objectif** : fermer un finding d'altitude **écarté en S185** (« refactor suite-wide ») et toujours ouvert. Après S191, l'inventaire des 7 tables RLS vit en **2 définitions** (`_RLS_TABLES` + `_TABLES`) plus **1 import**, et le harnais de skip (`_APP_DB_URL` + 2 marqueurs) est copié **verbatim dans 4 fichiers**. Une migration ajoutant une 8ᵉ table RLS devrait aujourd'hui être répercutée à plusieurs endroits — divergence silencieuse probable. Centraliser donne **une seule** source de l'ensemble des tables + du skip.

### Spécification

1. **Source unique de l'inventaire des tables RLS** : un module partagé (proposition `tests/integration/_rls_fixtures.py`, ou `tests/integration/conftest.py`) détient l'unique définition des 7 tables. `test_revoke_public_rls.py` (qui exporte `_RLS_TABLES` aujourd'hui) et `test_rls_isolation.py` (`_TABLES`) l'**importent** ; `test_force_rls.py` repointe son import vers la source partagée plutôt que vers `test_revoke_public_rls.py` (couple de tests entre eux à briser).
2. **Source unique du harnais de skip** : `_APP_DB_URL` + `pytestmark` (`integration` + `skipif`) exposés une fois et réutilisés par les 4 fichiers, **sans changer la sémantique de skip** (même `reason`, même condition `not _APP_DB_URL`).
3. **Décider et justifier le périmètre** : trancher si le pattern `await asyncpg.connect(_APP_DB_URL)` devient lui aussi un helper de connexion partagé (fixture async ?) **ou** reste en place (les casts par-table de `test_rls_isolation.py` peuvent rendre une fixture générique fragile). Mesurer combien de fichiers convergent réellement **avant** de s'engager — ne pas sur-abstraire.
4. **Ne pas casser la convention de skip** : le conteneur web n'a pas de PG migré → les tests doivent rester **skippés** localement et **passants en CI** sous `app_runtime`. Vérifier que `tests/__init__.py` + `tests/integration/__init__.py` rendent l'import partagé résoluble (déjà le cas pour l'import S191).

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check tests/`. **Pas de `mypy app/`** (aucun `app/` touché), **pas de frontend, pas d'eval**.
- **Preuve d'acceptation observable** : `grep` prouve qu'il ne reste **qu'une** définition de l'ensemble des 7 tables (les autres sont des imports) ; les 4 fichiers d'intégration RLS restent collectés et **skippés proprement** hors PG (`pytest tests/integration -q` → tous skipped dans le conteneur web, **0 erreur de collection**). En CI (PG migré, `app_runtime`) ils passent inchangés.
- **Pas de Docker/PG dans le conteneur web** → preuve par grep + collection/skip, pas un run réel sous PG.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 194 — E5 : helper front partagé `extractDetailMessage` (dé-duplication des parseurs d'erreur)
**Objectif** : extraire la logique de parsing du corps `detail` (objet structuré / tableau de validation Pydantic / string) répétée entre `client.ts` (`request`), `analyze.ts` (`streamAnalyze` SSE) et `quotaDetailFromError` (`QuotaBanner.tsx`) en un helper unique, pour fermer le risque de dérive entre parseurs.
**Complexité** : Faible.
**Justification** : note qualité **écartée** aux revues S189/S192 (split pré-existant, hors périmètre du delta). Les parseurs diffèrent déjà légèrement dans l'ordre des gardes (array-first dans `client.ts` vs object-with-`!Array` dans `analyze.ts`) ; un helper partagé supprime la divergence.
**Référence** : `request` (`frontend/src/api/client.ts:52` branche `if (!response.ok)`, parsing `detail` `:56-66`, vérifié cette session), `streamAnalyze` (`frontend/src/api/analyze.ts:147`, parsing `detail` `:173-181`, vérifié), `quotaDetailFromError` (`frontend/src/components/QuotaBanner.tsx:14`, vérifié). Le helper partagé est **à créer**.

### Sprint 195 — E5 : test e2e/composant du flux re-connexion cross-tenant (compléter S190)
**Objectif** : ajouter un test qui simule le scénario complet « logout tenant A → login tenant B sans rechargement » et asserte qu'aucune donnée de A n'apparaît (vs S190 qui prouve le **mécanisme** `clear()`, pas le flux applicatif bout-en-bout).
**Complexité** : Moyenne.
**Justification** : S190 a fermé la fuite par la purge ; un test de flux verrouille l'**intention** (pas juste l'appel `clear()`). Note de couverture relevée à la revue S190.
**Référence** : `login` (`frontend/src/contexts/AuthContext.tsx:43`, vérifié cette session), `logout` (`:58`, vérifié — `queryClient.clear()` à `:68`) ; le test de flux multi-tenant est **à créer** (composant avec deux `authMe`/`authLogin` mockés successifs + assertions sur le cache, ou e2e Playwright si le périmètre le justifie).

### Sprint 196 — Ops : test de boot worker réel sous DSN insecure (preuve d'intégration du garde S192)
**Objectif** : compléter la preuve unitaire S192 (mock `asyncpg.create_pool`) par un test d'intégration qui invoque la **construction réelle** d'un pool worker avec une DSN insecure et asserte le `RuntimeError` au boot — verrouille le changement de comportement S192 au niveau du chemin worker, pas seulement du helper isolé.
**Complexité** : Faible.
**Justification** : S192 a prouvé le garde au niveau de `create_runtime_pool` en isolation ; un test ciblant un `_execute_*` worker (ou le lifespan) confirme que le garde se déclenche bien **sur le chemin de boot réel**. À cadrer : sans PG dans le conteneur web, le test reste un mock ciblé du chemin worker (pas un boot Celery complet).
**Référence** : `create_runtime_pool` (`app/db/pool.py:9`, garde ajouté cette session), appelé **9×** dans `app/workers/tasks.py` (ex. `:83`, vérifié cette session) ; le test de boot worker ciblé est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.79.0),
.claude/rules/tests-pyramide.md.
Sprint actif : 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration).
Extraire en UNE source partagée (proposition tests/integration/_rls_fixtures.py ou conftest local) :
(1) l'inventaire des 7 tables RLS (aujourd'hui _RLS_TABLES test_revoke_public_rls.py:31 + _TABLES test_rls_isolation.py:40 + import test_force_rls.py:23),
(2) le harnais de skip _APP_DB_URL + pytestmark(integration + skipif) copié verbatim dans 4 fichiers
(test_revoke_public_rls.py:20-26, test_rls_isolation.py:28-29, test_force_rls.py:25-31, test_app_runtime_rls.py:22-28).
À VÉRIFIER AVANT D'ÉCRIRE : re-grep ces lignes (elles dérivent). Décider si await asyncpg.connect(_APP_DB_URL)
devient un helper de connexion partagé OU reste en place (casts par-table de test_rls_isolation.py = fragilité).
NE PAS changer la sémantique de skip (même reason, même condition). tests/__init__.py + tests/integration/__init__.py
présents → import partagé résoluble.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check tests/. Pas de mypy app/ (aucun app/ touché), pas de frontend, pas d'eval.
Preuve : grep = une seule définition des 7 tables ; pytest tests/integration -q → tous skipped hors PG, 0 erreur de collection.
```
