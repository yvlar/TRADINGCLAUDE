# Sprint 185 — E5-S7 : threading tenant à travers la frontière Celery (`run_full_analysis`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.71.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (184, E5-S6) a exposé le quota mensuel dans le header : endpoint `GET /quota` (authentifié, lecture seule, fail-open neutre) + `QuotaService.read_status()` + badge `QuotaBadge`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND/WORKER seul** : threading + metering du **dernier chemin d'analyse encore sous tenant legacy**. GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps → `.venv/bin/pip install -r requirements.txt` si un import échoue (`stripe`, `mypy` notamment). **Pas de Docker/PG/Redis/navigateur live** dans le conteneur web → la propagation tenant à travers Celery se prouve par tests (capture de `get_current_tenant()` au site d'analyse + test d'intégration RLS skippé hors PG), pas par un essai live. **Frontend non touché** (aucun fichier `frontend/` modifié → non-régression par construction).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.71.0)
2. `.claude/rules/gotchas-operationnels.md` (services/workers — timeouts, `max_parallel`, threading tenant) **et** `.claude/rules/tests-pyramide.md` (patch obligatoire de `call_claude_with_retry` ; nouveau comportement worker = test d'intégration ; marqueur `@pytest.mark.integration` pour les tests PG réels). Accessoirement `.claude/rules/conventions-python.md` (async/await, pas de `time.sleep`).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **`run_full_analysis`** (tâche Celery synchrone) est défini `app/workers/tasks.py:143` (vérifié) ; il appelle `asyncio.run(_execute_analysis(request_dict))` (`tasks.py:156`, vérifié). Il est **déclenché via `.delay()`** depuis la boucle d'alerte prix `app/workers/tasks.py:301` (vérifié) — un `for ticker in alerted` qui construit un `AnalyzeRequest` et l'envoie au broker.
   - **Le problème** : le `ContextVar` `current_tenant` (`app/db/tenant_context.py`) **ne traverse pas le broker Celery** (sérialisation JSON de la tâche). `run_full_analysis` tourne donc sous le **tenant legacy par défaut**, et `_execute_analysis` n'est **pas** métré (il ne passe pas par `_build_orchestrator(with_metering=True)`). → c'est le dernier chemin d'analyse non imputé à un tenant (cf. ROADMAP « Reste sous legacy »).
   - **Le patron de référence à cloner** : les chemins planifiés (`_execute_watchlist_analysis` `tasks.py:229`, screener `:417`, composite) énumèrent `SELECT id FROM tenants ORDER BY created_at` (pool hors-RLS) puis, **sous `with tenant_scope(tenant_id)`** (`tasks.py:245/454`, vérifié), exécutent le travail avec `_build_orchestrator(with_metering=True)` (`tasks.py:66`, vérifié). MAIS `run_full_analysis` n'énumère **pas** les tenants — il analyse **un seul ticker** pour **un seul tenant** (celui qui possède l'alerte). Le tenant doit donc être **capturé au site `.delay()`** (`tasks.py:301`) et **propagé en argument de tâche**, pas re-dérivé d'une énumération.
   - **À TRANCHER et documenter dans le bloc ROADMAP** : **(a)** ajouter un paramètre `tenant_id: str` à la signature `run_full_analysis` (et au `.delay(...)`) puis, dans le corps, `with tenant_scope(tenant_id):` autour de `_execute_analysis`, avec un orchestrateur **métré** — **vs (b)** sérialiser le tenant dans `request_dict`. Privilégier **(a)** : argument explicite, plus lisible et testable que de surcharger le payload de requête métier ; rétrocompat à assurer si d'autres appelants de `run_full_analysis` existent (vérifier : `grep -rn "run_full_analysis" app/ tests/`). Vérifier **sous quel contexte tenant tourne la boucle d'alerte prix** au site `:301` (est-elle déjà par-tenant sous `tenant_scope`, ou legacy ?) avant de décider d'où vient le `tenant_id` capturé.

---

## TÂCHE — Sprint 185 : threading tenant à travers la frontière Celery

**Objectif** : faire en sorte que `run_full_analysis` (déclenché par une alerte prix) tourne **sous le tenant propriétaire** de l'alerte et soit **métré** dans `usage_events`, fermant le dernier chemin d'analyse sous tenant legacy.

### Spécification

1. **Capture du tenant au site `.delay()`** (`tasks.py:301`) : déterminer le `tenant_id` propriétaire de l'alerte/du ticker (selon le contexte tenant de la boucle d'alerte prix — à vérifier en début de session) et le passer en argument à `run_full_analysis.delay(...)`.
2. **Restauration côté worker** : `run_full_analysis` accepte le `tenant_id`, pose `with tenant_scope(tenant_id):` autour de l'exécution, et utilise un orchestrateur **métré** (`with_metering=True`, comme les chemins planifiés) afin que la consommation soit imputée au bon tenant. La RLS (lecture/écriture `analysis_history`) et le metering dérivent du GUC `app.tenant_id`.
3. **Rétrocompatibilité** : si `run_full_analysis` est appelé par d'autres sites (à vérifier par `grep`), préserver leur comportement (param optionnel avec repli legacy documenté, ou mise à jour de tous les appelants). Best-effort : un échec de metering n'avorte jamais l'analyse (cohérent avec S166).
4. **Zéro régression** : le statut Redis du job (`pending`/`running`/`done`/`failed`), le retry transitoire (`self.retry`, `tasks.py:164`) et le contrat de `_execute_analysis` restent inchangés.

### Tests / validation
- **Worker** (`tests/workers/`) : `run_full_analysis` appelé avec un `tenant_id` → capture de `get_current_tenant()` au site `_execute_analysis`/`screen()` **== le tenant passé** (non-vacuous via `_TENANT != LEGACY_TENANT_ID`) ; orchestrateur construit avec `with_metering=True` ; `tenant_scope` restauré après la tâche (ContextVar revenu au défaut). Patch de `call_claude_with_retry` obligatoire (cf. tests-pyramide).
- **Intégration RLS** (skippé hors PG migré, exécuté en CI, marqueur `@pytest.mark.integration`) : une alerte prix d'un tenant B → l'analyse résultante apparaît dans `usage_events`/`analysis_history` **imputée à B**, masquée sous legacy. Ajouter le fichier au gate RLS NOSUPERUSER (`.github/workflows/ci.yml`, comme `test_scheduled_metering_rls.py`).
- Gates : `pytest` + `ruff` + `mypy`. **Pas d'eval** (worker + threading tenant — aucun prompt de skill ni l'orchestrateur de skills modifié ; `_execute_analysis` réutilisé tel quel).
- **Preuve d'acceptation observable** : après une alerte prix sur un ticker d'un tenant B, un `usage_event` (et la ligne `analysis_history`) est imputé à B — prouvé sans PG par capture du tenant au site d'analyse, et bout-en-bout par le test d'intégration RLS.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 186 — Ops : durcissement du provisioning DB (propriété des objets + revoke PUBLIC)
**Objectif** : compléter S182 en garantissant que `app_runtime` n'est **propriétaire** d'aucune table (sinon il pourrait `ALTER … DISABLE ROW LEVEL SECURITY`) et en révoquant les privilèges `PUBLIC` par défaut sur le schéma.
**Complexité** : Moyenne.
**Justification** : `NOSUPERUSER`/`NOBYPASSRLS` ne suffit pas si le rôle runtime **possède** les tables — un propriétaire peut désactiver `FORCE ROW LEVEL SECURITY`. Non-propriété explicitement exigée par `docs/revue-owasp-rls-2026-06.md` §2.3 (vérifié, `:48-49`).
**Référence** : la propriété actuelle des tables revient à `copilote` (créées par Alembic sous cette DSN — **à vérifier** via `\dt`/`pg_class.relowner` en CI) ; le revoke `PUBLIC` et la garantie de non-propriété de `app_runtime` sont **à créer**. La migration `0011_app_runtime_role.py` (S182, vérifiée présente) est le point d'extension naturel.

### Sprint 187 — Refactor : `create_runtime_pool()` (couplage DSN runtime + setup RLS inséparable)
**Objectif** : consolider les **10 sites** `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` en un seul helper `create_runtime_pool(*, min_size, max_size)` (`app/db/`) — rendre **impossible** de créer un pool runtime qui résout le bon rôle mais oublie le hook de contexte tenant (ou l'inverse).
**Complexité** : Moyenne.
**Justification** : finding d'altitude de la revue S182 — le sprint a centralisé la résolution de DSN mais a laissé les 10 `create_pool` copiés ; le couplage DSN+setup est l'invariant de sécurité. Reporté de S182 car le ripple touche les mocks `patch("app.workers.tasks.asyncpg.create_pool", …)` de **nombreux tests workers** (à re-pointer sur le nouveau home) — hors diff S182.
**Référence** : 9 `create_pool` dans `app/workers/tasks.py` (vérifié, `grep -c`) + 1 dans `app/api/main.py:173` (vérifié) ; `resolve_app_database_url()` (`app/utils/security_config.py:17`, vérifié) et `apply_tenant_context` (`app/db/tenant_context.py:79`, vérifié) existent — le helper et la migration des mocks de test sont **à créer**.

### Sprint 188 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)
**Objectif** : quand `/analyze` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade ciblé (plan courant, borne atteinte, lien `/facturation`) plutôt qu'une erreur générique.
**Complexité** : Faible.
**Justification** : transforme le mur de quota en point de conversion ; complète le badge S184 (visibilité continue) par une incitation **au moment du blocage**.
**Référence** : `QuotaExceededError` (`app/services/quota_service.py:64`, vérifié — porte `plan`/`used`/`limit`/`retry_after_s`) ; `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`, vérifié présent ; importé dans `BillingPage.tsx:11`, utilisé `:179`) est le composant d'accroche — l'enrichissement du corps `429` (champs structurés) et le routage du `QuotaBanner` vers `/facturation` sont **à créer/vérifier**.

### Sprint 189 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)
**Objectif** : vider le cache react-query (`queryClient.clear()`/`removeQueries`) lors du `logout` pour qu'une re-connexion sous un autre tenant sur la même session SPA ne serve jamais de données périmées du tenant précédent (`usage`, `usage-reporting`, etc.).
**Complexité** : Faible.
**Justification** : finding cross-tenant de la revue S184 — généralisé. S184 a scopé `['quota', tenantId]` par tenant au cas par cas ; les clés `['usage']`/`['usage-reporting']` (`BillingPage.tsx`) restent non scopées et non purgées au logout. Une purge unique au logout couvre tout le cache d'un coup (altitude supérieure au scoping par-clé).
**Référence** : `logout` est défini dans `frontend/src/contexts/AuthContext.tsx:56` (vérifié, `useCallback`) — il `setUser(null)` puis navigue ; il n'importe pas `useQueryClient`. Le `QueryClientProvider` global vit dans `frontend/src/main.tsx` (vérifié). L'injection de `useQueryClient` dans `AuthProvider` + l'appel de purge au logout sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/React senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.71.0),
.claude/rules/gotchas-operationnels.md et tests-pyramide.md.
Sprint actif : 185 — E5-S7 threading tenant à travers la frontière Celery (run_full_analysis).
Aujourd'hui run_full_analysis (tasks.py:143, déclenché par .delay() au site tasks.py:301 depuis la
boucle d'alerte prix) tourne sous le tenant LEGACY (le ContextVar current_tenant ne traverse pas le
broker Celery) et n'est PAS métré → dernier chemin d'analyse non imputé à un tenant.
À TRANCHER d'abord : (a) ajouter un paramètre tenant_id à run_full_analysis + .delay(), tenant_scope
dans le corps (recommandé) VS (b) sérialiser le tenant dans request_dict. Documenter dans le bloc ROADMAP.
À FAIRE : (1) capturer le tenant_id propriétaire au site .delay() (tasks.py:301) ; (2) run_full_analysis
pose with tenant_scope(tenant_id) autour de _execute_analysis avec _build_orchestrator(with_metering=True) ;
(3) rétrocompat des autres appelants (grep run_full_analysis) ; (4) zéro régression sur le statut Redis du
job + retry. Vérifier sous quel contexte tenant tourne la boucle d'alerte prix avant d'implémenter.
Tests : capture de get_current_tenant()==tenant au site d'analyse (non-vacuous), orchestrateur métré,
ContextVar restauré + test d'intégration RLS (skippé hors PG, ajouté au gate CI NOSUPERUSER).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest + ruff + mypy. Pas d'eval. Preuve : une alerte prix d'un tenant B → usage_event imputé à B.
```
