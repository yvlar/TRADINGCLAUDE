# Sprint 183 — E5-S5 : webhook de plan → invalidation live du CTA (push)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.69.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (182, Ops) a câblé les pools API + workers sur un rôle de connexion `app_runtime` (`NOSUPERUSER`/`NOBYPASSRLS`/non-propriétaire) via `APP_DATABASE_URL` → la **RLS multi-tenant est désormais active en prod** (risque résiduel OWASP n°1 clos) ; `DATABASE_URL`/`copilote` reste réservé aux migrations Alembic. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail FRONTEND dominant** (page Facturation + contexte d'auth + canal WS), avec **un petit signal serveur** à émettre/diffuser. GATES : `cd frontend && npm test` (Vitest) + `npm run typecheck` (`tsc --noEmit` 0 erreur) + ESLint (0/0) ; côté backend si touché `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps backend → `.venv/bin/pip install -r requirements.txt` si un import échoue. **Pas de Docker/PG/navigateur live** dans le conteneur web → la diffusion WS de bout en bout se prouve par tests (composant + unitaire du canal), pas par un essai navigateur.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.69.0)
2. `.claude/rules/conventions-frontend.md` (React 18 / TS strict / structure pages-composants) **et** `.claude/rules/tests-pyramide.md` (test composant happy-path + erreur, `vi.mock`).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **Le problème** : au retour de checkout (S178), `BillingPage` appelle `refreshUser()` **une seule fois** au montage (`frontend/src/pages/BillingPage.tsx:39,57`, vérifié — `void refreshUser()` sur `status==='success'`). Si le webhook Stripe met `tenants.plan` à jour **après** ce retour, le CTA reste périmé (« Passer à Pro ») jusqu'au prochain `authMe()`. `refreshUser()` existe et re-appelle `authMe()` (`frontend/src/contexts/AuthContext.tsx:48`, interface `:12`, vérifié).
   - **Le canal existant** : `frontend/src/api/ws.ts` expose `useMetrics()` qui ouvre une `WebSocket` (`:23`/`:32`, vérifié présent) pour le Dashboard live → **patron de hook WS réutilisable**. Son **extension à un signal de changement de plan** (côté serveur : émettre ; côté client : un hook qui invalide/rafraîchit le user) est **à créer**.
   - **À TRANCHER et documenter dans le bloc ROADMAP** : (a) **push WebSocket** (réutiliser le canal `ws.ts`, le serveur pousse un événement `plan_changed` au tenant depuis le handler webhook `app/services/stripe_service.py` `handle_event`) **vs** (b) **polling court** côté `BillingPage` (re-`refreshUser()` toutes ~3 s pendant ~30 s après un retour `?status=success`, sans backend). Le polling est **sans backend** (plus simple, borné) ; le push est **instantané** mais demande un canal serveur→client ciblé par tenant. Choisir en fonction du coût/bénéfice et de l'infra WS réellement disponible (vérifier comment le serveur émet aujourd'hui sur le WS Dashboard avant de promettre un push).

---

## TÂCHE — Sprint 183 : invalidation live du plan après upgrade

**Objectif** : fermer la fenêtre où, après un checkout réussi, le CTA de `/facturation` reste périmé parce que le webhook Stripe arrive **après** le `refreshUser()` ponctuel du retour (S178). Le plan affiché doit se mettre à jour **sans rechargement** dès que `tenants.plan` change.

### Spécification

1. **Mécanisme de rafraîchissement répété/poussé** (selon la décision tranchée) : soit un **polling court borné** côté `BillingPage` (re-`refreshUser()` à intervalle après `?status=success`, arrêt dès bascule `plan==='pro'` ou après un plafond de temps), soit un **hook WS** (`usesX`) qui écoute un événement serveur `plan_changed` et déclenche `refreshUser()`. **Pas de boucle infinie** : borne de temps/itérations explicite, nettoyage de l'`interval`/de la socket au démontage.
2. **Bascule du CTA** : dès que `user.plan` passe à `pro`, le CTA `billing-checkout-btn` → `billing-portal-btn` (comportement déjà éprouvé S178 — vérifier qu'il dérive bien de `user.plan`).
3. **Zéro régression** : sans `?status=success`, comportement strictement inchangé ; le `refreshUser()` write-once de S178 (garde `useRef`) reste correct.
4. **(Si option push)** côté backend : émettre un signal `plan_changed` ciblé au tenant depuis `StripeService.handle_event` après la synchro de `tenants.plan`, **best-effort** (un échec d'émission n'avorte jamais le traitement du webhook, déjà transactionnel). Réutiliser l'infra WS du Dashboard ; ne PAS introduire un second système temps-réel.

### Tests / validation
- **Composant** (`BillingPage.test.tsx`) : après `?status=success`, un changement simulé de `user.plan` (`free`→`pro`) fait basculer le CTA **sans rechargement** ; le mécanisme s'arrête (pas de polling après bascule / socket fermée au démontage) ; sans `?status` → aucun rafraîchissement répété. Tests **non-vacuous** (le mock de plan doit réellement changer entre deux ticks).
- **(Si push)** unitaire du hook/canal WS (ouverture, réception d'un message `plan_changed`, déclenchement de `refreshUser`, nettoyage au démontage) + backend : test d'émission best-effort depuis `handle_event` (échec d'émission → webhook quand même `200`).
- Gates : Vitest + `tsc --noEmit` + ESLint (0/0) ; backend si touché : `pytest` + `ruff` + `mypy`. **Pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — UI + signal temps-réel).
- **Preuve d'acceptation observable** : `BillingPage` montée avec `?status=success` et un `useAuth` dont `plan` bascule `free→pro` après le 1ᵉʳ tick → le CTA passe de checkout à portail **sans `window.location.reload`**, et le mécanisme de rafraîchissement est arrêté/nettoyé.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 184 — E5-S6 : badge de plan + quota restant dans le header
**Objectif** : exposer en continu (header global) le plan courant et le quota d'analyses restant du mois.
**Complexité** : Faible.
**Justification** : rend la consommation visible hors de `/facturation` — incite à l'upgrade au point d'usage.
**Référence** : `user.plan` exposé par `GET /auth/me` (S173, vérifié dans `ROADMAP.md` « État courant ») ; `QuotaService` existe (`app/services/quota_service.py:67`, `max_analyses_per_month` `:44`, borne dure `check()` `:105`, vérifié) mais **n'expose aucun endpoint de lecture du compteur restant** → un `GET /quota` (ou champ sur `/usage`) est **à créer**, ainsi que le composant header.

### Sprint 185 — E5-S7 : threading tenant à travers la frontière Celery (`run_full_analysis`)
**Objectif** : faire passer le `tenant_id` à travers le `.delay()` Celery pour que `run_full_analysis` (déclenché par une alerte prix) tourne sous le tenant propriétaire et soit métré — dernier chemin d'analyse encore sous legacy.
**Complexité** : Élevée.
**Justification** : le ContextVar ne traverse pas le broker → le passage de tenant à travers la sérialisation Celery est un sujet distinct des sprints worker planifiés (qui partagent un seul process async).
**Référence** : `run_full_analysis` défini (`app/workers/tasks.py:143`, vérifié) et déclenché via `.delay()` (`tasks.py:301`, vérifié) reste sous legacy ; la propagation du `tenant_id` dans l'argument de tâche + sa restauration via `tenant_scope` côté worker sont **à créer**.

### Sprint 186 — Ops : durcissement du provisioning DB (propriété des objets + revoke PUBLIC)
**Objectif** : compléter S182 en garantissant que `app_runtime` n'est **propriétaire** d'aucune table (sinon il pourrait `ALTER … DISABLE ROW LEVEL SECURITY`) et en révoquant les privilèges `PUBLIC` par défaut sur le schéma.
**Complexité** : Moyenne.
**Justification** : `NOSUPERUSER`/`NOBYPASSRLS` ne suffit pas si le rôle runtime **possède** les tables — un propriétaire peut désactiver `FORCE ROW LEVEL SECURITY`. Non-propriété explicitement exigée par `docs/revue-owasp-rls-2026-06.md` §2.4 (vérifié).
**Référence** : la propriété actuelle des tables revient à `copilote` (créées par Alembic sous cette DSN — **à vérifier** via `\dt`/`pg_class.relowner` en CI) ; le revoke `PUBLIC` et la garantie de non-propriété de `app_runtime` sont **à créer**. La migration `0011_app_runtime_role.py` (S182, vérifiée) est le point d'extension naturel.

### Sprint 187 — Refactor : `create_runtime_pool()` (couplage DSN runtime + setup RLS inséparable)
**Objectif** : consolider les **10 sites** `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` en un seul helper `create_runtime_pool(*, min_size, max_size)` (`app/db/`) — rendre **impossible** de créer un pool runtime qui résout le bon rôle mais oublie le hook de contexte tenant (ou l'inverse).
**Complexité** : Moyenne.
**Justification** : finding d'altitude de la revue S182 — le sprint a centralisé la résolution de DSN mais a laissé les 10 `create_pool` copiés ; le couplage DSN+setup est l'invariant de sécurité. Reporté de S182 car le ripple touche les mocks `patch("app.workers.tasks.asyncpg.create_pool", …)` de **nombreux tests workers** (à re-pointer sur le nouveau home) — hors diff S182.
**Référence** : 9 `create_pool` dans `app/workers/tasks.py` + 1 dans `app/api/main.py` (vérifié, tous avec `setup=apply_tenant_context`) ; `resolve_app_database_url()` (`app/utils/security_config.py`, S182) et `apply_tenant_context` (`app/db/tenant_context.py:79`) existent — le helper et la migration des mocks de test sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur React/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.69.0),
.claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 183 — E5-S5 invalidation live du CTA de /facturation après upgrade. Aujourd'hui
BillingPage ne fait qu'un refreshUser() ponctuel au retour de checkout (BillingPage.tsx:57, S178) ;
si le webhook Stripe met tenants.plan à jour APRÈS ce retour, le CTA reste périmé.
À TRANCHER d'abord : polling court borné (sans backend) VS push WebSocket (réutiliser ws.ts +
émettre plan_changed depuis StripeService.handle_event). Vérifier comment le serveur émet sur le WS
Dashboard avant de promettre un push. Documenter la décision dans le bloc ROADMAP.
À FAIRE : (1) mécanisme de rafraîchissement répété/poussé borné + nettoyé au démontage ; (2) bascule
CTA checkout→portail dès user.plan==='pro' ; (3) zéro régression sans ?status ; (4) si push : émission
best-effort côté backend (échec n'avorte pas le webhook).
Tests : BillingPage.test.tsx (bascule sans reload, arrêt/nettoyage, non-vacuous) + hook WS si push.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : Vitest + tsc --noEmit + ESLint 0/0 ; backend si touché pytest + ruff + mypy. Pas d'eval.
Preuve : CTA bascule checkout→portail sans window.location.reload ; mécanisme arrêté/nettoyé.
```
