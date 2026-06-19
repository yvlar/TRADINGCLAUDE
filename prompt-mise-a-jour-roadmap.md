# Sprint 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI »

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.92.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (205) a généralisé le garde anti-contournement asyncpg de `app/workers/` à **tout `app/**/*.py`** (scan AST + allowlist nommée de 2 fichiers, anti-vacuité prouvée) — décision tranchée meta-test AST plutôt que ruff banned-api. État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** : le job CI « Migrations — Alembic + RLS » exécute les tests d'intégration via une **liste explicite de fichiers** (`ci.yml:235-248`). Tout `tests/integration/test_*.py` oublié de cette liste est skippé localement (pas de PG) ET jamais exécuté en CI : couverture zéro silencieuse. **Gap déjà présent** (voir Réconciliation) : `test_quota_integration.py` est `@pytest.mark.integration` mais absent de la liste. Ce sprint pose un meta-test (patron S200/S205) qui ferme la fenêtre — et corrige le gap découvert.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.92.0)
2. `.claude/rules/tests-pyramide.md` (pyramide, meta-test = niveau statique ; marqueur `@pytest.mark.integration`).
3. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - Liste explicite des fichiers d'intégration dans le job CI : `.github/workflows/ci.yml:235-248` (bloc `run: >- pytest …`, 14 fichiers après S205), job « Migrations — Alembic + RLS » (`ci.yml:152`) — re-grep les lignes exactes.
   - Patron de meta-test AST/statique réutilisable : `tests/meta/test_no_direct_asyncpg_in_app.py` (helpers de parsing, `frozenset` d'allowlist, anti-vacuité) — livré S200, généralisé S205.
   - **Gap à corriger (vérifié S205, re-vérifier)** : `tests/integration/` contient **15** fichiers `test_*.py` ; la liste CI en nomme **14** — `tests/integration/test_quota_integration.py` (`pytestmark = [pytest.mark.integration]`, `:24-25`) est absent de `ci.yml`. Trancher en session : soit le fichier exige une vraie DB (→ l'ajouter à la liste), soit il est volontairement hors job DB (→ documenter l'exclusion dans le meta-test).
   - **Décision à trancher AVANT d'implémenter** : le meta-test lit-il la liste CI en **parsant `ci.yml` (YAML)** ou par **scan texte/regex de la commande `pytest …`** ? Le bloc est un scalaire `>-` multi-lignes : parser le YAML donne une chaîne, qu'il faut tokenizer ; un regex `tests/integration/test_\w+\.py` sur le texte est plus robuste au reformatage. Trancher selon la fragilité.

---

## TÂCHE — Sprint 206 : meta-test « tout test d'intégration est câblé dans le CI »

**Objectif** : un meta-test (patron S200/S205) qui échoue dès qu'un `tests/integration/test_*.py` (marqué `@pytest.mark.integration`) n'apparaît PAS dans la liste explicite du job CI « Migrations — Alembic + RLS ». Verrouille la discipline manuelle (S201/S203/S205 ont chacun édité `ci.yml` à la main) : un fichier oublié = couverture zéro silencieuse.

### Spécification

1. **Découvrir les fichiers d'intégration** : énumérer `tests/integration/test_*.py`. Ne retenir que ceux réellement marqués `@pytest.mark.integration` (au niveau module via `pytestmark` ou par marqueur — décider d'une détection robuste : import AST du marqueur, ou exécution `pytest --collect-only -m integration`). Un fichier non-integration (helper, unitaire égaré) n'a pas à être dans le job DB.
2. **Extraire la liste CI** : lire les fichiers `tests/integration/test_*.py` nommés dans le bloc `run` du job (`ci.yml:235-248`). Décision parsing YAML vs regex tranchée ci-dessus.
3. **Assertion** : `set(fichiers_integration_marqués) ⊆ set(fichiers_cités_CI)` (tout fichier marqué doit être câblé). Message d'erreur listant les fichiers manquants (fichier précis), pour qu'un oubli futur soit immédiatement localisable.
4. **Corriger le gap découvert** : `test_quota_integration.py` est marqué integration et absent du CI. Trancher : (a) il exige PG/Redis → l'**ajouter** à la liste explicite `ci.yml` (le meta-test passe au vert) ; (b) il est volontairement hors job DB → l'ajouter à une **allowlist d'exclusion nommée+commentée** dans le meta-test (le WHY). **Ne pas** rendre le test vert en vidant l'invariant.
5. **Anti-vacuité** : un test prouve que retirer un fichier de la liste CI (simulé en mémoire, pas d'édition de `ci.yml`) rend le scan rouge — l'invariant est load-bearing.
6. **Conventions** : type hints/docstrings FR ; pas de `print` ; aucun mock, lecture du système de fichiers local uniquement (comme S200/S205).

### Tests / validation
- **Meta-test** : (1) en l'état, tout fichier integration est câblé (vert APRÈS correction du gap) ; (2) anti-vacuité — liste CI amputée d'un fichier (en mémoire) → rouge avec le fichier manquant localisé ; (3) détection robuste du marqueur (un fichier integration ajouté hors liste → rouge).
- **Gates** : pytest (hors e2e/evals) + ruff. Frontend non touché.
- **Preuve d'acceptation observable** : créer un `tests/integration/test_zzz_probe.py` factice marqué `@pytest.mark.integration` (non ajouté à `ci.yml`) → meta-test **rouge** le localisant ; le supprimer → **vert**. (Alternative sans fichier réel : injecter le nom dans la fonction de découverte.)

### Note environnement conteneur web
`.venv` via hook `SessionStart` (sinon `pip install -r requirements.txt` — **`stripe` + `alembic` peuvent manquer**, les réinstaller) ; frontend non requis. Le meta-test ne nécessite **pas** de PG (lecture de fichiers).

---

## SPRINTS SUGGÉRÉS (suite Ops/E5 + frontend)

### Sprint 207 — Frontend : hook partagé `useQuota` + CTA contextuel à quota épuisé
**Objectif** : extraire un hook `useQuota(tenantId)` consommé par `QuotaBadge` ET la carte Quota de `/facturation` (mêmes clé/options, logique fail-open unique), et afficher un CTA « Passer à Pro » contextuel dans la carte quand `remaining === 0` et plan `free`.
**Complexité** : Faible.
**Justification** : findings écartés-YAGNI des revues S202/S205 — dès qu'un 3ᵉ consommateur apparaît, la duplication clé/options/fail-open devient un risque de divergence réel.
**Référence** : `frontend/src/components/QuotaBadge.tsx` (`useQuery` `:12`, `queryKey ['quota', tenantId]` `:13`, `retry: false` `:18`) — vérifié S205 ; carte Quota `BillingPage.tsx` (`billing-quota-card` `:187`, `getQuota` `:105`) — livrée S202, vérifiée S205 ; le hook et le CTA sont **à créer**.

### Sprint 208 — Ops : nettoyage du test frère E4-S7 (cleanup non protégé)
**Objectif** : aligner `tests/integration/test_stripe_billing_webhook.py` sur le patron `finally` imbriqué de S201 (un échec du DELETE de cleanup ne doit ni masquer l'échec d'origine ni laisser le pool ouvert).
**Complexité** : Faible.
**Justification** : finding hors-diff de la revue S201 — micro-sprint d'hygiène, zéro comportement.
**Référence** : `tests/integration/test_stripe_billing_webhook.py` cleanup inline dans `finally` (`:134-138`, 3 DELETE inline) — vérifié S205 ; patron cible : `test_stripe_plan_to_quota.py` (finally imbriqué) — livré S201.

### Sprint 209 — Frontend : recherche/tri de la table Tenants admin
**Objectif** : ajouter un filtre client (par nom/slug/plan) + tri sur la section « Tenants » de la page Admin, sur le modèle du filtre de la section Journal d'audit.
**Complexité** : Faible.
**Justification** : l'onboarding B2B fait croître la liste des tenants ; le filtre client de la section audit est un patron déjà éprouvé à réutiliser.
**Référence** : section « Tenants » `frontend/src/pages/AdminPage.tsx` (`admin-tenants-section` `:401`, query `['admin-tenants']` `:120`) — livrée S204, vérifiée S205 ; patron de filtre client `AdminPage.tsx` (`filterAction` `:80`, `useMemo filteredEntries` `:102`) — existant, vérifié S205 ; le filtre Tenants est **à créer**.

### Sprint 210 — Ops : meta-test « toute table métier RLS est dans la matrice d'isolation »
**Objectif** : verrouiller par un meta-test (patron S200/S205) que toute table portant `ENABLE ROW LEVEL SECURITY` dans une migration Alembic apparaît dans la matrice paramétrée de `tests/integration/test_rls_isolation.py` — une 8ᵉ table RLS ajoutée sans ligne de matrice serait non prouvée silencieusement.
**Complexité** : Moyenne.
**Justification** : symétrique de S205/S206 (le scan statique remplace la discipline manuelle) ; la RLS multi-tenant est l'invariant de sécurité n°1 du produit.
**Référence** : matrice paramétrée `tests/integration/test_rls_isolation.py` — existante (S165, citée `ROADMAP.md`) ; migrations RLS dans `alembic/versions/` (ex. `0006_usage_events.py` `ENABLE`+`FORCE`, cité `ROADMAP.md`) — **re-grep les `ENABLE ROW LEVEL SECURITY` exacts en session** ; le meta-test est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (FastAPI + Ops) sur TradingClaude. Lis CLAUDE.md,
ROADMAP.md (v10.92.0), .claude/rules/tests-pyramide.md.
Sprint actif : 206 — Ops : meta-test « tout test d'intégration est câblé dans le CI ».
COMMENCE PAR RE-GREP : liste explicite ci.yml:235-248 (job « Migrations — Alembic + RLS » :152),
fichiers tests/integration/test_*.py (15) vs liste CI (14) — test_quota_integration.py absent (pytest.mark.integration :24-25),
patron meta-test tests/meta/test_no_direct_asyncpg_in_app.py.
TRANCHE D'ABORD : parsing YAML vs regex texte pour lire la liste CI ; et sort du gap test_quota_integration
(ajouter à ci.yml OU allowlist d'exclusion commentée).
LIVRABLE : meta-test set(integration marqués) ⊆ set(cités CI), anti-vacuité (retirer un fichier → rouge),
gap test_quota_integration corrigé.
GATES : pytest (hors e2e/evals) + ruff. Frontend non touché. Pas de PG requis (lecture de fichiers).
PREUVE : test_zzz_probe.py integration non câblé → rouge le localisant ; retiré → vert.
```
