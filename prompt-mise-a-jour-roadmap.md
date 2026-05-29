# Sprint 124 — Persistance des préférences Screener côté serveur

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.10.0 — Sprint 123 complété)

**Nouveauté Sprint 123** — Code-splitting du frontend : les 14 pages du routeur sont chargées en `React.lazy` + `Suspense` (fallback `RouteFallback`), et recharts est isolé hors du bundle d'entrée (chunks séparés par page + chunk recharts dédié, vérifiés via `vite build`).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests vérifiés) : **`ROADMAP.md`** — source unique. Cette carte ne duplique pas l'état, elle y renvoie (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.10.0, Sprint 123 ✅
3. `.claude/rules/conventions-python.md` — pattern `execute()`/endpoints async, docstrings FR, style Python (cœur du sprint : nouveau service + endpoint)
4. `.claude/rules/tests-pyramide.md` — niveau intégration obligatoire pour tout nouvel endpoint FastAPI ; patch `call_claude_with_retry`
5. Point de départ exact : `frontend/src/lib/screenerView.ts` (persistance localStorage actuelle) + `frontend/src/components/ScreenerTable.tsx` (seul consommateur) ; côté backend `app/api/endpoints/annotations.py` (modèle d'endpoint auth+DB via `request.state.user_id`)

---

## TÂCHE — Sprint 124 : Persistance des préférences Screener côté serveur

**Objectif** : migrer le tri + les filtres du Screener du `localStorage` (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié, pour offrir une continuité multi-appareils. Le `localStorage` reste un fallback hors-ligne / anti-flash.

### Réconciliation préalable (vérifié cette session — `fichier:ligne`)
- Persistance localStorage actuelle : `frontend/src/lib/screenerView.ts` — `loadSortState`/`saveSortState` (localStorage `:18`/`:32`, clé `SORT_STORAGE_KEY` `:10`), `loadLabelFilter`/`saveLabelFilter` (`:40`/`:52`, clé `FILTER_STORAGE_KEY` `:11`). Seul consommateur : `frontend/src/components/ScreenerTable.tsx`.
- Identité utilisateur côté backend : le middleware pose `request.state.user_id` (JWT `sub`) — `app/middleware/auth.py:102`. Modèle d'endpoint lisant `request: Request` : `app/api/endpoints/annotations.py:23`.
- Migrations SQL : `infra/postgres/` (fichiers `migration_sprintNN.sql`, ex. `migration_sprint48.sql`) + `init.sql`. **À CRÉER** : table `user_preferences`, endpoints `/preferences/screener`.

### Spécification

1. **Migration SQL** — créer `infra/postgres/migration_sprint124.sql` : table `user_preferences (user_id TEXT/UUID selon le type de `sub`, key TEXT, value JSONB, updated_at TIMESTAMPTZ, PRIMARY KEY (user_id, key))`. Vérifier le type réel de `user_id` (cf. `init.sql` / table des comptes) avant de figer le type de colonne. Reporter aussi la création dans `init.sql` pour les nouveaux environnements.
2. **Service** — `app/services/user_preferences_service.py` : `get_preference(db_pool, user_id, key) -> dict | None` et `upsert_preference(db_pool, user_id, key, value: dict)` (asyncpg, `INSERT ... ON CONFLICT (user_id, key) DO UPDATE`). Type hints + docstrings FR.
3. **Endpoints** — `app/api/endpoints/preferences.py` (monté dans `app/api/main.py`) :
   - `GET /preferences/screener` → `{ "sort": {...} | null, "filter": [...] | null }` (200 ; 401 si non authentifié)
   - `PUT /preferences/screener` → corps Pydantic `{ sort?: ScreenerSort, filter?: string[] }`, upsert sous la clé `screener`, renvoie l'état persisté
   - Lire `request.state.user_id` ; 401 propre si absent. Schemas Pydantic v2 dédiés (pas de `dict` nu).
4. **Frontend** — `frontend/src/api/preferences.ts` (client typé `getScreenerPreferences` / `putScreenerPreferences` via `client.ts`, CSRF/cookies) ; types dans `frontend/src/types/index.ts`. Dans `ScreenerTable.tsx` : au montage, charger les préférences serveur (fallback `localStorage` si 401 / réseau KO / champ null) ; à chaque changement de tri/filtre, persister côté serveur (et garder le miroir `localStorage` pour l'anti-flash au prochain montage). Aucune régression du comportement hors-ligne.

### Tests obligatoires (pyramide)
- **Intégration** (backend) : `GET`/`PUT /preferences/screener` — 200 avec session valide, 401 sans session, round-trip (PUT puis GET renvoie la valeur), upsert idempotent. Utiliser la fixture `client` (`tests/conftest.py`). ⚠️ Aucun appel Claude ici, mais respecter le patch si un import le déclenche.
- **Unitaire** (backend) : service `upsert_preference`/`get_preference` (mock du pool ou DB d'intégration selon le pattern existant des services).
- **Composant** (frontend) : `ScreenerTable` charge les préférences serveur au montage (mock `getScreenerPreferences`) et bascule sur `localStorage` si l'appel échoue ; happy path + cas d'erreur.
- Tous les tests existants restent verts (les tests `screenerView` localStorage ne doivent pas régresser).

### Note d'environnement (session web)

Conteneur cloné à neuf ; dépendances préparées par le hook `SessionStart` → `scripts/setup-web-session.sh` (idempotent). ⚠️ **Si `frontend/node_modules` est absent, lancer `cd frontend && npm install`** (constaté Sprint 123 : le hook n'installe pas les deps npm). Commandes ensuite :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && node node_modules/vitest/vitest.mjs run` ; `node node_modules/typescript/bin/tsc --noEmit` ; `node node_modules/eslint/bin/eslint.js src`
- ⚠️ `cd frontend` persiste le cwd entre commandes — revenir à la racine avant les commandes backend
- La stack Docker (Postgres/Redis/Qdrant) n'est pas démarrée → la migration SQL ne peut pas être exécutée live dans le conteneur (valider la syntaxe + les tests d'intégration qui montent leur propre DB selon `conftest.py`). Pas de test navigateur live possible.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 125 — Annotations enrichies : tags + filtres
**Objectif** : ajouter un champ `tags` (liste de mots-clés libres) aux annotations, indexé GIN, filtrable via `GET /history?tags=value,growth` ; chips affichées dans `HistoryTable` et `AnnotationSection`.
**Complexité** : Moyenne
**Justification** : les annotations (Sprint 78) sont du texte libre sans structure ; les tags permettent un filtrage sémantique du portefeuille sans RAG.
**Référence** : EXISTANT (vérifié) — service `app/services/annotation_service.py`, endpoint `app/api/endpoints/annotations.py:22` (`upsert_annotation`) ; composants `frontend/src/components/AnnotationSection.tsx`, `frontend/src/components/HistoryTable.tsx`. À CRÉER — champ `tags`, index GIN, filtre `/history?tags=`.

### Sprint 126 — Vue « Portefeuille » agrégée
**Objectif** : page `/portefeuille` synthétisant la watchlist par pilier (ETF/thématique/valeur/algo) avec allocation cible vs réelle et score composite moyen par pilier.
**Complexité** : Élevée
**Justification** : matérialise le cadre four-pillar du projet, aujourd'hui conceptuel ; relie watchlist, composite_score et fiscalité par compte.
**Référence** : EXISTANT (vérifié) — `compute_composite_score` `app/services/composite_score.py:86`, modèle `class CompositeScore` `:19` ; page `frontend/src/pages/WatchlistPage.tsx`. À CRÉER — page `/portefeuille`, agrégation par pilier, allocation cible vs réelle.

### Sprint 127 — Cohérence inter-skills affichée dans l'UI
**Objectif** : exposer `inter_skill_conflicts` (déjà calculé côté backend, présent dans `AnalyzeResponse`) dans `AnalysisResult` — bannière listant les contradictions détectées entre skills.
**Complexité** : Faible
**Justification** : la donnée existe mais n'est pas rendue ; valeur immédiate pour repérer les thèses contradictoires.
**Référence** : EXISTANT (vérifié) — calcul `app/orchestrator/core.py:140` (`_detect_inter_skill_conflicts`), champ réponse `:245` (peuplé `:1031`), type frontend `frontend/src/types/index.ts:459`. NON rendu dans `frontend/src/components/AnalysisResult.tsx` (aucune référence — confirmé cette session). À CRÉER — bannière de contradictions.

### Sprint 128 — Comparaison de deux analyses d'un même ticker (diff temporel)
**Objectif** : `GET /ticker-report/{ticker}/diff?from_id=&to_id=` produisant un PDF (ou JSON) comparant deux analyses persistées du même ticker — évolution des verdicts skill par skill, du composite_score et des ratios clés.
**Complexité** : Moyenne
**Justification** : capitalise sur la reconstruction multi-skills du Sprint 122 ; donne une lecture « avant/après » d'une thèse dans le temps.
**Référence** : EXISTANT (vérifié) — endpoint `app/api/endpoints/ticker_report.py:26` + param `analysis_id` `:34` (reconstruction multi-skills Sprint 122). À CRÉER — route `/ticker-report/{ticker}/diff`, logique de comparaison.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.10.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 124 — Persistance des préférences Screener côté serveur (table user_preferences
PostgreSQL + service asyncpg + endpoints GET/PUT /preferences/screener auth-scoped via
request.state.user_id ; frontend : client preferences.ts + ScreenerTable charge le serveur
au montage avec fallback localStorage). Tests intégration endpoint + composant obligatoires.
```
