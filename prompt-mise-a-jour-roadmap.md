# Sprint 181 — E5-S4 : metering du screener planifié + alertes composites (reliquat S177)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.67.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (180, E5-S3) a exposé le **journal d'audit dans la page Admin** : type `AuditLogEntry` + client `getAuditLog()` (`frontend/src/api/admin.ts`) + section « Journal d'audit » dans `AdminPage` (table filtrable, filtre client sur action/type de cible, états chargement/erreur/vide). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND/WORKER dominant** : ce sprint étend le threading tenant + metering (établi en S177) à **deux chemins worker encore sous tenant legacy**. GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. **Pas de frontend** (sinon Vitest reste vert par non-régression). ⚠️ Le venv web peut manquer des deps backend → `.venv/bin/pip install -r requirements.txt` (+ `mypy` non pinné : `.venv/bin/pip install mypy`) si un import échoue. ⚠️ Pas de Docker/PG dans le conteneur web → tout test d'isolation RLS bout-en-bout y est **skippé** (le dire explicitement), exécuté en CI via le gate NOSUPERUSER.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.67.0)
2. `.claude/rules/gotchas-operationnels.md` (services/workers : timeouts screener, `max_parallel`) **et** `.claude/rules/tests-pyramide.md` (patch `call_claude_with_retry` à chaque niveau ; un test d'intégration RLS skippé hors PG migré).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **Patron à cloner** : `_execute_watchlist_analysis` (`app/workers/tasks.py:230`, vérifié) itère `SELECT id FROM tenants ORDER BY created_at` puis, **sous `tenant_scope(tenant_id)`** (`:246`), appelle `_analyze_watchlist_entries` (`:168`) avec un orchestrateur **métré**. Best-effort par tenant (try/except `:248`). C'est la structure exacte à reproduire pour les deux chemins ci-dessous.
   - `_build_orchestrator(*, with_metering=False)` **existe déjà** (`app/workers/tasks.py:65`, vérifié) : `with_metering=True` injecte un `UsageEventService` dans l'orchestrateur (S177).
   - **Chemin 1 — `_execute_composite_alert_check`** (`app/workers/tasks.py:419`, vérifié) : appelle `_build_orchestrator()` **sans metering** (`:432`) et `WatchlistService(db_pool).list_entries()` (`:359` via `CompositeAlertService`) **sous legacy**. La re-analyse passe par `CompositeAlertService.check_composite_alerts()` (`:448`) — vérifier comment ce service itère les entrées pour décider du point d'insertion du `tenant_scope`.
   - **Chemin 2 — `_execute_scheduled_screener`** (`app/workers/tasks.py:513`, vérifié) : appelle `wl_service.list_entries()` (`:526`) **sous legacy**, construit la liste de tickers, puis `_build_orchestrator()` **sans metering** (`:535`) + `ScreenerService`. Itération par lots de 20 (`:540`).
   - **À VÉRIFIER avant d'implémenter** : `CompositeAlertService` et `ScreenerService` reçoivent un orchestrateur partagé et bouclent sur des tickers **multi-tenant** ; le `tenant_scope` doit envelopper la lecture watchlist **ET** la re-analyse de chaque tenant pour que `_emit_usage_events` impute au bon tenant. Lire ces deux services (`app/services/`) pour confirmer qu'une itération **par tenant** est possible sans réécrire leur cœur (sinon STOP et me le signaler — la restructuration par chemin est **à créer**, pas garantie triviale).

---

## TÂCHE — Sprint 181 (E5-S4) : metrer les deux chemins worker restés sous legacy

**Objectif** : fermer le dernier reliquat de consommation planifiée non facturée. Après S177, seule la re-analyse watchlist hebdomadaire (`run_watchlist_analysis`) tourne sous le tenant propriétaire et est métrée ; le **screener planifié** (`run_scheduled_screener`, dimanche 11h UTC) et les **alertes composites** (`run_composite_alert_check`) lisent encore la watchlist via `WatchlistService.list_entries()` sous le tenant legacy → leur conso n'est imputée à aucun tenant et échappe à `run_usage_reporting` (S174).

### Spécification

1. **Restructurer les deux chemins par itération tenant** (patron `_execute_watchlist_analysis`) :
   - Énumérer `SELECT id FROM tenants ORDER BY created_at` sur un pool hors-RLS.
   - Pour chaque tenant, **sous `tenant_scope(tenant_id)`**, lire sa watchlist (RLS-scopée) et exécuter le travail (screener / vérif d'alerte composite) avec un orchestrateur construit **`with_metering=True`** → `_emit_usage_events` impute au tenant courant (l'`asyncio.gather` hérite du `contextvars.Context` posé par `tenant_scope`).
   - **Best-effort par tenant** : l'échec d'un tenant (loggé) n'avorte pas les autres et n'écrit jamais sous legacy par repli silencieux.
2. **Chemin alertes composites** : threader le tenant courant jusqu'à `CompositeAlertService.check_composite_alerts()` (l'email de dérive et l'écriture `alert_history` doivent rester scopés au bon tenant).
3. **Chemin screener planifié** : le webhook FORT et le résultat agrégé doivent refléter l'union des tenants (ou être émis par tenant — trancher et documenter la décision dans le bloc ROADMAP).
4. **Pas de régression** : le comportement fonctionnel observable (emails envoyés, webhook FORT, lignes `alert_history`) reste équivalent ; seule l'imputation tenant + le metering changent.

### Tests / validation
- **Unitaires worker** (mock `call_claude_with_retry` + pool mocké, patron `test_watchlist_analysis_task.py`) : chaque chemin réclame `with_metering=True` ; chaque tenant tourne sous son `tenant_scope` (capture `get_current_tenant()` au site orchestrateur, non-vacuous via `_TENANT_A != LEGACY_TENANT_ID`) ; best-effort (un tenant en échec n'interrompt pas les autres) ; ContextVar restauré après échec.
- **Intégration RLS bout-en-bout** (skippée hors PG migré, ajoutée au gate CI NOSUPERUSER `.github/workflows/ci.yml`) : entrée watchlist écrite sous le tenant B → run planifié → `usage_event` visible sous B, **masqué sous legacy**.
- `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. **Pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — worker + threading tenant uniquement).
- **Preuve d'acceptation observable** : après un run planifié, la conso d'un screener / d'une vérif d'alerte composite du tenant B apparaît dans `usage_events` imputée à B, jamais au tenant legacy.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 182 — Ops : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS` (risque résiduel n°1)
**Objectif** : matérialiser le rôle de connexion applicatif `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-propriétaire) pour les pools API + workers, et réserver `copilote` (superuser) aux seules migrations Alembic.
**Complexité** : Moyenne.
**Justification** : **sans ce rôle, la RLS est inerte en production** (un `BYPASSRLS`/`SUPERUSER` court-circuite toute policy) — 1ᵉʳ des deux pré-requis hors-code documentés ; le 2ᵉ (scoping `/report`) est clos par le S176.
**Référence** : exigence documentée dans `docs/revue-owasp-rls-2026-06.md` (vérifié, fichier présent) ; le rôle `copilote` par défaut est superuser (`DATABASE_URL` `.env.example:21`, vérifié) → le provisioning d'un rôle séparé (`infra/postgres/`) + le câblage des pools/workers sont **à créer**.

### Sprint 183 — E5-S5 : webhook de plan → invalidation live du CTA (push)
**Objectif** : remplacer le `refreshUser()` ponctuel au retour de checkout (S178) par une invalidation poussée (WebSocket Dashboard existant ou polling court) pour que le plan se mette à jour même si le webhook Stripe arrive **après** le retour sur `/facturation`.
**Complexité** : Moyenne.
**Justification** : S178 resync une seule fois au montage ; si le webhook met `tenants.plan` à jour quelques secondes plus tard, le CTA reste périmé jusqu'au prochain `authMe()`. Fermer cette fenêtre rend l'upgrade instantané.
**Référence** : `refreshUser()` existe (`frontend/src/contexts/AuthContext.tsx:12,48`, vérifié) ; le canal WebSocket du Dashboard existe (`frontend/src/api/ws.ts`, vérifié présent) — son extension à un signal serveur de changement de plan est **à créer**.

### Sprint 184 — E5-S6 : badge de plan + quota restant dans le header
**Objectif** : exposer en continu (header global) le plan courant et le quota d'analyses restant du mois, lus depuis `user.plan` (S173) et un compteur de quota.
**Complexité** : Faible.
**Justification** : rend la consommation visible hors de `/facturation` — incite à l'upgrade au point d'usage.
**Référence** : `user.plan` exposé par `GET /auth/me` (S173, vérifié dans `ROADMAP.md` « État courant ») ; `QuotaService` existe (`app/services/quota_service.py:67`, `max_analyses_per_month` `:44`, vérifié) et applique une borne dure, mais **n'expose aucun endpoint de lecture du compteur restant** → un `GET /quota` (ou champ sur `/usage`) est **à créer**, ainsi que le composant header.

### Sprint 185 — E5-S7 : threading tenant à travers la frontière Celery (`run_full_analysis`)
**Objectif** : faire passer le `tenant_id` à travers le `.delay()` Celery pour que `run_full_analysis` (déclenché par une alerte prix) tourne sous le tenant propriétaire et soit métré.
**Complexité** : Élevée.
**Justification** : dernier chemin d'analyse encore sous legacy après S177/S181 ; le passage de tenant à travers la sérialisation Celery est un sujet distinct (le ContextVar ne traverse pas le broker).
**Référence** : `run_full_analysis` déclenché via `.delay()` (chemin alerte prix, à localiser dans `app/workers/tasks.py` — **à vérifier**) reste sous legacy ; la propagation du tenant dans l'argument de tâche + sa restauration via `tenant_scope` côté worker sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.67.0),
.claude/rules/gotchas-operationnels.md et tests-pyramide.md.
Sprint actif : 181 — E5-S4 (metering screener planifié + alertes composites). Le patron à cloner
est _execute_watchlist_analysis (app/workers/tasks.py:230 — itère SELECT id FROM tenants, puis sous
tenant_scope(tenant_id) appelle _analyze_watchlist_entries avec un orchestrateur with_metering=True).
À RESTRUCTURER : _execute_composite_alert_check (tasks.py:419) et _execute_scheduled_screener
(tasks.py:513), qui appellent aujourd'hui _build_orchestrator() SANS metering et list_entries() sous
le tenant legacy (:432/:535, :359/:526). AVANT d'implémenter : lire CompositeAlertService et
ScreenerService pour confirmer qu'une itération PAR TENANT est possible sans réécrire leur cœur —
sinon STOP et me le signaler.
À FAIRE : envelopper lecture watchlist + re-analyse de chaque tenant sous tenant_scope, orchestrateur
with_metering=True, best-effort par tenant. Tests : unitaires worker (capture get_current_tenant() au
site orchestrateur, non-vacuous ; best-effort ; ContextVar restauré) + intégration RLS bout-en-bout
skippée hors PG migré, ajoutée au gate CI NOSUPERUSER. Backend/worker seul, pas d'eval.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check + mypy app/ --ignore-missing-imports.
Preuve : conso d'un screener/alerte composite du tenant B apparaît dans usage_events imputée à B,
jamais au tenant legacy.
```
