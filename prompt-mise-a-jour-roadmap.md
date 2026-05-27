# Sprint 114 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.0.0 — Sprint 113 complété)

Le dépôt est propre, publiable sur GitHub, et aucune dette technique n'est en suspens.

**Nouveauté Sprint 113** — Global Micro-UX Refresh : toutes les 11 pages React gagnent un système cohérent d'animations et de micro-interactions :
- **Système d'animations CSS** — 5 `@keyframes` (`shimmer`, `fade-in-up`, `scale-in`, `slide-in-right`, `count-pulse`) + classe `.skeleton-shimmer` (gradient 200% animé) déclarés dans `index.css` comme utilities Tailwind
- **Skeleton loaders** — `SkeletonTable`, `SkeletonCard`, `SkeletonCardGrid`, `SkeletonChart` remplacent tous les états "Chargement..." par des blocs shimmer correspondant au layout réel (DashboardPage, HistoryPage, ScreenerPage, WatchlistPage, EsgPage, AlertsPage, SearchPage, ComparePage)
- **AnimatedNumber** — count-up `requestAnimationFrame` cubic-out + pulsation CSS sur les 5 métriques WebSocket du Dashboard
- **PageTransition + StaggerItem** — fade-in-up à chaque navigation ; cascade décalée 55 ms/item sur les listes (SearchPage résultats, AnalyzePage form, StreamingProgress skills)
- **UI primitives** — boutons `active:scale-95` (press feedback), badges `animate-scale-in` (pop au montage), cartes `hover:border-primary/30` + box-shadow glow, `StreamingProgress` avec barre de progression globale (done/total) et indicateur `animate-ping`
- **Navigation** — indicateur actif `animate-scale-in` + hover `border-primary/30`

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Screener v2 — tri persistant + filtres composite + fraîcheur + export filtré (Sprint 109)
- Dashboard v2 — métriques détaillées (Sprint 107) + drill-down coût par skill + tendance quotidienne (Sprint 112)
  + recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages
- 1418 CI pytest verts + 294 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (100 lignes, pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.0.0, Sprint 113 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 114

**Ce sprint est à définir par Yves.** Choisir l'un des sprints suggérés ci-dessous, ou en spécifier un autre.

Aucun point de dette technique n'est en suspens : le dépôt est propre et la structure stable.

### Note d'environnement (session web)

En session Claude Code sur le web, le conteneur est cloné à neuf et les dépendances ne sont pas installées :
- Backend : `python -m venv .venv --system-site-packages && .venv/bin/pip install -r requirements-ci.txt`
  (la version Debian de `cryptography` casse un `pip install` global → utiliser un venv `--system-site-packages`)
- Frontend : `node_modules/` est présent mais le binaire natif rollup manque
  (`npm install @rollup/rollup-linux-x64-gnu --no-save` corrige l'erreur de démarrage de Vitest)
- Lancer les tests : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals`
  et `cd frontend && node node_modules/vitest/vitest.mjs run`
- Lint/typecheck : `node node_modules/typescript/bin/tsc --noEmit` + `node node_modules/eslint/bin/eslint.js src`
  (frontend), `.venv/bin/ruff check app/ tests/` (backend, après `pip install ruff`)
- ⚠️ `cd frontend` persiste le cwd entre commandes — penser à revenir à la racine avant les commandes backend
- La stack Docker (Postgres/Redis/Qdrant) n'est pas démarrée → pas de test navigateur live possible dans le conteneur

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 114 — Export analyse individuelle en PDF enrichi
**Objectif** : Générer un PDF par analyse (`GET /ticker-report/{ticker}?analysis_id=X`) incluant les verdicts skill par skill, les ratios clés, l'annotation existante, et le score ESG. Complète la boucle « analyser → lire → exporter » sans quitter l'interface.
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, mais pas une analyse individuelle. Valeur immédiate : archivage et partage d'une thèse précise.

### Sprint 115 — Recherche sémantique v2 : filtre par skill + surlignage
**Objectif** : Enrichir la page `/recherche` (Sprint 106) avec un filtre par skill source (déduit du `source_file`), le surlignage des termes de la requête dans les extraits, et un lien « Voir le skill » vers la page d'analyse correspondante.
**Complexité** : Moyenne
**Justification** : Le Sprint 106 a posé les fondations ; filtrer par framework et surligner les correspondances augmente nettement la valeur pédagogique de la recherche.

### Sprint 116 — Persistance d'un historique de coût quotidien
**Objectif** : Persister la tendance de coût quotidien (Sprint 112) dans une table `daily_cost_history` alimentée par une tâche Celery beat, au lieu de recalculer `daily_cost` à la volée dans `get_metrics()`. Permet des fenêtres longues (1 an) sans scanner `analysis_history` à chaque requête.
**Complexité** : Moyenne
**Justification** : Le Sprint 112 calcule `daily_cost` en direct ; au-delà de quelques centaines de milliers de lignes, l'agrégation par jour devient coûteuse.

### Sprint 117 — Notifications push navigateur (Web Push API)
**Objectif** : Ajouter des notifications push navigateur pour les alertes Celery critiques (ESG dégradé, composite_score en chute). Fonctionne directement dans le navigateur sans configuration Slack.
**Complexité** : Élevée
**Justification** : Les alertes sont générées, listées dans `/alerts` et visualisées sur le Dashboard, mais l'utilisateur doit consulter la page pour les voir. Une notification push ferme la boucle en temps réel.

### Sprint 118 — Persistance des préférences Screener côté serveur
**Objectif** : Migrer le tri et les filtres Screener (aujourd'hui en localStorage, Sprint 109) vers une table `user_preferences` PostgreSQL afin qu'ils suivent l'utilisateur entre navigateurs/appareils. Endpoints `GET/PUT /preferences/screener`.
**Complexité** : Moyenne
**Justification** : Le Sprint 109 persiste les préférences localement ; les lier au compte authentifié (Sprint Login) offre une vraie continuité multi-appareils.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.0.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 114 — [à compléter par Yves]
```
