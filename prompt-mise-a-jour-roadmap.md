# Sprint 173 — E4-S8 : page « Facturation » frontend (consommation + plan + abonnement)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.59.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (172, E4-S7) a branché **Stripe** : SDK + clés `.env`, migration `subscriptions`/`stripe_events` (HORS RLS), `StripeService` (checkout + synchro `tenants.plan` via webhooks), `POST /billing/webhook` (signature `Stripe-Signature` vérifiée AVANT traitement, idempotence atomique par `event.id`) et `POST /billing/checkout`. Le socle E4 backend est complet ; il reste à lui donner une **surface produit**. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail FRONTEND** : ce sprint est majoritairement React/TS. `cd frontend && npm test` (Vitest), `npm run typecheck` (tsc 0 erreur), `npm run lint` (ESLint 0 warning). Le proxy Vite `:5173 → :8000` permet d'exercer l'API ; pas de Docker dans le conteneur web → pas de test navigateur live (le dire, ne pas le simuler).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.59.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TS strict zéro `any`, structure pages/composants, client `frontend/src/api/` typé — central pour une page React) et `.claude/rules/variables-financieres.md` (casse `snake_case` Python ↔ `camelCase` TS pour tout champ de consommation/coût exposé — la page lit `UsageResponse`)
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `GET /usage` agrège déjà cost/tokens du tenant courant (`app/api/endpoints/usage.py:12`, S170) ; `UsageResponse`/`UsageBySkill` (`app/models/usage.py:16,6`) = forme JSON à typer côté TS ; `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`), `SkillCostPieChart` + `DailyCostTrendChart` (`frontend/src/components/`) existent et sont réutilisables ; `POST /billing/checkout` (`app/api/endpoints/billing.py:60`, S172) crée une session de checkout. **À VÉRIFIER / À CRÉER** : le plan du tenant **n'est PAS exposé au frontend** (`app/models/auth.py` n'a pas de champ `plan` ; `User` `frontend/src/types/index.ts:782-783` porte `tenant_id`/`tenant_name` mais pas `plan`) → l'afficher exige une exposition backend (champ sur `UserPublic`/`/auth/me` OU `GET /billing/subscription`) ; le client `frontend/src/api/usage.ts` **est absent** (à créer) ; aucune page `BillingPage`/client `frontend/src/api/billing.ts` (à créer) ; **aucune méthode de portail Stripe** (`StripeService` n'a que `create_checkout_session`, pas de `create_billing_portal_session`) → le bouton « Gérer l'abonnement » exige un nouvel endpoint + méthode service.

---

## TÂCHE — Sprint 173 (E4-S8) : page « Facturation » frontend

**Objectif** : donner une surface self-service au socle E4 + à Stripe (S172) — une page React qui consolide la **consommation** (`GET /usage`), le **plan courant** et un point d'entrée vers la **gestion de l'abonnement** (checkout pour souscrire, portail Stripe pour gérer).

### Spécification
1. **Exposer le plan courant** — le plan du tenant n'est pas lisible côté client. Ajouter `plan` à `UserPublic` (`app/models/auth.py`) + le résoudre dans `UserService` (déjà un JOIN `tenants` pour `tenant_name` au S169 — ajouter `t.plan`), threader aux 3 sites de construction (`/me`, login, register), et l'ajouter au type `User` (`frontend/src/types/index.ts`). **OU** créer `GET /billing/subscription` (plan + statut depuis `subscriptions`/`tenants`). **Trancher et documenter** le choix (réutiliser `/auth/me` = moins d'endpoints ; endpoint dédié = découple billing de l'authn).
2. **Portail de gestion Stripe** — `StripeService.create_billing_portal_session(tenant_id) -> str` (URL du [Billing Portal](https://stripe.com/docs/customer-management) Stripe, `asyncio.to_thread`) + endpoint `POST /billing/portal` (authentifié, résout le customer du tenant). Si le tenant n'a pas de `stripe_customer_id` → 409/404 clair. Si Stripe non configuré → 503 (cohérent avec `_service`, `billing.py:33`).
3. **Client API typé** — `frontend/src/api/usage.ts` (`getUsage(days)` → `UsageResponse` typé) + `frontend/src/api/billing.ts` (`createCheckout(plan)`, `openPortal()`), via `client.ts` (cookies/CSRF). Zéro `any` ; types miroir exacts du JSON (`snake_case` → conversion).
4. **Page `BillingPage`** (`frontend/src/pages/`, route `/facturation`) — tableau de bord : plan courant (badge), consommation du mois (total coût/tokens depuis `GET /usage`), **réutilise** `SkillCostPieChart` (ventilation `by_skill`) + `DailyCostTrendChart` (`daily_cost`), quota restant (réutilise `QuotaBanner` ou sa logique). Boutons : « Passer à Pro » (→ `createCheckout('pro')` → redirige vers l'URL Stripe) si plan `free` ; « Gérer l'abonnement » (→ `openPortal()`) si déjà abonné. Route ajoutée au router + lien de navigation.
5. **États** — chargement (skeleton), erreur (message assaini), `rag`/billing désactivé (503 → message « facturation indisponible » sans casser la page).

### Tests / validation
- **Backend** (si exposition du plan/portail) : unitaires `UserService`/`StripeService` (plan résolu ; `create_billing_portal_session` mocké ; 503/404 sans customer) + intégration endpoint(s) (`tests/api/`). `pytest` (hors e2e/evals) + `ruff` + `mypy app/` verts.
- **Frontend** (Vitest, **obligatoire par composant/page**) : `BillingPage` happy (plan free → bouton « Passer à Pro » ; plan pro → « Gérer l'abonnement »), état chargement, erreur, billing désactivé ; clients `usage.ts`/`billing.ts` (forme typée, appel correct). `npm test` + `npm run typecheck` + `npm run lint` à 0 erreur/0 warning.
- **Eval** : aucun prompt de skill touché → **pas d'eval** (le dire explicitement).
- **Preuve d'acceptation observable** : monter `BillingPage` avec un `GET /usage` mocké → le tableau affiche le total + la ventilation par skill ; plan `free` → CTA checkout, plan `pro` → CTA portail.

---

## SPRINTS SUGGÉRÉS (suite E4/E5 — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 174 — E4-S9 : facturation à l'usage métrée vers Stripe (metered records)
**Objectif** : pousser la consommation agrégée (`usage_events`) vers Stripe en **metered usage records** — la partie « facturation à l'usage » explicitement déférée au S172.
**Complexité** : Moyenne.
**Justification** : ferme la boucle de monétisation (abonnement *plus* usage réel facturé) ; le socle d'agrégation existe déjà.
**Référence** : `UsageEventService.aggregate(days)` agrège déjà cost/tokens par tenant (`app/services/usage_event_service.py:75`, vérifié) ; `StripeService` existe (`app/services/stripe_service.py`, S172, vérifié) mais **n'a aucune méthode de metered record** (à créer) ; un price `metered` Stripe + une tâche de report périodique (worker) sont **à créer**.

### Sprint 175 — E4-S10 : provisionnement de clés API par tenant (admin self-service)
**Objectif** : permettre à un admin de tenant de créer des clés rattachées à **son** tenant via un champ `tenant_id` optionnel sur `CreateKeyRequest` (aujourd'hui `create_key` hérite du tenant courant ; une clé env-admin retombe sur legacy).
**Complexité** : Faible.
**Justification** : rend le rattachement tenant des clés (S168) pilotable côté produit, prérequis d'un onboarding multi-tenant.
**Référence** : `create_key(...)` (`app/services/api_key_service.py:75`, vérifié) rattache au tenant courant ; `CreateKeyRequest` (`app/api/endpoints/admin.py:21`, vérifié) ; `POST /admin/keys` délègue à `service.create_key(...)` (`app/api/endpoints/admin.py:82,90`, vérifié) **sans** `tenant_id` explicite. L'ajout d'un champ `tenant_id` optionnel + sa validation (admin ne crée que pour son tenant) sont **à créer**.

### Sprint 176 — E4-S11 : scoping tenant du token de rapport (`/report`)
**Objectif** : faire passer les endpoints `/report` (auth-exemptés, donc sous tenant legacy par défaut) sous le contexte tenant du demandeur — risque résiduel n°2 de la revue OWASP RLS.
**Complexité** : Moyenne.
**Justification** : ferme le dernier trou d'isolation documenté — un rapport ne doit refléter que les données du tenant qui le demande.
**Référence** : `/report` exempté de l'auth middleware (`app/middleware/auth.py:49` `EXEMPT_PREFIXES = ("/telemetry", "/report", "/ws")`, vérifié) → GUC legacy par défaut ; décision « legacy-only documentée » dans `docs/revue-owasp-rls-2026-06.md` (existe, vérifié). Un token de rapport portant le tenant + le threading du contexte (réutilisant `tenant_scope`, `app/db/tenant_context.py:65`, vérifié) sont **à créer**.

### Sprint 177 — E5-S1 : threading tenant des analyses planifiées (workers métrés)
**Objectif** : faire tourner les analyses planifiées (screener/alertes/watchlist) **sous le tenant propriétaire** plutôt que legacy, afin de les metrer dans `usage_events` (chemin worker non métré, déféré au S166).
**Complexité** : Élevée.
**Justification** : ferme le dernier trou de facturation — la conso planifiée d'un tenant doit lui être imputée ; réutilise `tenant_scope` (S171).
**Référence** : le chemin worker tourne sous legacy (`app/workers/tasks.py:109-110` commentaire « threading tenant→worker relève d'un sprint E4 ultérieur », vérifié ; `_build_orchestrator` `tasks.py:63`) ; `tenant_scope` (`app/db/tenant_context.py:65`, vérifié) est la primitive d'exécution par-tenant ; `watchlist` porte déjà `tenant_id` (RLS, S163-165). Le threading du tenant propriétaire de chaque entrée watchlist vers l'orchestrateur + l'injection du `UsageEventService` au worker sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.59.0), .claude/rules/conventions-frontend.md et variables-financieres.md.
Sprint actif : 173 — E4-S8 (page « Facturation » frontend). Construire une page React /facturation
qui consolide la consommation (GET /usage, S170), le plan courant et la gestion d'abonnement Stripe.
Trancher l'exposition du plan (champ sur UserPublic/auth/me OU GET /billing/subscription — le plan
n'est PAS exposé aujourd'hui). Ajouter StripeService.create_billing_portal_session + POST /billing/portal
(bouton « Gérer l'abonnement »). Créer frontend/src/api/usage.ts + billing.ts (typés, zéro any),
BillingPage réutilisant SkillCostPieChart/DailyCostTrendChart/QuotaBanner, CTA checkout (plan free→Pro)
ou portail (déjà abonné).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; frontend Vitest + typecheck + lint 0/0 ;
preuve : BillingPage avec GET /usage mocké affiche total + ventilation by_skill + CTA selon le plan.
```
