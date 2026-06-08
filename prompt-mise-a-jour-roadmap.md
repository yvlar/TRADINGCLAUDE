# Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.63.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (176, E4-S11) a fermé le **dernier trou d'isolation lecture** : `/report` n'est plus auth-exempté — ses deux routes exigent une session (cookie JWT) et exécutent lecture/analyse sous `tenant_scope(tenant_id du demandeur)` → la RLS masque les analyses des autres tenants (un tiers détenant l'UUID obtient 404) et le metering POST cible le bon tenant ; **fail-closed** (401 sans session). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND (worker)** : ce sprint touche les **workers Celery** (`app/workers/tasks.py`) et le **contexte tenant** (`app/db/tenant_context.py`). `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports`. **Probablement sans migration ni frontend.** Le venv web suffit (mais le metering bout-en-bout réel nécessite un PG migré — sinon le dire). ⚠️ Le venv web peut manquer des deps (`stripe`, `alembic`, `mypy`) → `bash scripts/setup-web-session.sh` ou `.venv/bin/pip install -r requirements.txt` si un import échoue.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.63.0)
2. `.claude/rules/gotchas-operationnels.md` (central : workers Celery, `max_parallel=3` pour `compounder_buffett`, timeouts screener) et `.claude/rules/securite.md` (isolation tenant, jamais de fuite cross-tenant ; le metering doit imputer la conso au bon tenant). Si un nouvel endpoint/comportement de worker → `tests-pyramide.md` (test obligatoire).
3. **Code de référence à vérifier en début de session (anti-hallucination)** : le chemin worker tourne aujourd'hui **sous le tenant legacy** — commentaire explicite « le threading tenant→worker relève d'un sprint E4 ultérieur ; les facturer au legacy serait du bruit » (`app/workers/tasks.py:110-112`, vérifié) ; `_build_orchestrator()` construit l'orchestrateur **sans** `usage_event_service` (`app/workers/tasks.py:65`, vérifié — donc **aucun metering** côté worker). `_execute_watchlist_analysis()` itère `SELECT … FROM watchlist` (`app/workers/tasks.py:163,170`, vérifié) puis appelle l'orchestrateur par ticker. La primitive `tenant_scope` est **déjà importée** dans le worker (`from app.db.tenant_context import apply_tenant_context, tenant_scope`, `app/workers/tasks.py:15`, vérifié) et définie en `app/db/tenant_context.py:65` (vérifié). `UsageEventService` est **déjà importable** par le worker (`app/workers/tasks.py:30`, vérifié) mais **non injecté** à l'orchestrateur planifié. **À CRÉER** : (a) la lecture des entrées watchlist **de tous les tenants** (le `SELECT FROM watchlist` sous legacy ne voit que les lignes legacy — RLS), (b) l'exécution de chaque analyse **sous `tenant_scope(tenant_propriétaire)`**, (c) l'**injection d'un `UsageEventService`** à l'orchestrateur planifié pour émettre les `usage_events`.

---

## TÂCHE — Sprint 177 (E5-S1) : metrer les analyses planifiées sous le tenant propriétaire

**Objectif** : faire tourner les analyses planifiées (re-analyse watchlist `run_watchlist_analysis`, et le cas échéant le screener planifié / les alertes) **sous le tenant propriétaire de chaque entrée** plutôt que legacy, afin que leur consommation soit **métrée dans `usage_events`** (chemin worker non métré aujourd'hui, déféré au S166) — et donc **facturable** via `run_usage_reporting` (S174). C'est le dernier trou de facturation : la conso planifiée d'un tenant doit lui être imputée.

### Spécification (à affiner en Phase A selon le mécanisme retenu)
1. **Lecture cross-tenant des entrées planifiées** — trancher et documenter comment le worker énumère le travail de **tous** les tenants malgré la RLS sur `watchlist` :
   (a) **itérer les tenants** (table parente `tenants`, hors RLS) puis, **sous `tenant_scope(tenant_id)`**, lire la watchlist de chacun (le pool rejoue `apply_tenant_context` → GUC → RLS scopée) — patron **identique à `run_retention_purge`** (S171, `RetentionService.purge_tenant` itéré par tenant) ;
   (b) lire `watchlist` avec le `tenant_id` par ligne via une requête hors-RLS dédiée puis grouper — plus fragile (contourne la RLS applicative). **Défaut suggéré** : (a), aligné sur le précédent `run_retention_purge` et fail-closed par construction. **Documenter le choix.**
2. **Exécution scopée + metering** — pour chaque entrée, exécuter l'analyse **sous `tenant_scope(tenant_id)`** avec un orchestrateur **portant un `UsageEventService`** (injecté dans `_build_orchestrator`, comme le chemin requête) → les `usage_events` sont émis sous le bon tenant (le metering existant `_emit_usage_events` n'émet rien sur cache hit `cost_usd=0`, cohérent).
3. **Best-effort par tenant** — l'échec d'un tenant (ou d'un ticker) ne doit pas avorter les autres (patron `run_retention_purge` / `run_usage_reporting`), et ne doit pas écrire sous legacy par repli silencieux.

### Tests / validation
- **Unitaires worker** : `_build_orchestrator` injecte bien un `UsageEventService` ; l'itération exécute chaque analyse sous le `tenant_scope` attendu (capture de `get_current_tenant()` au site d'appel orchestrateur, patron `tests/api/test_report_endpoint.py` S176) ; best-effort (un tenant en échec n'interrompt pas les autres).
- **Intégration RLS bout-en-bout** (si PG migré + rôle NOSUPERUSER dispo) : une entrée watchlist du tenant B re-analysée par le worker émet un `usage_event` **sous B** (visible sous B, masqué sous legacy) — patron `tests/integration/test_retention_purge_rls.py`. Sinon le **dire explicitement** (pas de Docker/PG dans le conteneur web).
- `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Eval** : aucun prompt de skill touché (worker + injection de service) → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : après un run planifié, la conso d'une analyse watchlist du tenant B apparaît dans `usage_events` imputée à B (jamais au tenant legacy).

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)
**Objectif** : gérer le retour de checkout Stripe sur `BillingPage` — lire `?status=success|cancel` pour afficher une confirmation et **rafraîchir le plan** affiché (le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage).
**Complexité** : Faible.
**Justification** : sans rafraîchissement, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'au prochain rechargement complet — friction produit immédiate.
**Référence** : `success_url`/`cancel_url` pointent déjà `/facturation?status=success|cancel` (`app/api/endpoints/billing.py:81-82`, vérifié) ; `AuthContext` **n'expose aucune méthode de refresh** (`frontend/src/contexts/AuthContext.tsx` — `useAuth` retourne `user`/`isAuthenticated`/`login`/`logout`, pas de `refreshUser`, vérifié `:7-11` ; `authMe()` appelé au montage `:24`) → exposer un `refreshUser()` (re-`authMe()`) est **à créer** ; `BillingPage` lit `user.plan` (créée S173).

### Sprint 179 — E5-S2 : facturation à l'usage côté UI (compteur de report)
**Objectif** : exposer sur `/facturation` la consommation métrée déjà rapportée à Stripe vs en attente (lecture du curseur `subscriptions.usage_reported_through` + `usage_events` non encore rapportés).
**Complexité** : Moyenne.
**Justification** : rend la facturation à l'usage (S174) transparente pour le client — « X unités facturées, Y en attente du prochain cycle ».
**Référence** : curseur `subscriptions.usage_reported_through` **existe** (créé au S174, `alembic/versions/0010_usage_report_cursor.py`) et est lu/avancé par le worker (`app/workers/tasks.py:875,889,912`, vérifié) ; `GET /usage` agrège déjà `usage_events` (`app/api/endpoints/usage.py`, S170, vérifié) ; un endpoint exposant l'état du curseur + son rendu UI sont **à créer**.

### Sprint 180 — E5-S3 : audit log côté UI (page Admin)
**Objectif** : exposer le journal d'audit (`GET /admin/audit-log`, S160) dans la page Admin — table filtrable des mutations métier (watchlist, annotation, clé API), désormais enrichie du `tenant_id` effectif (S175).
**Complexité** : Faible.
**Justification** : la conformité (Loi 25) exige une traçabilité consultable ; le backend existe depuis S160 mais n'a aucune surface UI.
**Référence** : `GET /admin/audit-log` existe (`app/api/endpoints/admin.py:159`, route `list_audit_log` `:163`, vérifié) ; la métadonnée d'audit porte le `tenant_id` depuis S175 (`app/services/api_key_service.py`) ; le composant React + le client typé sont **à créer**.

### Sprint 181 — Ops : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS` (risque résiduel n°1)
**Objectif** : matérialiser le rôle de connexion applicatif `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-propriétaire) pour les pools API + workers, et réserver `copilote` (superuser) aux seules migrations Alembic.
**Complexité** : Moyenne.
**Justification** : **sans ce rôle, la RLS est inerte en production** (un `BYPASSRLS`/`SUPERUSER` court-circuite toute policy) — c'est le 1ᵉʳ des deux pré-requis hors-code documentés ; le 2ᵉ (scoping `/report`) est clos par le S176.
**Référence** : exigence documentée dans `docs/revue-owasp-rls-2026-06.md` §2.4 + §4 (vérifié) ; le rôle `copilote` par défaut est `SUPERUSER`+`BYPASSRLS` (`.env.example`, `POSTGRES_URL`) → le provisioning d'un rôle séparé (`infra/postgres/`) + le câblage des pools/workers sur ce rôle sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.63.0), .claude/rules/gotchas-operationnels.md et securite.md.
Sprint actif : 177 — E5-S1 (threading tenant des analyses planifiées). Les workers Celery
(app/workers/tasks.py) tournent sous le tenant LEGACY et NE METRENT PAS la conso planifiée :
_build_orchestrator (tasks.py:65) ne porte pas de UsageEventService, commentaire explicite
tasks.py:110-112, _execute_watchlist_analysis (tasks.py:163) lit `FROM watchlist` sous legacy.
Faire tourner chaque analyse planifiée sous tenant_scope(tenant_propriétaire) (tenant_context.py:65,
déjà importé tasks.py:15) avec un orchestrateur portant un UsageEventService → usage_events imputés
au bon tenant. Mécanisme cross-tenant : itérer les tenants puis lire la watchlist de chacun sous
tenant_scope (patron run_retention_purge S171). Best-effort par tenant (jamais d'écriture legacy par repli).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; pas d'eval (aucun prompt de skill touché) ;
preuve : la conso d'une analyse watchlist du tenant B apparaît dans usage_events imputée à B, jamais legacy.
```
