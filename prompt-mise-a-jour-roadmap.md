# Sprint 191 — Ops : `FORCE RLS` vérifié par test sur les 7 tables (verrou anti-régression)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.77.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (190, E5-S9) a ajouté la purge totale du cache react-query au `logout` (`queryClient.clear()` inconditionnel dans `AuthContext.tsx`) → hygiène cross-tenant côté SPA. État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul** (test d'intégration RLS) : asserter en CI que les 7 tables RLS portent `relforcerowsecurity = true` (catalogue `pg_class`), pour qu'une future migration ajoutant une table RLS sans `FORCE` (ou le retirant) échoue immédiatement. GATES : `pytest` (hors e2e/evals) + `ruff check`. Le nouveau test est `@pytest.mark.integration` (skippé hors PG migré) et tourne en CI sous le rôle réel `app_runtime`. **Pas de frontend, pas d'eval** (lecture catalogue PG — aucun prompt de skill ni l'orchestrateur touché).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.77.0)
2. `.claude/rules/tests-pyramide.md` (niveau **Intégration** — `@pytest.mark.integration`, skip hors PG migré ; c'est le cœur du sprint) **et** `.claude/rules/gotchas-operationnels.md` (conventions des tests d'intégration RLS sous rôle réel).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **L'ensemble des 7 tables RLS** : `_RLS_TABLES` (`tests/integration/test_revoke_public_rls.py:31`, vérifié cette session ; commentaire « 7 tables RLS » à `:30`) — réutiliser cet ensemble (ou son équivalent) plutôt que ré-énumérer de mémoire, pour rester synchrone avec S186.
   - **Le harnais d'intégration RLS existant** (connexion sous rôle `app_runtime` NOSUPERUSER, skip hors PG migré, gate CI) : `tests/integration/test_revoke_public_rls.py` (S186) et `tests/integration/test_rls_isolation.py` (S165) — calquer la fixture/skip et l'ajout au gate NOSUPERUSER de `.github/workflows/ci.yml`.
   - **La colonne catalogue à asserter** : `pg_class.relforcerowsecurity` (booléen ; `true` quand `FORCE ROW LEVEL SECURITY` est posé) — requête en lecture seule du catalogue, exécutable sous `app_runtime`.

---

## TÂCHE — Sprint 191 : `FORCE RLS` vérifié par test sur les 7 tables

**Objectif** : rendre l'invariant `FORCE ROW LEVEL SECURITY` **explicite et auto-documenté** par un test direct. Aujourd'hui (§2.3 OWASP), `FORCE` est prouvé **indirectement** — la matrice d'isolation (`test_rls_isolation.py`) échouerait si une table perdait `FORCE`, mais aucun test ne l'asserte en propre. Un test ciblé sur `relforcerowsecurity` rend la régression impossible à introduire silencieusement.

### Spécification

1. **Nouveau test d'intégration** (`tests/integration/test_force_rls.py` ou ajout dans un fichier RLS existant — trancher selon le périmètre) : sous le rôle réel `app_runtime`, lire `pg_class.relforcerowsecurity` pour les 7 tables RLS et asserter que **toutes** portent `true`. Réutiliser `_RLS_TABLES` (importer depuis `test_revoke_public_rls.py` ou centraliser l'ensemble si la duplication devient gênante — décision à trancher, ne pas dupliquer une 3ᵉ copie sans raison).
2. **Assertion non vacue** : vérifier d'abord que les 7 lignes sont bien trouvées (`{r["relname"]} == set(_RLS_TABLES)`, « tables RLS introuvables (PG migré ?) ») avant d'asserter `relforcerowsecurity`, pour qu'un environnement sans PG migré skippe proprement plutôt que de passer à vide.
3. **Gate CI** : ajouter le test au gate NOSUPERUSER de `.github/workflows/ci.yml` (à côté de `test_revoke_public_rls.py`).
4. **Marqueur** : `@pytest.mark.integration` + skip hors PG migré (calquer le harnais existant).

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` (le nouveau test skippé hors PG dans le conteneur web — le DIRE) + `ruff check` + `mypy app/` (si du code `app/` est touché — a priori non, test seul).
- **Preuve d'acceptation observable** : sous PG migré (CI), le test PASSE (les 7 tables portent `relforcerowsecurity = true`) ; hors PG migré (conteneur web), il SKIP proprement. **Pas de frontend, pas d'eval**.
- **Pas de Docker/PG dans le conteneur web** → la preuve réelle tourne en CI sous `app_runtime` ; localement, constater le skip et la forme du test.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 192 — Ops : garde `require_secure_db_url` uniformisé sur tous les pools runtime
**Objectif** : faire passer les **9 pools workers** par le même garde insecure-creds que le boot API, en l'absorbant dans `create_runtime_pool()` (ou un appel câblé dans le helper) — aujourd'hui seuls les pools API le portent.
**Complexité** : Faible.
**Justification** : finding d'altitude **différé** des revues S187 — laisser le garde API-only laisse un special-case permanent. Le rendre uniforme ferme un gap : un worker qui boote en prod avec des creds par défaut devrait échouer comme l'API. **Assumé comme changement de comportement** (d'où un sprint dédié avec tests de boot workers).
**Référence** : `require_secure_db_url` (`app/utils/security_config.py:41`, vérifié cette session) appelé **uniquement** à `app/api/main.py:158` (vérifié) ; `create_runtime_pool` (`app/db/pool.py:9`, vérifié) est le home naturel. L'absorption + les tests de boot workers sont **à créer**.

### Sprint 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration)
**Objectif** : extraire le harnais répété des tests d'intégration RLS (connexion sous rôle réel `app_runtime`/NOSUPERUSER, pose du GUC tenant, skip hors PG migré, et **l'ensemble `_RLS_TABLES`** s'il est désormais dupliqué entre S186 et S191) en une fixture/helper partagé.
**Complexité** : Moyenne.
**Justification** : finding **écarté** en S185 (« refactor suite-wide ») et toujours ouvert — plusieurs `tests/integration/test_*_rls.py` répètent le même setup. Le Sprint 191 risque d'ajouter une 2ᵉ/3ᵉ copie de `_RLS_TABLES` → ce sprint la centraliserait. À cadrer prudemment (ne pas casser la convention de skip existante).
**Référence** : les tests d'intégration RLS existent (`tests/integration/test_revoke_public_rls.py`, `test_rls_isolation.py`, `test_app_runtime_rls.py` — cités dans `ROADMAP.md`, à re-`grep` pour le harnais exact). Le helper/fixture partagé est **à créer** ; le périmètre exact (combien de fichiers convergent) est **à mesurer** avant de s'engager.

### Sprint 194 — E5 : helper front partagé `extractDetailMessage` (dé-duplication des parseurs d'erreur)
**Objectif** : extraire la logique de parsing du corps `detail` (objet structuré / tableau de validation Pydantic / string) répétée entre `client.ts` (`request`), `analyze.ts` (`streamAnalyze` SSE) et `quotaDetailFromError` (`QuotaBanner.tsx`) en un helper unique, pour fermer le risque de dérive entre parseurs.
**Complexité** : Faible.
**Justification** : note qualité **écartée** à la revue S189 (split pré-existant, hors périmètre du delta). Les deux parseurs diffèrent déjà légèrement dans l'ordre des gardes (array-first dans `client.ts`, object-with-`!Array` dans `analyze.ts`) ; un helper partagé supprime la divergence.
**Référence** : `request` (`frontend/src/api/client.ts:52`/`:99`, branches `if (!response.ok)`, vérifié cette session — distingue array/object/string), `streamAnalyze` (`frontend/src/api/analyze.ts`, même distinction), `quotaDetailFromError` (`frontend/src/components/QuotaBanner.tsx:14`, vérifié). Le helper partagé est **à créer**.

### Sprint 195 — E5 : test e2e/composant du flux re-connexion cross-tenant (compléter S190)
**Objectif** : ajouter un test qui simule le scénario complet « logout tenant A → login tenant B sans rechargement » et asserte qu'aucune donnée de A n'apparaît (vs S190 qui prouve le **mécanisme** `clear()`, pas le flux applicatif bout-en-bout).
**Complexité** : Moyenne.
**Justification** : S190 a fermé la fuite par la purge ; un test de flux verrouille l'**intention** (pas juste l'appel `clear()`). Note de couverture relevée à la revue S190 (« le flux re-login-as-different-tenant n'est pas littéralement simulé »).
**Référence** : `logout`/`login` (`frontend/src/contexts/AuthContext.tsx`, vérifié S190 — `queryClient.clear()` dans `logout`) ; le test de flux multi-tenant est **à créer** (composant avec deux `authMe`/`authLogin` mockés successifs + assertions sur le cache, ou e2e Playwright si le périmètre le justifie).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.77.0),
.claude/rules/tests-pyramide.md et gotchas-operationnels.md.
Sprint actif : 191 — Ops : FORCE RLS vérifié par test sur les 7 tables. Ajouter un test d'intégration
(@pytest.mark.integration, skip hors PG migré) qui, sous le rôle réel app_runtime, lit
pg_class.relforcerowsecurity pour les 7 tables RLS et asserte qu'elles portent toutes true.
À VÉRIFIER AVANT D'ÉCRIRE : _RLS_TABLES (tests/integration/test_revoke_public_rls.py:31, commentaire :30) —
le réutiliser, ne pas ré-énumérer de mémoire. Assertion non vacue : vérifier d'abord que les 7 lignes
sont trouvées (sinon skip/erreur claire) avant d'asserter relforcerowsecurity. Ajouter le test au gate
NOSUPERUSER de .github/workflows/ci.yml (à côté de test_revoke_public_rls.py).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : pytest (hors e2e/evals) + ruff check. Pas de frontend, pas d'eval.
Preuve : sous PG migré (CI) le test PASSE (7 tables relforcerowsecurity=true) ; hors PG migré il SKIP.
```
