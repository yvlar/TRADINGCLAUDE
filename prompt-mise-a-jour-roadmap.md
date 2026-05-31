# Sprint 145 — Provenance par ratio sur l'analyse rendue (AnalysisResult)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.28.0 — Sprint 142 complété)

Le Sprint 142 a rendu **déterministes les signaux détaillés** F-Score / C-Score : les 9 critères Piotroski (`f_score.criteria[].passe`) et 6 signaux Montier (`c_score.signaux[].present`) sont calculés en Python par signal (`piotroski_f_score_detail` / `montier_c_score_detail`, `app/services/financial_calculations.py`) et substitués post-parse, avec l'invariant `sum(passe)==f_score` / `sum(present)==c_score` garanti par construction. La UI (`FScoreCard`/`CScoreCard`) les affichait déjà → bénéfice immédiat sans changement frontend.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.28.0, Sprint 142 ✅
3. `.claude/rules/conventions-frontend.md` — cœur du sprint côté UI : React 18, TS strict (zéro `any`), structure composants, `data-testid` pour les tests Vitest
4. `.claude/rules/api-architecture.md` — pour le threading backend : `AnalyzeResponse`, `cost_usd` persisté, sérialisation des réponses (le champ provenance suit le même chemin que `ratios_fetched_at`/`ratios_source` posé au Sprint 139)

---

## TÂCHE — Sprint 145 : threader `ratios_provenance` jusqu'à `AnalyzeResponse` et l'afficher sur `AnalysisResult`

**Objectif** : le Sprint 141 a affiché la provenance par ratio (clé yfinance effective ≠ clé primaire → badge « repli ») **uniquement** sur `AnalyzeForm` (qui consomme le payload `/extract`). Une fois l'analyse lancée (SSE `complete`) ou rechargée depuis l'historique, `AnalysisResult` ne dispose pas de la provenance car `AnalyzeResponse` ne la porte pas. Combler l'écart **exactement comme le Sprint 139 l'a fait pour la source+date Graham** : threader `ratios_provenance` jusqu'à `AnalyzeResponse`, le reconstruire depuis l'historique, puis l'afficher sous la carte Graham de `AnalysisResult`.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Champ source backend** — `GrahamRatios.ratios_provenance: dict[str, str] | None` à `app/skills/tier2/graham_analysis/schemas.py:42` (posé Sprint 140).
2. **`AnalyzeResponse`** — porte déjà `ratios_fetched_at: str | None` `app/orchestrator/core.py:274` et `ratios_source: str | None` `:278` (threadés Sprint 139). **À AJOUTER** : `ratios_provenance: dict[str, str] | None = None` à côté. Helper existant à étendre : `_graham_ratios_trace(ratios)` `core.py:288` retourne `(date ISO|None, source|None)` ; les 4 sites de construction l'appellent (`core.py:521/537`, `:1045/1071`).
3. **Reconstruction depuis l'historique** — `report.py` : `_reconstruct_ratios_trace(row)` `app/api/endpoints/report.py:123` parse `GrahamRatios` depuis `input_data` (défensif) et appelle `_graham_ratios_trace` `:143` ; câblé `:190`. `ticker_report.py` : `_extract_ratios(row)` `app/api/endpoints/ticker_report.py:190` + `_graham_ratios_trace` `:289`. **À ÉTENDRE** pour propager aussi la provenance.
4. **Type TS** — `interface AnalyzeResponse` porte `ratios_fetched_at?`/`ratios_source?` `frontend/src/types/index.ts:39-40`. **À AJOUTER** : `ratios_provenance?: Record<string, string> | null`. `interface GrahamRatios` `:50` porte déjà `ratios_provenance` (Sprint 141).
5. **Affichage** — `AnalysisResult.tsx` affiche déjà la source+date sous la carte Graham (`data-testid="result-ratios-source"` `:212`). Helper d'affichage à cloner depuis `AnalyzeForm.tsx` : `ratiosEnRepli(provenance)` `:50`, `RATIO_PRIMARY_KEYS` `:36`, rendu badge `data-testid="ratios-provenance"` `:206`.

### Spécification

1. **Backend — `AnalyzeResponse`** : ajouter `ratios_provenance: dict[str, str] | None = None` (optionnel → rétrocompatible). Étendre `_graham_ratios_trace` (ou ajouter un helper parallèle) pour renvoyer aussi la provenance, et câbler les 4 sites de construction + les hits cache (round-trip `model_dump_json`/`model_validate_json` automatique). **Choix de type** : `dict[str, str] | None` direct (pas de hazard `datetime` ici, contrairement à Sprint 139).
2. **Backend — reconstruction historique** : `report.py` et `ticker_report.py` extraient `ratios_provenance` du `GrahamRatios` reparsé depuis `input_data` (défensif : None/illisible → `None` sans crash).
3. **Frontend** : ajouter `ratios_provenance?: Record<string, string> | null` à `AnalyzeResponse` (TS) ; factoriser le helper `ratiosEnRepli`/`RATIO_PRIMARY_KEYS` (aujourd'hui dans `AnalyzeForm.tsx`) — **envisager de l'extraire dans un module partagé** pour éviter la duplication, ou le cloner si l'extraction est trop coûteuse (justifier). Afficher le même badge signal-only sous la carte Graham de `AnalysisResult` (`data-testid` distinct, ex. `result-ratios-provenance`). Provenance `null`/toute-primaire → rien affiché.

### Tests obligatoires (pyramide)
- Backend : schema (`AnalyzeResponse` accepte `ratios_provenance` + défaut `None`), helper de trace (provenance présente / absente), reconstruction `report.py`/`ticker_report.py` (`input_data` avec/sans provenance + illisible → `None` sans crash).
- Frontend : composant `AnalysisResult` — provenance avec une clé de repli → badge affiché ; provenance toute-primaire ou `null` → aucun badge (cloner les cas du test `AnalyzeForm` du Sprint 141).
- Non-régression : `pytest`/`ruff` complets ; `tsc --noEmit` 0 erreur ; ESLint 0 ; Vitest vert.

### Note d'environnement (session web)
Sprint de threading/affichage — **aucun prompt de skill ni l'orchestrateur (routing) modifié → evals non concernées**. `node_modules` frontend probablement absent à l'amorçage → `npm install`. Stack Docker non démarrée, pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 141bis — Calibrer le drift `earnings_quality` (drapeaux_rouges + verdict)
**Objectif** : résoudre les 10 échecs d'evals `earnings` révélés au Sprint 137 — 8 × `drapeaux_rouges_cardinalite` (le modèle dépasse le `max` du golden) + 2 × `verdict_dans_valeurs_attendues` (005 KO, 020 MRO).
**Complexité** : Moyenne (point de jugement métier + re-run evals payant)
**Justification** : contrat sous-spécifié — le prompt n'impose aucune borne de cardinalité sur `drapeaux_rouges` alors que le golden en attend une. Deux pistes à trancher AVANT de coder : (a) resserrer le prompt (« liste au plus N drapeaux les plus matériels ») ; OU (b) élargir/corriger les bornes du golden. Commencer par auditer les 8 cas.
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` (champ `drapeaux_rouges_max`, 12 occurrences) ; prompt `app/skills/tier2/earnings_quality/prompts/system.md` (présent) ; schéma `app/skills/tier2/earnings_quality/schemas.py` (`drapeaux_rouges: list[str]` `:169`). **Contrainte** : re-run evals exige `ANTHROPIC_API_KEY` (absente du conteneur web → à faire en local, ~100 appels Haiku, ~33 min).

### Sprint 143 — Persistance + traçabilité des ratios earnings/valuation dans le PDF
**Objectif** : afficher la source+date des ratios `EarningsQualityRatios`/`ValuationRatios` dans les rapports PDF.
**Complexité** : Moyenne (PAS Faible — voir caveat)
**Justification** : le PDF ne reconstruit aujourd'hui **que** `GrahamRatios` depuis `input_data` ; les ratios earnings/valuation sont auto-extraits au runtime et **non persistés** dans `input_data`. Le sprint doit d'abord rendre ces ratios disponibles au moment de la construction du PDF (les persister ou les reconstruire), AVANT d'ajouter les lignes source+date. **À RECONCILIER avant d'implémenter** : vérifier si `input_data`/`result` contient ces ratios.
**Référence** : EXISTANT (vérifié cette session) — `_fmt_ratios_source` `app/services/pdf_report_service.py:150` et `_build_ratios_rows(r: GrahamRatios)` `:228` (Graham uniquement, ligne source `:245`) ; champs `EarningsQualityRatios.ratios_fetched_at` `app/skills/tier2/earnings_quality/schemas.py:69` / `.ratios_source` `:73` ; `ValuationRatios.ratios_fetched_at` `app/skills/tier2/stock_valuation/schemas.py:32` / `.ratios_source` `:36`. À CRÉER — disponibilité des ratios earnings/valuation au build PDF + rows source+date.

### Sprint 146 — Auditabilité : exposer le détail des accruals de Sloan
**Objectif** : décomposer le `accrual_ratio` de Sloan (aujourd'hui un seul flottant) en ses termes auditables (NI − CFO, actifs moyens), en parité avec les 8 indices Beneish et les termes X1-X5 Altman déjà exposés.
**Complexité** : Faible
**Justification** : `SloanDetail` ne porte que `accrual_ratio` + `interpretation` alors que M/Z/F/C exposent désormais leurs sous-composantes (Sprints 131/142) ; combler l'asymétrie d'auditabilité du 5ᵉ cadre.
**Référence** : EXISTANT (vérifié cette session) — `sloan_accrual_ratio(...)` `app/services/financial_calculations.py:703` (retourne `(NI - CFO)/actifs_moyens`) ; `class SloanDetail` `app/skills/tier2/earnings_quality/schemas.py:156` (`accrual_ratio` + `interpretation` seuls) ; substitution `_injecter_scores` `app/skills/tier2/earnings_quality/skill.py:157`. À CRÉER — fonction `sloan_accrual_detail` + champs termes sur `SloanDetail` + substitution.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.28.0), .claude/rules/conventions-frontend.md et api-architecture.md avant de commencer.
Sprint actif : 145 — Provenance par ratio sur l'analyse rendue (AnalysisResult).
Objectif : threader GrahamRatios.ratios_provenance (schemas.py:42) jusqu'à AnalyzeResponse (core.py:274-288, à côté de ratios_fetched_at/ratios_source posés au Sprint 139), le reconstruire depuis l'historique (report.py:123, ticker_report.py:190/289), puis l'afficher en signal-only sous la carte Graham de AnalysisResult — en clonant ratiosEnRepli/RATIO_PRIMARY_KEYS de AnalyzeForm.tsx:36-50 (badge data-testid="ratios-provenance" :206).
Pattern de référence : Sprint 139 (threading source+date) est le modèle exact à suivre.
Evals : sprint de threading/affichage → aucun prompt de skill modifié → evals non concernées.
```
