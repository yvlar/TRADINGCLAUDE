# Sprint 175 — E4-S10 : provisionnement de clés API par tenant (admin self-service)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.61.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (174, E4-S9) a fermé la **boucle de monétisation** : la tâche worker `run_usage_reporting` pousse quotidiennement la consommation `usage_events` vers Stripe en metered usage records (API meters `stripe.billing.MeterEvent`), avec idempotence par table `usage_report_log`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND** (+ test d'intégration endpoint) : ce sprint est un ajout de champ + validation sur l'endpoint admin de création de clé. `pytest` (hors e2e/evals) + `ruff` + `mypy app/`. Pas de Docker dans le conteneur web. Aucune dépendance externe nouvelle.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.61.0)
2. `.claude/rules/securite.md` (rattachement tenant des clés API, pas de secret loggé — central pour le provisionnement de clé) et `.claude/rules/tests-pyramide.md` (un nouveau champ d'endpoint exige un test d'intégration : 401 non-admin, rattachement au bon tenant, refus de cibler un autre tenant)
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `ApiKeyService.create_key(...)` accepte **déjà** `tenant_id: UUID | None = None` (`app/services/api_key_service.py:80`, vérifié) et le résout via `resolve_tenant(tenant_id)` (rattachement au tenant courant si absent, `:84`) → **le plumbing service existe**. `CreateKeyRequest` (`app/api/endpoints/admin.py:21`, vérifié) **ne porte PAS** de `tenant_id` (champs : `name`/`role`/`expires_at`). L'endpoint `POST /admin/keys` (`async def create_key`, `app/api/endpoints/admin.py:82`) délègue à `service.create_key(...)` (`:90`) **sans** passer de `tenant_id` → la clé hérite toujours du tenant courant de l'admin. **À CRÉER** : le champ `tenant_id` optionnel sur `CreateKeyRequest`, son threading vers `create_key(tenant_id=...)`, et la **validation d'autorisation** (un admin ne crée une clé QUE pour son propre tenant — sinon 403).

---

## TÂCHE — Sprint 175 (E4-S10) : `tenant_id` optionnel sur la création de clé admin

**Objectif** : rendre le rattachement tenant des clés API (posé au S168) **pilotable côté produit** — permettre à un admin de créer explicitement une clé pour un tenant cible (prérequis d'un onboarding multi-tenant), tout en empêchant l'escalade cross-tenant.

### Spécification
1. **Champ requête** — ajouter `tenant_id: UUID | None = None` à `CreateKeyRequest` (`admin.py:21`). Absent → comportement inchangé (clé rattachée au tenant courant de l'admin via `resolve_tenant`).
2. **Validation d'autorisation** — si `tenant_id` est fourni et **diffère** du tenant courant de l'admin (`get_current_tenant()`), répondre **403** (un admin ne provisionne que pour son propre tenant). **Trancher et documenter** : le tenant legacy peut-il provisionner pour n'importe quel tenant (super-admin) ou s'applique-t-il la même règle ? Recommandation : même règle stricte (pas d'exception legacy) tant qu'un rôle super-admin n'existe pas — plus sûr, cohérent fail-closed.
3. **Threading** — passer `tenant_id` validé à `service.create_key(tenant_id=...)` (`admin.py:90`). Le service écrit déjà la colonne `api_keys.tenant_id` et l'audit.
4. **Cohérence GUC/colonne** — si l'on autorise un `tenant_id` explicite ≠ courant un jour, rappeler l'invariant RLS (`tenant_context.py:40-45`) : `api_keys` est **HORS RLS** (S168) donc l'INSERT n'est pas bloqué par le `WITH CHECK`, mais la validation applicative (point 2) reste la seule barrière — la garder explicite.

### Tests / validation
- **Intégration** `POST /admin/keys` : (a) sans `tenant_id` → clé au tenant courant (inchangé) ; (b) `tenant_id` == tenant courant → 200, clé rattachée ; (c) `tenant_id` ≠ tenant courant → **403** (aucune clé créée) ; (d) non-admin → 401/403 (inchangé).
- **Unitaire** éventuel sur la validation si extraite en helper.
- `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Eval** : aucun prompt de skill touché → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : un admin du tenant A crée une clé en passant `tenant_id=A` → 200 + `key.tenant_id == A` ; en passant `tenant_id=B` → 403, et `GET /admin/keys` ne montre aucune clé pour B.

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 176 — E4-S11 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` exempté via `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")` (`app/middleware/auth.py:49`, vérifié) → GUC legacy par défaut ; `docs/revue-owasp-rls-2026-06.md` (existe, vérifié) documente la décision « legacy-only ». Un token de rapport portant le tenant + le threading du contexte (réutilisant `tenant_scope`, `app/db/tenant_context.py:65`, vérifié) sont **à créer**.

### Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que legacy, afin de les metrer dans `usage_events` (chemin worker non métré, déféré au S166) — et donc de les rapporter à Stripe via le S174.
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ET facturée ; complémentaire direct du S174 (qui rapporte la conso métrée, mais ne voit pas encore la conso worker).
**Référence** : le chemin worker tourne sous legacy (`app/workers/tasks.py:111` commentaire « threading tenant→worker relève d'un sprint E4 ultérieur », vérifié ; `_build_orchestrator` `:65`, vérifié) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive d'exécution par-tenant ; `watchlist` porte déjà `tenant_id` (RLS, S163-165). Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

### Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)
**Objectif** : gérer le retour de checkout Stripe sur `BillingPage` — lire `?status=success|cancel` pour afficher une confirmation et **rafraîchir le plan** affiché (le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage).
**Complexité** : Faible.
**Justification** : sans rafraîchissement, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'au prochain rechargement complet — friction produit immédiate.
**Référence** : `success_url`/`cancel_url` pointent déjà `/facturation?status=...` (`app/api/endpoints/billing.py:81-82`, vérifié) ; `BillingPage` lit `user.plan` du contexte (`frontend/src/pages/BillingPage.tsx`, créé S173) ; `AuthContext` **n'expose aucune méthode de refresh** (`useAuth` à `frontend/src/contexts/AuthContext.tsx:70`, vérifié — retourne `user`/`isAuthenticated`/`isLoading`/`login`/`logout`) → exposer un `refreshUser()` (re-`authMe()`) est **à créer**.

### Sprint 179 — E4-S13 : ligne metered au checkout (abonnement avec price metered)
**Objectif** : ajouter le **price metered** au line_items du checkout d'abonnement, pour que la souscription d'un tenant porte effectivement le price lié au billing meter ciblé par `report_usage` (S174) — sinon les metered records ne sont rattachés à aucune ligne facturable.
**Complexité** : Moyenne.
**Justification** : le S174 rapporte l'usage au meter, mais tant que l'abonnement du customer n'inclut pas le price metered, Stripe n'a rien à facturer — c'est le maillon manquant entre report et facture.
**Référence** : `create_checkout_session` ajoute aujourd'hui un seul `line_items=[{"price": price_id, "quantity": 1}]` (`app/services/stripe_service.py`, méthode `create_checkout_session`, vérifié au S172) ; le meter est ciblé par `STRIPE_METER_EVENT_NAME` (S174) mais **aucun `STRIPE_PRICE_METERED`** n'est encore défini ni ajouté au checkout — la clé `price metered` + son ajout conditionnel au line_items sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.61.0), .claude/rules/securite.md et tests-pyramide.md.
Sprint actif : 175 — E4-S10 (provisionnement de clés API par tenant). Ajouter un champ tenant_id
optionnel à CreateKeyRequest (admin.py:21), le valider (un admin ne crée une clé QUE pour son
tenant courant → 403 sinon ; trancher le cas legacy, recommandation : même règle stricte) et le
threader vers ApiKeyService.create_key(tenant_id=...) qui l'accepte déjà (api_key_service.py:80).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; pas d'eval (aucun prompt de skill touché) ;
preuve : admin tenant A, tenant_id=A → 200 clé rattachée à A ; tenant_id=B → 403, aucune clé pour B.
```
