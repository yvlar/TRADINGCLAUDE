# Sprint 175 — E4-S10 : provisionnement de clés API par tenant (admin self-service)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.61.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (174, E4-S9) a fermé la **boucle de monétisation** : `StripeService.report_usage` pousse la consommation agrégée (`usage_events`) vers Stripe en *metered usage records* (Billing Meters API `stripe.billing.MeterEvent`), via la tâche worker `run_usage_reporting` (best-effort par tenant abonné, curseur d'idempotence `subscriptions.usage_reported_through`, beat 02h00 UTC). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND léger** : ce sprint touche un **endpoint admin** + le **service de clés API** (`app/api/endpoints/admin.py`, `app/services/api_key_service.py`). `pytest` (hors e2e/evals) + `ruff` + `mypy app/`. Pas de migration, pas de Stripe, pas de frontend. Le venv web suffit (aucune dépendance nouvelle).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.61.0)
2. `.claude/rules/securite.md` (clés API : rattachement tenant, jamais de fuite ; central pour ce sprint) et `.claude/rules/tests-pyramide.md` (nouveau comportement d'endpoint → **test d'intégration obligatoire** ; patch des dépendances).
3. **Code de référence à vérifier en début de session (anti-hallucination)** : le service `ApiKeyService.create_key(...)` **accepte DÉJÀ un `tenant_id: UUID | None = None`** (`app/services/api_key_service.py:80`, défaut résolu par `resolve_tenant` `:84`) — **la plomberie service existe**, le sprint n'a PAS à la créer. **À CRÉER** : (a) le champ `tenant_id: UUID | None = None` sur `CreateKeyRequest` (`app/api/endpoints/admin.py:21`, aujourd'hui `name`/`role`/`expires_at` uniquement) ; (b) son threading au service dans l'endpoint `create_key` (`app/api/endpoints/admin.py:90-91` passe aujourd'hui `name`/`role`/`expires_at` **sans** `tenant_id` → utilise donc le tenant courant par défaut) ; (c) la **validation d'autorisation** : un admin ne peut créer une clé que pour **son propre tenant** (le tenant du contexte courant), sauf décision explicite d'un rôle super-admin — **à trancher et documenter**.

---

## TÂCHE — Sprint 175 (E4-S10) : `tenant_id` optionnel sur la création de clé API

**Objectif** : rendre le rattachement tenant des clés API (S168) **pilotable côté produit** — permettre à un admin de provisionner une clé rattachée à un tenant choisi via un champ `tenant_id` optionnel sur `CreateKeyRequest`, au lieu d'hériter silencieusement du tenant courant. Prérequis d'un onboarding multi-tenant.

### Spécification
1. **Champ requête** — `CreateKeyRequest.tenant_id: UUID | None = None` (`admin.py:21`). Absent → comportement inchangé (tenant courant, rétrocompatible).
2. **Threading endpoint** — `create_key` (`admin.py:82`) passe `tenant_id=body.tenant_id` à `service.create_key(...)` (le service le résout via `resolve_tenant` : `None` → tenant courant ; valeur → ce tenant).
3. **Autorisation (à trancher et documenter)** — un admin ne doit pas pouvoir créer une clé pour un **tenant arbitraire** (escalade cross-tenant). Options : (a) restreindre au tenant courant — `body.tenant_id` doit égaler `get_current_tenant()` sinon **403** (la clé env / super-admin legacy peut être exempté) ; (b) introduire une notion de super-admin. **Trancher (a) par défaut** (minimal, fail-closed) et documenter. Vérifier l'existence du tenant cible (FK `api_keys.tenant_id → tenants`) → **422/404** propre plutôt qu'une violation FK 500.
4. **Audit** — journaliser la création avec le `tenant_id` effectif (le traçage `AuditLogService` existe déjà sur ce chemin — vérifier et étendre si besoin).

### Tests / validation
- **Intégration** `POST /admin/keys` : sans `tenant_id` → clé rattachée au tenant courant (inchangé) ; avec `tenant_id` = tenant courant → 201 ; avec `tenant_id` ≠ tenant courant → **403** (ou le code tranché) ; `tenant_id` inexistant → 404/422 (pas de 500 FK).
- **Unitaires** service si une nouvelle logique de validation y descend (sinon endpoint only).
- `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Eval** : aucun prompt de skill touché → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : deux requêtes `POST /admin/keys` (avec/sans `tenant_id`) → la clé créée porte le bon `tenant_id` (vérifiable sur `ApiKeyRecord.tenant_id` retourné) ; une requête cross-tenant est refusée.

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 176 — E4-S11 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` exempté via `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")` (`app/middleware/auth.py:49`, vérifié) → GUC legacy par défaut ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive d'exécution par-tenant ; décision « legacy-only documentée » dans `docs/revue-owasp-rls-2026-06.md` (existe, vérifié). Un token de rapport portant le tenant + le threading du contexte sont **à créer**.

### Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que legacy, afin de les metrer dans `usage_events` (chemin worker non métré, déféré au S166) — et de les facturer ensuite via `run_usage_reporting` (S174).
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ; complémentaire au S174 (qui rapporte la conso métrée à Stripe mais ne capte aujourd'hui que le chemin requête).
**Référence** : le chemin worker tourne sous legacy (`app/workers/tasks.py:111` commentaire « threading tenant→worker relève d'un sprint E4 ultérieur », vérifié ; `_build_orchestrator` `:65`, vérifié) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive par-tenant ; `watchlist` porte déjà `tenant_id` (RLS, S163-165). Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

### Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)
**Objectif** : gérer le retour de checkout Stripe sur `BillingPage` — lire `?status=success|cancel` pour afficher une confirmation et **rafraîchir le plan** affiché (le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage).
**Complexité** : Faible.
**Justification** : sans rafraîchissement, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'au prochain rechargement complet — friction produit immédiate.
**Référence** : `success_url`/`cancel_url` pointent déjà `/facturation?status=success|cancel` (`app/api/endpoints/billing.py:81-82`, vérifié) ; `AuthContext` **n'expose aucune méthode de refresh** (`frontend/src/contexts/AuthContext.tsx` — `useAuth` retourne `user`/`isAuthenticated`/`isLoading`/`login`/`logout`, pas de `refreshUser`, vérifié `:58-70`) → exposer un `refreshUser()` (re-`authMe()`) est **à créer** ; `BillingPage` lit `user.plan` (créée S173).

### Sprint 179 — E5-S2 : facturation à l'usage côté UI (compteur de report)
**Objectif** : exposer sur `/facturation` la consommation métrée déjà rapportée à Stripe vs en attente (lecture du curseur `subscriptions.usage_reported_through` + `usage_events` non encore rapportés).
**Complexité** : Moyenne.
**Justification** : rend la facturation à l'usage (S174) transparente pour le client — « X unités facturées, Y en attente du prochain cycle ».
**Référence** : curseur `subscriptions.usage_reported_through` (**à créer** au S174 — `alembic/versions/0010_usage_report_cursor.py`, vérifié) ; `GET /usage` agrège déjà `usage_events` (`app/api/endpoints/usage.py`, S170) ; un endpoint exposant l'état du curseur + son rendu UI sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.61.0), .claude/rules/securite.md et tests-pyramide.md.
Sprint actif : 175 — E4-S10 (provisionnement de clés API par tenant). Ajouter un champ
tenant_id: UUID | None = None sur CreateKeyRequest (admin.py:21) + le threader à
service.create_key (qui l'accepte DÉJÀ, api_key_service.py:80) dans l'endpoint POST /admin/keys
(admin.py:82-92, ne le passe pas aujourd'hui). Autorisation à trancher (défaut : un admin ne
crée que pour son tenant courant → 403 sinon ; tenant cible inexistant → 404/422, jamais 500 FK).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; pas d'eval (aucun prompt de skill touché) ;
preuve : POST /admin/keys avec/sans tenant_id → ApiKeyRecord.tenant_id correct ; requête
cross-tenant refusée. Sans migration, sans frontend, sans Stripe.
```
