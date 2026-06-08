# Sprint 178 — E4-S12 : retour de checkout sur la page Facturation (UX)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.64.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (177, E5-S1) a metré la **re-analyse watchlist planifiée** sous le tenant propriétaire : `run_watchlist_analysis` itère désormais `tenants` (hors RLS) puis ré-analyse chaque watchlist sous `tenant_scope(tenant_id)` avec un orchestrateur portant un `UsageEventService` → la conso planifiée est imputée au bon tenant dans `usage_events` (facturable via `run_usage_reporting`), jamais legacy. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail FRONTEND (+ un petit ajout backend nul)** : ce sprint touche surtout `frontend/src/` (la page `BillingPage` et le contexte d'auth). **Aucune migration, aucun endpoint backend nouveau.** GATES : `cd frontend && npm test` (Vitest) + `npm run typecheck` (0 erreur) + ESLint (0 warning) ; backend `pytest` (hors e2e/evals) seulement si un fichier `app/**` est touché. ⚠️ Le venv web peut manquer des deps backend (`stripe`, `alembic`, `sqlalchemy`, `mako`, `mypy`) → `bash scripts/setup-web-session.sh` ou `.venv/bin/pip install -r requirements.txt` si un import échoue.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.64.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TypeScript strict, structure pages/composants, zéro `any`) et `.claude/rules/tests-pyramide.md` (test composant obligatoire : happy path + cas d'erreur). Backend non touché → pas besoin de charger les règles `app/**`.
3. **Code de référence à vérifier en début de session (anti-hallucination)** : `success_url`/`cancel_url` du checkout pointent **déjà** `/facturation?status=success|cancel` (`app/api/endpoints/billing.py:81-82`, vérifié) — donc le retour de Stripe atterrit sur la bonne route, il reste à **lire le query param**. `BillingPage` lit le plan via `user?.plan ?? 'free'` (`frontend/src/pages/BillingPage.tsx:33`, vérifié) ; ce `user` vient du `AuthContext` monté une seule fois (`authMe()` au montage, `frontend/src/contexts/AuthContext.tsx:24`, vérifié). **`useAuth` n'expose AUCUNE méthode de refresh** (`AuthContext.tsx:7-11` → `user`/`isAuthenticated`/`login`/`logout` seulement, vérifié) → exposer un `refreshUser()` (re-`authMe()` + `setUser`) est **À CRÉER**.

---

## TÂCHE — Sprint 178 (E4-S12) : gérer le retour de checkout Stripe sur `BillingPage`

**Objectif** : après un retour de checkout Stripe, `BillingPage` doit (1) afficher une confirmation selon `?status=success|cancel`, et (2) **rafraîchir le plan affiché** — car le webhook met `tenants.plan` à jour de façon asynchrone, mais `user.plan` du contexte est figé au montage. Sans cela, un tenant qui vient de passer à `pro` voit encore le CTA « Passer à Pro » jusqu'à un rechargement complet (friction produit immédiate).

### Spécification
1. **`refreshUser()` dans `AuthContext`** — exposer une méthode qui re-appelle `authMe()` et met à jour `user` (parité avec le `setUser` du `login`). L'ajouter au type `AuthContextValue` (`AuthContext.tsx:7-11`) et à la valeur du provider. Gérer l'échec (token expiré → ne pas casser, garder l'état courant ou déconnecter selon le comportement existant de `authMe` au montage).
2. **Lecture du query param sur `BillingPage`** — lire `?status` (via `useSearchParams` de react-router, déjà une dépendance). `success` → bandeau de confirmation (« Abonnement activé ») + appel `refreshUser()` (une seule fois, au montage si `status===success`) pour repiloter le CTA ; `cancel` → message neutre (« Paiement annulé »). Nettoyer le param de l'URL après lecture (éviter un re-trigger au refresh manuel) ou garder un garde-fou pour ne `refreshUser()` qu'une fois.
3. **Pas de régression** : sans `?status`, la page se comporte exactement comme avant.

### Tests / validation
- **Composant Vitest `BillingPage`** : `?status=success` → bandeau de succès affiché **et** `refreshUser` appelé une fois ; `?status=cancel` → message d'annulation, `refreshUser` non appelé ; sans param → aucun bandeau, comportement inchangé ; après `refreshUser` retournant un plan `pro`, le CTA bascule de checkout → portail (mock du contexte). Mock de `useAuth`/`useSearchParams`.
- **Test `AuthContext`** (ou via un composant de test) : `refreshUser()` re-appelle `authMe` et met à jour `user`.
- `cd frontend && npm test` + `npm run typecheck` (0) + ESLint (0/0). **Backend non touché** → pas d'eval, pas de `pytest` requis (le dire).
- **Preuve d'acceptation observable** : monté avec `useSearchParams` = `?status=success` et `useAuth` mocké, `BillingPage` affiche le bandeau de succès et déclenche `refreshUser`; quand le mock renvoie ensuite `plan='pro'`, le CTA affiché est `billing-portal-btn` (plus `billing-checkout-btn`).

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 179 — E5-S2 : facturation à l'usage côté UI (compteur de report)
**Objectif** : exposer sur `/facturation` la consommation métrée déjà rapportée à Stripe vs en attente (curseur `subscriptions.usage_reported_through` + `usage_events` non encore rapportés).
**Complexité** : Moyenne.
**Justification** : rend la facturation à l'usage (S174) transparente pour le client — « X unités facturées, Y en attente du prochain cycle ».
**Référence** : le curseur `usage_reported_through` est lu/avancé par le worker (`app/workers/tasks.py:910,924,947`, vérifié) ; `GET /usage` agrège déjà `usage_events` (`app/api/endpoints/usage.py:29` → `service.aggregate`, vérifié) ; un endpoint exposant l'état du curseur + son rendu UI sont **à créer**.

### Sprint 180 — E5-S3 : audit log côté UI (page Admin)
**Objectif** : exposer le journal d'audit (`GET /admin/audit-log`, S160) dans la page Admin — table filtrable des mutations métier (watchlist, annotation, clé API), enrichie du `tenant_id` effectif (S175).
**Complexité** : Faible.
**Justification** : la conformité (Loi 25) exige une traçabilité consultable ; le backend existe depuis S160 mais n'a aucune surface UI.
**Référence** : `GET /admin/audit-log` existe (`app/api/endpoints/admin.py:159`, route `list_audit_log` `:163`, vérifié) ; le composant React + le client typé sont **à créer**.

### Sprint 181 — E5-S4 : metering du screener planifié + alertes composites (reliquat S177)
**Objectif** : étendre le threading tenant + metering (S177) aux deux chemins worker encore sous legacy — `run_scheduled_screener` et `run_composite_alert_check` — qui lisent la watchlist via `WatchlistService.list_entries()` sous le tenant legacy.
**Complexité** : Moyenne.
**Justification** : ferme le dernier reliquat de conso planifiée non facturée ; complète l'objectif E5-S1.
**Référence** : `_execute_scheduled_screener` (`app/workers/tasks.py:517`) et `_execute_composite_alert_check` (`app/workers/tasks.py:423`) appellent `wl_service.list_entries()` (`:530`, `:363`, vérifié) sans `tenant_scope` ; `_build_orchestrator(with_metering=True)` existe déjà (créé S177, `app/workers/tasks.py`, vérifié) — la restructuration d'itération tenant par chemin est **à créer**.

### Sprint 182 — Ops : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS` (risque résiduel n°1)
**Objectif** : matérialiser le rôle de connexion applicatif `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-propriétaire) pour les pools API + workers, et réserver `copilote` (superuser) aux seules migrations Alembic.
**Complexité** : Moyenne.
**Justification** : **sans ce rôle, la RLS est inerte en production** (un `BYPASSRLS`/`SUPERUSER` court-circuite toute policy) — 1ᵉʳ des deux pré-requis hors-code documentés ; le 2ᵉ (scoping `/report`) est clos par le S176.
**Référence** : exigence documentée dans `docs/revue-owasp-rls-2026-06.md` (vérifié, fichier présent) ; le rôle `copilote` par défaut est superuser (`POSTGRES_URL`/`DATABASE_URL` `.env.example:21`, vérifié) → le provisioning d'un rôle séparé (`infra/postgres/`) + le câblage des pools/workers sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur React/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md
(v10.64.0), .claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 178 — E4-S12 (retour de checkout sur la page Facturation). Le checkout Stripe revient
déjà sur /facturation?status=success|cancel (billing.py:81-82) mais BillingPage n'en fait rien et
n'affiche pas le bon CTA après upgrade : user.plan (BillingPage.tsx:33) vient d'un AuthContext figé au
montage (authMe à AuthContext.tsx:24) et useAuth n'expose AUCUN refresh (AuthContext.tsx:7-11).
À FAIRE : exposer refreshUser() (re-authMe + setUser) dans AuthContext ; sur BillingPage lire
?status (useSearchParams) → bandeau succès/annulation + refreshUser() une fois si success → CTA
repiloté checkout↔portail. Tests composant Vitest (success→bandeau+refreshUser, cancel→message,
sans param→inchangé, plan pro→portail). Backend non touché.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : npm test + npm run typecheck (0) + ESLint (0/0) ; pas d'eval (frontend) ;
preuve : ?status=success → bandeau + refreshUser appelé, et un mock renvoyant plan='pro' bascule le
CTA vers billing-portal-btn.
```
