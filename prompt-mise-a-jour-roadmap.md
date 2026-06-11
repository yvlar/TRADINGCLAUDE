# Sprint 205 — Ops : étendre le garde anti-contournement asyncpg à `app/` entier (allowlist)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.91.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (204) a livré `GET /admin/tenants` (admin only, LEFT JOIN `subscriptions`, modèle `TenantAdminEntry`) + une section « Tenants » sur la page Admin (tableau nom/slug/plan/customer Stripe tronqué/date). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** : S200 a posé un meta-test (scan AST) interdisant tout `asyncpg.create_pool`/`connect` direct dans `app/workers/`. Mais un endpoint ou service de `app/` pourrait encore créer un pool direct — contournant le garde insecure-creds (`require_secure_db_url`) ET le hook tenant RLS câblé par `create_runtime_pool`. Ce sprint généralise le scan à **tout `app/`** avec une **allowlist explicite** des deux usages légitimes.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.91.0)
2. `.claude/rules/tests-pyramide.md` (pyramide, meta-test = niveau statique) + `.claude/rules/api-architecture.md` (contraintes `app/`, pool/infra).
3. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `tests/meta/test_no_direct_asyncpg_in_workers.py` — `_is_asyncpg_module` (`:32`), `_scan_violations` (`:85`), boucle de scan (`:122`) — scan AST réutilisable, vérifié S204.
   - Usages légitimes à **allowlister** : `app/db/pool.py:24-25` (`require_secure_db_url(dsn)` → `asyncpg.create_pool`) et `app/db/provision_app_runtime.py:47` (`asyncpg.connect(admin_url)` — provisioning admin sous superuser, hors RLS volontairement) — vérifiés `grep` S204.
   - **Décision à trancher AVANT d'implémenter** : meta-test AST généralisé (patron S200) **vs** règle lint `ruff` banned-api (`flake8-tidy-imports` / `TID251`). Trancher en session selon le coût de maintenance de l'allowlist.

---

## TÂCHE — Sprint 205 : généraliser le garde anti-contournement asyncpg à `app/`

**Objectif** : un meta-test (ou règle lint) qui échoue dès qu'un fichier de `app/` (hors allowlist) fabrique une connexion asyncpg directe (`asyncpg.create_pool`, `asyncpg.connect`, et leurs formes dérivées déjà couvertes par `_scan_violations` : alias, sous-modules, `from asyncpg import …`, wildcard).

### Spécification

1. **Étendre le scan** : appliquer `_scan_violations` (ou un équivalent factorisé) à **tout `app/**/*.py`** au lieu du seul `app/workers/`. Réutiliser la logique S200 (immunité commentaires/docstrings via AST, pas de faux positif sur les type hints `asyncpg.Pool`).
2. **Allowlist explicite** : exactement deux fichiers exemptés — `app/db/pool.py` (le chokepoint `create_runtime_pool`) et `app/db/provision_app_runtime.py` (provisioning admin). L'allowlist doit être une **constante nommée et commentée** (le WHY de chaque exemption), pas une exception silencieuse. **Anti-vacuité** : un test prouve que retirer un fichier de l'allowlist rend le scan rouge (l'allowlist est load-bearing, pas décorative).
3. **Si décision = ruff banned-api** : configurer `[tool.ruff.lint.flake8-tidy-imports.banned-api]` dans `pyproject.toml`/`ruff.toml` avec `per-file-ignores` pour les deux fichiers allowlistés ; documenter le choix. Vérifier que `ruff check app/` reste vert (les 2 usages légitimes ignorés) et qu'un usage ajouté ailleurs casse.
4. **Conventions** : type hints/docstrings FR ; pas de `print`.

### Tests / validation
- **Meta-test** : (1) scan de `app/` vert en l'état (les 2 usages légitimes allowlistés) ; (2) anti-vacuité — bypass synthétique ajouté dans un fichier `app/` réel hors allowlist → scan rouge (fichier+ligne localisés), restauré byte-identique (sha256) ; (3) retrait d'un fichier de l'allowlist → rouge.
- **Gates** : pytest (hors e2e/evals) + ruff. Frontend non touché.
- **Preuve d'acceptation observable** : ajouter `asyncpg.create_pool(...)` dans un endpoint réel (ex. `app/api/endpoints/admin.py`) → meta-test/lint **rouge** ; le retirer → **vert** ; fichier restauré sha256-identique.

### Note environnement conteneur web
`.venv` via hook `SessionStart` (sinon `pip install -r requirements.txt` — **`stripe` + `alembic` peuvent manquer**, les réinstaller) ; frontend non requis pour ce sprint.

---

## SPRINTS SUGGÉRÉS (suite Ops/E5)

### Sprint 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI »
**Objectif** : verrouiller par un meta-test (patron S200) que chaque `tests/integration/test_*.py` apparaît dans la liste explicite du job CI « Migrations — Alembic + RLS » — un fichier oublié est skippé localement ET jamais exécuté en CI : couverture zéro silencieuse.
**Complexité** : Faible.
**Justification** : finding d'altitude S201 ; S201/S203 ont chacun dû éditer `ci.yml` à la main — la discipline manuelle ne se prouve pas.
**Référence** : liste explicite `.github/workflows/ci.yml:235-248` (14 fichiers d'intégration après S203 — re-grep les lignes exactes) — vérifié S204 ; patron `tests/meta/test_no_direct_asyncpg_in_workers.py` — livré S200 ; le meta-test est **à créer**.

### Sprint 207 — Frontend : hook partagé `useQuota` + CTA contextuel à quota épuisé
**Objectif** : extraire un hook `useQuota(tenantId)` consommé par `QuotaBadge` ET la carte Quota de `/facturation` (mêmes clé/options, logique fail-open unique), et afficher un CTA « Passer à Pro » contextuel dans la carte quand `remaining === 0` et plan `free`.
**Complexité** : Faible.
**Justification** : findings écartés-YAGNI de la revue S202 — dès qu'un 3ᵉ consommateur apparaît, la duplication clé/options/fail-open devient un risque de divergence réel.
**Référence** : `frontend/src/components/QuotaBadge.tsx` (query `:12-20`) — vérifié S202 ; carte Quota `BillingPage.tsx` — livrée S202 ; le hook et le CTA sont **à créer**.

### Sprint 208 — Ops : nettoyage du test frère E4-S7 (cleanup non protégé)
**Objectif** : aligner `tests/integration/test_stripe_billing_webhook.py` sur le patron `finally` imbriqué de S201 (un échec du DELETE de cleanup ne doit ni masquer l'échec d'origine ni laisser le pool ouvert).
**Complexité** : Faible.
**Justification** : finding hors-diff de la revue S201 (le fichier frère a un cleanup inline non protégé) — micro-sprint d'hygiène, zéro comportement.
**Référence** : `tests/integration/test_stripe_billing_webhook.py` (cleanup inline ~`:134-138`) — observé revue S201 ; patron cible : `test_stripe_plan_to_quota.py` (finally imbriqué) — livré S201.

### Sprint 209 — Frontend : recherche/tri de la table Tenants admin
**Objectif** : ajouter un filtre client (par nom/slug/plan) + tri sur la section « Tenants » de la page Admin, sur le modèle du filtre de la section Journal d'audit.
**Complexité** : Faible.
**Justification** : l'onboarding B2B fait croître la liste des tenants ; le filtre client de la section audit (`filterAction`/`filterCibleType`) est un patron déjà éprouvé à réutiliser.
**Référence** : section « Tenants » `frontend/src/pages/AdminPage.tsx` — livrée S204 ; patron de filtre client `AdminPage.tsx` (état `filterAction`/`useMemo` `filteredEntries`) — existant ; le filtre Tenants est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (FastAPI + Ops) sur TradingClaude. Lis CLAUDE.md,
ROADMAP.md (v10.91.0), .claude/rules/tests-pyramide.md, .claude/rules/api-architecture.md.
Sprint actif : 205 — Ops : étendre le garde anti-contournement asyncpg à app/ entier (allowlist).
COMMENCE PAR RE-GREP : _scan_violations + _is_asyncpg_module (tests/meta/test_no_direct_asyncpg_in_workers.py),
usages légitimes app/db/pool.py:24-25 + app/db/provision_app_runtime.py:47.
TRANCHE D'ABORD : meta-test AST généralisé (patron S200) vs règle ruff banned-api (TID251) — décider AVANT d'implémenter.
LIVRABLE : scan/lint de tout app/**/*.py interdisant asyncpg.create_pool/connect direct, allowlist nommée+commentée
(app/db/pool.py + app/db/provision_app_runtime.py), anti-vacuité (retirer un fichier de l'allowlist → rouge).
GATES : pytest (hors e2e/evals) + ruff. Frontend non touché.
PREUVE : asyncpg.create_pool ajouté dans un endpoint réel → rouge ; retiré → vert ; fichier sha256-identique.
```
