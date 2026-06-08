# Sprint 180 — E5-S3 : audit log côté UI (page Admin)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.66.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (179, E5-S2) a rendu la **facturation à l'usage transparente** : endpoint `GET /usage/reporting` (authentifié, lecture seule) exposant le curseur `subscriptions.usage_reported_through` + `pending_events` (`count_events_in_window`), et une carte « Facturation à l'usage » sur `BillingPage`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail FRONTEND dominant** : ce sprint ajoute **un client typé + une surface UI** ; l'endpoint backend `GET /admin/audit-log` **existe déjà** (S160). GATES : frontend `cd frontend && npm test` (Vitest) + `npm run typecheck` (0) + ESLint (0/0). Backend touché seulement si un ajustement de l'endpoint s'avère nécessaire (sinon `pytest` reste vert par non-régression). ⚠️ Le venv web peut manquer des deps backend → `.venv/bin/pip install -r requirements.txt` (+ `mypy` non pinné : `.venv/bin/pip install mypy`) si un import échoue. ⚠️ `frontend/node_modules` peut être absent → `cd frontend && npm ci`.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.66.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TS strict, structure pages/composants, zéro `any`, `data-testid` sur éléments interactifs) **et** `.claude/rules/tests-pyramide.md` (test composant obligatoire : happy path + cas d'erreur ; mock du client API).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - `GET /admin/audit-log` **existe déjà** : route `app/api/endpoints/admin.py:159`, handler `list_audit_log` `:163` (`limit` borné 1-200 → 422, `_require_admin`, `service.list_recent(limit)` — vérifié). Renvoie `list[AuditLogEntry]`.
   - Modèle `AuditLogEntry` (`app/services/audit_log_service.py:16`, vérifié) : `id: UUID`, `tenant_id: UUID | None`, `user_id: UUID | None`, `action: str`, `cible_type: str`, `cible_id: str | None`, `metadata: dict`, `created_at: datetime`. **Le type frontend `AuditLogEntry` est À CRÉER** dans `frontend/src/types/index.ts` (miroir snake_case, zéro `any`).
   - Le client typé `frontend/src/api/admin.ts` (vérifié : `listApiKeys`/`createApiKey`/`revokeApiKey`) n'a **aucune** fonction audit-log → `getAuditLog(limit?)` est **À CRÉER** (patron `apiClient.request<AuditLogEntry[]>('/admin/audit-log?limit=…')`).
   - La page `frontend/src/pages/AdminPage.tsx` (vérifiée, existe — gestion des clés API) est la **surface UI à étendre** ; pas de nouvelle route à créer.

---

## TÂCHE — Sprint 180 (E5-S3) : exposer le journal d'audit dans la page Admin

**Objectif** : la conformité (Loi 25) exige une traçabilité **consultable**. Le journal d'audit append-only (`audit_log`, S160) enregistre les mutations métier (watchlist, annotation, clé API) avec le `tenant_id` effectif (S175), mais n'a **aucune surface UI** — un admin ne peut pas le lire sans requête SQL. Ce sprint ajoute une table filtrable dans la page Admin.

### Spécification

1. **Type + client typé frontend** — `frontend/src/types/index.ts` : interface `AuditLogEntry` (miroir snake_case du modèle Pydantic, zéro `any` ; `metadata: Record<string, unknown>`). `frontend/src/api/admin.ts` : `getAuditLog(limit = 50): Promise<AuditLogEntry[]>` appelant `/admin/audit-log?limit=…`.
2. **UI table dans `AdminPage.tsx`** — une section « Journal d'audit » sous la gestion des clés : table des entrées récentes (colonnes : date `fr-CA`, `action`, `cible_type`, `cible_id`, `tenant_id` tronqué/abrégé). **Filtre côté client** sur `action` et/ou `cible_type` (un `<select>` ou champ de recherche — pas de nouvel endpoint, on filtre la liste déjà chargée). États chargement (skeleton) / erreur / liste vide. `data-testid` dédiés (table, lignes, filtre). Réutiliser les composants `ui/` existants (`Card`, `Table` si présent, `Skeleton`, `Badge`).
3. **Pas de régression** : la gestion des clés API existante (créer/lister/révoquer) se comporte exactement comme avant.

### Tests / validation
- **Frontend (composant Vitest `AdminPage`)** : table rendue avec des entrées mockées (`getAuditLog` mocké) ; filtre par `action` réduit les lignes affichées ; état chargement ; état erreur ; liste vide → message neutre. Mock du client `api/admin.ts` (patron `tests-pyramide.md`).
- **Backend** : aucun changement attendu sur l'endpoint (déjà testé S160) ; si un ajustement s'avère nécessaire (ex. champ manquant), ajouter un test d'intégration. Sinon, le DIRE explicitement (pas de nouveau test backend = endpoint réutilisé tel quel).
- `cd frontend && npm test` + `npm run typecheck` (0) + ESLint (0/0) ; si backend touché : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff` + `mypy app/`. **Pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché).
- **Preuve d'acceptation observable** : `AdminPage` montée avec N entrées d'audit mockées affiche N lignes ; un filtre `action='api_key.create'` réduit la table aux seules entrées correspondantes.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 181 — E5-S4 : metering du screener planifié + alertes composites (reliquat S177)
**Objectif** : étendre le threading tenant + metering (S177) aux deux chemins worker encore sous legacy — `run_scheduled_screener` et `run_composite_alert_check` — qui lisent la watchlist via `WatchlistService.list_entries()` sous le tenant legacy.
**Complexité** : Moyenne.
**Justification** : ferme le dernier reliquat de conso planifiée non facturée ; complète l'objectif E5-S1.
**Référence** : `_execute_scheduled_screener` (`app/workers/tasks.py:513`) et `_execute_composite_alert_check` (`app/workers/tasks.py:419`) appellent `wl_service.list_entries()` (`:526`, `:359`, vérifié) sans `tenant_scope` ; `_build_orchestrator(*, with_metering=True)` existe déjà (S177, `app/workers/tasks.py:65`, vérifié) et `_analyze_watchlist_entries` (`:168`, vérifié) est le patron d'itération tenant à cloner — la restructuration par chemin est **à créer**.

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

### Sprint 184 — E5-S6 : badge de plan + quota restant dans le header
**Objectif** : exposer en continu (header global) le plan courant et le quota d'analyses restant du mois, lus depuis `user.plan` (S173) et un compteur de quota.
**Complexité** : Faible.
**Justification** : rend la consommation visible hors de `/facturation` — incite à l'upgrade au point d'usage.
**Référence** : `user.plan` exposé par `GET /auth/me` (S173, vérifié dans `ROADMAP.md` « État courant ») ; le `QuotaService` applique une borne dure (`app/services/quota_service.py`, à vérifier) mais **n'expose aucun endpoint de lecture du compteur restant** → un `GET /quota` (ou champ sur `/usage`) est **à créer**, ainsi que le composant header.

---

## Template de démarrage

```
Tu es un développeur React/Python senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.66.0),
.claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 180 — E5-S3 (audit log côté UI). L'endpoint GET /admin/audit-log existe DÉJÀ
(admin.py:159, handler list_audit_log :163, list[AuditLogEntry], _require_admin, limit 1-200) ;
le modèle AuditLogEntry est à audit_log_service.py:16 (id/tenant_id/user_id/action/cible_type/
cible_id/metadata/created_at). Le type frontend AuditLogEntry, le client getAuditLog() dans
api/admin.ts, et la table UI dans AdminPage.tsx sont À CRÉER.
À FAIRE : type + client typés (zéro any) ; section « Journal d'audit » dans AdminPage : table
(date fr-CA, action, cible_type, cible_id, tenant_id) + filtre client sur action/cible_type ;
états chargement/erreur/vide ; data-testid dédiés. Tests : composant Vitest AdminPage (table
rendue, filtre réduit les lignes, chargement, erreur, vide). Frontend dominant, pas d'eval.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : npm test + npm run typecheck (0) + ESLint (0/0) ; (backend pytest+ruff+mypy si touché).
Preuve : AdminPage montée avec N entrées mockées affiche N lignes ; filtre action réduit la table.
```
