# Sprint 123 — Code-splitting des routes + lazy-load recharts

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.9.0 — Sprint 122 complété)

**Nouveauté Sprint 122** — Export d'une analyse individuelle précise en PDF enrichi :
- **Endpoint** — `GET /ticker-report/{ticker}` accepte un paramètre optionnel `analysis_id` :
  - fourni → charge **cette** ligne de `analysis_history` (`WHERE id = $1::uuid AND ticker = $2`), 404 si absente, ticker différent ou id mal formé ; l'historique composite devient optionnel
  - absent → comportement inchangé (dernière analyse + historique 90 j, 404 si aucune donnée composite) — **rétrocompatible**
- **Reconstruction multi-skills** — `_reconstruct_analyze_response` parse désormais **les 16 outputs tier2** présents dans `result` (plus seulement Graham/Buffett/Dorsey) via un mapping `result_key → champ AnalyzeResponse → classe Pydantic` ; un skill dont le JSON ne valide pas est ignoré (`model_validate` tolérant, pas d'échec global) ; n'exige plus la présence de Graham
- **PDF enrichi** (`PdfReportService.generate_ticker_report`, nouveaux params `ratios` / `annotation` / `esg_score`) :
  - **tableau « Verdicts par skill »** (skill / verdict / détail court) pour chaque skill présent
  - **tableau « Ratios clés »** depuis `input_data` (GrahamRatios : cours, BPA, valeur comptable, P/E, P/B, dette/capitaux, croissance BPA 10 a, ratio de liquidité)
  - **annotation existante** (table `annotations`, Sprint 78) si présente
  - **score ESG** depuis le `result` (output `esg`), sinon dernier point `esg_score_history`
- **Frontend** — bouton « Exporter cette analyse » dans `AnalysisResult` (AnalyzePage) appelant `downloadTickerPdf(ticker, 90, analysis_id)` ; masqué pour un score depuis cache composite (`analysis_id` ∈ {`cached`, `cached_composite`})
- **Tests** — +9 pytest (reconstruction multi-skills, skill corrompu ignoré, result illisible, `analysis_id` 200/404 inconnu/404 mismatch/404 mal formé, PDF enrichi), +2 Vitest (export appelle `downloadTickerPdf` avec `analysis_id` ; bouton masqué si cache)

**Fonctionnalités actives** :
- 18 skills (16 tier2 + 2 tier1), orchestrateur multi-workflow, streaming SSE skill par skill avec event `plan`
- Auth JWT cookie httpOnly + CSRF + argon2 (Sprint Login)
- Screener v2 — tri persistant + filtres composite + fraîcheur + export filtré (Sprint 109/114)
- Dashboard v2 — métriques détaillées + drill-down coût par skill + tendance quotidienne, grille responsive 12 colonnes
- Recherche sémantique RAG `/recherche` (Sprint 106)
- Tableau de bord alertes Celery (Sprint 99) + page Alertes `/alerts`
- Rapports PDF : ticker (par ticker **ou par analyse précise** depuis Sprint 122), screener, watchlist, mensuel
- RAG Qdrant, Langfuse, Redis cache, Celery beat
- Frontend React 18 + Tailwind 4 + Vite 8 (port 5173) — 11 pages + auth, shell pleine largeur `max-w-shell`, design tokens sémantiques, palette de commandes ⌘K
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants structurés ; plus aucun JSON brut
- 1 432 CI pytest verts + 393 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.9.0, Sprint 122 ✅
3. `.claude/rules/conventions-frontend.md` — React 18, TS strict, structure pages/composants
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles
5. `frontend/src/App.tsx` (ou le routeur racine) + `frontend/src/pages/` — point de départ exact du sprint

---

## TÂCHE — Sprint 123 : Code-splitting des routes + lazy-load recharts

**Objectif** : accélérer le Time-To-Interactive de la première vue (Analyse) en isolant chaque page et la librairie recharts du bundle initial. Toutes les pages sont aujourd'hui importées statiquement dans le routeur — le navigateur télécharge tout le code (y compris recharts, lourd) avant d'afficher la première page.

### Spécification

1. **`React.lazy` + `Suspense` par route** — convertir les imports statiques de pages (`AnalyzePage`, `ScreenerPage`, `HistoryPage`, `WatchlistPage`, `DashboardPage`, `ComparePage`, `EsgPage`, `AlertsPage`, `SearchPage`, `AdminPage`, pages auth…) en imports dynamiques `React.lazy(() => import('./pages/...'))`. Envelopper le `<Routes>` (ou chaque `<Route element>`) dans un `<Suspense>` avec un fallback skeleton cohérent avec le design system.
2. **Fallback skeleton** — créer un composant `RouteFallback` (ou réutiliser un skeleton existant) affiché pendant le chargement d'un chunk de page. Doit respecter `max-w-shell` et les design tokens.
3. **Isoler recharts** — s'assurer que les composants utilisant recharts (`TickerComparisonChart`, graphiques Dashboard, etc.) ne sont chargés que dans les pages concernées (Dashboard, Comparer). Vérifier qu'aucun import statique de recharts ne subsiste dans le bundle d'entrée (App/routeur/composants partagés). Au besoin, `lazy`-charger le composant graphique lui-même.
4. **Vérifier le découpage** — confirmer via `npm run build` que des chunks séparés sont générés par page et que recharts est dans son propre chunk (analyser la sortie Vite/rollup).

### Tests obligatoires (pyramide)
- **Composant** : un test Vitest vérifiant que le routeur monte une page lazy après résolution du `Suspense` (le fallback skeleton apparaît puis la page) — utiliser `findBy*` / `waitFor`
- **Composant** : un test garantissant que le fallback `RouteFallback` se rend sans erreur
- Tous les tests existants doivent rester verts (le lazy-loading ne doit pas casser les tests de pages — adapter les `render` avec `Suspense` si nécessaire)
- ⚠️ Mock des appels API Claude inchangé (règle `tests-pyramide.md`)

### Note d'environnement (session web)

En session Claude Code sur le web, le conteneur est cloné à neuf. La préparation
des dépendances (venv backend `--system-site-packages` + binaire natif rollup) est
**automatisée** par le hook `SessionStart` → `scripts/setup-web-session.sh`
(idempotent). Si une commande échoue faute de dépendances, relancer
`bash scripts/setup-web-session.sh`. Commandes utiles ensuite :
- Lancer les tests : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals`
  et `cd frontend && node node_modules/vitest/vitest.mjs run`
- Lint/typecheck : `node node_modules/typescript/bin/tsc --noEmit` + `node node_modules/eslint/bin/eslint.js src`
  (frontend), `.venv/bin/ruff check app/ tests/` (backend)
- Build (pour vérifier le découpage) : `cd frontend && node node_modules/vite/bin/vite.js build`
- ⚠️ `cd frontend` persiste le cwd entre commandes — penser à revenir à la racine avant les commandes backend
- La stack Docker (Postgres/Redis/Qdrant) n'est pas démarrée → pas de test navigateur live possible dans le conteneur

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 124 — Persistance des préférences Screener côté serveur
**Objectif** : Migrer tri + filtres Screener du localStorage (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié. Endpoints `GET/PUT /preferences/screener`.
**Complexité** : Moyenne
**Justification** : Lier les préférences au compte (Sprint Login) offre une continuité multi-appareils.

### Sprint 125 — Annotations enrichies : tags + filtres
**Objectif** : Ajouter un champ `tags` (liste de mots-clés libres) aux annotations, indexé GIN, filtrable via `GET /history?tags=value,growth`. Affichage chips dans `HistoryTable` et `AnnotationSection`.
**Complexité** : Moyenne
**Justification** : Les annotations (Sprint 78) sont du texte libre sans structure ; les tags permettent un filtrage sémantique du portefeuille sans RAG.

### Sprint 126 — Vue « Portefeuille » agrégée
**Objectif** : Page `/portefeuille` synthétisant la watchlist par pilier (ETF/thématique/valeur/algo) avec allocation cible vs réelle et score composite moyen par pilier.
**Complexité** : Élevée
**Justification** : Matérialise le cadre four-pillar du projet, aujourd'hui conceptuel ; relie watchlist, composite_score et fiscalité par compte.

### Sprint 127 — Cohérence inter-skills affichée dans l'UI
**Objectif** : Exposer `inter_skill_conflicts` (déjà calculé côté backend, présent dans `AnalyzeResponse`) dans `AnalysisResult` — bannière listant les contradictions détectées entre skills.
**Complexité** : Faible
**Justification** : La donnée existe mais n'est pas rendue ; valeur immédiate pour repérer les thèses contradictoires.

### Sprint 128 — Comparaison de deux analyses d'un même ticker (diff temporel)
**Objectif** : `GET /ticker-report/{ticker}/diff?from_id=&to_id=` produisant un PDF (ou JSON) qui compare deux analyses persistées du même ticker — évolution des verdicts skill par skill, du composite_score et des ratios clés.
**Complexité** : Moyenne
**Justification** : Capitalise sur la reconstruction multi-skills du Sprint 122 ; donne une lecture « avant/après » d'une thèse dans le temps.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.9.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 123 — Code-splitting des routes + lazy-load recharts (React.lazy + Suspense
par page, fallback skeleton RouteFallback, isolation de recharts hors du bundle d'entrée,
vérification du découpage via vite build).
```
