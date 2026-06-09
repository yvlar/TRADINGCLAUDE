# Sprint 199 — Ops : parité du garde insecure sur le boot API réel (compléter S196 côté API)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.85.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (198) a ajouté `frontend/src/__tests__/BillingPageCrossTenant.test.tsx` : test page prouvant qu'après une bascule cross-tenant (logout A `free` → login B `pro`) le CTA Facturation reflète le plan de B et qu'aucune conso de A ne survit (purge S190). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** (zéro `app/` modifié, zéro frontend, pas d'eval) : prouver, en **miroir de S196** (qui a verrouillé le chemin **worker**), que le **boot API réel** refuse une DSN insecure en prod — le `lifespan` FastAPI doit lever `RuntimeError` **avant** `asyncpg.create_pool`. Ferme le dernier site de boot (API) non couvert par un test d'intégration ciblé du garde fail-closed.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.85.0)
2. `.claude/rules/tests-pyramide.md` (niveau **intégration** ; règle absolue de patch des appels externes ; marqueurs pytest).
3. `.claude/rules/conventions-python.md` (async/await, type hints partout, docstrings FR d'une ligne du WHY, imports groupés).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `app/api/main.py` — `async def lifespan` (`:148`) ; `create_runtime_pool` importé (`:44`) et appelé `await create_runtime_pool(min_size=2, max_size=10)` (`:169`) en **tout premier `await`** du lifespan (lignes 150-168 = lectures d'env synchrones, aucune I/O) ; commentaire du garde dans le chokepoint (`:154-156`). Vérifiés `grep` S198.
   - `app/db/pool.py` — `create_runtime_pool` (`:9`) résout `dsn = resolve_app_database_url()` (`:23`) puis `require_secure_db_url(dsn)` (`:24`) **avant** `asyncpg.create_pool(...)` (`:25`). Vérifiés S198.
   - `app/utils/security_config.py` — `resolve_app_database_url` lit `APP_DATABASE_URL` ; marqueur insecure `copilote:copilote@` ; message du garde « Identifiants PostgreSQL **par défaut**… » (match `par défaut`). `app/utils/env.py` — `is_dev_environment` → `production` hors `{dev,development,test,testing}`. (À re-confirmer par `grep`, n° exacts S196.)
   - **Patron à mirrorer** : `tests/workers/test_worker_boot_insecure.py` (S196) — même stratégie (mock `app.db.pool.asyncpg.create_pool` en `AsyncMock`, `APP_ENV=production` via `monkeypatch`, `APP_DATABASE_URL` insecure, `assert_not_awaited`). Repérer aussi un test de boot existant (`tests/api/…` ou `test_healthz_prod.py`) pour réutiliser son setup de lifespan/mocks aval.

---

## TÂCHE — Sprint 199 : test d'intégration du boot API sous DSN insecure

**Objectif** : S196 a prouvé le garde sur le chemin **worker** (`_execute_*` → `create_runtime_pool` 1ᵉʳ `await`). Le chemin **API** repose sur le **même chokepoint** mais aucun test n'exerce le **lifespan** sous DSN insecure prod. Un refactor futur résolvant la DSN ailleurs (ou court-circuitant `create_runtime_pool` dans `main.py`) repasserait `test_pool.py`/`test_worker_boot_insecure.py` mais ré-ouvrirait le trou côté API. Ce sprint pose la **preuve d'intégration manquante**.

### Spécification

1. **Nouveau fichier `tests/api/test_api_boot_insecure.py`** (auto-portant, patron S196 — ne pas étendre un test existant).
2. **Test obligatoire (insecure → lève avant `create_pool`)** : `monkeypatch` `APP_ENV=production` + `APP_DATABASE_URL` insecure (`postgresql://copilote:copilote@.../copilote`) ; patcher `app.db.pool.asyncpg.create_pool` en `AsyncMock` ; entrer le `lifespan(app)` (via `async with lifespan(app):` ou en appelant le contextmanager ASGI) → `pytest.raises(RuntimeError, match="par défaut")` (fragment **propre** au garde insecure-creds, discrimine d'un `RuntimeError` de boot non lié) + `asyncpg.create_pool.assert_not_awaited()`. Le garde se déclenche à `:169` **avant** `anthropic.AsyncAnthropic` (`:175`) et `RagClient.ensure_collection()` (`:178`) → aucune I/O Qdrant/Anthropic n'est atteinte (pas à mocker dans ce test).
3. **2ᵉ test discriminant (secure → garde passé → `create_pool` awaité)** : DSN **secure** en prod ; patcher `app.db.pool.asyncpg.create_pool` (`AsyncMock`, retourne un pool factice) ET l'aval atteint après le garde (le lifespan poursuit vers `RagClient.ensure_collection` qui ferait une I/O Qdrant — patcher `RagClient.ensure_collection` en `AsyncMock`, et tout autre appel réseau du lifespan repéré au re-grep : `anthropic.AsyncAnthropic` est un constructeur sans I/O, mais `ensure_collection` est un `await` réseau). Asserter `asyncpg.create_pool.assert_awaited()` (le garde a laissé passer). But : écarter le faux positif « tout lève en prod » — prouver que le `RuntimeError` du test 1 vient bien des creds insecure, pas de l'env prod en soi. *(Si mocker tout l'aval du lifespan s'avère trop intrusif, repli acceptable et documenté : asserter au niveau `create_runtime_pool` que la DSN secure ne lève pas — mais privilégier l'exercice du vrai `lifespan`.)*
4. **`create_runtime_pool` n'est PAS mocké** (sinon le garde réel n'est pas exercé) ; seul `app.db.pool.asyncpg.create_pool` (+ l'aval réseau pour le test 2) est patché. Type hints partout (`monkeypatch: pytest.MonkeyPatch`, `-> None`), mocks typés (`AsyncMock`), docstrings FR du WHY.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/` (+ `mypy app/ --ignore-missing-imports` doit rester vert, mais **aucun `app/` n'est touché** → inchangé).
- **Pas de frontend, pas d'eval** (aucun prompt de skill ni l'orchestrateur touché ; aucun `frontend/` touché).
- **Preuve d'acceptation observable** : le test insecure **échoue** quand on neutralise `require_secure_db_url(dsn)` dans `create_runtime_pool` (remplacer la ligne par `pass`, lancer, puis **restaurer `pool.py` byte-identique** via `git checkout`) — il verrouille le **chemin de boot API réel**, pas seulement le helper isolé. Les tests S192/S196 (`test_pool.py`, `test_worker_boot_insecure.py`) restent **verts**.

### Note environnement conteneur web
`pytest`/`ruff`/`mypy` tournent depuis `.venv` (préparé par le hook `SessionStart`). Si des imports manquent (`stripe`/`alembic` ont déjà manqué en S196), relancer `.venv/bin/pip install -r requirements.txt`. **Pas de PostgreSQL dans le conteneur** → preuve par mock ciblé de `asyncpg.create_pool`, jamais un boot Postgres réel.

---

## SPRINTS SUGGÉRÉS (suite Ops/E5 — voir plan directeur §7-§8)

### Sprint 200 — Ops : meta-test anti-contournement du chokepoint `create_runtime_pool`
**Objectif** : verrouiller par un test l'invariant architectural dont S192/S196/S199 dépendent — **aucun** worker ne crée de pool via `asyncpg.create_pool`/`asyncpg.connect` en direct (tous passent par `create_runtime_pool`, donc par le garde).
**Complexité** : Faible.
**Justification** : le garde est centralisé dans `create_runtime_pool` ; rien n'empêche un futur worker d'appeler `asyncpg.create_pool` en direct (ré-ouvrant le trou). Un meta-test (scan source / AST de `app/workers/tasks.py`) rend ce contournement impossible à introduire silencieusement.
**Référence** : `app/workers/tasks.py` — **0** occurrence de `asyncpg.create_pool`/`asyncpg.connect` en direct (vérifié `grep` S198, `grep -c` = 0) ; **10** matches `create_runtime_pool` (1 import `:44`-style + 9 usages — `grep -c` S198 = 10) ; le meta-test est **à créer**.

### Sprint 201 — E5 : test d'intégration de la bascule de plan Stripe (synchro webhook → quotas)
**Objectif** : prouver qu'après un événement Stripe `customer.subscription.updated`, le plan du tenant est mis à jour dans `tenants.plan` ET que `QuotaService` reflète la nouvelle limite sans redémarrage.
**Complexité** : Moyenne.
**Justification** : S172/S173 ont livré la facturation Stripe ; aucun test ne couvre le chemin bout-en-bout webhook → `tenants.plan` → lecture `QuotaService`. Un test (event signé mocké, vraie DB sous `app_runtime` ou mock asyncpg ciblé) ferme ce gap.
**Référence** : `app/services/stripe_service.py` — `handle_event` (`:247`), libellé `"customer.subscription.updated"` (`:41`), `UPDATE tenants SET plan = $1 WHERE id = $2::uuid` (`:315`) — vérifiés `grep` S198 ; `app/services/quota_service.py` — `_resolve_limits` (`:89`) lit le plan par `SELECT pl.plan … FROM plan_limits pl` joint au tenant (`:93`) — vérifié S198 ; le test est **à créer**.

### Sprint 202 — Frontend : carte « Quota mensuel » sur la page Facturation
**Objectif** : afficher l'état courant du quota mensuel d'analyses (plan, `used`/`limit`/`remaining`, `reset_at`) dans une carte de la page `/facturation`, en réutilisant le client `getQuota()` et le composant `QuotaBadge`/`QuotaBanner` existants.
**Complexité** : Faible.
**Justification** : `GET /quota` existe (S184) et alimente déjà le `QuotaBadge` du header, mais la page Facturation — pourtant le lieu naturel de gestion d'abonnement — n'affiche pas l'état du quota. Additif pur, aucun backend à créer. *(Pas d'historique mensuel exposé aujourd'hui → s'en tenir à l'état courant, ne pas promettre de graphique temporel.)*
**Référence** : `GET /quota` → `app/api/endpoints/quota.py` (`get_quota` `:19`) — vérifié `grep` S198 ; client typé `frontend/src/api/quota.ts` (`getQuota()` `:5`, type `QuotaStatus`) — vérifié S198 ; `frontend/src/pages/BillingPage.tsx` (page cible existante) ; la carte est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.85.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 199 — Ops : parité du garde insecure sur le boot API réel (miroir de S196 côté API).
COMMENCE PAR RE-GREP : app/api/main.py (lifespan, 1ᵉʳ await = create_runtime_pool), app/db/pool.py
  (create_runtime_pool → resolve_app_database_url → require_secure_db_url AVANT asyncpg.create_pool),
  app/utils/security_config.py (marqueur copilote:copilote@, message "par défaut").
PATRON : tests/workers/test_worker_boot_insecure.py (S196).
NOUVEAU FICHIER : tests/api/test_api_boot_insecure.py — 2 tests :
  1. APP_ENV=production + APP_DATABASE_URL insecure → entrer lifespan(app) → pytest.raises(RuntimeError, match="par défaut")
     + app.db.pool.asyncpg.create_pool (AsyncMock) .assert_not_awaited().
  2. Discriminant : DSN secure en prod → mocker asyncpg.create_pool + l'aval réseau du lifespan
     (RagClient.ensure_collection AsyncMock, etc.) → create_pool.assert_awaited().
  create_runtime_pool NON mocké (garde réel exercé) ; seul asyncpg.create_pool (+ aval) patché.
GATES : pytest (hors e2e/evals) + ruff. Pas de frontend, pas d'eval, mypy inchangé (zéro app/).
PREUVE : le test insecure échoue si on neutralise require_secure_db_url dans create_runtime_pool
  (puis restaurer pool.py byte-identique via git checkout). Confirmer avant git push.
```
