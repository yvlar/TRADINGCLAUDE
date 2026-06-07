# Sprint 174 — E4-S9 : facturation à l'usage métrée vers Stripe (metered usage records)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.60.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (173, E4-S8) a livré la **page Facturation** : `plan` exposé via `/auth/me`, `StripeService.create_billing_portal_session` + `POST /billing/portal`, clients `usage.ts`/`billing.ts`, page React `/facturation` (consommation `GET /usage` + badge plan + CTA checkout/portail). L'abonnement (`free`/`pro`) est désormais souscriptible ET gérable côté produit ; reste à **facturer la consommation réelle** au-delà de l'abonnement forfaitaire. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND** : ce sprint est worker + service Stripe (+ éventuelle migration de suivi). `pytest` (hors e2e/evals) + `ruff` + `mypy app/`. Pas de Docker dans le conteneur web → la validation Stripe réelle est mockée ; le DIRE, ne pas la simuler. **Le SDK `stripe` et `mypy`/`alembic` ne sont pas préinstallés dans le venv du conteneur web** — si une commande échoue sur un import manquant, `bash scripts/setup-web-session.sh` puis `.venv/bin/pip install stripe mypy alembic` (déjà dans `requirements.txt`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.60.0)
2. `.claude/rules/gotchas-operationnels.md` (patterns worker/service `app/workers/**` — central pour une tâche Celery périodique de report) et `.claude/rules/securite.md` (clé Stripe via `.env`, jamais loggée — le report Stripe appelle le SDK avec `api_key=`)
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `UsageEventService.aggregate(days)` agrège déjà `cost_usd`/tokens par tenant (`app/services/usage_event_service.py:75`, S170) et `record(...)` est l'écriture append-only (`:43`, S166) ; `StripeService` existe (`app/services/stripe_service.py:58`) avec checkout (`:88`) et portal (`:114`) mais **AUCUNE méthode de metered record** (vérifié — pas de `usage_record`/`metered` dans le fichier) → à créer. Le chemin worker tourne **sous le tenant legacy** (`app/workers/tasks.py:109-110`, commentaire « threading tenant→worker relève d'un sprint E4 ultérieur ») ; `_build_orchestrator` (`:63`) est le constructeur partagé des tâches. **À VÉRIFIER / À CRÉER** : un **price `metered` Stripe** (nouvelle clé `.env` `STRIPE_PRICE_METERED` + `.env.example` factice) ; une **tâche worker périodique** de report (clonée sur `run_retention_purge`/`run_scheduled_screener`, enregistrée dans `beat_schedule`) ; un mécanisme **anti-double-report** (idempotence : la fenêtre déjà rapportée ne doit pas l'être deux fois — soit une table de suivi `usage_report_log`, soit un horodatage `reported_at`, à trancher et documenter).

---

## TÂCHE — Sprint 174 (E4-S9) : metered usage records vers Stripe

**Objectif** : fermer la boucle de monétisation — pousser la consommation agrégée (`usage_events`) vers Stripe en **metered usage records**, pour facturer l'usage réel *en plus* de l'abonnement forfaitaire (partie « facturation à l'usage » explicitement déférée au S172).

### Spécification
1. **Price metered Stripe** — nouvelle clé `STRIPE_PRICE_METERED` (`.env` + `.env.example` factice). La facturation à l'usage est **désactivée** (no-op loggé, jamais d'erreur) si la clé ou Stripe ne sont pas configurés (cohérent avec `is_configured`, `stripe_service.py:73`).
2. **Méthode service** — `StripeService.report_usage(subscription_item_id, quantity, timestamp) -> None` (ou signature équivalente) : appelle l'API Stripe metered usage records via `asyncio.to_thread` (boucle non bloquée, clé par appel `api_key=`, aucune clé loggée). **Vérifier l'API exacte du SDK installé** (`stripe.billing.MeterEvent` vs `SubscriptionItem.create_usage_record` selon la version `>=15`) et documenter le choix — ne pas supposer.
3. **Idempotence du report** — **trancher et documenter** : une fenêtre de consommation ne doit jamais être rapportée deux fois (sinon double facturation). Soit une table `usage_report_log` (tenant + fenêtre + `reported_at`), soit un curseur de dernière fenêtre rapportée par tenant. Migration Alembic chaînée après `0009` si table (décision RLS à trancher comme `subscriptions` S172 — probablement HORS RLS, report tourne sous legacy).
4. **Tâche worker périodique** — `run_usage_reporting` (clonée sur `run_retention_purge`, `tasks.py`) : pour chaque tenant abonné (`subscriptions.status='active'` avec un `stripe_subscription_id`), agrège la consommation de la fenêtre non encore rapportée et la pousse en metered record. **Best-effort par tenant** (un échec n'avorte pas les autres) ; enregistrée dans `beat_schedule` (heure creuse, ex. quotidien). Aucune clé Stripe loggée.
5. **Résolution de l'item d'abonnement** — le metered record cible un `subscription_item` (price metered) ; résoudre l'item depuis `subscriptions.stripe_subscription_id` (lookup Stripe ou colonne persistée — trancher).

### Tests / validation
- **Unitaires** `StripeService.report_usage` (SDK mocké : quantity/timestamp transmis ; no-op si non configuré ; aucune clé loggée) + idempotence (fenêtre déjà rapportée → skip).
- **Unitaires/intégration** worker `run_usage_reporting` (itération tenants abonnés, best-effort un échec n'interrompt pas les autres, `beat_schedule` incrémenté, fenêtre rapportée marquée).
- Si migration : forme (`tests/test_alembic_*`) — chaînage après `0009`, colonnes, downgrade ; décision RLS documentée.
- `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Eval** : aucun prompt de skill touché → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : worker exécuté avec `UsageEventService.aggregate` + SDK Stripe mockés → un tenant abonné consommant N unités produit **un** metered record de quantité N ; une 2ᵉ exécution sur la même fenêtre **ne re-rapporte pas** (idempotence).

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 175 — E4-S10 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via un champ `tenant_id` optionnel sur `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (S168) pilotable côté produit, prérequis d'un onboarding multi-tenant.
**Référence** : `create_key(...)` (`app/services/api_key_service.py:75`, vérifié) rattache au tenant courant ; `CreateKeyRequest` (`app/api/endpoints/admin.py:21`, vérifié) ; `POST /admin/keys` délègue à `service.create_key(...)` (`app/api/endpoints/admin.py:82,90`, vérifié) **sans** `tenant_id` explicite. L'ajout d'un champ `tenant_id` optionnel + sa validation (admin ne crée que pour son tenant) sont **à créer**.

### Sprint 176 — E4-S11 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` exempté via `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")` (`app/middleware/auth.py:49`, vérifié) → GUC legacy par défaut ; décision « legacy-only documentée » dans `docs/revue-owasp-rls-2026-06.md` (existe, vérifié). Un token de rapport portant le tenant + le threading du contexte (réutilisant `tenant_scope`, `app/db/tenant_context.py:65`, vérifié) sont **à créer**.

### Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que legacy, afin de les metrer dans `usage_events` (chemin worker non métré, déféré au S166).
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ; complémentaire au S174 (qui rapporte la conso métrée à Stripe).
**Référence** : le chemin worker tourne sous legacy (`app/workers/tasks.py:109-110` commentaire « threading tenant→worker relève d'un sprint E4 ultérieur », vérifié ; `_build_orchestrator` `:63`, vérifié) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive d'exécution par-tenant ; `watchlist` porte déjà `tenant_id` (RLS, S163-165). Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

### Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)
**Objectif** : gérer le retour de checkout Stripe sur `BillingPage` — lire `?status=success|cancel` (params du `success_url`/`cancel_url`) pour afficher une confirmation et **rafraîchir le plan** affiché (le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage).
**Complexité** : Faible.
**Justification** : sans rafraîchissement, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'au prochain rechargement complet — friction produit immédiate.
**Référence** : `success_url`/`cancel_url` pointent déjà `/facturation?status=...` (`app/api/endpoints/billing.py:81`, vérifié, corrigé au S173) ; `BillingPage` lit `user.plan` du contexte (`frontend/src/pages/BillingPage.tsx`, créé S173) ; `AuthContext` **n'expose aucune méthode de refresh** (`frontend/src/contexts/AuthContext.tsx` — `useAuth` ne retourne que `user`/`isAuthenticated`/`isLoading`/`login`/`logout`, vérifié) → exposer un `refreshUser()` (re-`authMe()`) est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.60.0), .claude/rules/gotchas-operationnels.md et securite.md.
Sprint actif : 174 — E4-S9 (facturation à l'usage métrée vers Stripe). Pousser la consommation
agrégée (usage_events) en metered usage records Stripe : nouvelle clé STRIPE_PRICE_METERED,
StripeService.report_usage (SDK via asyncio.to_thread, vérifier l'API du SDK installé >=15),
idempotence anti-double-report (table usage_report_log OU curseur par tenant — trancher),
tâche worker run_usage_reporting (clonée sur run_retention_purge, best-effort par tenant abonné,
beat_schedule). Désactivé proprement (no-op loggé) si Stripe/price non configuré.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; pas d'eval (aucun prompt de skill touché) ;
preuve : worker avec aggregate + SDK mockés → 1 metered record de quantité N, 2ᵉ run même
fenêtre → pas de re-report (idempotence). Note : stripe/mypy/alembic non préinstallés dans le
venv web → pip install si import manquant.
```
