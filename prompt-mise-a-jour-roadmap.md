# Sprint 144 — Traçabilité source+date earnings/valuation dans le PDF

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.29.0 — Sprint 143 complété)

Le Sprint 143 a rendu déterministes les **libellés d'interprétation au niveau cadre** F/C : `f_score.interpretation` (`forte_qualite`/`bonne_qualite`/`qualite_moyenne`/`value_trap`) et `c_score.interpretation` (`propre`/`signaux_mineurs`/`signaux_multiples`) sont dérivés du score agrégé déterministe et substitués post-parse — parité complète avec M/Z (Sprint 131). Reste LLM : l'interprétation Sloan (cf. sprint suggéré 148).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals différées** — `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutables ici. **CE sprint touche un rapport PDF, pas un prompt de skill ni l'orchestrateur → evals non concernées.** (Le PDF est rendu en Python depuis l'output persisté.)

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.29.0, Sprint 143 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : « une donnée sans date est inutilisable » ; traçabilité source+date obligatoire sur tout rapport.
4. `.claude/rules/api-architecture.md` — section sur la reconstruction depuis `analysis_history` / `input_data` (le PDF reconstruit les ratios depuis le JSONB persisté).

---

## TÂCHE — Sprint 144 : afficher la source+date des ratios earnings/valuation dans les rapports PDF

**Objectif** : le rapport PDF par ticker ne rend aujourd'hui la ligne « Source des ratios » **que pour Graham** (`_build_ratios_rows(r: GrahamRatios)`). Les ratios `EarningsQualityRatios` et `ValuationRatios` portent désormais `ratios_fetched_at`/`ratios_source` (Sprint 138) mais cette traçabilité n'apparaît pas dans le PDF. Compléter la parité de traçabilité côté rapport.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Helper de formatage réutilisable** — `_fmt_ratios_source(source: str | None, fetched_at: datetime | None) -> str` `app/services/pdf_report_service.py:150` (réutilisable tel quel pour earnings/valuation).
2. **Rendu Graham actuel** — `_build_ratios_rows(r: GrahamRatios)` `pdf_report_service.py:228` ; ligne « Source des ratios » `:245` ; appelé `:327`.
3. **Champs disponibles sur les schemas** — `EarningsQualityRatios.ratios_fetched_at` `app/skills/tier2/earnings_quality/schemas.py:69` / `ratios_source` `:73` ; `ValuationRatios.ratios_fetched_at` `app/skills/tier2/stock_valuation/schemas.py:32` / `ratios_source` `:36`.
4. **Reconstruction des ratios pour le PDF (LE point à vérifier en premier — d'où la complexité Moyenne)** — `_extract_ratios(row) -> GrahamRatios | None` `app/api/endpoints/ticker_report.py:190` ne reconstruit **que** `GrahamRatios` depuis `input_data`. **AVANT d'implémenter l'affichage**, vérifier si les ratios earnings/valuation (avec leur `ratios_fetched_at`/`ratios_source`) sont **persistés dans `input_data` et reconstructibles**. Si oui → ajouter leur reconstruction + lignes PDF. Si non → le sprint doit d'abord les threader/persister (re-cadrer le périmètre et me le signaler).

### Spécification

1. **Vérification de reconstructibilité d'abord** (Phase A de réconciliation) : inspecter le contenu réel de `input_data` persisté (test/mock ou structure du payload `/analyze`) pour confirmer la présence des ratios earnings/valuation horodatés. Documenter le constat (`fichier:ligne`) avant de coder l'affichage.
2. **Si reconstructibles** : étendre `pdf_report_service.py` pour rendre une ligne « Source des ratios (Qualité bénéfices) » et/ou « Source des ratios (Valorisation) » via le helper `_fmt_ratios_source` existant — **réutiliser le helper, ne pas dupliquer le formatage**. Câbler la reconstruction dans `ticker_report.py` (analogue à `_extract_ratios`).
3. **Périmètre** : traçabilité PDF earnings/valuation **uniquement**. Ne pas retoucher l'affichage Graham existant ni le threading `AnalyzeResponse` (Sprints 139/143). Pas de changement de prompt de skill.
4. **Honnêteté None** : ratio sans source/date → ne pas afficher de ligne trompeuse (cohérent avec le comportement Graham `None` → ligne omise).

### Tests obligatoires (pyramide)
- Unitaire `pdf_report_service` : `_build_ratios_rows` (ou nouveau builder) rend la ligne source+date quand présente, l'omet sinon (parité avec le comportement Graham).
- Intégration `ticker_report.py` : reconstruction earnings/valuation depuis un `input_data` avec/sans horodatage + `input_data` illisible → pas de crash.
- Non-régression : `pytest` (hors e2e/evals) + `ruff` complets ; frontend inchangé (sprint backend pur).

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals non exécutables, **mais ce sprint ne touche aucun prompt de skill ni l'orchestrateur → evals non concernées**. Stack Docker non démarrée ; pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 145 — Affichage de la traçabilité earnings sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios`, sous la carte Earnings Quality.
**Complexité** : Moyenne (threading backend jusqu'à `AnalyzeResponse`).
**Justification** : parité d'affichage avec Graham ; les champs existent sur le schema mais ne sont ni threadés jusqu'à `AnalyzeResponse` ni affichés.
**Référence** : EXISTANT (vérifié cette session) — `EarningsQualityRatios.ratios_fetched_at` `earnings_quality/schemas.py:69` / `ratios_source` `:73` ; pattern de threading Graham déjà fait (`AnalyzeResponse.ratios_fetched_at` `app/orchestrator/core.py:274` / `ratios_source` `:278`, helper `_graham_ratios_trace` `:284`). À CRÉER — un `_earnings_ratios_trace` analogue + champ(s) sur `AnalyzeResponse` + reconstruction historique + affichage `EarningsQualitySection`.

### Sprint 146 — Provenance par ratio sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage signal-only de la provenance (posé pour `AnalyzeForm` au Sprint 141) à `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (comme la source+date au Sprint 139).
**Complexité** : Moyenne (backend : `AnalyzeResponse` + reconstruction historique).
**Justification** : le Sprint 141 s'est limité au frontend (`/extract`) ; `AnalysisResult` reconstruit depuis l'historique n'a pas la provenance.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance` `app/skills/tier2/graham_analysis/schemas.py:42` ; threading source+date Graham déjà en place (`core.py:274/278/284`) ; helper d'affichage à cloner `frontend/src/components/AnalyzeForm.tsx` (`ratiosEnRepli`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` + reconstruction historique + affichage.

### Sprint 147 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre **désormais** la cardinalité — fix déjà livré, pas absent. Reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — consigne de cardinalité `app/skills/tier2/earnings_quality/prompts/system.md:195` (et `:291`) ; golden `tests/evals/fixtures/earnings_golden.json` (`"drapeaux_rouges_max": 2` aux cas, lignes 47/96/145/193/241) ; schema `EarningsQualityOutput.drapeaux_rouges: list[str]` `earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 148 — Interprétation déterministe Sloan (dernier cadre LLM)
**Objectif** : rendre déterministe `sloan.interpretation` (dernier libellé d'interprétation encore produit par le LLM après les Sprints 131/143), dérivé du `accrual_ratio` déjà calculé en Python — parité finale des 5 cadres.
**Complexité** : Faible (calque exact du pattern Sprint 143).
**Justification** : `_injecter_scores` substitue déjà `sloan.accrual_ratio` mais **pas** `sloan.interpretation` → seul cadre où le libellé peut diverger du chiffre déterministe. Boucle la cohérence chiffre↔libellé sur l'ensemble M/Z/F/C/Sloan.
**Référence** : EXISTANT (vérifié cette session) — `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (LLM, jamais substitué) ; `_injecter_scores` ne pose que `data["sloan"]["accrual_ratio"]` `app/skills/tier2/earnings_quality/skill.py:190` ; `scores.accrual_ratio` déjà calculé (`sloan_accrual_ratio`, `skill.py:155`) ; seuils canoniques `app/skills/tier2/earnings_quality/prompts/system.md:163-165` (≤ −0.05 `qualite_elevee` · −0.05 à 0.05 `neutre` · > 0.05 `qualite_degradee`). À CRÉER — `_sloan_interpretation(accrual_ratio: float | None) -> str` dans `financial_calculations.py` (calque `_piotroski_interpretation`) + champ `sloan_interpretation` sur `_ScoresDeterministes` + substitution sous gate `accrual_ratio is not None`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.29.0), .claude/rules/donnees-financieres.md et api-architecture.md avant de commencer.
Sprint actif : 144 — Traçabilité source+date earnings/valuation dans le PDF.
Objectif : afficher la source+date des ratios EarningsQualityRatios / ValuationRatios dans les rapports PDF (le PDF ne rend aujourd'hui que la ligne « Source des ratios » Graham).
Point de départ vérifié : helper _fmt_ratios_source réutilisable (pdf_report_service.py:150), _build_ratios_rows Graham (:228, ligne source :245), champs sur les schemas (earnings_quality/schemas.py:69/73, stock_valuation/schemas.py:32/36).
ÉTAPE 1 OBLIGATOIRE (réconciliation) : vérifier si les ratios earnings/valuation (avec source/date) sont persistés dans input_data et reconstructibles — _extract_ratios (ticker_report.py:190) ne reconstruit que GrahamRatios. Si non reconstructibles, re-cadrer le périmètre et me le signaler AVANT de coder.
Evals : ce sprint ne touche aucun prompt de skill ni l'orchestrateur → evals non concernées.
```
