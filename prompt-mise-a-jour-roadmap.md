# Sprint 115 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.1.0 — Sprint 114 complété)

Le dépôt est propre, publiable sur GitHub, et aucune dette technique n'est en suspens.

**Nouveauté Sprint 114** — Quick wins UX/UI (issus d'un audit senior) : quatre lacunes transverses comblées sans changer la structure des pages :
- **Tokens sémantiques financiers** — `--bull` / `--bear` / `--neutral` (`index.css` + `@theme inline`) génèrent `text-bull`, `bg-bull/15`, `border-bear/40`, etc. Nouveau module `frontend/src/lib/colors.ts` (`CHART` + `SERIES`) = source unique des couleurs recharts. Plus aucune couleur en dur (~80 hex + ~43 utilities supprimés).
- **Progression de streaming fidèle** — nouvel event SSE `plan` (`Orchestrator._planned_skill_ids()`) annonçant les skills qui s'exécuteront réellement ; `StreamingProgress` affiche le pipeline complet (terminé ✓ / actif ping / **en attente** pastille creuse) avec un `done/total` correct (fin de l'effet « 100 % puis recule »).
- **Squelettes partout** — les 11 placeholders texte « Chargement… » des graphiques/tableaux remplacés par `Skeleton`/`SkeletonTable`.
- **Accessibilité de base** — `@media (prefers-reduced-motion: reduce)` (WCAG 2.3.3) ; en-têtes de tri du Screener en `<button>` focusables + `aria-sort`.

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow, streaming SSE skill par skill avec event `plan`
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Screener v2 — tri persistant accessible + filtres composite + fraîcheur + export filtré (Sprint 109/114)
- Dashboard v2 — métriques détaillées (Sprint 107) + drill-down coût par skill + tendance quotidienne (Sprint 112)
  + recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages, design tokens sémantiques
- 1423 CI pytest verts + 296 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.1.0, Sprint 114 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 115

**Ce sprint est à définir par Yves.** Choisir l'un des sprints suggérés ci-dessous, ou en spécifier un autre.

Aucun point de dette technique n'est en suspens : le dépôt est propre et la structure stable.

### Note d'environnement (session web)

En session Claude Code sur le web, le conteneur est cloné à neuf et les dépendances ne sont pas installées :
- Backend : `python -m venv .venv --system-site-packages && .venv/bin/pip install -r requirements-ci.txt ruff`
  (la version Debian de `cryptography` casse un `pip install` global → utiliser un venv `--system-site-packages`)
- Frontend : `node_modules/` est présent mais le binaire natif rollup manque
  (`npm install @rollup/rollup-linux-x64-gnu --no-save` corrige l'erreur de démarrage de Vitest)
- Lancer les tests : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals`
  et `cd frontend && node node_modules/vitest/vitest.mjs run`
- Lint/typecheck : `node node_modules/typescript/bin/tsc --noEmit` + `node node_modules/eslint/bin/eslint.js src`
  (frontend), `.venv/bin/ruff check app/ tests/` (backend)
- ⚠️ `cd frontend` persiste le cwd entre commandes — penser à revenir à la racine avant les commandes backend
- La stack Docker (Postgres/Redis/Qdrant) n'est pas démarrée → pas de test navigateur live possible dans le conteneur
- **Couleurs** : utiliser les tokens `text-bull`/`text-bear`/`text-neutral` (jamais `text-green-400` ni hex) ; pour recharts, importer depuis `frontend/src/lib/colors.ts` (`CHART`, `SERIES`)

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 115 — Layout pleine largeur + grille dense configurable
**Objectif** : Remplacer le conteneur `max-w-5xl` (`App.tsx`) par un shell fluide (`max-w-screen-2xl`/full-bleed) et transformer le Dashboard d'une pile verticale en grille responsive 12 colonnes, pour exploiter les grands écrans façon plateforme financière.
**Complexité** : Moyenne
**Justification** : L'audit UX a identifié le conteneur étroit comme le frein n°1 à la densité d'information ; quick win de fort impact visuel.

### Sprint 116 — Palette de commandes ⌘K
**Objectif** : Ajouter une command palette (`cmdk`) — recherche ticker, navigation entre pages, actions « Analyser X » / « Comparer » — déclenchée par ⌘K, branchée sur les routes et la recherche sémantique existante.
**Complexité** : Moyenne
**Justification** : Aucune navigation clavier n'existe ; fonctionnalité la plus attendue du persona « power user / trader ».

### Sprint 117 — Export analyse individuelle en PDF enrichi
**Objectif** : `GET /ticker-report/{ticker}?analysis_id=X` incluant verdicts skill par skill, ratios clés, annotation existante et score ESG. Complète la boucle « analyser → lire → exporter ».
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, pas une analyse précise ; valeur immédiate d'archivage et de partage.

### Sprint 118 — Code-splitting des routes + lazy-load recharts
**Objectif** : `React.lazy` + `Suspense` (fallback skeleton) par page, isolant recharts du bundle initial pour accélérer le TTI de la première vue (Analyse).
**Complexité** : Faible
**Justification** : Toutes les pages sont importées statiquement aujourd'hui ; quick win de performance perçue identifié à l'audit.

### Sprint 119 — Persistance des préférences Screener côté serveur
**Objectif** : Migrer tri + filtres Screener du localStorage (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié. Endpoints `GET/PUT /preferences/screener`.
**Complexité** : Moyenne
**Justification** : Lier les préférences au compte (Sprint Login) offre une continuité multi-appareils.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.1.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 115 — [à compléter par Yves]
```
