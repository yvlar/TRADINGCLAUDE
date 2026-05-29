# Sprint 125 — Annotations enrichies : tags + filtres

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.11.0 — Sprint 124 complété)

**Nouveauté Sprint 124** — Les préférences du Screener (tri + filtres) sont persistées côté serveur dans une table `user_preferences` (JSONB, PK `(user_id, key)`) liée au compte authentifié ; `localStorage` reste un fallback hors-ligne / anti-flash. Endpoints `GET`/`PUT /preferences/screener` auth-scopés via `_get_current_user` (cookie JWT).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests vérifiés) : **`ROADMAP.md`** — source unique. Cette carte ne duplique pas l'état, elle y renvoie (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.11.0, Sprint 124 ✅
3. `.claude/rules/conventions-python.md` — pattern endpoint/service async, docstrings FR (cœur du sprint : migration colonne + filtre service + endpoint)
4. `.claude/rules/tests-pyramide.md` — niveau intégration obligatoire pour le filtre `/history` ; fixture `client`
5. `.claude/rules/conventions-frontend.md` — chips de tags (TypeScript strict, `data-testid`, test composant happy + erreur)
6. Point de départ exact (vérifié cette session — `fichier:ligne`) :
   - Table `annotations` (bootstrap lifespan) : `app/api/main.py:193` ; modèle `app/models/annotation.py` (`Annotation`, `AnnotationCreate`)
   - Service : `app/services/annotation_service.py:12` (`AnnotationService`), `upsert` `:18`
   - Endpoint : `app/api/endpoints/annotations.py:23` (`POST` upsert), `:107` (`GET /{analysis_id}`)
   - Route historique : `app/api/main.py:667-668` (`@app.get("/history")`)
   - Frontend : `frontend/src/components/AnnotationSection.tsx`, `frontend/src/components/HistoryTable.tsx`

---

## TÂCHE — Sprint 125 : Annotations enrichies — tags + filtres

**Objectif** : ajouter un champ `tags` (liste de mots-clés libres) aux annotations, filtrable via `GET /history?tags=value,growth`, avec chips affichées et éditables dans `AnnotationSection` et visibles dans `HistoryTable`. Les annotations (Sprint 78) sont aujourd'hui du texte libre sans structure ; les tags permettent un filtrage sémantique léger du portefeuille sans RAG.

### Réconciliation préalable (vérifié cette session — `fichier:ligne`)
- La table `annotations` est créée dans le bootstrap du lifespan (`app/api/main.py:193`), **pas** dans `infra/postgres/init.sql` → la colonne `tags` + l'index GIN doivent être ajoutés (a) dans le bootstrap lifespan via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` et (b) dans `infra/postgres/migration_sprint125.sql` pour les DB existantes.
- `AnnotationCreate` (`app/models/annotation.py:16`) n'a que `analysis_id` + `note` → étendre avec `tags: list[str]`.
- `AnnotationService.upsert` (`app/services/annotation_service.py:18`) écrit uniquement `note` → étendre la requête `INSERT ... ON CONFLICT` pour persister `tags` (JSONB ou `TEXT[]`).
- `/history` (`app/api/main.py:667`) délègue à `orchestrator.get_history` → le filtre `?tags=` se branche là (jointure/filtre sur `annotations.tags`). Vérifier la signature réelle de `get_history` avant de figer l'implémentation.

### Spécification
1. **Migration** — `infra/postgres/migration_sprint125.sql` : `ALTER TABLE annotations ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'` (ou `TEXT[]` — choisir selon le pattern de filtrage retenu) + index GIN sur `tags`. Reporter le `ALTER` + l'index dans le bootstrap lifespan (`app/api/main.py`). Choisir le type (JSONB vs TEXT[]) en fonction de l'opérateur de filtre (`@>` JSONB ou `&&` TEXT[]) — documenter le choix.
2. **Modèle + service** — `tags: list[str] = []` dans `Annotation` et `AnnotationCreate` ; `upsert` persiste les tags ; `get`/`get_all_with_ticker` les renvoient.
3. **Filtre `/history`** — `?tags=value,growth` (CSV → liste) : ne renvoyer que les analyses dont l'annotation porte **tous** (ou **au moins un** — choisir et documenter) les tags demandés. Index GIN obligatoire. 422 si paramètre malformé.
4. **Frontend** — chips de tags éditables dans `AnnotationSection.tsx` (ajout/suppression, persistées via le client annotations) ; chips en lecture seule dans `HistoryTable.tsx` ; filtre `?tags=` câblé depuis l'UI Historique. Types dans `frontend/src/types/index.ts` (`Annotation.tags: string[]`).

### Tests obligatoires (pyramide)
- **Intégration** : `GET /history?tags=` filtre correctement (match / non-match / multi-tags) ; `POST` annotation avec tags round-trip. Fixture `client`.
- **Unitaire** : `AnnotationService.upsert`/`get` avec tags (mock pool).
- **Composant** : `AnnotationSection` ajoute/retire un tag (happy + cas d'erreur) ; `HistoryTable` rend les chips.
- Aucune régression des tests annotations/historique existants.

### Note d'environnement (session web)
Conteneur cloné à neuf ; dépendances préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). ⚠️ **Si `frontend/node_modules` est absent, lancer `npm install` depuis `frontend/`** (le hook n'installe pas les deps npm — constaté Sprints 123-124). Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend (depuis `frontend/`) : `node node_modules/vitest/vitest.mjs run` ; `node node_modules/typescript/bin/tsc --noEmit` ; `node node_modules/eslint/bin/eslint.js src`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker (Postgres/Redis/Qdrant) non démarrée → migration non exécutée live (valider la syntaxe + les tests d'intégration sur DB/pool mocké). Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 126 — Vue « Portefeuille » agrégée
**Objectif** : page `/portefeuille` synthétisant la watchlist par pilier (ETF/thématique/valeur/algo) avec allocation cible vs réelle et score composite moyen par pilier.
**Complexité** : Élevée
**Justification** : matérialise le cadre four-pillar du projet, aujourd'hui conceptuel ; relie watchlist, composite_score et fiscalité par compte.
**Référence** : EXISTANT (vérifié) — `compute_composite_score` `app/services/composite_score.py:86`, `class CompositeScore` `:19` ; page `frontend/src/pages/WatchlistPage.tsx`. À CRÉER — page `/portefeuille`, agrégation par pilier, allocation cible vs réelle.

### Sprint 127 — Cohérence inter-skills affichée dans l'UI
**Objectif** : exposer `inter_skill_conflicts` (déjà calculé côté backend) dans `AnalysisResult` — bannière listant les contradictions détectées entre skills.
**Complexité** : Faible
**Justification** : la donnée existe mais n'est pas rendue ; valeur immédiate pour repérer les thèses contradictoires.
**Référence** : EXISTANT (vérifié) — calcul `app/orchestrator/core.py:140` (`_detect_inter_skill_conflicts`), champ réponse `:245` (peuplé `:1031`), type frontend `frontend/src/types/index.ts:459`. NON rendu dans `frontend/src/components/AnalysisResult.tsx` (0 occurrence `inter_skill` — confirmé cette session). À CRÉER — bannière de contradictions.

### Sprint 128 — Comparaison de deux analyses d'un même ticker (diff temporel)
**Objectif** : `GET /ticker-report/{ticker}/diff?from_id=&to_id=` produisant un PDF (ou JSON) comparant deux analyses persistées du même ticker — évolution des verdicts skill par skill, du composite_score et des ratios clés.
**Complexité** : Moyenne
**Justification** : capitalise sur la reconstruction multi-skills du Sprint 122 ; lecture « avant/après » d'une thèse dans le temps.
**Référence** : EXISTANT (vérifié) — endpoint `app/api/endpoints/ticker_report.py:25` + param `analysis_id` `:34`. À CRÉER — route `/ticker-report/{ticker}/diff`, logique de comparaison.

### Sprint 129 — Préférences utilisateur généralisées (Dashboard / Comparer)
**Objectif** : réutiliser la table `user_preferences` (Sprint 124) pour persister d'autres préférences UI côté serveur (ex. disposition Dashboard, derniers tickers Comparer), via un client générique.
**Complexité** : Faible
**Justification** : capitalise sur l'infrastructure du Sprint 124 (table + service + endpoint pattern) pour étendre la continuité multi-appareils sans nouveau schéma.
**Référence** : EXISTANT (vérifié) — table `user_preferences` bootstrappée `app/api/main.py` (Sprint 124), service `app/services/user_preferences_service.py` (`get_preference`/`upsert_preference`), endpoints `app/api/endpoints/preferences.py`. À CRÉER — clés `dashboard`/`compare`, endpoints/clients génériques.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.11.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 125 — Annotations enrichies : tags + filtres (colonne tags sur la table
annotations + index GIN, filtre GET /history?tags=, chips éditables dans AnnotationSection
et lecture seule dans HistoryTable). Migration + bootstrap lifespan ; tests intégration
filtre /history + composant obligatoires.
```
