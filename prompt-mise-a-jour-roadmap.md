# Sprint 179 — E5-S2 : facturation à l'usage côté UI (compteur de report)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.65.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (178, E4-S12) a câblé le **retour de checkout Stripe** sur `BillingPage` : `AuthContext` expose un `refreshUser()` (re-`authMe()` + `setUser`), et `BillingPage` lit `?status=success|cancel` → bandeau de confirmation + `refreshUser()` une seule fois (garde-fou `useRef`) pour repiloter le CTA checkout↔portail dès la synchro `tenants.plan`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail MIXTE backend + frontend** : ce sprint ajoute **un endpoint de lecture** (état du curseur de report Stripe) et **un rendu UI** sur `/facturation`. GATES : backend `pytest` (hors e2e/evals) + `ruff` + `mypy app/` ; frontend `cd frontend && npm test` (Vitest) + `npm run typecheck` (0) + ESLint (0/0). ⚠️ Le venv web peut manquer des deps backend (`stripe`, `alembic`, `sqlalchemy`, `mako`, `mypy`) → `bash scripts/setup-web-session.sh` ou `.venv/bin/pip install -r requirements.txt` si un import échoue. ⚠️ `frontend/node_modules` peut être absent au démarrage → `cd frontend && npm ci`.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.65.0)
2. `.claude/rules/api-architecture.md` (nouvel endpoint FastAPI : modèle `cost_usd`, async/await, lifespan) **et** `.claude/rules/conventions-frontend.md` (React 18, TS strict, structure pages/composants, zéro `any`) **et** `.claude/rules/tests-pyramide.md` (test d'intégration obligatoire pour un nouvel endpoint ; test composant happy path + erreur).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - Le curseur `subscriptions.usage_reported_through` est **lu et avancé par le worker** `run_usage_reporting` (`app/workers/tasks.py:906` SELECT, `:920` lecture `since`, `:943` UPDATE — vérifié) ; il n'est exposé par **aucun endpoint** → l'endpoint de lecture est **À CRÉER**.
   - `UsageEventService.count_events_in_window(since, until)` **existe déjà** (Sprint 174, contrat append-only `{record, aggregate, count_events_in_window}` — `COUNT(*)` des `usage_events` sur `(since, until]`, isolation RLS, aucun `WHERE tenant_id`) — c'est lui qui comptera les événements **non encore rapportés** (`(usage_reported_through, now]`). Vérifier sa signature dans `app/services/usage_event_service.py` avant de l'appeler.
   - `GET /usage` agrège déjà `usage_events` pour le tenant courant (`app/api/endpoints/usage.py:29` → `service.aggregate(days)`, authentifié, RLS — vérifié) ; le client typé frontend est `getUsage()` (`frontend/src/api/usage.ts:5`, vérifié). Le nouvel endpoint suit le **même patron** (auth `_get_current_user`, RLS, response_model Pydantic).
   - **Décision RLS du curseur** : la table `subscriptions` est **HORS RLS** (Sprint 172 — le webhook auth-exempté tourne sous legacy). L'endpoint de lecture devra donc **scoper explicitement** au tenant courant (`WHERE tenant_id = get_current_tenant()` applicatif, **pas** la RLS) — contrairement à `usage_events` qui est sous RLS. **Ne pas supposer** que la RLS protège `subscriptions` : la vérifier (`grep -n "subscriptions" alembic/versions/0009_stripe_billing.py` pour confirmer l'absence de `ENABLE ROW LEVEL SECURITY`) avant d'écrire la requête.

---

## TÂCHE — Sprint 179 (E5-S2) : exposer la consommation rapportée vs en attente sur `/facturation`

**Objectif** : rendre la facturation à l'usage (S174) **transparente pour le client** — sur `/facturation`, afficher « X unités déjà rapportées à Stripe (jusqu'au <date>), Y unités en attente du prochain cycle ». Aujourd'hui le curseur `usage_reported_through` n'est visible que côté worker ; le client ne sait pas ce qui a été facturé ni ce qui reste à facturer.

### Spécification

1. **Endpoint backend `GET /usage/reporting`** (ou `GET /billing/usage-report` — choisir et justifier) — authentifié (`_get_current_user`, 401 sinon), retourne pour le **tenant courant** :
   - `reported_through: datetime | None` — valeur de `subscriptions.usage_reported_through` (None si jamais rapporté ou pas d'abonnement).
   - `pending_events: int` — `count_events_in_window(reported_through, now())` (les `usage_events` non encore poussés à Stripe). Si `reported_through` est None → tout l'historique (cohérent avec le contrat `since=None` du service).
   - **Lecture du curseur scopée applicativement** au tenant courant (`subscriptions` HORS RLS — voir anti-hallucination) ; le `count_events_in_window` reste sous RLS (poser/vérifier le contexte tenant). Réutiliser le `StripeService`/un service `subscriptions` existant plutôt qu'une requête inline si un accès lecture existe déjà (vérifier `app/services/stripe_service.py`).
   - **503** si la facturation Stripe n'est pas configurée (parité avec `/billing/checkout`/`/billing/portal`), ou réponse neutre `reported_through=None, pending_events=<total>` — trancher et documenter.
2. **Client typé + rendu UI** — `frontend/src/api/billing.ts` (ou `usage.ts`) : fonction typée appelant le nouvel endpoint, type dans `frontend/src/types/index.ts` (zéro `any`). Sur `BillingPage`, une carte/section « Facturation à l'usage » : compteur `pending_events` + date `reported_through` (format `fr-CA`), `data-testid` dédiés. États chargement (skeleton) / erreur / facturation désactivée (503 → message neutre sans casser la page, comme l'existant).
3. **Pas de régression** : la page existante (plan, CTA, consommation 30 j, retour de checkout S178) se comporte exactement comme avant.

### Tests / validation
- **Backend (intégration obligatoire, `tests/api/`)** : nouvel endpoint → 401 sans session ; tenant courant avec curseur posé → `reported_through` + `pending_events` corrects (mock du service / pool) ; sans abonnement → None + total ; 503 si Stripe non configuré (si retenu). Patch des appels Stripe/DB selon `tests-pyramide.md`.
- **Frontend (composant Vitest `BillingPage`)** : section « à l'usage » rendue avec `pending_events`/`reported_through` mockés ; état chargement ; état erreur ; 503 → message neutre. Mock du nouveau client + `useAuth`/`useSearchParams` (déjà mockés dans `BillingPage.test.tsx`).
- `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff` + `mypy app/` ; `cd frontend && npm test` + `npm run typecheck` (0) + ESLint (0/0). **Pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — endpoint de lecture + UI) → le dire.
- **Preuve d'acceptation observable** : appeler le nouvel endpoint pour un tenant ayant N `usage_events` dont K déjà rapportés (`usage_reported_through` posé entre les deux) → `pending_events == N-K` ; la `BillingPage` montée avec ce mock affiche « K rapportées / N-K en attente ».

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 180 — E5-S3 : audit log côté UI (page Admin)
**Objectif** : exposer le journal d'audit (`GET /admin/audit-log`, S160) dans la page Admin — table filtrable des mutations métier (watchlist, annotation, clé API), enrichie du `tenant_id` effectif (S175).
**Complexité** : Faible.
**Justification** : la conformité (Loi 25) exige une traçabilité consultable ; le backend existe depuis S160 mais n'a aucune surface UI.
**Référence** : `GET /admin/audit-log` existe (`app/api/endpoints/admin.py:159` route `/audit-log`, handler `list_audit_log` `:163`, vérifié) ; le composant React + le client typé sont **à créer**.

### Sprint 181 — E5-S4 : metering du screener planifié + alertes composites (reliquat S177)
**Objectif** : étendre le threading tenant + metering (S177) aux deux chemins worker encore sous legacy — `run_scheduled_screener` et `run_composite_alert_check` — qui lisent la watchlist via `WatchlistService.list_entries()` sous le tenant legacy.
**Complexité** : Moyenne.
**Justification** : ferme le dernier reliquat de conso planifiée non facturée ; complète l'objectif E5-S1.
**Référence** : `_execute_scheduled_screener` (`app/workers/tasks.py:513`) et `_execute_composite_alert_check` (`app/workers/tasks.py:419`) appellent `wl_service.list_entries()` (`:526`, `:359`, vérifié) sans `tenant_scope` ; `_build_orchestrator(*, with_metering=True)` existe déjà (S177, `app/workers/tasks.py:65`, vérifié) — la restructuration d'itération tenant par chemin est **à créer**.

### Sprint 182 — Ops : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS` (risque résiduel n°1)
**Objectif** : matérialiser le rôle de connexion applicatif `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-propriétaire) pour les pools API + workers, et réserver `copilote` (superuser) aux seules migrations Alembic.
**Complexité** : Moyenne.
**Justification** : **sans ce rôle, la RLS est inerte en production** (un `BYPASSRLS`/`SUPERUSER` court-circuite toute policy) — 1ᵉʳ des deux pré-requis hors-code documentés ; le 2ᵉ (scoping `/report`) est clos par le S176.
**Référence** : exigence documentée dans `docs/revue-owasp-rls-2026-06.md` (vérifié, fichier présent) ; le rôle `copilote` par défaut est superuser (`DATABASE_URL` `.env.example:21`, vérifié) → le provisioning d'un rôle séparé (`infra/postgres/`) + le câblage des pools/workers sont **à créer**.

### Sprint 183 — E5-S5 : webhook de plan → invalidation live du CTA (push)
**Objectif** : remplacer le `refreshUser()` ponctuel au retour de checkout (S178) par une invalidation poussée (WebSocket Dashboard existant ou polling court) pour que le plan se mette à jour même si le webhook Stripe arrive **après** le retour sur `/facturation`.
**Complexité** : Moyenne.
**Justification** : S178 resync une seule fois au montage ; si le webhook met `tenants.plan` à jour quelques secondes plus tard, le CTA reste périmé jusqu'au prochain `authMe()`. Fermer cette fenêtre rend l'upgrade instantané.
**Référence** : `refreshUser()` existe (`frontend/src/contexts/AuthContext.tsx`, créé S178, vérifié) ; le canal WebSocket live du Dashboard (`frontend/src/api/ws.ts`, à vérifier) et un signal serveur de changement de plan sont **à créer / à vérifier**.

---

## Template de démarrage

```
Tu es un développeur Python/React senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.65.0),
.claude/rules/api-architecture.md, conventions-frontend.md et tests-pyramide.md.
Sprint actif : 179 — E5-S2 (facturation à l'usage côté UI). Le curseur subscriptions.usage_reported_through
est lu/avancé par le worker run_usage_reporting (tasks.py:906/920/943) mais exposé par AUCUN endpoint ;
UsageEventService.count_events_in_window(since, until) existe déjà (S174) ; subscriptions est HORS RLS
(scoper le curseur applicativement, pas via RLS — vérifier 0009_stripe_billing.py).
À FAIRE : endpoint GET authentifié retournant {reported_through, pending_events=count_events_in_window(
reported_through, now)} scopé au tenant courant ; client typé + section UI « à l'usage » sur BillingPage
(compteur + date, états chargement/erreur/503). Tests : intégration endpoint (401/curseur/sans abo/503) +
composant Vitest BillingPage. Backend + frontend touchés, pas d'eval.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff + mypy app/ ; npm test + npm run typecheck (0) + ESLint (0/0).
Preuve : N usage_events dont K rapportés → endpoint renvoie pending_events == N-K ; BillingPage l'affiche.
```
