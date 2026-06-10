# Sprint 203 — Ops : test d'isolation RLS `usage_events` sur le chemin orchestrateur métré

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.89.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (202) a ajouté la carte « Quota mensuel » sur `/facturation` (plan, `used`/`limit`, barre, `reset_at`) via `GET /quota`, options react-query alignées sur le `QuotaBadge` (clé partagée). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** (zéro `app/` modifié, zéro frontend, pas d'eval) : `usage_events` est la table de facturation (source unique du metering E4/E5). Les tests RLS S163-S166 prouvent la policy table par table, et les tests S177/S181/S185 prouvent que les chemins **workers planifiés** émettent sous le bon tenant. Le chaînon non couvert : l'émission depuis **l'orchestrateur lui-même** (`_emit_usage_events`) sous un `tenant_scope` donné ne peut pas écrire sous un autre tenant — une fuite ici serait une anomalie de facturation silencieuse.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.89.0)
2. `.claude/rules/tests-pyramide.md` (niveau **intégration** ; marqueur `@pytest.mark.integration` ; vraie DB requise).
3. `.claude/rules/conventions-python.md` (type hints partout, docstrings FR du WHY, imports groupés).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `app/orchestrator/core.py` — `_emit_usage_events(self, skills_applied, all_usages, workflow)` (`:462`, best-effort, appariement lockstep) ; sites d'appel `:1098` et `:1677` — vérifiés `grep` S202.
   - `app/db/tenant_context.py` — `tenant_scope` (`:65`, context manager ContextVar→GUC) — vérifié S202.
   - `alembic/versions/0006_usage_events.py` — table + policy `usage_events_tenant_isolation` (USING + WITH CHECK) — vérifié S202.
   - **Patron à suivre** : `tests/integration/test_watchlist_metering_rls.py` (S177) — même squelette (`_RLS_DB_URL`, `pytestmark` skipif, PG migré, rôle NOSUPERUSER, pool + `apply_tenant_context`) ; déjà câblé dans le job CI « Migrations — Alembic + RLS ».

---

## TÂCHE — Sprint 203 : prouver que `_emit_usage_events` ne peut pas écrire cross-tenant

**Objectif** : sous un pool RLS réel (rôle NOSUPERUSER, `setup=apply_tenant_context`), exercer `_emit_usage_events` (pas une simple policy SQL) dans un contexte `tenant_scope(A)` et prouver : (a) l'événement émis est visible par A et **invisible** par B (lecture scopée B → 0 ligne) ; (b) une tentative d'émission forgée sous B depuis le contexte A (INSERT avec `tenant_id=B` explicite) est **rejetée par la policy WITH CHECK** — la RLS, pas l'applicatif, est la barrière.

### Spécification

1. **Nouveau fichier `tests/integration/test_orchestrator_metering_rls.py`** (patron `test_watchlist_metering_rls.py` : `_RLS_DB_URL`, skipif, probe NOSUPERUSER, cleanup).
2. **Test obligatoire (émission scopée)** : construire un orchestrateur minimal (ou appeler `_emit_usage_events` directement sur une instance avec le pool RLS) sous `tenant_scope(tenant_a)` avec des `UsageDetail` factices → asserter qu'une ligne `usage_events` existe **vue depuis le scope A**, et que la même lecture **sous scope B** retourne 0 ligne (isolation de lecture).
3. **Test obligatoire (WITH CHECK)** : depuis une connexion scopée A, tenter un `INSERT INTO usage_events (..., tenant_id) VALUES (..., B)` explicite → asserter l'échec (`asyncpg.exceptions` policy violation) — prouve que même un bug applicatif passant le mauvais tenant serait bloqué par la DB.
4. **Contraintes** : aucun appel Claude réel (les `UsageDetail` sont des objets construits, pas issus d'une analyse) ; mocker le strict nécessaire de l'orchestrateur pour atteindre `_emit_usage_events` sans exécuter de skills ; marqueur `@pytest.mark.integration` ; type hints partout, docstrings FR du WHY ; cleanup des lignes de test (DELETE sous le scope propriétaire ou rôle migrations).

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/`.
- **Câblage CI obligatoire** : ajouter le fichier à la liste explicite du job « Migrations — Alembic + RLS » (`.github/workflows/ci.yml` — liste actuelle `:235-247`, 13 fichiers + celui-ci) — sans cette ligne le test ne tournera JAMAIS en CI (cf. sprint suggéré S206).
- **Pas de frontend, pas d'eval.**
- **⚠️ Pas de PostgreSQL dans le conteneur web** : constater localement collection + skip propre ; le gate vert réel est le CI.
- **Preuve d'acceptation observable** : le test d'isolation **échoue** si on neutralise le scope (ex. émettre hors `tenant_scope` → l'événement n'est visible par personne sous RLS, ou lecture B non vide si la policy était `ENABLE` sans `FORCE`) — injecter la régression factice puis restaurer byte-identique.

### Note environnement conteneur web
`pytest`/`ruff` tournent depuis `.venv` (hook `SessionStart`). Si des imports manquent (`stripe` a manqué S196-S201), relancer `.venv/bin/pip install -r requirements.txt`.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — voir plan directeur §7-§8)

### Sprint 204 — Frontend : page d'administration des tenants (super-admin)
**Objectif** : page `/admin/tenants` listant les tenants (nom, plan, `stripe_customer_id` tronqué, date de création) via un endpoint `GET /admin/tenants` à créer, accessible admin uniquement.
**Complexité** : Moyenne.
**Justification** : aucune UI n'expose la liste des tenants — l'administrateur doit inspecter la DB. Utile pour l'onboarding B2B et le support.
**Référence** : `app/api/endpoints/admin.py` — `_require_admin` (`:58`) — vérifié `grep` S200 ; `app/services/user_service.py` — `UserService` (`:22`) — vérifié S200 ; la route et la page sont **à créer**.

### Sprint 205 — Ops : étendre le garde anti-contournement asyncpg à `app/` entier (allowlist)
**Objectif** : généraliser le meta-test S200 de `app/workers/` à tout `app/`, avec allowlist explicite des deux usages légitimes — le chokepoint lui-même et le provisioning admin.
**Complexité** : Faible.
**Justification** : S200 verrouille les workers ; un endpoint ou service pourrait encore créer un pool direct (contournant garde insecure-creds + hook RLS). Alternative à évaluer en session : règle lint `ruff` banned-api — trancher AVANT d'implémenter.
**Référence** : scan AST réutilisable `tests/meta/test_no_direct_asyncpg_in_workers.py` (`_scan_violations`) — livré S200 ; à allowlister : `app/db/pool.py:25` et `app/db/provision_app_runtime.py:47` — vérifiés `grep` S200 ; l'extension est **à créer**.

### Sprint 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI »
**Objectif** : verrouiller par un meta-test (patron S200) que chaque `tests/integration/test_*.py` apparaît dans la liste explicite de fichiers du job CI « Migrations — Alembic + RLS » — un fichier oublié est aujourd'hui skippé localement ET jamais exécuté en CI : couverture zéro silencieuse.
**Complexité** : Faible.
**Justification** : finding d'altitude de la revue S201 ; S201 et S203 ont chacun dû éditer `ci.yml` à la main — la discipline manuelle ne se prouve pas.
**Référence** : liste explicite `.github/workflows/ci.yml:235-247` (13 fichiers) — vérifié `grep` S201 ; patron meta-test filesystem `tests/meta/test_no_direct_asyncpg_in_workers.py` — livré S200 ; le meta-test est **à créer**.

### Sprint 207 — Frontend : hook partagé `useQuota` + CTA contextuel à quota épuisé
**Objectif** : extraire un hook `useQuota(tenantId)` consommé par `QuotaBadge` ET la carte Quota de `/facturation` (mêmes clé/options, logique fail-open unique), et afficher un CTA « Passer à Pro » contextuel dans la carte quand `remaining === 0` et plan `free`.
**Complexité** : Faible.
**Justification** : findings écartés-YAGNI de la revue S202 — dès qu'un 3ᵉ consommateur du quota apparaît (badge + carte aujourd'hui), la duplication clé/options/fail-open devient un risque de divergence réel ; le CTA à épuisement ferme la friction « scroller vers la carte Plan ».
**Référence** : `frontend/src/components/QuotaBadge.tsx` (query `:12-20`) — vérifié S202 ; carte Quota `BillingPage.tsx` (query + JSX) — livré S202 ; le hook et le CTA sont **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.89.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 203 — Ops : test d'isolation RLS usage_events sur le chemin orchestrateur métré.
COMMENCE PAR RE-GREP : core.py _emit_usage_events (:462, appels :1098/:1677), tenant_context.tenant_scope (:65),
patron tests/integration/test_watchlist_metering_rls.py, policy 0006_usage_events.
LIVRABLE : tests/integration/test_orchestrator_metering_rls.py — 2 tests : (1) émission sous tenant_scope(A)
visible par A / invisible par B ; (2) INSERT forgé tenant_id=B depuis scope A rejeté par WITH CHECK.
+ AJOUTER le fichier à la liste du job CI « Migrations — Alembic + RLS » (ci.yml) — sinon jamais exécuté.
GATES : pytest (hors e2e/evals) + ruff. Pas de PG local → collection + skip propre, preuve verte au CI.
PREUVE : neutraliser le scope → test rouge → restaurer byte-identique.
```
