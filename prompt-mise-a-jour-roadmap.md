# Sprint 200 — Ops : meta-test anti-contournement du chokepoint `create_runtime_pool`

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.86.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (199) a ajouté `tests/api/test_api_boot_insecure.py` : 2 tests prouvant que le lifespan FastAPI refuse une DSN insecure en prod avant `asyncpg.create_pool` — miroir de S196 (chemin worker). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** (zéro `app/` modifié, zéro frontend, pas d'eval) : verrouiller par un test l'invariant architectural dont S192/S196/S199 dépendent — **aucun** worker ne crée de pool via `asyncpg.create_pool`/`asyncpg.connect` en direct (tous passent par `create_runtime_pool`, donc par le garde). Un meta-test (scan AST / `grep` source de `app/workers/tasks.py`) rend ce contournement impossible à introduire silencieusement.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.86.0)
2. `.claude/rules/tests-pyramide.md` (niveau **unitaire** ; no I/O, no DB ; marqueurs pytest).
3. `.claude/rules/conventions-python.md` (type hints partout, docstrings FR du WHY, imports groupés).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `app/workers/tasks.py` — **0** occurrence de `asyncpg.create_pool`/`asyncpg.connect` en direct (vérifié `grep` S198, `grep -c` = 0) ; **≥1** `create_runtime_pool` (vérifié S198) ; **à re-confirmer par `grep -c`**.
   - `app/db/pool.py` — `create_runtime_pool` (`:9`) résout `dsn = resolve_app_database_url()` (`:23`) puis `require_secure_db_url(dsn)` (`:24`) **avant** `asyncpg.create_pool(...)` (`:25`). Chokepoint unique — vérifié S199.
   - `app/api/main.py` — `from app.db.pool import create_runtime_pool` (`:44`) ; `await create_runtime_pool(...)` (`:169`). Vérifié S199.
   - **Patron à suivre** : `tests/workers/test_worker_boot_insecure.py` (S196) et `tests/api/test_api_boot_insecure.py` (S199) — même style, même auto-portance.

---

## TÂCHE — Sprint 200 : meta-test anti-contournement du chokepoint

**Objectif** : S192/S196/S199 prouvent que le garde `require_secure_db_url` verrouille les chemins **pool/worker/API** à condition que tous les workers et le lifespan passent par `create_runtime_pool`. Rien n'empêche un futur développeur d'appeler `asyncpg.create_pool`/`asyncpg.connect` en direct dans un worker (contournant le garde). Ce sprint pose un **meta-test** qui détecte statiquement ce contournement.

### Spécification

1. **Nouveau fichier `tests/meta/test_no_direct_asyncpg_in_workers.py`** (auto-portant, pas d'import de fixtures externes).
2. **Test obligatoire (scan statique)** : lire le source de `app/workers/tasks.py` comme chaîne de caractères ; asserter que **ni** `asyncpg.create_pool` **ni** `asyncpg.connect` n'y apparaissent en dehors d'un commentaire ou d'une chaîne de documentation. Deux approches équivalentes acceptées :
   - **AST** : `ast.parse(source)` + `ast.walk` pour trouver tous les `Attribute` nœuds dont `attr` est `create_pool` ou `connect` et `value` est `asyncpg` ; asserter `len(calls) == 0`.
   - **Grep source** : `re.search(r'asyncpg\.(create_pool|connect)\s*\(', source)` ; asserter `None`.
3. **Test positif (l'invariant est satisfait aujourd'hui)** : asserter qu'au moins une occurrence de `create_runtime_pool` est présente dans `tasks.py` — confirme que le chokepoint est bien utilisé (sinon le test serait vacueux si le fichier est vide ou si les workers n'y sont pas).
4. **Aucun mock, aucun I/O réseau, aucune DB** : le test lit uniquement le système de fichiers local via `pathlib.Path`. Type hints partout, docstrings FR du WHY.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/` (+ `mypy app/ --ignore-missing-imports` — aucun `app/` touché → inchangé).
- **Pas de frontend, pas d'eval**.
- **Preuve d'acceptation observable** : le test de scan **échoue** si on ajoute `asyncpg.create_pool(...)` dans `tasks.py` (même en commentaire si l'implémentation grep-naïve, auquel cas préférer le filtre AST) — vérifier en ajoutant une ligne factice puis en la retirant.

### Note environnement conteneur web
`pytest`/`ruff` tournent depuis `.venv` (préparé par le hook `SessionStart`). Si des imports manquent (`stripe`/`alembic` ont manqué en S196/S199), relancer `.venv/bin/pip install -r requirements.txt`. **Pas de PostgreSQL dans le conteneur** — ce sprint ne nécessite aucune DB.

---

## SPRINTS SUGGÉRÉS (suite Ops/E5 — voir plan directeur §7-§8)

### Sprint 201 — E5 : test d'intégration de la bascule de plan Stripe (synchro webhook → quotas)
**Objectif** : prouver qu'après un événement Stripe `customer.subscription.updated`, le plan du tenant est mis à jour dans `tenants.plan` ET que `QuotaService` reflète la nouvelle limite sans redémarrage.
**Complexité** : Moyenne.
**Justification** : S172/S173 ont livré la facturation Stripe ; aucun test ne couvre le chemin bout-en-bout webhook → `tenants.plan` → lecture `QuotaService`. Un test (event signé mocké, vraie DB sous `app_runtime` ou mock asyncpg ciblé) ferme ce gap.
**Référence** : `app/services/stripe_service.py` — `handle_event` (`:247`), libellé `"customer.subscription.updated"` (`:41`), `UPDATE tenants SET plan = $1 WHERE id = $2::uuid` (`:315`) — vérifiés `grep` S198 ; `app/services/quota_service.py` — `_resolve_limits` (`:89`) lit le plan par `SELECT pl.plan … FROM plan_limits pl` joint au tenant (`:93`) — vérifié S198 ; le test est **à créer**.

### Sprint 202 — Frontend : carte « Quota mensuel » sur la page Facturation
**Objectif** : afficher l'état courant du quota mensuel d'analyses (plan, `used`/`limit`/`remaining`, `reset_at`) dans une carte de la page `/facturation`, en réutilisant le client `getQuota()` et le composant `QuotaBadge`/`QuotaBanner` existants.
**Complexité** : Faible.
**Justification** : `GET /quota` existe (S184) et alimente déjà le `QuotaBadge` du header, mais la page Facturation — pourtant le lieu naturel de gestion d'abonnement — n'affiche pas l'état du quota. Additif pur, aucun backend à créer.
**Référence** : `GET /quota` → `app/api/endpoints/quota.py` (`get_quota` `:19`) — vérifié `grep` S198 ; client typé `frontend/src/api/quota.ts` (`getQuota()` `:5`, type `QuotaStatus`) — vérifié S198 ; `frontend/src/pages/BillingPage.tsx` (page cible existante) ; la carte est **à créer**.

### Sprint 203 — Ops : test d'isolation RLS `usage_events` sur le chemin worker métré
**Objectif** : prouver que `_emit_usage_events` dans l'orchestrateur ne peut pas écrire un événement `usage_events` sous un tenant B depuis un contexte tenant A — gap couvert par la RLS PostgreSQL mais sans test d'intégration ciblé sur le chemin worker.
**Complexité** : Moyenne.
**Justification** : `usage_events` est la table de facturation (S166) ; une fuite cross-tenant serait une anomalie de facturation silencieuse. Les tests RLS S163-S165 couvrent la policy, mais pas l'émission depuis l'orchestrateur sous un tenant scopé.
**Référence** : `app/orchestrator/core.py` — `_emit_usage_events` (à localiser par `grep` — à vérifier avant d'affirmer) ; `app/db/tenant_context.py` — `tenant_scope` (à vérifier) ; le test est **à créer**.

### Sprint 204 — Frontend : page d'administration des tenants (super-admin)
**Objectif** : page `/admin/tenants` listant les tenants (nom, plan, `stripe_customer_id` tronqué, date de création) via un endpoint `GET /admin/tenants` à créer, accessible super-admin uniquement.
**Complexité** : Moyenne.
**Justification** : aucune UI n'expose la liste des tenants — l'administrateur doit inspecter directement la DB. Utile pour l'onboarding B2B et le support.
**Référence** : `app/api/endpoints/admin.py` — `_require_admin` (à re-grepper) ; `app/services/user_service.py` — `UserService` (à re-grepper) ; la route et la page sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.86.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 200 — Ops : meta-test anti-contournement du chokepoint `create_runtime_pool`.
COMMENCE PAR RE-GREP : app/workers/tasks.py (0 occurrence asyncpg.create_pool/connect direct, ≥1 create_runtime_pool).
NOUVEAU FICHIER : tests/meta/test_no_direct_asyncpg_in_workers.py — 2 tests :
  1. Scan statique tasks.py : asserter 0 occurrence asyncpg.create_pool/asyncpg.connect en dehors commentaires.
  2. Positif : ≥1 occurrence create_runtime_pool dans tasks.py (test non vacueux).
  Pas de mock, pas de I/O réseau — lecture filesystem uniquement.
GATES : pytest (hors e2e/evals) + ruff. Pas de frontend, pas d'eval.
PREUVE : ajouter asyncpg.create_pool(...) factice dans tasks.py → test 1 rouge → retirer.
```
