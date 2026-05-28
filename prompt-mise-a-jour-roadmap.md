# Sprint 120 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.6.0 — Sprint 119 complété)

Le dépôt est public-ready et les cinq skills les plus riches ont maintenant un rendu UI structuré (plus de JSON brut).

**Nouveauté Sprint 119** — Refonte UI Dorsey Moat + Buffett Quality + Valorisation :
- **`DorseyMoatSection.tsx`** — badge type de moat (WIDE/NARROW/NONE), barre de confiance, durabilité ROIC, grille des 5 sources d'avantage concurrentiel (intangibles, coûts de transfert, effets de réseau, avantages de coûts, échelle efficiente) avec présence ✓/✗, badge d'intensité et justification ; red flags ; recommandations
- **`BuffettQualitySection.tsx`** — verdict (COMPOUNDER/QUALITE_CORRECTE/REJETER) + quality score /4 + barre de confiance ; owner earnings par action mis en évidence ; 4 filtres séquentiels ✓/✗ avec score et justification
- **`ValuationSection.tsx`** — verdict (SOUS_EVALUE/JUSTE_VALEUR/SUREVALUE) + marge de sécurité composite ; fourchette basse/centrale/haute ; 3 méthodes (DCF/comparables/sectoriel) avec hypothèses ; matrice de sensibilité WACC × croissance
- **Types TypeScript** structurés (`DorseyMoatOutput`, `BuffettQualityOutput`, `StockValuationOutput` et sous-types) — `AnalyzeResponse.dorsey`, `.buffett` et `.valuation` ne sont plus `SkillOutput` générique
- **18 tests Vitest** — 6 par composant
- **AnalysisResult.tsx** — branché sur les nouveaux composants, plus de JSON brut pour ces trois skills

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow, streaming SSE skill par skill avec event `plan`
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Screener v2 — tri persistant + filtres composite + fraîcheur + export filtré (Sprint 109/114)
- Dashboard v2 — métriques détaillées + drill-down coût par skill + tendance quotidienne, grille responsive 12 colonnes
- Recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages + auth, shell pleine largeur `max-w-shell`, design tokens sémantiques, palette de commandes ⌘K
- **Repo public-ready** — README · CODE_OF_CONDUCT · CHANGELOG · CODEOWNERS · CI permissions minimales
- **UI skills riches** — EarningsQuality + Thèse + Dorsey Moat + Buffett Quality + Valorisation (plus JSON brut)
- 1 423 CI pytest verts + 337 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.6.0, Sprint 119 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 120

**Ce sprint est à définir par Yves.** Choisir l'un des sprints suggérés ci-dessous, ou en spécifier un autre.

Aucun point de dette technique n'est en suspens. Les skills encore affichés en JSON brut générique (`SkillSection`) : Lynch, Fisher, Klarman, Greenblatt, Damodaran, Marks, Pabrai, Munger, Fiscalité CA/QC — la refonte UI peut continuer, ou le projet peut pivoter vers le pipeline de données / l'export.

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
- **Largeur** : le shell applicatif utilise `max-w-shell` (token `--container-shell` dans `index.css`) — ne pas réintroduire `max-w-5xl` ni `max-w-screen-*` (retiré en Tailwind 4)

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 120 — Refonte UI skills restants (Lynch, Klarman, Greenblatt, Munger…)
**Objectif** : Continuer le pattern Sprint 118/119 sur les skills encore en JSON brut — p. ex. `LynchCategoriesSection` (catégorie + PEG), `GreenblattSection` (rang ROC + earnings yield), `MungerSection` (biais cognitifs détectés), `KlarmanSection` (marge de sécurité + downside).
**Complexité** : Moyenne
**Justification** : Dernier lot de skills affichés en JSON brut générique ; complète la refonte UI entamée aux Sprints 118-119.

### Sprint 121 — Export analyse individuelle en PDF enrichi
**Objectif** : `GET /ticker-report/{ticker}?analysis_id=X` incluant verdicts skill par skill, ratios clés, annotation existante et score ESG. Complète la boucle « analyser → lire → exporter ».
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, pas une analyse précise ; valeur immédiate d'archivage et de partage.

### Sprint 122 — Code-splitting des routes + lazy-load recharts
**Objectif** : `React.lazy` + `Suspense` (fallback skeleton) par page, isolant recharts du bundle initial pour accélérer le TTI de la première vue (Analyse).
**Complexité** : Faible
**Justification** : Toutes les pages sont importées statiquement aujourd'hui ; quick win de performance perçue identifié à l'audit. Sans infrastructure à modifier, purement frontend.

### Sprint 123 — Persistance des préférences Screener côté serveur
**Objectif** : Migrer tri + filtres Screener du localStorage (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié. Endpoints `GET/PUT /preferences/screener`.
**Complexité** : Moyenne
**Justification** : Lier les préférences au compte (Sprint Login) offre une continuité multi-appareils.

### Sprint 124 — Annotations enrichies : tags + filtres
**Objectif** : Ajouter un champ `tags` (liste de mots-clés libres) aux annotations, indexé GIN, filtrable via `GET /history?tags=value,growth`. Affichage chips dans `HistoryTable` et `AnnotationSection`.
**Complexité** : Moyenne
**Justification** : Les annotations (Sprint 78) sont du texte libre sans structure ; les tags permettent un filtrage sémantique du portefeuille sans RAG.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.6.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 120 — [à compléter par Yves]
```
