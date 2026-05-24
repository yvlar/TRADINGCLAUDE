# Sprint 101 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v9.5.0 — Sprint 100 complété)

Le dépôt est maintenant propre et publiable sur GitHub :
- Racine épurée : tous les prompts internes déplacés dans `.claude/prompts/`, artefacts supprimés
- `analyses/` et `.claude/settings.local.json` exclus du suivi git (données personnelles)
- `tests/` réorganisé en 5 sous-dossiers thématiques (skills/, api/, services/, workers/, orchestrator/)
- 1401 CI pytest verts + 217 Vitest verts + 4 jobs CI GitHub Actions opérationnels

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Tableau de bord alertes Celery (Sprint 99)
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173)

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (100 lignes, pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v9.5.0, Sprint 100 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 101

**Ce sprint est à définir par Yves.** Voici le contexte pour l'orienter :

Deux points techniques en suspens issus du Sprint 100 :
1. **`.claude/skills/.git`** — dépôt git imbriqué sans `.gitmodules`. Git traite `.claude/skills/` comme un submodule non enregistré. Si tu veux que les SKILL.md soient trackés dans le repo principal (recommandé), il faut supprimer `.claude/skills/.git` (action irréversible — confirmer avec Yves). Si `.claude/skills/` doit rester un repo séparé, créer un `.gitmodules` et l'enregistrer comme submodule.
2. **`.claude/skills/investment/`** — dossier orphelin (README.md méta + sous-dossier investment-skills). Semble résiduel d'une installation manuelle de skills. À supprimer ou à intégrer.

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 101 — Export analyse individuelle en PDF enrichi
**Objectif** : Générer un PDF par analyse (`GET /ticker-report/{ticker}?analysis_id=X`) incluant les verdicts skill par skill, les ratios clés, l'annotation existante, et le score ESG. Complète la boucle "analyser → lire → exporter" sans quitter l'interface.
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, mais pas une analyse individuelle. Valeur immédiate : archivage et partage d'une thèse précise.

### Sprint 102 — Tableaux de bord métriques enrichis (Dashboard v2)
**Objectif** : Enrichir DashboardPage avec les métriques manquantes : top tickers analysés (barre), coût par skill (pie chart), taux de cache par workflow, évolution du nombre d'alertes dans le temps.
**Complexité** : Moyenne
**Justification** : Le Dashboard v1 montre les coûts et le cache mais reste peu lisible pour un usage quotidien. Les données existent déjà via `/metrics` et `/alerts`.

### Sprint 103 — Nettoyage `.claude/skills/` (résolution dette technique)
**Objectif** : Résoudre les deux points en suspens du Sprint 100 — supprimer le `.git` imbriqué dans `.claude/skills/` pour que les SKILL.md soient trackés normalement par le repo principal, et supprimer le dossier orphelin `investment/`.
**Complexité** : Faible
**Justification** : Prérequis pour que `git clone` du repo public ne se retrouve pas avec un submodule cassé.

### Sprint 104 — Page Screener v2 : filtres avancés et tri persistant
**Objectif** : Améliorer ScreenerPage avec tri multi-colonnes persistant (localStorage), filtres inline par label composite (FORT/BON/NEUTRE/FAIBLE), export direct depuis les résultats filtrés, et indicateur de "fraîcheur" des données (date de la dernière analyse par ticker).
**Complexité** : Moyenne
**Justification** : Le screener est l'outil le plus utilisé après l'analyse individuelle. Les améliorations de navigation ont un impact direct sur l'efficacité du flux de travail d'investissement.

### Sprint 105 — Notifications push navigateur (Web Push API)
**Objectif** : Ajouter des notifications push navigateur pour les alertes Celery critiques (ESG dégradé, composite_score en chute). Fonctionne directement dans le navigateur sans configuration Slack.
**Complexité** : Élevée
**Justification** : Les alertes sont générées mais l'utilisateur doit consulter `/alerts` pour les voir. Une notification push ferme la boucle en temps réel.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v9.5.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 101 — [à compléter par Yves]
```
