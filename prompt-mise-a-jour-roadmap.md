# Sprint 107 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v9.6.0 — Sprint 106 complété)

Le dépôt est propre, publiable sur GitHub, et aucune dette technique n'est en suspens.

**Nouveauté Sprint 106** — Le corpus RAG Qdrant (`investment_knowledge`, ~67 documents) est désormais
surfacé à l'utilisateur via une page de recherche sémantique :
- `GET /semantic-search?q=&k=5` — recherche en langage naturel, retourne `{query, rag_enabled, results: [Citation]}`
- `rag_service` exposé dans `app.state` (lifespan FastAPI), `rag_enabled=false` + `results=[]` si `OPENAI_API_KEY` absente
- Page `/recherche` (React) — champ de recherche, résultats en cartes (source + score + extrait), badge de similarité

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages
- 1406 CI pytest verts + 223 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (100 lignes, pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v9.6.0, Sprint 106 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 107

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

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 107 — Export analyse individuelle en PDF enrichi
**Objectif** : Générer un PDF par analyse (`GET /ticker-report/{ticker}?analysis_id=X`) incluant les verdicts skill par skill, les ratios clés, l'annotation existante, et le score ESG. Complète la boucle « analyser → lire → exporter » sans quitter l'interface.
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, mais pas une analyse individuelle. Valeur immédiate : archivage et partage d'une thèse précise.

### Sprint 108 — Tableaux de bord métriques enrichis (Dashboard v2)
**Objectif** : Enrichir DashboardPage avec les métriques manquantes : top tickers analysés (barre), coût par skill (pie chart), taux de cache par workflow, évolution du nombre d'alertes dans le temps.
**Complexité** : Moyenne
**Justification** : Le Dashboard v1 montre les coûts et le cache mais reste peu lisible pour un usage quotidien. Les données existent déjà via `/metrics` et `/alerts`.

### Sprint 109 — Page Screener v2 : filtres avancés et tri persistant
**Objectif** : Améliorer ScreenerPage avec tri multi-colonnes persistant (localStorage), filtres inline par label composite (FORT/BON/NEUTRE/FAIBLE), export direct depuis les résultats filtrés, et indicateur de « fraîcheur » des données (date de la dernière analyse par ticker).
**Complexité** : Moyenne
**Justification** : Le screener est l'outil le plus utilisé après l'analyse individuelle. Les améliorations de navigation ont un impact direct sur l'efficacité du flux de travail d'investissement.

### Sprint 110 — Notifications push navigateur (Web Push API)
**Objectif** : Ajouter des notifications push navigateur pour les alertes Celery critiques (ESG dégradé, composite_score en chute). Fonctionne directement dans le navigateur sans configuration Slack.
**Complexité** : Élevée
**Justification** : Les alertes sont générées et listées dans `/alerts` (Sprint 99), mais l'utilisateur doit consulter la page pour les voir. Une notification push ferme la boucle en temps réel.

### Sprint 111 — Recherche sémantique v2 : filtre par skill + surlignage
**Objectif** : Enrichir la page `/recherche` (Sprint 106) avec un filtre par skill source (déduit du `source_file`), le surlignage des termes de la requête dans les extraits, et un lien « Voir le skill » vers la page d'analyse correspondante. Optionnel : exposer `skill_id` et `section` dans la réponse `/semantic-search` (nécessite d'enrichir `RagClient.search` → `Citation`).
**Complexité** : Moyenne
**Justification** : Le Sprint 106 a posé les fondations ; filtrer par framework et surligner les correspondances augmente nettement la valeur pédagogique de la recherche.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v9.6.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 107 — [à compléter par Yves]
```
