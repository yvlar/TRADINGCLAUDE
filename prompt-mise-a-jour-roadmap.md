# Sprint 182 — Ops : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS` (risque résiduel n°1 OWASP RLS)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.68.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (181, E5-S4) a metré les **deux derniers chemins worker planifiés** restés sous legacy : `_execute_composite_alert_check` et `_execute_scheduled_screener` (`app/workers/tasks.py`) itèrent désormais par tenant sous `tenant_scope` avec un orchestrateur `with_metering=True` → conso imputée au tenant propriétaire dans `usage_events`. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Travail OPS/INFRA + DB dominant** : ce sprint matérialise un rôle de connexion PostgreSQL applicatif `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, **non-propriétaire** des tables) pour les pools API + workers, et réserve `copilote` (superuser) aux **seules migrations Alembic**. GATES : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. ⚠️ Le venv web peut manquer des deps backend → `.venv/bin/pip install -r requirements.txt` (+ `mypy` non pinné : `.venv/bin/pip install mypy`) si un import échoue. ⚠️ **Pas de Docker/PG dans le conteneur web** → la preuve que les pools applicatifs tournent bien sous `app_runtime` (et que la RLS est donc active en prod) est **un test d'intégration skippé hors PG migré**, exécuté en CI via le gate NOSUPERUSER.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.68.0)
2. `.claude/rules/api-architecture.md` (lifespan FastAPI + pools PostgreSQL + infra) **et** `.claude/rules/securite.md` (clés/secrets `.env` + `.env.example`, mots de passe de rôle jamais loggés).
3. **Code de référence à vérifier en début de session (anti-hallucination)** :
   - **Exigence documentée** : `docs/revue-owasp-rls-2026-06.md` §2.4 (vérifié — lignes 56-63 et 107) : « le rôle de connexion **runtime** (API + workers) doit être `NOSUPERUSER`, `NOBYPASSRLS`, et non-propriétaire ; sinon la RLS est **inerte** en production ». C'est le **1ᵉʳ des deux risques résiduels** ; le 2ᵉ (scoping `/report`) est clos par le S176.
   - **Le défaut est superuser** : `DATABASE_URL=postgresql://copilote:copilote@…` (`.env.example:21`, vérifié) ; `copilote` est `SUPERUSER`+`BYPASSRLS` → court-circuite **toute** policy RLS.
   - **Sites de création de pool à recâbler** : (a) lifespan API `app/api/main.py:170` (`asyncpg.create_pool(db_url, …, setup=apply_tenant_context)`, vérifié `:155`/`:170`) ; (b) workers — `_build_orchestrator` (`app/workers/tasks.py:83`, vérifié) **et** les `asyncpg.create_pool` directs des tâches planifiées (`tasks.py` — composite/screener/retention/usage_reporting/price_alert/etc., tous avec `setup=apply_tenant_context`). Tous lisent `DATABASE_URL`/`os.environ` aujourd'hui → ils héritent du rôle de la DSN.
   - **Bootstrap DB** : `infra/postgres/init.sql` (vérifié présent) est le point d'entrée du provisioning DB ; les migrations de schéma vivent dans Alembic (`alembic/versions/…`, cf. `0006_usage_events.py` cité dans `ROADMAP.md`). **À TRANCHER et documenter** : où créer le rôle `app_runtime` + ses GRANTs (init.sql idempotent vs migration Alembic) — sachant que le rôle est une ressource **cluster/instance**, pas un objet de schéma applicatif.
   - **À VÉRIFIER avant d'implémenter** : confirmer qu'aucun chemin applicatif ne dépend de privilèges superuser (ex. `set_config(..., false)` de `apply_tenant_context` — `app/db/tenant_context.py:90` — fonctionne sous un rôle non-superuser ; les `GRANT` doivent couvrir SELECT/INSERT/UPDATE/DELETE sur les 7 tables RLS + tenants + api_keys + subscriptions + plan_limits + séquences, cf. le bloc de GRANT du gate CI `.github/workflows/ci.yml` ~ligne 199 qui modélise déjà ce périmètre pour `rls_tester`). Si un chemin exige réellement le superuser (à part les migrations), **STOP et me le signaler**.

---

## TÂCHE — Sprint 182 : rôle de connexion runtime `app_runtime` (RLS active en prod)

**Objectif** : rendre la RLS multi-tenant **effective en production**. Aujourd'hui toutes les policies RLS (Sprints 163-181) sont correctes mais **inertes** dès que le runtime se connecte avec `copilote` (SUPERUSER+BYPASSRLS). Ce sprint provisionne un rôle `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-propriétaire) et câble les pools API + workers dessus, en réservant `copilote` aux migrations Alembic.

### Spécification

1. **Provisionner le rôle `app_runtime`** : `CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD …` (mot de passe via env, jamais hardcodé ni loggé) + `GRANT` SELECT/INSERT/UPDATE/DELETE sur les tables métier (7 RLS + `tenants`/`api_keys`/`subscriptions`/`stripe_events`), `GRANT SELECT` sur `plan_limits`, `GRANT USAGE` sur le schéma + les séquences (BIGSERIAL). Idempotent (`DO $$ … IF NOT EXISTS`). Décision init.sql vs migration : **trancher et documenter dans le bloc ROADMAP**.
2. **Variable d'environnement dédiée** : introduire `APP_DATABASE_URL` (rôle `app_runtime`) lue par les pools API + workers ; `DATABASE_URL` (rôle `copilote`/owner) reste pour Alembic uniquement. Ajouter `APP_DATABASE_URL` à `.env.example` (valeur factice) **et** documenter le boot fail-safe si absente (repli sur `DATABASE_URL` en dev, ou fail-fast — trancher).
3. **Recâbler tous les sites de pool applicatifs** : `app/api/main.py` lifespan + chaque `create_pool` des workers (`_build_orchestrator` + tâches planifiées) lisent `APP_DATABASE_URL`. Ne PAS toucher la DSN Alembic.
4. **Pas de régression fonctionnelle** : le comportement observable est identique ; seul le rôle de connexion change. Tous les tests existants (qui tournent sur `copilote` en CI hors gate RLS) restent verts.

### Tests / validation
- **Unitaires** : le sélecteur de DSN (helper de résolution `APP_DATABASE_URL` → repli/fail-fast) testé en isolation (env présent / absent).
- **Intégration RLS bout-en-bout** (skippée hors PG migré, ajoutée au gate CI NOSUPERUSER `.github/workflows/ci.yml`) : un pool ouvert sous `app_runtime` (NOSUPERUSER) **voit la RLS s'appliquer** (0 ligne sans contexte tenant, lignes du tenant courant sous `tenant_scope`) — preuve directe que le rôle ne contourne pas les policies. Réutiliser le harnais `rls_tester` existant si possible (ou prouver l'équivalence des GRANTs).
- `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check` + `mypy app/ --ignore-missing-imports`. **Pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — infra DB + câblage de pools uniquement).
- **Preuve d'acceptation observable** : avec `APP_DATABASE_URL` pointant `app_runtime`, une requête authentifiée tenant B ne voit que ses lignes (RLS active) ; le même rôle ne peut pas `SET ROLE`/contourner les policies. Sous `copilote` (migrations) la RLS resterait contournée — d'où la séparation.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 183 — E5-S5 : webhook de plan → invalidation live du CTA (push)
**Objectif** : remplacer le `refreshUser()` ponctuel au retour de checkout (S178) par une invalidation poussée (WebSocket Dashboard existant ou polling court) pour que le plan se mette à jour même si le webhook Stripe arrive **après** le retour sur `/facturation`.
**Complexité** : Moyenne.
**Justification** : S178 resync une seule fois au montage ; si le webhook met `tenants.plan` à jour quelques secondes plus tard, le CTA reste périmé jusqu'au prochain `authMe()`. Fermer cette fenêtre rend l'upgrade instantané.
**Référence** : `refreshUser()` existe (`frontend/src/contexts/AuthContext.tsx:12,48`, vérifié) ; le canal WebSocket du Dashboard existe (`frontend/src/api/ws.ts`, vérifié présent) — son extension à un signal serveur de changement de plan est **à créer**.

### Sprint 184 — E5-S6 : badge de plan + quota restant dans le header
**Objectif** : exposer en continu (header global) le plan courant et le quota d'analyses restant du mois, lus depuis `user.plan` (S173) et un compteur de quota.
**Complexité** : Faible.
**Justification** : rend la consommation visible hors de `/facturation` — incite à l'upgrade au point d'usage.
**Référence** : `user.plan` exposé par `GET /auth/me` (S173, vérifié dans `ROADMAP.md` « État courant ») ; `QuotaService` existe (`app/services/quota_service.py:67`, `max_analyses_per_month` `:44`, borne dure `check()` `:105`, vérifié) mais **n'expose aucun endpoint de lecture du compteur restant** → un `GET /quota` (ou champ sur `/usage`) est **à créer**, ainsi que le composant header.

### Sprint 185 — E5-S7 : threading tenant à travers la frontière Celery (`run_full_analysis`)
**Objectif** : faire passer le `tenant_id` à travers le `.delay()` Celery pour que `run_full_analysis` (déclenché par une alerte prix) tourne sous le tenant propriétaire et soit métré — dernier chemin d'analyse encore sous legacy après S177/S181.
**Complexité** : Élevée.
**Justification** : le ContextVar ne traverse pas le broker → le passage de tenant à travers la sérialisation Celery est un sujet distinct des sprints worker planifiés (qui partagent un seul process async).
**Référence** : `run_full_analysis` défini (`app/workers/tasks.py:144`, vérifié) et déclenché via `.delay()` sur le chemin alerte prix (`tasks.py:304`, vérifié) reste sous legacy ; la propagation du `tenant_id` dans l'argument de tâche + sa restauration via `tenant_scope` côté worker sont **à créer**.

### Sprint 186 — Ops : durcissement du provisioning DB (propriété des objets + revoke PUBLIC)
**Objectif** : compléter S182 en s'assurant que `app_runtime` n'est **propriétaire** d'aucune table (sinon il pourrait `ALTER … DISABLE ROW LEVEL SECURITY`) et en révoquant les privilèges `PUBLIC` par défaut sur le schéma.
**Complexité** : Moyenne.
**Justification** : `NOSUPERUSER`/`NOBYPASSRLS` ne suffit pas si le rôle runtime **possède** les tables — un propriétaire peut désactiver `FORCE ROW LEVEL SECURITY`. La non-propriété est explicitement exigée par `docs/revue-owasp-rls-2026-06.md` §2.4 (vérifié).
**Référence** : la propriété actuelle des tables revient à `copilote` (créées par Alembic sous cette DSN — **à vérifier** via `\dt`/`pg_class.relowner` en CI) ; le revoke `PUBLIC` et la garantie de non-propriété de `app_runtime` sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior + ops sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.68.0),
.claude/rules/api-architecture.md et securite.md.
Sprint actif : 182 — Ops rôle runtime app_runtime (NOSUPERUSER/NOBYPASSRLS/non-propriétaire) pour
rendre la RLS active en prod. Aujourd'hui les pools applicatifs se connectent avec `copilote`
(SUPERUSER+BYPASSRLS, .env.example:21) → toute policy RLS est INERTE (docs/revue-owasp-rls-2026-06.md
§2.4, risque résiduel n°1).
À FAIRE : (1) provisionner le rôle app_runtime + GRANTs (init.sql vs migration Alembic — trancher) ;
(2) introduire APP_DATABASE_URL (.env.example factice) lue par les pools ; (3) recâbler le lifespan API
(app/api/main.py:170) ET tous les create_pool des workers (app/workers/tasks.py:83 + tâches planifiées),
DATABASE_URL réservé à Alembic ; (4) zéro régression fonctionnelle.
AVANT d'implémenter : confirmer qu'aucun chemin applicatif n'exige le superuser (apply_tenant_context
tenant_context.py:90 sous rôle non-superuser ; périmètre des GRANTs = bloc rls_tester du gate CI ~ci.yml:199).
Sinon STOP et me le signaler.
Tests : unitaires sélecteur de DSN + intégration RLS bout-en-bout sous app_runtime (skippée hors PG migré,
ajoutée au gate CI NOSUPERUSER). Backend/infra seul, pas d'eval.
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check + mypy app/ --ignore-missing-imports.
Preuve : un pool sous app_runtime voit la RLS s'appliquer (0 ligne sans contexte tenant ; lignes du
tenant courant sous tenant_scope) — la RLS n'est plus contournée.
```
