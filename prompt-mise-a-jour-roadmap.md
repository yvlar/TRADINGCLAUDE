# Sprint 197 — Ops : fixture de connexion RLS partagée (suite S193, périmètre `connect` re-mesuré)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.83.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (196) a complété la preuve du garde fail-closed S192 sur le **chemin de boot worker réel** : `tests/workers/test_worker_boot_insecure.py` appelle le vrai `_execute_weekly_watchlist_report` (où `create_runtime_pool` est le 1ᵉʳ `await`) sous `APP_ENV=production` + DSN insecure → `RuntimeError` avant `asyncpg.create_pool`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint OPS/TEST seul, à décision préalable** (zéro `app/`, zéro `frontend/`, pas d'eval, pas de `mypy app/` car aucun `app/` touché) : reconsidérer l'extraction d'un **helper de connexion `asyncpg.connect` partagé** pour les tests d'intégration RLS, **explicitement différée** en S193 (« ne pas sur-abstraire »). ⚠️ **Ce sprint commence par une DÉCISION mesurée** : le gain dépasse-t-il la fragilité ? Si **non**, le livrable est de **statuer « clos, ne pas extraire »** (documenté) plutôt que de forcer une abstraction. GATES si extraction : `pytest` (hors e2e/evals) + `ruff check tests/`.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.83.0)
2. `.claude/rules/tests-pyramide.md` (niveau **intégration** ; marqueurs pytest ; règle de skip `APP_DATABASE_URL`).
3. `.claude/rules/conventions-python.md` (type hints partout, docstrings FR une ligne, async/await, « ne pas sur-abstraire »).
4. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `tests/integration/_rls_fixtures.py` (S193, vérifié cette session) — `RLS_TABLES` (`:23`), `APP_DB_URL` (`:35`), `app_runtime_pytestmark` (`:37`). C'est ici qu'une fixture/helper de connexion serait **ajoutée** si la décision est « extraire ».
   - **Famille `_APP_DB_URL`** (connexion simple, vérifiée cette session) : `asyncpg.connect(_APP_DB_URL)` à `test_revoke_public_rls.py:28/47/62/83` + `test_force_rls.py:31` — **5 sites**, motif `conn = await asyncpg.connect(...)` + `try/finally close`.
   - **Famille `_RLS_DB_URL`** (probe/`create_pool` avec contexte tenant, vérifiée cette session) : `test_retention_purge_rls.py:60`, `test_scheduled_metering_rls.py:54/149`, `test_price_alert_metering_rls.py:53`, `test_report_tenant_rls.py:63`. Reasons/setup **distincts** de la famille simple.

---

## TÂCHE — Sprint 197 : décider, puis (peut-être) extraire la fixture de connexion RLS

**Objectif** : S193 a centralisé l'inventaire des 7 tables RLS (`RLS_TABLES`) + le harnais de skip (`app_runtime_pytestmark`) mais a **laissé le motif `asyncpg.connect` en place** (décision explicite « ne pas sur-abstraire » — une fixture générique serait fragile face aux deux familles à reasons/setup distincts). Ce sprint **re-mesure** ce périmètre maintenant que `_rls_fixtures.py` existe et tranche.

### Spécification

1. **Phase de décision (obligatoire, AVANT tout code)** : re-grep les deux familles (`_APP_DB_URL` simple vs `_RLS_DB_URL` probe+setup). Évaluer si un helper de connexion partagé pour la **seule famille simple** (`async with` / context manager autour de `asyncpg.connect(APP_DB_URL)` + `close`) réduit réellement la duplication **sans** effacer les reasons distinctes ni fragiliser la famille `_RLS_DB_URL` (qui ne doit PAS être foldée). Documenter la décision (commit message + docstring si extraction).
2. **Si « extraire »** : ajouter dans `tests/integration/_rls_fixtures.py` un helper minimal (ex. `@asynccontextmanager async def app_runtime_connection()` cédant une connexion `app_runtime`, fermée en `finally`) ; repointer **uniquement** les 5 sites de la famille `_APP_DB_URL` (`test_revoke_public_rls.py`, `test_force_rls.py`). Laisser la famille `_RLS_DB_URL` **intacte** (setup `apply_tenant_context`/casts par-table ≠ connexion simple). Type hints + docstring FR du WHY + note de périmètre (pourquoi `_RLS_DB_URL` est exclue).
3. **Si « ne pas extraire »** : livrer une note de décision courte (dans le commit + éventuellement un commentaire dans `_rls_fixtures.py`) statuant « clos » avec la mesure (5 sites simples sur 2 fichiers, `try/finally close` déjà idiomatique, gain < fragilité). C'est un **livrable valide** — le sprint ferme la question, il ne force pas l'abstraction.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check tests/`. **Pas de frontend, pas d'eval, pas de `mypy app/`** (aucun `app/` touché).
- **Preuve d'acceptation observable** : les 5 fichiers RLS de la famille simple restent **collectés et skippés proprement** hors PG migré (conteneur web) ; sous PG migré (CI, rôle `app_runtime`) leur comportement est **inchangé**. Si extraction : `grep` prouve que la famille `_RLS_DB_URL` n'a PAS été touchée. Le `parametrize` de la matrice d'isolation couvre toujours **7** tables.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — voir plan directeur §7-§8)

### Sprint 198 — E5 : test composant de bascule CTA Facturation cross-tenant
**Objectif** : prouver, au niveau **page**, qu'après la purge S190 la page `/facturation` re-fetch les données du nouveau tenant (et n'affiche pas le plan/conso de l'ancien) lors d'une re-connexion sans rechargement.
**Complexité** : Moyenne.
**Justification** : S190 + S195 verrouillent le cache au niveau `AuthContext` (mécanisme + flux) ; un test au niveau `BillingPage` confirme que l'**UI** reflète bien le nouveau tenant (CTA checkout↔portail repiloté sur `user.plan`). Complète la couverture cross-tenant côté présentation.
**Référence** : `BillingPage` lit `user?.plan` (`frontend/src/pages/BillingPage.tsx:46`) et consomme `['usage', 30]` (`:83`) + `['usage-reporting']` (`:88`) — vérifiés `grep` cette session ; le test de bascule au niveau page est **à créer**.

### Sprint 199 — Ops : parité du garde insecure sur le boot API réel (compléter S196 côté API)
**Objectif** : prouver, en miroir de S196 (chemin worker), que le **boot API réel** refuse une DSN insecure en prod — le lifespan FastAPI doit lever `RuntimeError` **avant** `asyncpg.create_pool`.
**Complexité** : Faible.
**Justification** : S196 a verrouillé le chemin **worker** ; le chemin **API** repose sur le même chokepoint (`create_runtime_pool`) mais n'a pas de test exerçant le **lifespan** sous DSN insecure prod. La parité ferme le dernier site de boot non couvert par un test d'intégration ciblé.
**Référence** : `app/api/main.py` — `lifespan` (`:148`) appelle `create_runtime_pool(min_size=2, max_size=10)` (`:169`), garde appliqué dans le chokepoint (commentaire `:155`) — vérifiés `grep` cette session ; le test de lifespan insecure→`RuntimeError` est **à créer** (patron : mock `app.db.pool.asyncpg.create_pool`, `APP_ENV=production` + `APP_DATABASE_URL` insecure, exercer le lifespan).

### Sprint 200 — Ops : meta-test anti-contournement du chokepoint `create_runtime_pool`
**Objectif** : verrouiller par un test l'invariant architectural dont S192/S196 dépendent — **aucun** worker ne crée de pool via `asyncpg.create_pool`/`asyncpg.connect` en direct (tous passent par `create_runtime_pool`, donc par le garde).
**Complexité** : Faible.
**Justification** : S192 a centralisé le garde dans `create_runtime_pool` ; S196 a prouvé qu'il se déclenche sur un chemin worker. Mais rien n'empêche un futur worker d'appeler `asyncpg.create_pool` en direct (re-ouvrant le trou). Un meta-test (lecture du source / AST de `app/workers/tasks.py`) rend ce contournement impossible à introduire silencieusement.
**Référence** : `app/workers/tasks.py` — **0** occurrence de `asyncpg.create_pool`/`asyncpg.connect` en direct, **10** matches `create_runtime_pool` (1 import + 9 usages) — vérifiés `grep` cette session ; le meta-test est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.83.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 197 — Ops : fixture de connexion RLS partagée (suite S193, périmètre `connect` re-mesuré).
COMMENCE PAR LA DÉCISION : re-grep les 2 familles de connexion (_APP_DB_URL simple : test_revoke_public_rls.py:28/47/62/83
+ test_force_rls.py:31, 5 sites ; _RLS_DB_URL probe+setup : test_retention_purge_rls.py:60, test_scheduled_metering_rls.py:54/149,
test_price_alert_metering_rls.py:53, test_report_tenant_rls.py:63). Le gain d'un helper partagé (famille simple SEULE) dépasse-t-il
la fragilité ? Si NON → statuer « clos, ne pas extraire » (livrable valide). Si OUI → ajouter le helper dans
tests/integration/_rls_fixtures.py (RLS_TABLES:23, APP_DB_URL:35, app_runtime_pytestmark:37) et repointer les 5 sites simples
UNIQUEMENT ; laisser _RLS_DB_URL INTACTE. Type hints + docstring FR.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check tests/. Pas de frontend, pas d'eval, pas de mypy (zéro app/).
Preuve : les 5 fichiers RLS restent collectés+skippés hors PG ; si extraction, grep prouve _RLS_DB_URL non touchée ; matrice = 7 tables.
```
