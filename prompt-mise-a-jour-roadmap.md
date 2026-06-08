# Sprint 187 — Refactor : `create_runtime_pool()` (couplage DSN runtime + setup RLS inséparable)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.73.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (186, Ops) a livré la migration `0012` : revoke des privilèges `PUBLIC` par défaut sur le schéma + re-GRANT explicite au seul `app_runtime`, fermant le résidu §2.3 d'OWASP que `0011` (S182) avait différé (non-propriété assertée, jamais transférée). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND seul (refactor de plomberie, zéro changement de comportement)** : consolider les **10 sites** `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` en un helper unique `create_runtime_pool()` (`app/db/`). GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps → `.venv/bin/pip install -r requirements.txt && .venv/bin/pip install mypy` si un import échoue (`stripe`, `mypy`, `alembic` notamment). **Frontend non touché** (aucun fichier `frontend/` → non-régression par construction). **Pas d'eval** (plomberie de pool — aucun prompt de skill ni l'orchestrateur de skills touché).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.73.0)
2. `.claude/rules/conventions-python.md` (pattern async, imports, docstrings FR) **et** `.claude/rules/tests-pyramide.md` (re-pointage des mocks `patch(...asyncpg.create_pool...)` au nouveau home — le ripple de test est le cœur du sprint). Accessoirement `.claude/rules/api-architecture.md` (contraintes infra : pools, lifespan).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **L'invariant de sécurité dupliqué** : les 10 sites couplent **deux** décisions indissociables — (a) résoudre la DSN runtime via `resolve_app_database_url()` (rôle `app_runtime`, pas `copilote`) et (b) câbler `setup=apply_tenant_context` (hook qui pose le GUC `app.tenant_id` à chaque acquisition). Oublier l'un OU l'autre casse silencieusement l'isolation RLS. Vérifié : **9** `asyncpg.create_pool` dans `app/workers/tasks.py` (lignes 82/345/397/472/663/756/811/898/985, `grep -c` = 9) **tous** avec `setup=apply_tenant_context` + **1** dans `app/api/main.py:173-174` (`min_size=2, max_size=10, setup=apply_tenant_context`). Les workers utilisent uniformément `min_size=1, max_size=3`.
   - `resolve_app_database_url()` existe (`app/utils/security_config.py:17`, vérifié) ; `apply_tenant_context` existe (`app/db/tenant_context.py:79`, vérifié, `async def`). `app/db/` contient déjà `tenant_context.py` + `provision_app_runtime.py` — **home naturel** du nouveau helper.
   - **Le ripple de test (cœur du sprint, à ne pas sous-estimer)** : ~**25** occurrences de `patch("app.workers.tasks.asyncpg.create_pool", …)` / `app.workers.tasks.asyncpg` dans `tests/workers/**` et ailleurs (vérifié `grep -rn ... | wc -l` = 25, incl. `tests/api/test_api.py`, `tests/services/test_price_alert.py`, `tests/orchestrator/test_analyze_stream.py`). Si le helper appelle `asyncpg.create_pool` depuis `app/db/`, **tous ces patchs cessent d'intercepter** → ils doivent être re-pointés sur le nouveau symbole (`app.db.<module>.asyncpg.create_pool` ou le helper lui-même). C'est le gros du diff.

---

## TÂCHE — Sprint 187 : helper `create_runtime_pool()`

**Objectif** : rendre **impossible** de créer un pool runtime qui résout le bon rôle mais oublie le hook de contexte tenant (ou l'inverse) — finding d'altitude répété des revues S182 ET S185. Extraire l'invariant DSN+setup dans un seul helper, pour qu'un futur pool ne puisse plus diverger.

### Spécification

1. **Helper `create_runtime_pool(*, min_size: int, max_size: int) -> asyncpg.Pool`** dans `app/db/` (ex. `app/db/pool.py` ou dans `tenant_context.py` — TRANCHER et documenter ; co-localiser avec `apply_tenant_context` est défendable). Il résout `resolve_app_database_url()` en interne et câble `setup=apply_tenant_context` — l'appelant ne fournit QUE `min_size`/`max_size`. Docstring FR expliquant l'invariant (le WHY : DSN+setup indissociables pour la RLS).
2. **Remplacer les 10 sites** (`app/api/main.py:173` + 9 dans `app/workers/tasks.py`) par un appel au helper, en **préservant** les tailles existantes (`2/10` pour l'API, `1/3` pour les workers). Aucun changement de comportement runtime.
3. **Re-pointer tous les mocks de test** (`patch(...asyncpg.create_pool...)`) sur le nouveau home pour qu'ils continuent d'intercepter — la suite doit rester verte. C'est le critère d'acceptation principal.

### Tests / validation
- **Unitaire** sur le helper : appelé avec `min_size/max_size`, il passe bien `resolve_app_database_url()` comme DSN ET `apply_tenant_context` comme `setup` (mock `asyncpg.create_pool`, asserter les kwargs) — prouve que l'invariant est verrouillé en un point.
- **Non-régression** : toute la suite workers + API + orchestrateur reste verte après re-pointage des mocks (c'est la preuve que le ripple est correct).
- Gates : `pytest` + `ruff` + `mypy`. **Pas d'eval**.
- **Preuve d'acceptation observable** : `grep -c "asyncpg.create_pool(" app/workers/tasks.py app/api/main.py` tombe à **0** (tous les sites passent par le helper) ; un nouvel appel `create_runtime_pool(min_size=1, max_size=3)` suffit à obtenir un pool RLS-correct.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 188 — Refactor : helper `_for_each_tenant()` (5 copies du squelette énumère-et-scope)
**Objectif** : extraire le squelette répété `SELECT id FROM tenants ORDER BY created_at` → boucle → `tenant_scope(tenant_id)` → try/except best-effort log-and-continue en un helper async unique (`app/workers/`), appliqué aux chemins planifiés.
**Complexité** : Moyenne.
**Justification** : finding d'altitude des revues S185/S186 — le squelette atteint **5 copies** dans `app/workers/tasks.py`, seuil où la duplication devient dette load-bearing. Les corps divergent (retour `None` / `list[str]` / `dict`), donc le helper doit accepter un callback et laisser l'agrégation à l'appelant.
**Référence** : 5 occurrences de `SELECT id FROM tenants ORDER BY created_at` dans `app/workers/tasks.py` (vérifié cette session, lignes **254/352/495/675/902**) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié). Le helper est **à créer**.

### Sprint 189 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)
**Objectif** : quand `/analyze` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade ciblé (plan courant, borne atteinte, lien `/facturation`) plutôt qu'une erreur générique.
**Complexité** : Faible.
**Justification** : transforme le mur de quota en point de conversion ; complète le badge S184 (visibilité continue) par une incitation **au moment du blocage**.
**Référence** : `QuotaExceededError` (`app/services/quota_service.py:64`, vérifié cette session) ; `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`, vérifié présent) est le composant d'accroche — l'enrichissement du corps `429` (champs structurés) et le routage du `QuotaBanner` vers `/facturation` sont **à créer/vérifier**.

### Sprint 190 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)
**Objectif** : vider le cache react-query (`queryClient.clear()`) lors du `logout` pour qu'une re-connexion sous un autre tenant sur la même session SPA ne serve jamais de données périmées du tenant précédent (`usage`, `usage-reporting`, etc.).
**Complexité** : Faible.
**Justification** : finding cross-tenant de la revue S184 — généralisé. S184 a scopé `['quota', tenantId]` par tenant au cas par cas ; les clés `['usage']`/`['usage-reporting']` restent non scopées et non purgées au logout. Une purge unique au logout couvre tout le cache d'un coup.
**Référence** : `logout` défini dans `frontend/src/contexts/AuthContext.tsx:56` (vérifié cette session, `useCallback`) — il n'importe pas `useQueryClient`. Le `QueryClientProvider` global vit dans `frontend/src/main.tsx:21` (vérifié). L'injection de `useQueryClient` dans `AuthProvider` + l'appel de purge au logout sont **à créer**.

### Sprint 191 — Ops : `FORCE RLS` vérifié par test sur les 7 tables (verrou anti-régression)
**Objectif** : asserter en CI que les 7 tables RLS portent bien `relforcerowsecurity = true` (`pg_class`), pour qu'une future migration qui ajoute une table RLS sans `FORCE` (ou qui le retire) échoue immédiatement.
**Complexité** : Faible.
**Justification** : §2.3 d'OWASP repose sur `FORCE` ; aujourd'hui c'est prouvé indirectement (la matrice échouerait), jamais asserté directement. Un test ciblé rend l'invariant explicite et auto-documenté.
**Référence** : `docs/revue-owasp-rls-2026-06.md` §2.3 (vérifié `:40-45`) note « Les 6 tables portent `FORCE` (vérifié) » ; les 7 tables RLS sont énumérées dans `tests/integration/test_revoke_public_rls.py:32-40` (créé S186). Le test d'assertion `relforcerowsecurity` est **à créer** (peut tourner sous le rôle `copilote` ou en lecture catalogue, pas besoin de NOSUPERUSER).

---

## Template de démarrage

```
Tu es un développeur Python/infra senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.73.0),
.claude/rules/conventions-python.md et tests-pyramide.md.
Sprint actif : 187 — Refactor create_runtime_pool() : consolider les 10 sites
asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context) en un helper unique
dans app/db/, pour rendre IMPOSSIBLE de créer un pool runtime qui oublie la DSN app_runtime OU le
hook apply_tenant_context (invariant de sécurité RLS, finding répété S182/S185).
Sites vérifiés : 9 dans app/workers/tasks.py (82/345/397/472/663/756/811/898/985, tous setup=
apply_tenant_context, min/max 1/3) + 1 dans app/api/main.py:173 (min/max 2/10). resolve_app_database_url
(app/utils/security_config.py:17) et apply_tenant_context (app/db/tenant_context.py:79) existent.
⚠️ COEUR DU SPRINT = re-pointer ~25 mocks patch(...asyncpg.create_pool...) (tests/workers/**, tests/api,
tests/services, tests/orchestrator) sur le nouveau home, sinon ils cessent d'intercepter.
À TRANCHER : home du helper (app/db/pool.py vs dans tenant_context.py). Documenter dans le bloc ROADMAP.
À FAIRE : (1) create_runtime_pool(*, min_size, max_size) résout DSN + câble setup ; (2) remplacer les
10 sites en préservant les tailles ; (3) re-pointer les mocks ; (4) test unitaire du helper (asserte
DSN=resolve_app_database_url() ET setup=apply_tenant_context).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest + ruff + mypy. Pas d'eval. Preuve : grep -c "asyncpg.create_pool(" app/workers/tasks.py
app/api/main.py == 0.
```
