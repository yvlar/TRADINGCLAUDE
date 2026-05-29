# Sprint 126 — Vue « Portefeuille » agrégée par pilier

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.12.0 — Sprint 125 complété)

**Nouveauté Sprint 125** — Les annotations (Sprint 78) portent désormais un champ `tags` (mots-clés libres, colonne JSONB + index GIN `jsonb_path_ops`). Filtre `GET /history?tags=value,growth` (containment `@>`, sémantique ET ; aussi sur `/history-paged`, tags seuls autorisés, 422 si malformé), chips éditables dans `AnnotationSection` et en lecture seule dans `HistoryTable`.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests vérifiés) : **`ROADMAP.md`** — source unique. Cette carte ne duplique pas l'état, elle y renvoie (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`) + table Four-pillar (ETF / thématique / valeur / algo)
2. `ROADMAP.md` — état courant v10.12.0, Sprint 125 ✅
3. `.claude/rules/conventions-python.md` — pattern endpoint/service async, docstrings FR (cœur du sprint : migration colonne `pilier` + service d'agrégation + endpoint)
4. `.claude/rules/conventions-frontend.md` — nouvelle page React, TypeScript strict, `data-testid`, test composant happy + erreur (page `/portefeuille` + sélecteur de pilier)
5. Point de départ exact (vérifié cette session — `fichier:ligne`) :
   - Modèle : `app/models/watchlist.py:11` (`WatchlistEntry` — **aucun champ pilier aujourd'hui**), `:30` (`WatchlistCreate`)
   - Service watchlist : `app/services/watchlist_service.py`
   - Score composite : `app/services/composite_score.py:86` (`compute_composite_score`), `:19` (`class CompositeScore`)
   - Champ déjà persisté par entrée : `WatchlistEntry.last_composite_score` (`app/models/watchlist.py:24`), `last_esg_score` (`:27`)
   - Page watchlist existante : `frontend/src/pages/WatchlistPage.tsx`
   - Table `watchlist` bootstrappée via lifespan : `app/api/main.py` (chercher `ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS …` — pattern Sprint 124/125)

---

## TÂCHE — Sprint 126 : Vue « Portefeuille » agrégée par pilier

**Objectif** : matérialiser le cadre Four-pillar du projet (aujourd'hui purement conceptuel — **aucun champ pilier n'existe sur `watchlist`**) en (a) ajoutant une classification `pilier` à chaque entrée de watchlist et (b) exposant une page `/portefeuille` qui agrège la watchlist par pilier : nombre de positions, score composite moyen, score ESG moyen, et allocation cible vs réelle par pilier.

### Réconciliation préalable (vérifié cette session — `fichier:ligne`)
- `WatchlistEntry` (`app/models/watchlist.py:11`) n'a **pas** de champ `pilier`/`pillar`/`category` (`grep` → 0 résultat) → la colonne `pilier` est **à créer** (migration + bootstrap lifespan + modèle).
- `last_composite_score` (`app/models/watchlist.py:24`) et `last_esg_score` (`:27`) sont **déjà persistés** par entrée → l'agrégation par pilier les consomme sans recalcul Claude.
- `compute_composite_score` (`app/services/composite_score.py:86`) existe **mais n'est pas requis** pour l'agrégation (on moyenne `last_composite_score` déjà stocké) — ne l'appeler que si une entrée n'a jamais été analysée.
- Les 4 piliers (ETF passif / thématique / valeur / algo) sont décrits dans `CLAUDE.md` (table Four-pillar) — il n'existe **aucun enum/constante** côté code : à créer.

### Spécification
1. **Migration** — `infra/postgres/migration_sprint126.sql` : `ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS pilier TEXT NOT NULL DEFAULT 'valeur'` (les 4 valeurs : `etf` / `thematique` / `valeur` / `algo`). Reporter le `ALTER` dans le bootstrap lifespan (`app/api/main.py`). Documenter le choix de valeur par défaut.
2. **Modèle + service** — `pilier: Literal["etf","thematique","valeur","algo"] = "valeur"` sur `WatchlistEntry` et `WatchlistCreate` (validator) ; `watchlist_service` persiste/retourne `pilier` ; endpoint `PATCH`/`PUT` pour reclasser une entrée existante (ou étendre l'upsert existant).
3. **Endpoint d'agrégation** — `GET /portfolio/summary` : pour chaque pilier, retourner `{ pilier, count, avg_composite_score, avg_esg_score, allocation_reelle_pct }` (allocation réelle = part des positions du pilier sur le total). L'allocation **cible** par pilier est une constante côté backend (documentée) ou un paramètre — choisir et documenter. Schemas Pydantic dédiés.
4. **Frontend** — page `/portefeuille` (`frontend/src/pages/PortfolioPage.tsx`) : un bloc par pilier (count, score composite moyen, ESG moyen, barre allocation cible vs réelle) ; sélecteur de pilier inline dans `WatchlistPage.tsx` (reclasser une position) ; client typé `frontend/src/api/portfolio.ts` ; types dans `frontend/src/types/index.ts` ; route ajoutée dans `App.tsx` (lazy-load, cf. Sprint 123) + lien de navigation.

### Tests obligatoires (pyramide)
- **Intégration** : `GET /portfolio/summary` agrège correctement (plusieurs piliers, pilier vide, moyenne pondérée, allocation réelle = somme à 100 %) ; reclassement d'une entrée round-trip. Fixture `client`.
- **Unitaire** : logique d'agrégation (moyennes, allocation) sur pool mocké ; validator `pilier` rejette une valeur hors enum (422).
- **Composant** : `PortfolioPage` rend les blocs par pilier (happy + état vide) ; sélecteur de pilier dans `WatchlistPage` déclenche le reclassement (happy + erreur).
- Aucune régression des tests watchlist existants.

### Note d'environnement (session web)
Conteneur cloné à neuf ; dépendances backend préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). ⚠️ **Si `frontend/node_modules` est absent, lancer `npm install` depuis `frontend/`** (le hook n'installe pas les deps npm — constaté Sprints 123-125). Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend (depuis `frontend/`) : `node node_modules/vitest/vitest.mjs run` ; `node node_modules/typescript/bin/tsc --noEmit` ; `node node_modules/eslint/bin/eslint.js src`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker (Postgres/Redis/Qdrant) non démarrée → migration non exécutée live (valider la syntaxe + les tests d'intégration sur DB/pool mocké). Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 127 — Cohérence inter-skills affichée dans l'UI
**Objectif** : exposer `inter_skill_conflicts` (déjà calculé côté backend) dans `AnalysisResult` — bannière listant les contradictions détectées entre skills.
**Complexité** : Faible
**Justification** : la donnée existe et est peuplée dans la réponse mais n'est jamais rendue ; valeur immédiate pour repérer les thèses contradictoires.
**Référence** : EXISTANT (vérifié cette session) — calcul `app/orchestrator/core.py:140` (`_detect_inter_skill_conflicts`), champ réponse `:273`, peuplé `:1007`/`:1060` (et `:1582`/`:1635`), type frontend `frontend/src/types/index.ts:459`. NON rendu dans `frontend/src/components/AnalysisResult.tsx` (0 occurrence `inter_skill` — confirmé cette session). À CRÉER — bannière de contradictions + test composant.

### Sprint 128 — Comparaison de deux analyses d'un même ticker (diff temporel)
**Objectif** : `GET /ticker-report/{ticker}/diff?from_id=&to_id=` produisant un PDF (ou JSON) comparant deux analyses persistées du même ticker — évolution des verdicts skill par skill, du composite_score et des ratios clés.
**Complexité** : Moyenne
**Justification** : capitalise sur la reconstruction multi-skills du Sprint 122 ; lecture « avant/après » d'une thèse dans le temps.
**Référence** : EXISTANT (vérifié cette session) — endpoint `app/api/endpoints/ticker_report.py:30` (`get_ticker_report`) + param `analysis_id` `:34` + helper `_fetch_analysis_by_id` `:141`. À CRÉER — route `/ticker-report/{ticker}/diff`, logique de comparaison.

### Sprint 129 — Préférences utilisateur généralisées (Dashboard / Comparer)
**Objectif** : réutiliser la table `user_preferences` (Sprint 124) pour persister d'autres préférences UI côté serveur (ex. disposition Dashboard, derniers tickers Comparer), via un client générique.
**Complexité** : Faible
**Justification** : capitalise sur l'infrastructure du Sprint 124 (table + service + endpoint pattern) pour étendre la continuité multi-appareils sans nouveau schéma.
**Référence** : EXISTANT (vérifié cette session) — service `app/services/user_preferences_service.py` (`get_preference`/`upsert_preference`), endpoints `app/api/endpoints/preferences.py`. À CRÉER — clés `dashboard`/`compare`, endpoints/clients génériques.

### Sprint 130 — Export des tags d'annotation + nuage de tags
**Objectif** : inclure la colonne `tags` (Sprint 125) dans les exports CSV/XLSX des annotations et exposer `GET /annotations/tags` (tags distincts + fréquence) pour un nuage de tags filtrable dans l'UI Historique.
**Complexité** : Faible
**Justification** : capitalise directement sur le Sprint 125 ; les exports ignorent aujourd'hui les tags et il n'existe aucune vue d'ensemble des tags utilisés.
**Référence** : EXISTANT (vérifié cette session) — `get_all_with_ticker` renvoie déjà `tags` (`app/services/annotation_service.py`), exports CSV/XLSX `app/api/endpoints/annotations.py` (listes de colonnes explicites n'incluant pas `tags`). À CRÉER — colonne export, endpoint `/annotations/tags`, composant nuage de tags.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.12.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 126 — Vue « Portefeuille » agrégée par pilier (colonne pilier sur la table
watchlist + migration/bootstrap lifespan, endpoint GET /portfolio/summary agrégeant
count/composite moyen/ESG moyen/allocation par pilier, page /portefeuille + sélecteur de
pilier dans WatchlistPage). ATTENTION : aucun champ pilier n'existe aujourd'hui (à créer).
Tests intégration agrégation + composant obligatoires.
```
