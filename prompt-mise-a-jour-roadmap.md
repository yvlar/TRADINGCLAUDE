# Sprint 102 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v9.5.1 — Sprint 101 complété)

Le dépôt est propre, publiable sur GitHub, et la dette technique du Sprint 100 est close :
- `.claude/skills/` est entièrement tracké par le dépôt principal (158 fichiers, dont les 16 SKILL.md) — **aucun** `.git` imbriqué, **aucun** gitlink cassé, **aucun** `.gitmodules`, **aucun** dossier `investment/` orphelin
- `analyses/`, `reports/`, `tmp_replacements.txt` et `.claude/settings.local.json` exclus du suivi git (données personnelles / artefacts)
- `tests/` organisé en 5 sous-dossiers thématiques (skills/, api/, services/, workers/, orchestrator/)
- 1401 CI pytest verts + 217 Vitest verts + 4 jobs CI GitHub Actions opérationnels

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173)

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (100 lignes, pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v9.5.1, Sprint 101 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 102

**Ce sprint est à définir par Yves.** Choisir l'un des sprints suggérés ci-dessous, ou en spécifier un autre.

Aucun point de dette technique n'est en suspens : le dépôt est propre et la structure stable. Le projet est mûr pour de nouvelles fonctionnalités utilisateur ou des enrichissements de l'observabilité.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 102 — Export analyse individuelle en PDF enrichi
**Objectif** : Générer un PDF par analyse (`GET /ticker-report/{ticker}?analysis_id=X`) incluant les verdicts skill par skill, les ratios clés, l'annotation existante, et le score ESG. Complète la boucle « analyser → lire → exporter » sans quitter l'interface.
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, mais pas une analyse individuelle. Valeur immédiate : archivage et partage d'une thèse précise.

### Sprint 103 — Tableaux de bord métriques enrichis (Dashboard v2)
**Objectif** : Enrichir DashboardPage avec les métriques manquantes : top tickers analysés (barre), coût par skill (pie chart), taux de cache par workflow, évolution du nombre d'alertes dans le temps.
**Complexité** : Moyenne
**Justification** : Le Dashboard v1 montre les coûts et le cache mais reste peu lisible pour un usage quotidien. Les données existent déjà via `/metrics` et `/alerts`.

### Sprint 104 — Page Screener v2 : filtres avancés et tri persistant
**Objectif** : Améliorer ScreenerPage avec tri multi-colonnes persistant (localStorage), filtres inline par label composite (FORT/BON/NEUTRE/FAIBLE), export direct depuis les résultats filtrés, et indicateur de « fraîcheur » des données (date de la dernière analyse par ticker).
**Complexité** : Moyenne
**Justification** : Le screener est l'outil le plus utilisé après l'analyse individuelle. Les améliorations de navigation ont un impact direct sur l'efficacité du flux de travail d'investissement.

### Sprint 105 — Notifications push navigateur (Web Push API)
**Objectif** : Ajouter des notifications push navigateur pour les alertes Celery critiques (ESG dégradé, composite_score en chute). Fonctionne directement dans le navigateur sans configuration Slack.
**Complexité** : Élevée
**Justification** : Les alertes sont générées et listées dans `/alerts` (Sprint 99), mais l'utilisateur doit consulter la page pour les voir. Une notification push ferme la boucle en temps réel.

### Sprint 106 — Recherche sémantique RAG dans l'historique (UI)
**Objectif** : Exposer le RAG Qdrant (collection `investment_knowledge`) directement dans le frontend : champ de recherche en langage naturel qui retourne les passages de référence (formules, seuils, frameworks) avec citations, en réutilisant `get_citations()`.
**Complexité** : Moyenne
**Justification** : Le corpus RAG (~67 documents) est alimenté et interrogé côté backend, mais jamais surfacé à l'utilisateur. Forte valeur pédagogique pour comprendre les verdicts des skills.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v9.5.1), et les règles .claude/rules/ avant de commencer.
Sprint actif : 102 — [à compléter par Yves]
```
