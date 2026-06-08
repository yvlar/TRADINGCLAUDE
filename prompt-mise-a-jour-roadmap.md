# Sprint 188 — Refactor : helper `_for_each_tenant()` (5 copies du squelette énumère-et-scope)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.74.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (187, Refactor) a extrait `create_runtime_pool()` (`app/db/pool.py`) : les 10 sites `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` passent par un helper unique qui câble DSN runtime + hook tenant en un point — impossible désormais d'en oublier un (invariant RLS). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND/WORKER seul (refactor de plomberie, zéro changement de comportement)** : extraire le squelette répété « énumère les tenants → boucle → `tenant_scope(tenant_id)` → try/except best-effort log-and-continue » en un helper async unique dans `app/workers/`, appliqué aux **5 chemins planifiés** de `app/workers/tasks.py`. GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps → `.venv/bin/pip install -r requirements.txt && .venv/bin/pip install mypy` si un import échoue (`stripe`, `mypy`, `alembic` notamment). **Frontend non touché** (aucun fichier `frontend/` → non-régression par construction). **Pas d'eval** (plomberie workers — aucun prompt de skill ni l'orchestrateur de skills touché).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.74.0)
2. `.claude/rules/conventions-python.md` (pattern async, imports, docstrings FR) **et** `.claude/rules/gotchas-operationnels.md` (contraintes workers/services — le périmètre est `app/workers/tasks.py`). Accessoirement `.claude/rules/tests-pyramide.md` (les 5 chemins planifiés ont chacun des tests workers à garder verts).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **Le squelette dupliqué (cœur du sprint)** : `5` occurrences de `SELECT id FROM tenants ORDER BY created_at` dans `app/workers/tasks.py` (vérifié cette session, lignes **251 / 346 / 483 / 660 / 878**, `grep -c` = 5). Chacune ouvre le même patron : `tenant_rows = await db_pool.fetch("SELECT id FROM tenants ORDER BY created_at")` → `for row in tenant_rows:` → `with tenant_scope(row["id"]):` → `try: … except Exception: logger.…(…) ; continue`. **Les corps divergent** (retour `None` / `list[str]` agrégée / `dict` de compteurs) — le helper doit donc accepter un **callback async** et laisser l'agrégation à l'appelant.
   - `tenant_scope` existe (`app/db/tenant_context.py:65`, vérifié, `@contextmanager`, `Iterator[None]`). `create_runtime_pool` existe (`app/db/pool.py:9`, livré S187) — le pool est créé une fois puis ré-utilisé sous chaque scope (le `setup=apply_tenant_context` rejoue le GUC à chaque acquisition).
   - **Les 5 fonctions hôtes** (à confirmer par lecture) : `_execute_price_alert_check` (union `list[str]`), `_execute_composite_alert_check` (union `list[str]`), `_execute_scheduled_screener` (`dict`), `_execute_retention_purge` (`dict` de compteurs), `_execute_usage_reporting` (`dict`). Vérifier le **type de retour exact** et le **mode d'agrégation** de chacune AVANT d'écrire la signature du callback — c'est ce qui décide si le helper retourne `list[T]` (résultats par tenant, l'appelant réduit) ou ne retourne rien (effets de bord seuls).
   - **Le ripple de test** : chaque chemin a un test workers (`tests/workers/test_price_alert_task.py`, `test_celery_composite_alert.py`, `test_scheduled_screener.py`, `test_retention_purge_task.py`, `test_usage_reporting_task.py`) qui mocke `app.workers.tasks.asyncpg.create_pool` (intercepte toujours, cf. réconciliation S187) et asserte le comportement best-effort par tenant. La suite doit rester **verte sans re-pointage** — c'est la preuve que le squelette extrait préserve la sémantique.

---

## TÂCHE — Sprint 188 : helper `_for_each_tenant()`

**Objectif** : éliminer la 5ᵉ copie d'un squelette load-bearing (finding d'altitude des revues S185/S186). Le patron « énumère les tenants → exécute un corps sous `tenant_scope` → best-effort log-and-continue » est dupliqué 5×, seuil où une divergence silencieuse (un chemin qui oublie le `tenant_scope`, ou qui avorte au premier échec au lieu de continuer) devient probable. Centraliser le squelette pour que les 5 chemins partagent **une seule** implémentation de l'énumération + scoping + tolérance aux pannes.

### Spécification

1. **Helper `_for_each_tenant(...)`** dans `app/workers/` (ex. dans `tasks.py` près des tâches, ou un nouveau `app/workers/tenant_iteration.py` — **TRANCHER et documenter** ; co-localiser avec les tâches est défendable, un module dédié évite d'alourdir `tasks.py`). Signature à concevoir d'après la réconciliation : il prend le `db_pool` (ou exécute le `SELECT`), un **callback async** `async def body(tenant_id) -> T`, et gère pour chaque tenant : `tenant_scope(tenant_id)` + `try/except` best-effort (log + `continue`, l'échec d'un tenant n'avorte pas les autres). Décider s'il **retourne** `list[T]` (laissant l'agrégation `list`/`dict` à l'appelant) ou rien. Docstring FR du WHY (l'invariant : énumérer-puis-scoper indissociable, tolérance par tenant).
2. **Appliquer aux 5 chemins** en **préservant exactement** le comportement : type de retour, contenu des logs d'erreur, sémantique d'agrégation (union de tickers, dict de compteurs). Aucun changement observable.
3. **Garder les 5 tests workers verts** sans re-pointer les mocks — preuve que l'extraction est sémantiquement neutre.

### Tests / validation
- **Unitaire** sur le helper : un callback qui réussit sur N tenants → N résultats / N effets ; un callback qui lève sur 1 tenant → les autres tenants sont quand même traités (best-effort prouvé non-vacuous), l'erreur est loggée.
- **Non-régression** : les 5 tests workers (price_alert, composite_alert, scheduled_screener, retention_purge, usage_reporting) restent verts.
- Gates : `pytest` + `ruff` + `mypy`. **Pas d'eval**.
- **Preuve d'acceptation observable** : `grep -c "SELECT id FROM tenants ORDER BY created_at" app/workers/tasks.py` tombe à **1** (le helper) ou **0** (si le helper vit dans un autre module) ; les 5 fonctions hôtes appellent `_for_each_tenant(...)` au lieu de ré-implémenter la boucle.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 189 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)
**Objectif** : quand `/analyze` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade ciblé (plan courant, borne atteinte, lien `/facturation`) plutôt qu'une erreur générique.
**Complexité** : Faible.
**Justification** : transforme le mur de quota en point de conversion ; complète le badge S184 (visibilité continue) par une incitation **au moment du blocage**.
**Référence** : `QuotaExceededError` (`app/services/quota_service.py:64`, vérifié cette session) ; `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`, vérifié présent) est le composant d'accroche — l'enrichissement du corps `429` (champs structurés : plan, borne, restant) et le routage du `QuotaBanner` vers `/facturation` sont **à créer/vérifier**.

### Sprint 190 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)
**Objectif** : vider le cache react-query (`queryClient.clear()`) lors du `logout` pour qu'une re-connexion sous un autre tenant sur la même session SPA ne serve jamais de données périmées du tenant précédent (`usage`, `usage-reporting`, etc.).
**Complexité** : Faible.
**Justification** : finding cross-tenant de la revue S184 — généralisé. S184 a scopé `['quota', tenantId]` par tenant au cas par cas ; les clés `['usage']`/`['usage-reporting']` restent non scopées et non purgées au logout. Une purge unique au logout couvre tout le cache d'un coup.
**Référence** : `logout` défini dans `frontend/src/contexts/AuthContext.tsx:56` (vérifié cette session, `useCallback`) — il n'importe **pas** `useQueryClient`. Le `QueryClientProvider` global vit dans `frontend/src/main.tsx:21` (vérifié). L'injection de `useQueryClient` dans `AuthProvider` + l'appel de purge au logout sont **à créer**.

### Sprint 191 — Ops : `FORCE RLS` vérifié par test sur les 7 tables (verrou anti-régression)
**Objectif** : asserter en CI que les 7 tables RLS portent bien `relforcerowsecurity = true` (`pg_class`), pour qu'une future migration qui ajoute une table RLS sans `FORCE` (ou qui le retire) échoue immédiatement.
**Complexité** : Faible.
**Justification** : §2.3 d'OWASP repose sur `FORCE` ; aujourd'hui c'est prouvé indirectement (la matrice échouerait), jamais asserté directement. Un test ciblé rend l'invariant explicite et auto-documenté.
**Référence** : `docs/revue-owasp-rls-2026-06.md` §2.3 (vérifié présent) ; les 7 tables RLS sont énumérées dans `tests/integration/test_revoke_public_rls.py:30` (« 7 tables RLS », créé S186). Le test d'assertion `relforcerowsecurity` est **à créer** (peut tourner sous le rôle `copilote` ou en lecture catalogue, pas besoin de NOSUPERUSER).

### Sprint 192 — Ops : garde `require_secure_db_url` uniformisé sur tous les pools runtime
**Objectif** : faire passer les **9 pools workers** par le même garde insecure-creds que le boot API, en l'absorbant dans `create_runtime_pool()` (ou un appel câblé dans le helper) — aujourd'hui seuls les pools API le portent.
**Complexité** : Faible.
**Justification** : finding d'altitude **différé** de la revue S187 — laisser le garde API-only laisse un special-case permanent. Le rendre uniforme ferme un gap : un worker qui boote en prod avec des creds par défaut devrait échouer comme l'API. **Assumé comme changement de comportement** (d'où un sprint dédié avec tests de boot workers, pas un refactor silencieux).
**Référence** : `require_secure_db_url` (`app/utils/security_config.py:41`, vérifié cette session) appelé **uniquement** à `app/api/main.py:158` (vérifié) ; `create_runtime_pool` (`app/db/pool.py:9`, livré S187) est le home naturel. L'absorption + les tests de boot workers sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/infra senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.74.0),
.claude/rules/conventions-python.md et gotchas-operationnels.md.
Sprint actif : 188 — Refactor _for_each_tenant() : extraire le squelette répété
« SELECT id FROM tenants ORDER BY created_at → boucle → tenant_scope(tenant_id) → try/except
best-effort log-and-continue » en un helper async unique dans app/workers/, appliqué aux 5 chemins
planifiés de app/workers/tasks.py. Les corps divergent (retour None / list[str] / dict) → le helper
prend un callback async et laisse l'agrégation à l'appelant.
Sites vérifiés (n° de ligne DÉRIVENT, re-grep obligatoire) : 5 occurrences de
SELECT id FROM tenants ORDER BY created_at dans app/workers/tasks.py (251/346/483/660/878) ;
fonctions hôtes _execute_price_alert_check, _execute_composite_alert_check, _execute_scheduled_screener,
_execute_retention_purge, _execute_usage_reporting. tenant_scope (app/db/tenant_context.py:65) et
create_runtime_pool (app/db/pool.py:9) existent.
À TRANCHER : home du helper (dans tasks.py vs app/workers/tenant_iteration.py) ; retourne-t-il list[T]
ou rien. Documenter dans le bloc ROADMAP. AVANT d'écrire la signature : vérifier le type de retour et
le mode d'agrégation exacts des 5 fonctions hôtes.
⚠️ Garder les 5 tests workers verts SANS re-pointer les mocks (ils interceptent via le module asyncpg
partagé, cf. réconciliation S187) — c'est la preuve que l'extraction est sémantiquement neutre.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest + ruff + mypy. Pas d'eval. Preuve : grep -c "SELECT id FROM tenants ORDER BY created_at"
app/workers/tasks.py == 1 (helper) ou 0, et les 5 hôtes appellent _for_each_tenant(...).
```
