# Sprint 121 — à définir

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.7.0 — Sprint 120 complété)

Le dépôt est public-ready et neuf des skills tier2 ont maintenant un rendu UI structuré (plus de JSON brut). Il ne reste que cinq skills affichés en JSON brut générique : **Fisher, Damodaran, Marks, Pabrai, Fiscalité CA/QC**.

**Nouveauté Sprint 120** — Refonte UI Lynch + Greenblatt + Munger + Klarman :
- **`LynchCategoriesSection.tsx`** — badge catégorie (6 archétypes en libellé FR), ratio PEG coloré (< 1 bull / 1-2 neutral / > 2 bear, N/A si null), badge tenbagger potentiel, score de qualité de croissance /5
- **`GreenblattSection.tsx`** — ROC + rendement des bénéfices en % avec couleur seuillée, situations spéciales en badges, verdict (TOP_DECILE/BON/MOYEN/EVITER)
- **`MungerSection.tsx`** — grille des biais cognitifs détectés (nom + impact MINEUR/MODERE/MAJEUR + description), badge lollapalooza si risque, analyse par inversion, verdict comportemental (CONFIANCE_JUSTIFIEE/BIAIS_DETECTE/ALERTE_ROUGE)
- **`KlarmanSection.tsx`** — type de situation qualifié (libellé FR), décote vs valeur intrinsèque colorée, scores marge de sécurité + préservation du capital /10, verdict (OPPORTUNITE_FORTE/OPPORTUNITE_MODEREE/ATTENDRE/PASSER)
- **Types TypeScript** structurés (`LynchCategoriesOutput`, `GreenblattOutput`, `BiaisCognitif`, `MungerOutput`, `KlarmanOutput`) — `AnalyzeResponse.lynch`, `.greenblatt`, `.munger` et `.klarman` ne sont plus `SkillOutput` générique
- **24 tests Vitest** — 6 par composant
- **AnalysisResult.tsx** — branché sur les nouveaux composants, plus de JSON brut pour ces quatre skills

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
- **UI skills riches** — EarningsQuality + Thèse + Dorsey Moat + Buffett Quality + Valorisation + Lynch + Greenblatt + Munger + Klarman (plus JSON brut)
- 1 423 CI pytest verts + 361 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.7.0, Sprint 120 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles

---

## TÂCHE — Sprint 121

**Ce sprint est à définir par Yves.** Choisir l'un des sprints suggérés ci-dessous, ou en spécifier un autre.

Aucun point de dette technique n'est en suspens. Skills encore affichés en JSON brut générique (`SkillSection`) : **Fisher, Damodaran, Marks, Pabrai, Fiscalité CA/QC** — la refonte UI peut se terminer (Sprint 121 ci-dessous), ou le projet peut pivoter vers le pipeline de données / l'export.

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

### Sprint 121 — Refonte UI skills restants (Fisher, Damodaran, Marks, Pabrai, Fiscalité)
**Objectif** : Terminer le pattern Sprints 118-120 sur les cinq derniers skills en JSON brut — p. ex. `FisherSection` (15 points + scuttlebutt), `DamodaranSection` (story vs numbers, test possible/plausible/probable), `MarksSection` (position dans le cycle / pendule de sentiment), `PabraiSection` (Dhandho + asymétrie), `CanadianTaxSection` (allocation par compte CELI/REER/CELIAPP). Lire d'abord les `schemas.py` de chaque skill dans `app/skills/tier2/` pour typer précisément.
**Complexité** : Moyenne
**Justification** : Clôt définitivement la refonte UI — plus aucun skill affiché en JSON brut générique.

### Sprint 122 — Export analyse individuelle en PDF enrichi
**Objectif** : `GET /ticker-report/{ticker}?analysis_id=X` incluant verdicts skill par skill, ratios clés, annotation existante et score ESG. Complète la boucle « analyser → lire → exporter ».
**Complexité** : Moyenne
**Justification** : Le PDF par ticker (Sprint 63) couvre 90 jours d'historique, pas une analyse précise ; valeur immédiate d'archivage et de partage.

### Sprint 123 — Code-splitting des routes + lazy-load recharts
**Objectif** : `React.lazy` + `Suspense` (fallback skeleton) par page, isolant recharts du bundle initial pour accélérer le TTI de la première vue (Analyse).
**Complexité** : Faible
**Justification** : Toutes les pages sont importées statiquement aujourd'hui ; quick win de performance perçue identifié à l'audit. Sans infrastructure à modifier, purement frontend.

### Sprint 124 — Persistance des préférences Screener côté serveur
**Objectif** : Migrer tri + filtres Screener du localStorage (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié. Endpoints `GET/PUT /preferences/screener`.
**Complexité** : Moyenne
**Justification** : Lier les préférences au compte (Sprint Login) offre une continuité multi-appareils.

### Sprint 125 — Annotations enrichies : tags + filtres
**Objectif** : Ajouter un champ `tags` (liste de mots-clés libres) aux annotations, indexé GIN, filtrable via `GET /history?tags=value,growth`. Affichage chips dans `HistoryTable` et `AnnotationSection`.
**Complexité** : Moyenne
**Justification** : Les annotations (Sprint 78) sont du texte libre sans structure ; les tags permettent un filtrage sémantique du portefeuille sans RAG.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.7.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 121 — [à compléter par Yves]
```
