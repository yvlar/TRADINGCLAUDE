# Sprint 186 — Ops : durcissement du provisioning DB (non-propriété `app_runtime` + revoke PUBLIC)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.72.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (185, E5-S7) a threadé le tenant à travers la frontière Celery : `run_full_analysis` accepte un `tenant_id` (capturé au site `.delay()`) et tourne sous `tenant_scope` + orchestrateur métré ; la boucle d'alerte prix énumère désormais les tenants → **plus aucun chemin d'analyse sous tenant legacy**. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail BACKEND/INFRA seul (migration Alembic + GRANTs/REVOKEs)** : durcir le provisioning du rôle `app_runtime` (S182). GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps → `.venv/bin/pip install -r requirements.txt` si un import échoue (`stripe`, `mypy`, `alembic` notamment). **Pas de Docker/PG dans le conteneur web** → la propriété des objets et le revoke `PUBLIC` se prouvent par tests de forme de migration (CI standard) + un test d'intégration RLS sous rôle réel (skippé hors PG migré). **Frontend non touché** (aucun fichier `frontend/` modifié → non-régression par construction).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.72.0)
2. `.claude/rules/securite.md` (hygiène secrets — aucun mot de passe dans la migration ; valeurs `.env` factices) **et** `.claude/rules/tests-pyramide.md` (marqueur `@pytest.mark.integration` pour les tests PG réels ; forme de migration testée en CI standard). Accessoirement `.claude/rules/api-architecture.md` (contraintes infra : pools, lifespan).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **Migration `0011_app_runtime_role.py`** (vérifiée présente) crée le rôle `app_runtime` (`NOSUPERUSER`/`NOBYPASSRLS`, `LOGIN` sans mot de passe) + GRANTs (7 tables RLS + `tenants`/`api_keys`/`subscriptions`/`stripe_events`, SELECT `plan_limits`, USAGE schéma + séquences). Son docstring **différe explicitement** « la non-propriété explicite + le revoke `PUBLIC` » au **Sprint 186** (vérifié dans l'en-tête du fichier). C'est le point d'extension naturel : ajouter une migration `0012` chaînée.
   - **Le problème** (`docs/revue-owasp-rls-2026-06.md` §2.3, vérifié `:48-49`) : sans `FORCE`, le **propriétaire** d'une table contourne sa propre RLS ; et un propriétaire peut `ALTER … DISABLE/NO FORCE ROW LEVEL SECURITY`. Les tables sont créées par Alembic sous la DSN `copilote` → **`copilote` en est propriétaire**. Tant que `app_runtime` n'est pas propriétaire (vérifié par construction au S182) le risque est contenu, MAIS il n'est **pas garanti explicitement** ni testé, et les privilèges `PUBLIC` par défaut sur le schéma ne sont pas révoqués.
   - **À TRANCHER et documenter dans le bloc ROADMAP** : **(a)** une migration `0012` qui `REVOKE ALL ON SCHEMA public FROM PUBLIC` + `REVOKE ALL ON ALL TABLES … FROM PUBLIC` puis re-GRANT explicite au seul `app_runtime` (les GRANTs du S182 restent la source) — **vs (b)** se contenter d'un test d'intégration qui **asserte** la non-propriété de `app_runtime` (`pg_class.relowner`) et l'absence de privilège `PUBLIC` sans rien changer au schéma. Privilégier **(a)** : le revoke `PUBLIC` est un durcissement réel exigé par la revue OWASP §2.3, le test seul ne corrige rien. Vérifier d'abord **qui possède réellement les tables** en CI (`pg_class.relowner` / `\dt`) avant de décider du re-GRANT.

---

## TÂCHE — Sprint 186 : durcissement du provisioning DB

**Objectif** : garantir **explicitement** que `app_runtime` n'est propriétaire d'aucune table (sinon il pourrait désactiver `FORCE RLS`) et **révoquer les privilèges `PUBLIC` par défaut** sur le schéma, fermant le résidu de §2.3 de la revue OWASP que la migration `0011` (S182) a explicitement différé.

### Spécification

1. **Migration Alembic `0012` chaînée** (`down_revision = "0011_app_runtime_role"`) : `REVOKE ALL ON SCHEMA public FROM PUBLIC` + `REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC` (et séquences si pertinent), puis re-GRANT explicite au seul `app_runtime` (réutiliser le périmètre de GRANTs du S182 — ne pas diverger). Idempotente (`REVOKE`/`GRANT` sont idempotents ; pas de `DO $$` requis si pas de garde `IF EXISTS` nécessaire). `downgrade()` re-`GRANT … TO PUBLIC` (retour à l'état Postgres par défaut).
2. **Garantie de non-propriété** : NE PAS transférer la propriété (les tables restent à `copilote` pour qu'Alembic puisse migrer) ; le livrable est le **revoke PUBLIC** + un test qui **asserte** que `app_runtime` n'est PAS dans `pg_class.relowner` des tables RLS et n'a aucun privilège via `PUBLIC`.
3. **Hygiène secrets** (`securite.md`) : aucun mot de passe dans la migration (cohérent S182).

### Tests / validation
- **Forme de migration** (CI standard, sans PG — patron `tests/test_alembic_*.py`) : `0012` chaînée après `0011` ; contient `REVOKE … FROM PUBLIC` ; re-GRANT au seul `app_runtime` ; `upgrade`/`downgrade` appelables.
- **Intégration RLS** (skippé hors PG migré, marqueur `@pytest.mark.integration`, ajouté au gate NOSUPERUSER `.github/workflows/ci.yml`) : sous le rôle réel `app_runtime`, asserter via `information_schema.role_table_grants` / `has_table_privilege('public', …)` qu'aucun privilège ne provient de `PUBLIC`, et que `app_runtime` n'est propriétaire d'aucune table RLS (`pg_class.relowner`). Vérifier que le runtime conserve bien ses accès (SELECT/INSERT sur les tables RLS via le GRANT explicite).
- Gates : `pytest` + `ruff` + `mypy`. **Pas d'eval** (infra DB pure — aucun prompt de skill ni l'orchestrateur de skills touché).
- **Preuve d'acceptation observable** : après `alembic upgrade head`, `app_runtime` a ses accès via GRANT explicite et **zéro** via `PUBLIC` ; un rôle anonyme/`PUBLIC` ne voit plus aucune table. Prouvé en CI sous le rôle réel.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 187 — Refactor : `create_runtime_pool()` (couplage DSN runtime + setup RLS inséparable)
**Objectif** : consolider les **10 sites** `asyncpg.create_pool(resolve_app_database_url(), …, setup=apply_tenant_context)` en un seul helper `create_runtime_pool(*, min_size, max_size)` (`app/db/`) — rendre **impossible** de créer un pool runtime qui résout le bon rôle mais oublie le hook de contexte tenant (ou l'inverse).
**Complexité** : Moyenne.
**Justification** : finding d'altitude répété des revues S182 ET S185 — le couplage DSN+setup est l'invariant de sécurité, copié à l'identique. Reporté car le ripple touche les mocks `patch("app.workers.tasks.asyncpg.create_pool", …)` de **nombreux tests workers** (à re-pointer sur le nouveau home).
**Référence** : **9** `asyncpg.create_pool` dans `app/workers/tasks.py` (vérifié `grep -c`) + 1 dans `app/api/main.py:173` (vérifié) ; `resolve_app_database_url()` (`app/utils/security_config.py:17`, vérifié) et `apply_tenant_context` (`app/db/tenant_context.py:79`, vérifié) existent — le helper et la migration des mocks de test sont **à créer**.

### Sprint 188 — Refactor : helper `_for_each_tenant()` (5 copies du squelette énumère-et-scope)
**Objectif** : extraire le squelette répété `SELECT id FROM tenants ORDER BY created_at` → boucle → `tenant_scope(tenant_id)` → try/except best-effort log-and-continue en un helper async unique (`app/workers/`), appliqué aux chemins planifiés.
**Complexité** : Moyenne.
**Justification** : finding d'altitude de la revue S185 — le squelette atteint **5 copies** dans `app/workers/tasks.py`, seuil où la duplication devient dette load-bearing. Les corps divergent (retour `None` / `list[str]` union / `dict`), donc le helper doit accepter un callback et laisser l'agrégation à l'appelant — chantier isolé, hors de tout sprint fonctionnel.
**Référence** : 5 occurrences de `SELECT id FROM tenants ORDER BY created_at` dans `app/workers/tasks.py` (vérifié, lignes 254/352/495/675/902) — `_execute_watchlist_analysis`, `_execute_price_alert_check`, `_execute_composite_alert_check`, `_execute_scheduled_screener`, `_execute_retention_purge` ; `tenant_scope` (`app/db/tenant_context.py:64`, vérifié). Le helper est **à créer**.

### Sprint 189 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)
**Objectif** : quand `/analyze` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade ciblé (plan courant, borne atteinte, lien `/facturation`) plutôt qu'une erreur générique.
**Complexité** : Faible.
**Justification** : transforme le mur de quota en point de conversion ; complète le badge S184 (visibilité continue) par une incitation **au moment du blocage**.
**Référence** : `QuotaExceededError` (`app/services/quota_service.py:64`, vérifié — porte `plan`/`used`/`limit`/`retry_after_s`) ; `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx`, vérifié présent) est le composant d'accroche — l'enrichissement du corps `429` (champs structurés) et le routage du `QuotaBanner` vers `/facturation` sont **à créer/vérifier**.

### Sprint 190 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)
**Objectif** : vider le cache react-query (`queryClient.clear()`) lors du `logout` pour qu'une re-connexion sous un autre tenant sur la même session SPA ne serve jamais de données périmées du tenant précédent (`usage`, `usage-reporting`, etc.).
**Complexité** : Faible.
**Justification** : finding cross-tenant de la revue S184 — généralisé. S184 a scopé `['quota', tenantId]` par tenant au cas par cas ; les clés `['usage']`/`['usage-reporting']` restent non scopées et non purgées au logout. Une purge unique au logout couvre tout le cache d'un coup.
**Référence** : `logout` est défini dans `frontend/src/contexts/AuthContext.tsx:56` (vérifié, `useCallback`) — il n'importe pas `useQueryClient`. Le `QueryClientProvider` global vit dans `frontend/src/main.tsx:21` (vérifié). L'injection de `useQueryClient` dans `AuthProvider` + l'appel de purge au logout sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python/infra senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.72.0),
.claude/rules/securite.md et tests-pyramide.md.
Sprint actif : 186 — Ops durcissement du provisioning DB (non-propriété app_runtime + revoke PUBLIC).
La migration 0011 (S182) crée le rôle app_runtime (NOSUPERUSER/NOBYPASSRLS) + GRANTs mais DIFFÈRE
explicitement (cf. son docstring) la non-propriété explicite + le revoke des privilèges PUBLIC par
défaut sur le schéma — exigés par docs/revue-owasp-rls-2026-06.md §2.3 (sans quoi un propriétaire de
table peut DISABLE/NO FORCE RLS).
À TRANCHER d'abord : (a) migration 0012 chaînée REVOKE ALL … FROM PUBLIC + re-GRANT explicite à
app_runtime (recommandé) VS (b) test d'assertion seul sans changement de schéma. Documenter dans le
bloc ROADMAP.
À FAIRE : (1) migration 0012 (down_revision=0011) revoke PUBLIC + re-GRANT au seul app_runtime,
idempotente, downgrade re-GRANT PUBLIC ; (2) test de forme de migration (CI standard) ; (3) test
d'intégration RLS sous rôle réel (app_runtime n'est pas propriétaire via pg_class.relowner, zéro
privilège via PUBLIC, accès conservés via GRANT explicite), ajouté au gate CI NOSUPERUSER.
Vérifier d'abord QUI possède les tables (pg_class.relowner) en CI avant de décider du re-GRANT.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest + ruff + mypy. Pas d'eval. Preuve : après upgrade, app_runtime a ses accès via GRANT
explicite et zéro via PUBLIC.
```
