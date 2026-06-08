# Sprint 184 — E5-S6 : badge de plan + quota restant dans le header

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.70.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (183, E5-S5) a fermé la fenêtre de CTA périmé sur `/facturation` : après un retour de checkout `?status=success`, un **polling court borné** (frontend seul, 3 s × ≤10 itérations) re-`refreshUser()` jusqu'à la bascule `tenants.plan`, puis le CTA passe checkout→portail **sans rechargement** (décision tranchée vs push WebSocket — l'infra WS Dashboard n'a ni auth ni ciblage tenant). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail MIXTE backend + frontend** : un petit endpoint de lecture du compteur de quota restant + un composant header (badge plan + quota). GATES : backend `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports` ; frontend `cd frontend && npm test` (Vitest) + `npm run typecheck` (`tsc --noEmit` 0 erreur) + ESLint (0/0). ⚠️ Le venv web peut manquer des deps backend → `.venv/bin/pip install -r requirements.txt` si un import échoue ; `node_modules` frontend peut être absent → `cd frontend && npm ci`. **Pas de Docker/PG/Redis/navigateur live** dans le conteneur web → l'isolation RLS et le compteur Redis se prouvent par tests (endpoint avec services mockés + composant), pas par un essai live.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.70.0)
2. `.claude/rules/conventions-frontend.md` (React 18 / TS strict / structure pages-composants) **et** `.claude/rules/tests-pyramide.md` (test composant happy-path + erreur, `vi.mock` ; nouvel endpoint FastAPI = test d'intégration obligatoire).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **`user.plan`** est exposé par `GET /auth/me` (S173) et threadé jusqu'au frontend (`user?.plan` lu dans `BillingPage.tsx:40`, `User.plan` dans `types/index.ts`, vérifié). Le header rend déjà `TenantBadge` (`frontend/src/App.tsx:102`, vérifié) — point d'insertion naturel du badge de plan.
   - **`QuotaService`** existe (`app/services/quota_service.py:67`, vérifié) avec `max_analyses_per_month` (`PlanLimits.:44`), borne dure `check()` (`:105`), `increment()` (`:125`) et un **compteur mensuel Redis** `quota:{tenant}:{YYYY-MM}` (`_month_key` `:168`, `_current_count` `:96`, vérifié). **MAIS aucun getter « restant » ni endpoint de lecture** n'est exposé : le compteur n'est lu qu'en interne par `check()`. → un **`GET /quota`** (plan + utilisé + limite + restant + reset) et la méthode de lecture associée sur `QuotaService` sont **à créer**.
   - **`plan_limits`** (table de référence globale, `alembic/versions/0007_plan_limits.py`) porte `max_analyses_per_month` par plan (`free`/`pro`) — résolu par `_resolve_limits()` (`quota_service.py:74`, JOIN `tenants`↔`plan_limits`, vérifié). Réutiliser cette résolution plutôt que de re-requêter.
   - **À TRANCHER et documenter dans le bloc ROADMAP** : (a) **nouvel endpoint `GET /quota`** (router dédié, sémantique « état de quota » distincte de `GET /usage` qui agrège `usage_events`) **vs** (b) **champ ajouté à `GET /usage`** (un seul appel pour la page Facturation, mais couple deux sémantiques : consommation facturable durable vs borne d'application éphémère). Le compteur de quota est **Redis éphémère** (fenêtre mensuelle, fail-open), `usage_events` est **durable par skill** — privilégier un endpoint distinct sauf raison forte. Vérifier le contrat auth + RLS de `GET /usage` (`app/api/endpoints/usage.py`) avant de décider du home.

---

## TÂCHE — Sprint 184 : badge de plan + quota restant dans le header

**Objectif** : rendre la consommation visible **en continu, hors de `/facturation`** — exposer dans le header global le plan courant et le quota d'analyses restant du mois, pour inciter à l'upgrade au point d'usage.

### Spécification

1. **Endpoint de lecture du quota** (selon la décision tranchée) : `GET /quota` **authentifié** (cookie JWT → 401 sinon), retourne le plan du tenant courant, le nombre d'analyses **utilisées** ce mois, la **limite** `max_analyses_per_month`, le **restant** (`max(0, limit − used)`), et le **reset** (date de bascule du mois UTC). **Lecture seule** — n'incrémente jamais le compteur. **Fail-open cohérent** avec `QuotaService` : si Redis est indisponible ou le plan non résolu, renvoyer une réponse neutre (ex. `used=0` / restant = limite, ou un indicateur `unlimited`/`unknown` honnête) plutôt qu'une erreur — ne jamais casser le header.
2. **Méthode de lecture sur `QuotaService`** : ajouter un getter `read_status()`/`get_remaining()` (nom au choix) qui **réutilise** `_resolve_limits()` + `_current_count()` (ne pas dupliquer la résolution de plan ni la clé Redis `_month_key`). Retourne un dataclass/typed dict `(plan, used, limit, remaining, reset_at)`.
3. **Composant header** : un badge compact près de `TenantBadge` (`App.tsx:102`) affichant le plan (ex. `Badge` du design system, réutiliser le pattern `TenantBadge`/`billing-plan-badge`) + le quota restant (« N analyses restantes » ou « N/M »). Masqué proprement si non authentifié ou si la donnée est absente (rétrocompat). Client typé `frontend/src/api/` + type dans `types/index.ts` (zéro `any`). États : chargement discret (pas de skeleton bloquant le header), erreur silencieuse (le header ne doit jamais casser).
4. **Zéro régression** : `TenantBadge`, le CTA de `/facturation` et le polling S183 restent inchangés ; pas de nouvel appel sur le chemin chaud `/analyze`.

### Tests / validation
- **Backend** (`tests/api/test_quota_endpoint.py`) : 401 sans session ; tenant `free` avec K analyses utilisées → `used=K`, `remaining=limit−K`, `reset_at` = bascule de mois ; **fail-open** Redis indisponible → réponse neutre (pas de 500) ; lecture **non-incrémentante** (le compteur Redis ne bouge pas après l'appel — vérifier via mock/`call_args`). Réutilisation de `_resolve_limits` prouvée (plan résolu depuis `plan_limits`).
- **Frontend** (`*.test.tsx`) : le badge rend plan + restant depuis la donnée mockée ; masqué si non authentifié / donnée absente ; erreur de fetch → header intact (pas de crash). Tests **non-vacuous**.
- Gates : backend `pytest` + `ruff` + `mypy` ; frontend Vitest + `tsc --noEmit` + ESLint (0/0). **Pas d'eval** (endpoint de lecture + UI, aucun prompt de skill ni l'orchestrateur de skills touché).
- **Preuve d'acceptation observable** : un tenant `free` ayant consommé K analyses voit dans le header « plan FREE · (M−K) analyses restantes », et un appel `GET /quota` renvoie `{plan, used:K, limit:M, remaining:M−K, reset_at}` **sans** modifier le compteur Redis.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 185 — E5-S7 : threading tenant à travers la frontière Celery (`run_full_analysis`)
**Objectif** : faire passer le `tenant_id` à travers le `.delay()` Celery pour que `run_full_analysis` (déclenché par une alerte prix) tourne sous le tenant propriétaire et soit métré — dernier chemin d'analyse encore sous legacy.
**Complexité** : Élevée.
**Justification** : le ContextVar ne traverse pas le broker → le passage de tenant à travers la sérialisation Celery est un sujet distinct des sprints worker planifiés (qui partagent un seul process async).
**Référence** : `run_full_analysis` défini (`app/workers/tasks.py:143`, vérifié) et déclenché via `.delay()` (`tasks.py:301`, vérifié) reste sous legacy ; la propagation du `tenant_id` dans l'argument de tâche + sa restauration via `tenant_scope` côté worker sont **à créer**.

### Sprint 186 — Ops : durcissement du provisioning DB (propriété des objets + revoke PUBLIC)
**Objectif** : compléter S182 en garantissant que `app_runtime` n'est **propriétaire** d'aucune table (sinon il pourrait `ALTER … DISABLE ROW LEVEL SECURITY`) et en révoquant les privilèges `PUBLIC` par défaut sur le schéma.
**Complexité** : Moyenne.
**Justification** : `NOSUPERUSER`/`NOBYPASSRLS` ne suffit pas si le rôle runtime **possède** les tables — un propriétaire peut désactiver `FORCE ROW LEVEL SECURITY`. Non-propriété explicitement exigée par `docs/revue-owasp-rls-2026-06.md` §2.4 (vérifié, `:53`).
**Référence** : la propriété actuelle des tables revient à `copilote` (créées par Alembic sous cette DSN — **à vérifier** via `\dt`/`pg_class.relowner` en CI) ; le revoke `PUBLIC` et la garantie de non-propriété de `app_runtime` sont **à créer**. La migration `0011_app_runtime_role.py` (S182, vérifiée présente) est le point d'extension naturel.

### Sprint 187 — Refactor : `create_runtime_pool()` (couplage DSN runtime + setup RLS inséparable)
**Objectif** : consolider les **10 sites** `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` en un seul helper `create_runtime_pool(*, min_size, max_size)` (`app/db/`) — rendre **impossible** de créer un pool runtime qui résout le bon rôle mais oublie le hook de contexte tenant (ou l'inverse).
**Complexité** : Moyenne.
**Justification** : finding d'altitude de la revue S182 — le sprint a centralisé la résolution de DSN mais a laissé les 10 `create_pool` copiés ; le couplage DSN+setup est l'invariant de sécurité. Reporté de S182 car le ripple touche les mocks `patch("app.workers.tasks.asyncpg.create_pool", …)` de **nombreux tests workers** (à re-pointer sur le nouveau home) — hors diff S182.
**Référence** : 9 `create_pool` dans `app/workers/tasks.py` + 1 dans `app/api/main.py:172` (vérifié) ; `resolve_app_database_url()` (`app/utils/security_config.py:17`, S182) et `apply_tenant_context` (`app/db/tenant_context.py:79`) existent — le helper et la migration des mocks de test sont **à créer**.

### Sprint 188 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)
**Objectif** : quand `/analyze` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade ciblé (plan courant, borne atteinte, lien `/facturation`) plutôt qu'une erreur générique.
**Complexité** : Faible.
**Justification** : transforme le mur de quota en point de conversion ; complète le badge S184 (visibilité continue) par une incitation **au moment du blocage**.
**Référence** : `QuotaExceededError` (`app/services/quota_service.py:49`, vérifié) porte déjà `plan`/`used`/`limit`/`retry_after_s` ; le mapping `429` existe côté endpoints et `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`, réutilisé dans `BillingPage.tsx:11`) est le composant d'accroche — l'enrichissement du corps `429` (champs structurés) et le routage du `QuotaBanner` vers `/facturation` sont **à créer/vérifier**.

---

## Template de démarrage

```
Tu es un développeur Python/React senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.70.0),
.claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 184 — E5-S6 badge de plan + quota restant dans le header.
Aujourd'hui le quota d'analyses (QuotaService, compteur Redis quota:{tenant}:{YYYY-MM}) n'est
lisible qu'en interne par check() — aucun endpoint ne l'expose ; le header rend TenantBadge mais
pas le plan ni le restant.
À TRANCHER d'abord : nouvel endpoint GET /quota (recommandé, sémantique distincte de /usage) VS
champ ajouté à GET /usage. Documenter la décision dans le bloc ROADMAP.
À FAIRE : (1) getter de lecture sur QuotaService réutilisant _resolve_limits + _current_count
(plan/used/limit/remaining/reset_at, JAMAIS d'incrément) ; (2) GET /quota authentifié, fail-open
neutre si Redis/plan indisponible ; (3) badge header (plan + restant) près de TenantBadge, masqué
proprement si non-auth/donnée absente ; (4) zéro régression sur le chemin chaud /analyze.
Tests : test_quota_endpoint.py (401, used/remaining/reset, fail-open, lecture non-incrémentante)
+ composant header. Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : backend pytest + ruff + mypy ; frontend Vitest + tsc --noEmit + ESLint 0/0. Pas d'eval.
Preuve : header affiche « FREE · (M−K) analyses restantes » ; GET /quota renvoie le restant SANS
modifier le compteur Redis.
```
