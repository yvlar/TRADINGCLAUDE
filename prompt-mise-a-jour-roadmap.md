# Sprint 126 — Vue « Portefeuille » agrégée

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.12.0 — Sprint 125 complété)

**Nouveauté Sprint 125** — Les annotations portent désormais des `tags` (colonne `annotations.tags TEXT[]` + index GIN) ; `GET /history?tags=value,growth` et `/history-paged?tags=` filtrent les analyses dont l'annotation contient TOUS les tags (`@>`), avec chips éditables dans `AnnotationSection` et lecture seule dans `HistoryTable`.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests vérifiés) : **`ROADMAP.md`** — source unique. Cette carte ne duplique pas l'état, elle y renvoie (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.12.0, Sprint 125 ✅
3. `.claude/rules/conventions-frontend.md` — nouvelle page + composants React (TypeScript strict, `data-testid`, recharts, test composant happy + erreur) — cœur du sprint
4. `.claude/rules/comptes-canadiens-fiscalite.md` — cadre four-pillar (ETF/thématique/valeur/algo) + allocation par compte, pour structurer l'agrégation par pilier
5. Point de départ exact (vérifié cette session — `fichier:ligne`) :
   - Scoring composite : `compute_composite_score` `app/services/composite_score.py:86`, `class CompositeScore` `app/services/composite_score.py:19`
   - Watchlist : page `frontend/src/pages/WatchlistPage.tsx`, client `frontend/src/api/watchlist.ts`, types watchlist dans `frontend/src/types/index.ts`
   - Routage SPA + lazy-load : `frontend/src/App.tsx` (pattern `React.lazy` Sprint 123)

---

## TÂCHE — Sprint 126 : Vue « Portefeuille » agrégée

**Objectif** : matérialiser le cadre four-pillar du projet (aujourd'hui purement conceptuel dans `CLAUDE.md`) via une page `/portefeuille` qui synthétise la watchlist par pilier (ETF passif / thématique / valeur / algo) avec **allocation cible vs réelle** et **score composite moyen par pilier**.

### Réconciliation préalable (à confirmer en Phase A par `grep`/lecture)
- Le cadre four-pillar n'est **pas** stocké en base aujourd'hui : aucune colonne `pilier`/`pillar` n'existe sur `watchlist` (à vérifier dans le bootstrap lifespan `app/api/main.py` autour de la création `watchlist`). → il faut soit ajouter une colonne `pillar TEXT` (migration + bootstrap, pattern Sprint 124/125), soit dériver le pilier d'une heuristique. **Décider et documenter.**
- `compute_composite_score` (`app/services/composite_score.py:86`) renvoie un `CompositeScore` (`:19`) — vérifier les champs réellement disponibles (score total, sous-scores) avant de figer l'agrégation par pilier.
- La watchlist expose `last_composite_score` (colonne ajoutée au bootstrap lifespan — vérifier `app/api/main.py`) : c'est probablement la source du score par titre pour la moyenne par pilier, sans recalcul live.

### Spécification (à affiner après réconciliation)
1. **Modèle de données du pilier** — ajouter l'appartenance d'un titre à un pilier (colonne `watchlist.pillar` + migration `infra/postgres/migration_sprint126.sql` + bootstrap lifespan ; éditable via l'UID watchlist) OU justifier une dérivation. Allocation cible par pilier : table dédiée ou config.
2. **Endpoint d'agrégation** — `GET /portfolio/summary` (ou nom cohérent avec les routers existants) renvoyant, par pilier : nombre de titres, allocation réelle (% de la watchlist), allocation cible, score composite moyen. Test d'intégration obligatoire (fixture `client`).
3. **Page `/portefeuille`** — ajoutée au routeur lazy (`App.tsx`) ; tableau/graphe par pilier (allocation cible vs réelle, score moyen) ; recharts pour la visualisation ; types dans `frontend/src/types/index.ts` (zéro `any`).
4. **Édition du pilier** — depuis la Watchlist, affecter chaque titre à un pilier (réutiliser le pattern d'édition inline existant des seuils watchlist).

### Tests obligatoires (pyramide)
- **Intégration** : `GET /portfolio/summary` — agrégation correcte (plusieurs piliers, pilier vide, allocation cible vs réelle). Fixture `client`.
- **Unitaire** : logique d'agrégation par pilier (moyenne composite, % allocation) sur données mockées.
- **Composant** : page `/portefeuille` (happy + état vide) ; édition du pilier d'un titre dans la Watchlist (happy + erreur).
- Aucune régression des tests watchlist/composite existants.

### Note d'environnement (session web)
Conteneur cloné à neuf ; dépendances backend préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). ⚠️ **`frontend/node_modules` est absent au démarrage → lancer `npm install` depuis `frontend/`** (constaté Sprints 123-125). Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend (depuis `frontend/`) : `node node_modules/vitest/vitest.mjs run` ; `node node_modules/typescript/bin/tsc --noEmit` ; `node node_modules/eslint/bin/eslint.js src`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker (Postgres/Redis/Qdrant) non démarrée → migration non exécutée live (valider la syntaxe + tests d'intégration sur DB/pool mocké). Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 127 — Cohérence inter-skills affichée dans l'UI
**Objectif** : exposer `inter_skill_conflicts` (déjà calculé côté backend) dans l'UI — bannière listant les contradictions détectées entre skills.
**Complexité** : Faible
**Justification** : la donnée existe mais n'est pas rendue ; valeur immédiate pour repérer les thèses contradictoires.
**Référence** : EXISTANT (vérifié) — calcul `app/orchestrator/core.py:140` (`_detect_inter_skill_conflicts`), champ réponse `app/orchestrator/core.py:262` (peuplé `:1049`), type frontend `frontend/src/types/index.ts:459`. NON rendu dans `frontend/src/components/AnalysisResult.tsx` (0 occurrence `inter_skill` — confirmé cette session). À CRÉER — bannière de contradictions + test composant.

### Sprint 128 — Comparaison de deux analyses d'un même ticker (diff temporel)
**Objectif** : `GET /ticker-report/{ticker}/diff?from_id=&to_id=` produisant un PDF (ou JSON) comparant deux analyses persistées du même ticker — évolution des verdicts skill par skill, du composite_score et des ratios clés.
**Complexité** : Moyenne
**Justification** : capitalise sur la reconstruction multi-skills du Sprint 122 ; lecture « avant/après » d'une thèse dans le temps.
**Référence** : EXISTANT (vérifié) — endpoint `app/api/endpoints/ticker_report.py:25` (`get_ticker_report`) + param `analysis_id` `:34`, helper `_fetch_analysis_by_id` `:141`. À CRÉER — route `/ticker-report/{ticker}/diff`, logique de comparaison.

### Sprint 129 — Préférences utilisateur généralisées (Dashboard / Comparer)
**Objectif** : réutiliser la table `user_preferences` (Sprint 124) pour persister d'autres préférences UI côté serveur (ex. disposition Dashboard, derniers tickers Comparer), via un client générique.
**Complexité** : Faible
**Justification** : capitalise sur l'infrastructure du Sprint 124 (table + service + endpoint pattern) pour étendre la continuité multi-appareils sans nouveau schéma.
**Référence** : EXISTANT (vérifié) — service `app/services/user_preferences_service.py` (`get_preference` `:11`, `upsert_preference` `:23`), endpoints `app/api/endpoints/preferences.py`. À CRÉER — clés `dashboard`/`compare`, endpoints/clients génériques.

### Sprint 130 — Tags : autocomplétion + nuage de tags
**Objectif** : endpoint `GET /annotations/tags` listant les tags distincts utilisés (avec compte), pour alimenter une autocomplétion dans `AnnotationSection` et un nuage cliquable filtrant l'historique.
**Complexité** : Faible
**Justification** : capitalise directement sur le Sprint 125 (colonne `tags TEXT[]` + index GIN) ; rend la taxonomie découvrable au lieu de la saisie libre à l'aveugle.
**Référence** : EXISTANT (vérifié) — colonne `annotations.tags TEXT[]` + index GIN `idx_annotations_tags` (bootstrap `app/api/main.py`, Sprint 125), client `frontend/src/api/annotations.ts`, composant `frontend/src/components/AnnotationSection.tsx`. À CRÉER — endpoint d'agrégation `DISTINCT unnest(tags)`, autocomplétion + nuage.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.12.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 126 — Vue « Portefeuille » agrégée (page /portefeuille synthétisant la
watchlist par pilier four-pillar : allocation cible vs réelle + score composite moyen par
pilier ; modèle de données du pilier sur watchlist + endpoint d'agrégation + page React lazy).
Migration + bootstrap lifespan ; tests intégration endpoint + composant page obligatoires.
```
