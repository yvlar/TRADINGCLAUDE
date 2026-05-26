# Sprint 108 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v9.7.0 — Sprint 107 complété)

Le dépôt est propre, publiable sur GitHub, et aucune dette technique n'est en suspens.

**Nouveauté Sprint 107** — Le Dashboard est enrichi d'une section « Métriques détaillées » (Dashboard v2)
qui surface des agrégats jusqu'ici invisibles dans l'interface :
- `GET /metrics` enrichi côté backend — `skills_cost` (coût USD réparti par skill) et `cache_by_workflow`
  (taux de cache moyen par workflow) ajoutés à `MetricsResponse` (défauts `{}` → rétrocompatible)
- `DashboardPage` — section `DetailedMetricsSection` avec sélecteur de période (7/30/90 j) et 4 graphiques recharts :
  top tickers analysés (barres), coût par skill (camembert), taux de cache par workflow (barres),
  alertes regroupées par jour (barres, alimentées par `GET /alerts`)

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Dashboard v2 — métriques détaillées (Sprint 107) + recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages
- 1410 CI pytest verts + 241 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (100 lignes, pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v9.7.0, Sprint 107 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 108

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
- La stack Docker (Postgres/Redis/Qdrant) n'est pas démarrée → pas de test navigateur live possible dans le conteneur

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 108 — Export analyse individuelle en PDF enrichi
**Objectif** : Générer un PDF par analyse (`GET /ticker-report/{ticker}?analysis_id=X`) incluant les verdicts skill par skill, les ratios clés, l'annotation existante, et le score ESG. Complète la boucle « analyser → lire → exporter » sans quitter l'interface.
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, mais pas une analyse individuelle. Valeur immédiate : archivage et partage d'une thèse précise.

### Sprint 109 — Page Screener v2 : filtres avancés et tri persistant
**Objectif** : Améliorer ScreenerPage avec tri multi-colonnes persistant (localStorage), filtres inline par label composite (FORT/BON/NEUTRE/FAIBLE), export direct depuis les résultats filtrés, et indicateur de « fraîcheur » des données (date de la dernière analyse par ticker).
**Complexité** : Moyenne
**Justification** : Le screener est l'outil le plus utilisé après l'analyse individuelle. Les améliorations de navigation ont un impact direct sur l'efficacité du flux de travail d'investissement.

### Sprint 110 — Notifications push navigateur (Web Push API)
**Objectif** : Ajouter des notifications push navigateur pour les alertes Celery critiques (ESG dégradé, composite_score en chute). Fonctionne directement dans le navigateur sans configuration Slack.
**Complexité** : Élevée
**Justification** : Les alertes sont générées et listées dans `/alerts` (Sprint 99) et désormais visualisées dans le temps sur le Dashboard (Sprint 107), mais l'utilisateur doit consulter la page pour les voir. Une notification push ferme la boucle en temps réel.

### Sprint 111 — Recherche sémantique v2 : filtre par skill + surlignage
**Objectif** : Enrichir la page `/recherche` (Sprint 106) avec un filtre par skill source (déduit du `source_file`), le surlignage des termes de la requête dans les extraits, et un lien « Voir le skill » vers la page d'analyse correspondante. Optionnel : exposer `skill_id` et `section` dans la réponse `/semantic-search` (nécessite d'enrichir `RagClient.search` → `Citation`).
**Complexité** : Moyenne
**Justification** : Le Sprint 106 a posé les fondations ; filtrer par framework et surligner les correspondances augmente nettement la valeur pédagogique de la recherche.

### Sprint 112 — Coût par skill : drill-down et tendance
**Objectif** : Prolonger le Dashboard v2 (Sprint 107) avec un drill-down sur le camembert « coût par skill » (clic → liste des analyses ayant utilisé ce skill sur la période) et une mini-tendance du coût total par jour. Optionnellement persister un historique de coût quotidien pour éviter de recalculer à la volée.
**Complexité** : Moyenne
**Justification** : Le Sprint 107 montre la répartition statique du coût ; voir l'évolution dans le temps et drill-downer aide à piloter le budget API Claude.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v9.7.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 108 — [à compléter par Yves]
```
