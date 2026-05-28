# Sprint 122 — Export analyse individuelle en PDF enrichi

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.8.0 — Sprint 121 complété)

La refonte UI est **terminée** : les 16 skills tier2 ont désormais un rendu UI structuré. Le composant générique `SkillSection` (qui affichait du JSON brut) a été **retiré** — plus aucun skill n'est affiché en JSON brut.

**Nouveauté Sprint 121** — Refonte UI Fisher + Damodaran + Marks + Pabrai + Fiscalité :
- **`FisherSection.tsx`** — badge qualité de direction (libellé FR exceptionnelle/bonne/adéquate/médiocre), score Fisher /30, liste des 15 points (titre + commentaire + score /2 coloré)
- **`DamodaranSection.tsx`** — échelle possible→plausible→probable (niveau atteint mis en évidence, état incohérent en rouge), solidité de la narrative /10, ERP implicite en %, divergences story vs numbers en badges
- **`MarksSection.tsx`** — jauge du pendule de sentiment −5/+5 avec marqueur, position dans le cycle (libellé FR), badge timing, second-level thinking ; score coloré selon la logique contrariante (négatif = opportunité)
- **`PabraiSection.tsx`** — asymétrie upside/downside (×), Kelly fractionnel (% ou N/A), score heads-I-win /9, grille des 9 principes Dhandho ✓/✗ + commentaire
- **`CanadianTaxSection.tsx`** — badge compte recommandé (CELI/REER/CELIAPP/non-enregistré, libellé FR + sigle EN), taux d'inclusion gain en capital, retenue US, badge Smith Manœuvre
- **Types TypeScript** structurés (`FisherOutput`, `FisherPoint`, `DamodaranOutput`, `MarksOutput`, `DhandhoPrincipe`, `PabraiOutput`, `CanadianTaxOutput`) — `AnalyzeResponse.fisher`, `.damodaran`, `.marks`, `.pabrai` et `.canadian_tax` ne sont plus `SkillOutput` générique
- **30 tests Vitest** — 6 par composant
- **AnalysisResult.tsx** — branché sur les cinq nouveaux composants ; `SkillSection` et l'import `SkillOutput` retirés

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
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants structurés ; plus aucun JSON brut
- 1 423 CI pytest verts + 391 Vitest verts + 4 jobs CI GitHub Actions opérationnels

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.8.0, Sprint 121 ✅
3. `.claude/rules/` — 16 fichiers de règles path-scoped (conventions, architecture, tests)
4. `docs/cheatsheet.md` — toutes les commandes opérationnelles
5. `app/api/endpoints/ticker_report.py` + `app/services/pdf_report_service.py` — point de départ exact du sprint

---

## TÂCHE — Sprint 122 : Export analyse individuelle en PDF enrichi

**Objectif** : permettre l'export PDF d'**une analyse précise** (pas seulement l'historique 90 jours). Aujourd'hui `GET /ticker-report/{ticker}?days=90` agrège l'historique `composite_score` et reconstruit la **dernière** analyse en ne parsant que 3 skills (Graham/Buffett/Dorsey — voir `_reconstruct_analyze_response`). Le sprint ajoute le ciblage par `analysis_id` et un PDF riche.

### Spécification

1. **Endpoint** — étendre `GET /ticker-report/{ticker}` avec un paramètre optionnel `analysis_id: str | None = None` :
   - si `analysis_id` fourni → charger **cette** ligne précise de `analysis_history` (`WHERE id = $1 AND ticker = $2`), 404 si absente/mismatch ticker
   - si absent → comportement actuel inchangé (dernière analyse + historique 90 j) — **rétrocompatibilité obligatoire**
2. **Reconstruction complète** — généraliser `_reconstruct_analyze_response` pour parser **tous** les skills présents dans `result` (les 16 outputs tier2), pas seulement Graham/Buffett/Dorsey. Réutiliser les schemas Pydantic existants (`model_validate` tolérant : un skill qui ne parse pas est ignoré, pas d'échec global).
3. **Enrichissement du PDF** (`PdfReportService.generate_ticker_report`) — ajouter, pour une analyse ciblée :
   - **verdicts skill par skill** (un tableau : skill / verdict / détail court)
   - **ratios clés** (depuis l'input/ratios Graham : eps, bvps, pe, pb, roe, debt_equity…)
   - **annotation existante** si présente (table annotations, Sprint 78 — `GET /annotations` / service associé)
   - **score ESG** si présent dans le `result` ou via `last_esg_score`
4. **Frontend (optionnel si le temps le permet)** — bouton « Exporter cette analyse » dans `AnalysisResult` / `HistoryPage` passant `analysis_id` à `downloadTickerPdf()`.

### Tests obligatoires (pyramide)
- **Intégration** : `GET /ticker-report/{ticker}?analysis_id=<id>` → 200 + `application/pdf` ; 404 si id inconnu ; 404 si id appartient à un autre ticker ; rétrocompat sans `analysis_id`
- **Unitaire** : `_reconstruct_analyze_response` parse correctement un `result` multi-skills et ignore un skill corrompu
- Patcher `call_claude_with_retry` partout (règle `tests-pyramide.md`) — aucun appel Claude réel

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
- **reportlab** est déjà la dépendance PDF du projet — ne pas en introduire une autre

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 123 — Code-splitting des routes + lazy-load recharts
**Objectif** : `React.lazy` + `Suspense` (fallback skeleton) par page, isolant recharts du bundle initial pour accélérer le TTI de la première vue (Analyse).
**Complexité** : Faible
**Justification** : Toutes les pages sont importées statiquement aujourd'hui ; quick win de performance perçue, purement frontend, sans infrastructure à modifier.

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

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.8.0), et les règles .claude/rules/ avant de commencer.
Sprint actif : 122 — Export analyse individuelle en PDF enrichi (ciblage par analysis_id,
reconstruction multi-skills, PDF avec verdicts skill par skill + ratios + annotation + ESG).
```
