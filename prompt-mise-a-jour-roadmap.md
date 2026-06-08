# Sprint 196 — Ops : test de boot worker réel sous DSN insecure (preuve d'intégration du garde S192)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.82.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (195) a ajouté un test de **flux** re-connexion cross-tenant (`frontend/src/__tests__/AuthContextCrossTenant.test.tsx`) verrouillant l'intention applicative de S190 : login tenant A → cache pré-rempli → logout → login tenant B, assertion d'absence de fuite (clés → `undefined`) + `user` = B. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul** (test d'intégration ciblé, zéro `frontend/`) : compléter la preuve **unitaire** S192 (mock `asyncpg.create_pool` dans `test_pool.py`) par un test ciblant le **chemin de boot worker réel** — un `_execute_*` worker (`app/workers/tasks.py`) qui appelle `create_runtime_pool` doit lever `RuntimeError` sous une DSN insecure en prod, **avant** d'atteindre la DB. GATES : `pytest` (hors e2e/evals) + `ruff check` + `mypy app/`. **Pas de frontend, pas d'eval** (aucun prompt de skill ni l'orchestrateur touché). ⚠️ **Sprint de test** → ne PAS modifier le comportement de `create_runtime_pool` ni des workers ; n'ajouter que des tests.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.82.0)
2. `.claude/rules/tests-pyramide.md` (niveau **intégration** = plusieurs modules ; règle absolue de mock — ici on mocke `asyncpg.create_pool` pour ne PAS toucher de vraie DB ; marqueurs pytest).
3. `.claude/rules/conventions-python.md` (pattern `execute()`, type hints partout, docstrings FR, async/await).
4. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `create_runtime_pool` (`app/db/pool.py:9`) : résout `dsn` une fois, appelle `require_secure_db_url(dsn)` (`:24`, vérifié cette session) **avant** `asyncpg.create_pool(dsn, …)`. Le garde fait un retour anticipé en dev (`is_dev_environment()`), sinon lève si la DSN contient le marqueur insecure `copilote:copilote@`.
   - Workers appelant `create_runtime_pool` (`grep -c` = **10** dans `app/workers/tasks.py`, vérifié) : ex. `_execute_price_alert_check` (`:329`, pool `:339`), `_execute_weekly_watchlist_report` (`:377`, pool `:386`), `_execute_composite_alert_check` (`:449`, pool `:458`) — le pool est créé **en tête** de chaque coroutine. Cible idéale : un `_execute_*` qui appelle `create_runtime_pool` **en premier** (le garde y déclenche avant toute autre I/O).
   - `tests/db/test_pool.py` (S192) — pattern de référence : `APP_ENV=production` (le `conftest.py` pose `APP_ENV=test` par défaut → forcer `production` pour exercer le vrai chemin insecure) + DSN `copilote:copilote@` → `RuntimeError`, `asyncpg.create_pool` patché et `assert_not_awaited`.

---

## TÂCHE — Sprint 196 : test de boot worker réel sous DSN insecure

**Objectif** : compléter S192. S192 a déplacé le garde `require_secure_db_url` dans `create_runtime_pool` (chokepoint unique) et l'a prouvé en **isolation** (`test_pool.py`, mock `asyncpg.create_pool`). Il reste à prouver que sur le **chemin de boot worker réel** — quand un `_execute_*` worker démarre sous une DSN insecure en prod — le garde **se déclenche bien** et avorte le boot avant toute I/O DB. Sans ce test, un refactor futur qui résoudrait la DSN ailleurs (ou court-circuiterait `create_runtime_pool` dans un worker) repasserait `test_pool.py` mais ré-ouvrirait le trou côté worker.

### Spécification

1. **Nouveau test d'intégration ciblé** (proposition : `tests/workers/test_worker_boot_insecure.py`, ou étendre un fichier worker existant) : choisir un `_execute_*` qui appelle `create_runtime_pool` **en premier** (cf. `_execute_price_alert_check`/`_execute_weekly_watchlist_report`/`_execute_composite_alert_check`). Le re-grep en début de session pour confirmer que `create_runtime_pool` est bien le **premier** await (sinon une I/O antérieure fausserait la preuve).
2. **Scénario** : `APP_ENV=production` (monkeypatch) + DSN insecure (`copilote:copilote@…` via `APP_DATABASE_URL`/`DATABASE_URL` selon la résolution de `resolve_app_database_url`) ; patcher `asyncpg.create_pool` (`AsyncMock`) ; `await _execute_*()` (ou `asyncio.run(...)` selon le niveau) → **assertions** : `RuntimeError` levé, `asyncpg.create_pool` **jamais awaité** (`assert_not_awaited`), aucune autre I/O worker atteinte.
3. **Type hints partout**, mocks typés (`AsyncMock`). Ne PAS modifier `pool.py` ni `tasks.py` (sprint de test pur). **Sans PG dans le conteneur web** → le test reste un **mock ciblé du chemin worker** (pas un boot Celery complet) : le DIRE dans la docstring.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/` + `mypy app/ --ignore-missing-imports`. **Pas de frontend, pas d'eval**.
- **Tests obligatoires** : le test de boot worker ci-dessus (insecure prod → `RuntimeError` avant `create_pool`). Les tests `test_pool.py` (S192) restent **verts**.
- **Preuve d'acceptation observable** : le nouveau test **échoue** si on neutralise l'appel `require_secure_db_url(dsn)` dans `create_runtime_pool` (preuve qu'il verrouille bien le chemin worker, pas seulement le helper isolé) — le vérifier par un essai local (commenter la ligne, constater l'échec, restaurer).

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 197 — Ops : fixture de connexion RLS partagée (suite S193, périmètre `connect` re-mesuré)
**Objectif** : reconsidérer l'extraction d'un helper de connexion `asyncpg.connect` partagé pour les tests d'intégration RLS, **explicitement différée** en S193 (décision « ne pas sur-abstraire »).
**Complexité** : Faible.
**Justification** : S193 a centralisé l'inventaire de tables + le skip harness mais a **laissé le motif `connect` en place**. Les sites `asyncpg.connect` se répartissent en deux familles : `_APP_DB_URL` (**5** sites simples — `test_revoke_public_rls.py:28/47/62/83`, `test_force_rls.py:31`, vérifiés `grep` cette session) et `_RLS_DB_URL` (≥5 sites probe/`create_pool` — `test_retention_purge_rls.py:60`, `test_scheduled_metering_rls.py:54/149`, `test_price_alert_metering_rls.py:53`, `test_report_tenant_rls.py:63`, vérifiés). **À valider d'abord** : le gain dépasse-t-il la fragilité (familles à reasons distinctes) ? Sinon, statuer « clos, ne pas extraire ».
**Référence** : module partagé `tests/integration/_rls_fixtures.py` (`RLS_TABLES:23`, `APP_DB_URL:35`, `app_runtime_pytestmark:37`, vérifiés cette session) existe déjà (S193) — une fixture de connexion y serait **ajoutée** ; sites `asyncpg.connect` vérifiés par `grep` cette session.

### Sprint 198 — E5 : test composant de bascule CTA Facturation cross-tenant
**Objectif** : prouver, au niveau **page**, qu'après la purge S190 la page `/facturation` re-fetch les données du nouveau tenant (et n'affiche pas le plan/conso de l'ancien) lors d'une re-connexion sans rechargement.
**Complexité** : Moyenne.
**Justification** : S190 + S195 verrouillent le cache au niveau `AuthContext` ; un test au niveau `BillingPage` confirme que l'**UI** reflète bien le nouveau tenant (CTA checkout↔portail repiloté sur `user.plan`). Complète la couverture cross-tenant du côté présentation.
**Référence** : `BillingPage` consomme `['usage', 30]` (`frontend/src/pages/BillingPage.tsx:83`), `['usage-reporting']` (`:88`) et `user?.plan` (`:46`) — vérifiés `grep` cette session ; le test de bascule au niveau page est **à créer**.

### Sprint 199 — Ops : assertion `NOBYPASSRLS`/`NOSUPERUSER` du rôle runtime par test catalogue
**Objectif** : verrouiller par un test direct que le rôle de connexion runtime (`app_runtime`) porte bien `NOSUPERUSER` **et** `NOBYPASSRLS` (sans quoi la RLS serait silencieusement contournée en prod), en lecture du catalogue `pg_roles`.
**Complexité** : Faible.
**Justification** : S182 prouve l'application de la RLS sous le rôle réel via `test_app_runtime_rls.py`, mais l'**attribut de rôle** lui-même (`rolsuper`/`rolbypassrls = false`) n'est pas asserté en propre — un `ALTER ROLE` accidentel le ré-activant passerait inaperçu jusqu'à une fuite. Parité avec le verrou `FORCE RLS` direct posé en S191.
**Référence** : harnais d'intégration RLS réutilisable (`tests/integration/_rls_fixtures.py` — `APP_DB_URL:35`, `app_runtime_pytestmark:37`, vérifiés cette session) + `test_app_runtime_rls.py` (existant S182, à confirmer par `grep` en début de sprint) comme modèle de connexion sous le rôle réel. Le test catalogue `pg_roles` (`rolsuper`/`rolbypassrls`) est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.82.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 196 — Ops : test de boot worker réel sous DSN insecure (preuve d'intégration du garde S192).
Ajouter un test d'intégration ciblé : un _execute_* worker (app/workers/tasks.py) qui appelle create_runtime_pool
EN PREMIER doit lever RuntimeError sous APP_ENV=production + DSN insecure (copilote:copilote@), AVANT asyncpg.create_pool
(patché AsyncMock → assert_not_awaited). Pattern de référence : tests/db/test_pool.py (S192).
NE PAS modifier pool.py ni tasks.py (sprint de test pur). Type hints partout, mocks typés (AsyncMock).
À VÉRIFIER AVANT D'ÉCRIRE : re-grep create_runtime_pool (app/db/pool.py:9, garde :24) + les _execute_* de tasks.py
(grep -c create_runtime_pool = 10) — confirmer que le pool est le 1er await du _execute_ choisi (les lignes dérivent).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check + mypy app/. Pas de frontend, pas d'eval.
Preuve : le test échoue si on neutralise require_secure_db_url(dsn) dans create_runtime_pool (il verrouille le chemin worker).
```
