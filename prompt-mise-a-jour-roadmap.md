# Sprint 176 — E4-S11 : scoping tenant du token de rapport (`/report`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.62.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (175, E4-S10) a rendu le rattachement tenant des clés API **pilotable** : champ `tenant_id` optionnel sur `CreateKeyRequest`, autorisation **fail-closed** (un admin — clé Bearer DB **ou** cookie JWT — ne provisionne que pour son tenant courant, sinon 403 ; **seule la clé env** est exemptée), garde `ApiKeyService.tenant_exists` (tenant absent → 404, jamais une FK 500). La revue a fermé un **fail-open** pré-existant : `_require_admin` exige désormais le rôle admin pour les utilisateurs JWT (le chemin cookie posait `api_key_record=None`, identique à la clé env). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND** : ce sprint touche le **middleware d'auth** (`app/middleware/auth.py` — `EXEMPT_PREFIXES`), les **endpoints `/report`** (`app/api/endpoints/report.py`) et le **contexte tenant** (`app/db/tenant_context.py`). `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports`. Probablement **sans migration** ni frontend (à confirmer selon le mécanisme de token retenu). Le venv web suffit.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.62.0)
2. `.claude/rules/securite.md` (isolation tenant, jamais de fuite cross-tenant ; central pour ce sprint) et `.claude/rules/api-architecture.md` (avant toute modification du middleware d'auth — lire `architecture-copilote-financier.md` §11.2 ; `tests-pyramide.md` si un nouvel endpoint/comportement → test d'intégration obligatoire).
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `/report` est **auth-exempté** via `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")` (`app/middleware/auth.py:49`, vérifié, prédicat `startswith` `:102`) → la requête tourne sous le **tenant legacy** (aucun `tenant_id` posé dans `scope.state` → `TenantContextMiddleware` retombe sur legacy). Deux endpoints concernés : `POST /report` (analyse fraîche → PDF, `report.py:46`) et `GET /report/{analysis_id}` (régénère depuis `analysis_history`, `report.py:80` — `db_pool.fetchrow … WHERE id = $1::uuid` `:88-95`, **donc soumis à la RLS sous le GUC legacy**). La primitive d'exécution par-tenant `tenant_scope` existe (`app/db/tenant_context.py:65`, vérifié). **À CRÉER** : le mécanisme de propagation du tenant du demandeur jusqu'au contexte du rapport (token signé portant le `tenant_id`, ou levée de l'exemption pour ces routes).

---

## TÂCHE — Sprint 176 (E4-S11) : faire passer `/report` sous le tenant du demandeur

**Objectif** : fermer le **risque résiduel n°2** de la revue OWASP RLS (`docs/revue-owasp-rls-2026-06.md`, existe, vérifié) — un rapport PDF ne doit refléter QUE les données du tenant qui le demande. Aujourd'hui `/report` est auth-exempté → il s'exécute sous le tenant **legacy**, si bien que `GET /report/{analysis_id}` ne voit (RLS) que les analyses legacy et `POST /report` écrit/lit sous legacy. C'est le dernier trou d'isolation documenté.

### Spécification (à affiner en Phase A selon le mécanisme retenu)
1. **Mécanisme de propagation tenant** — trancher et documenter entre :
   (a) **token de rapport signé** (ex. `itsdangerous`, déjà utilisé pour le reset password — vérifier) portant le `tenant_id`, émis par un endpoint authentifié et passé en query/header à `/report` ; le middleware/endpoint le décode et pose le contexte ;
   (b) **lever l'exemption** de `/report` (le retirer de `EXEMPT_PREFIXES`) et exiger l'auth normale (cookie JWT / Bearer) — plus simple, mais change le contrat d'appel (un lien PDF anonyme ne marche plus).
   **Défaut suggéré** : évaluer (b) d'abord (moins de surface, réutilise le threading tenant existant) ; ne retenir (a) que si un accès non-cookie au PDF est un requirement produit. **Documenter le choix.**
2. **Threading du contexte** — une fois le `tenant_id` du demandeur résolu, exécuter l'analyse/la lecture **sous `tenant_scope(tenant_id)`** (`tenant_context.py:65`) pour que la RLS + le metering ciblent le bon tenant, plus legacy.
3. **Fail-closed** — un `/report` sans tenant résoluble ne doit PAS retomber silencieusement sur legacy avec des données d'un autre tenant : soit 401/403, soit un scope vide explicite (à trancher selon (a)/(b)).

### Tests / validation
- **Intégration** : `GET /report/{analysis_id}` d'une analyse du tenant A demandé sous le contexte de A → 200 + PDF ; demandé sous un autre contexte / sans tenant → 404 (RLS masque) ou 401/403 selon le mécanisme. `POST /report` exécute l'analyse sous le tenant du demandeur (metering/écriture scopés).
- Si un PostgreSQL migré + rôle NOSUPERUSER est disponible : prouver l'isolation RLS bout-en-bout (patron `tests/integration/test_*_rls.py`) ; sinon le **dire explicitement** (pas de Docker dans le conteneur web).
- `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Eval** : aucun prompt de skill touché → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : un rapport demandé par le tenant A ne contient jamais une analyse du tenant B (et inversement).

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que legacy, afin de les metrer dans `usage_events` (chemin worker non métré, déféré au S166) — et de les facturer ensuite via `run_usage_reporting` (S174).
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ; complémentaire au S174 (qui rapporte la conso métrée mais ne capte aujourd'hui que le chemin requête).
**Référence** : le chemin worker tourne sous legacy (`app/workers/tasks.py:111-112` commentaire « le threading tenant→worker relève d'un sprint E4 ultérieur », vérifié ; `_build_orchestrator` `:65`, vérifié) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive par-tenant. Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

### Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)
**Objectif** : gérer le retour de checkout Stripe sur `BillingPage` — lire `?status=success|cancel` pour afficher une confirmation et **rafraîchir le plan** affiché (le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage).
**Complexité** : Faible.
**Justification** : sans rafraîchissement, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'au prochain rechargement complet — friction produit immédiate.
**Référence** : `success_url`/`cancel_url` pointent déjà `/facturation?status=success|cancel` (`app/api/endpoints/billing.py:81-82`, vérifié) ; `AuthContext` **n'expose aucune méthode de refresh** (`frontend/src/contexts/AuthContext.tsx` — `useAuth` retourne `user`/`isAuthenticated`/`login`/`logout`, pas de `refreshUser`, vérifié `:7-8,58-59`) → exposer un `refreshUser()` (re-`authMe()`) est **à créer** ; `BillingPage` lit `user.plan` (créée S173).

### Sprint 179 — E5-S2 : facturation à l'usage côté UI (compteur de report)
**Objectif** : exposer sur `/facturation` la consommation métrée déjà rapportée à Stripe vs en attente (lecture du curseur `subscriptions.usage_reported_through` + `usage_events` non encore rapportés).
**Complexité** : Moyenne.
**Justification** : rend la facturation à l'usage (S174) transparente pour le client — « X unités facturées, Y en attente du prochain cycle ».
**Référence** : curseur `subscriptions.usage_reported_through` **existe** (créé au S174, `alembic/versions/0010_usage_report_cursor.py` ; lu par le worker `app/workers/tasks.py:875`, vérifié) ; `GET /usage` agrège déjà `usage_events` (`app/api/endpoints/usage.py`, S170, vérifié) ; un endpoint exposant l'état du curseur + son rendu UI sont **à créer**.

### Sprint 180 — E5-S3 : audit log côté UI (page Admin)
**Objectif** : exposer le journal d'audit (`GET /admin/audit-log`, S160) dans la page Admin — table filtrable des mutations métier (watchlist, annotation, clé API), désormais enrichie du `tenant_id` effectif (S175).
**Complexité** : Faible.
**Justification** : la conformité (Loi 25) exige une traçabilité consultable ; le backend existe depuis S160 mais n'a aucune surface UI.
**Référence** : `GET /admin/audit-log?limit=50` existe (`app/api/endpoints/admin.py`, route `list_audit_log`, vérifié — voir `ROADMAP.md` « Ce qui fonctionne aujourd'hui ») ; la métadonnée d'audit porte le `tenant_id` depuis S175 (`app/services/api_key_service.py`) ; le composant React + le client typé sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.62.0), .claude/rules/securite.md et api-architecture.md.
Sprint actif : 176 — E4-S11 (scoping tenant du token de rapport /report). Les endpoints /report
(report.py:46 POST, report.py:80 GET {analysis_id}) sont auth-exemptés (auth.py:49 EXEMPT_PREFIXES)
→ ils tournent sous le tenant LEGACY, donc un rapport ne reflète pas le tenant du demandeur (risque
résiduel n°2 de docs/revue-owasp-rls-2026-06.md). Faire passer /report sous le tenant du demandeur
via tenant_scope (tenant_context.py:65). Trancher le mécanisme : (a) token de rapport signé portant
le tenant_id, ou (b) lever l'exemption et exiger l'auth normale — défaut : évaluer (b) d'abord.
Fail-closed (jamais de repli silencieux sur legacy avec des données d'un autre tenant).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; pas d'eval (aucun prompt de skill touché) ;
preuve : un rapport demandé par le tenant A ne contient jamais une analyse du tenant B.
```
