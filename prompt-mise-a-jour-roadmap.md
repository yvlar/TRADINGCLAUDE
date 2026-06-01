# Sprint 143 — Interprétations déterministes F-Score / C-Score (parité M-Score / Z-Score)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.28.0 — Sprint 142 complété)

Le Sprint 142 a rendu déterministes les **signaux détaillés** F/C : `f_score.criteria[].passe` (9 Piotroski) et `c_score.signaux[].present` (6 Montier) sont calculés en Python (`piotroski_f_criteria`/`montier_c_signaux`) et substitués post-parse, avec invariant `sum(passe) == f_score` / `sum(present) == c_score` garanti par construction.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals différées** — `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutables ici. **Pertinent pour CE sprint** : rendre l'interprétation F/C déterministe modifie l'output `earnings_quality` → relancer les evals ciblées en local (ou expliciter « non exécutées faute de clé »).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.28.0, Sprint 142 ✅
3. `.claude/rules/api-skills-tier2.md` — cœur du sprint : skill tier2 `earnings_quality`, schemas Pydantic font foi, substitution post-parse via `_injecter_scores`.
4. `.claude/rules/donnees-financieres.md` — un score `None` (donnée manquante / financière) → interprétation `"DONNEES_MANQUANTES"`, jamais un libellé trompeur ; conserver la valeur LLM si le calcul Python n'aboutit pas.

---

## TÂCHE — Sprint 143 : rendre déterministe l'interprétation au niveau cadre F-Score / C-Score

**Objectif** : le Sprint 142 a rendu déterministes les *signaux* F/C, mais les **libellés d'interprétation au niveau cadre** — `f_score.interpretation` et `c_score.interpretation` — restent **produits par le LLM**, alors que les interprétations M-Score / Z-Score sont déjà déterministes (Python, Sprint 131 : `_beneish_interpretation` / `_altman_interpretation`, portées par le dataclass et substituées en bloc). Compléter la parité : dériver l'interprétation F/C du **score agrégé déjà déterministe** selon les seuils des références, et la substituer post-parse. C'est le même remède qui a éliminé la dérive de vocabulaire des golden M/Z.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Champs à substituer** — `FScoreDetail.interpretation` `app/skills/tier2/earnings_quality/schemas.py:141` ; `CScoreDetail.interpretation` `:153` (actuellement peuplés par le LLM).
2. **Précédent M/Z à cloner** — `_beneish_interpretation` / `_altman_interpretation` dans `app/services/financial_calculations.py` (None → `"DONNEES_MANQUANTES"`, sinon libellé par seuil ; testés par `TestInterpretationsDeterministes` dans `tests/services/test_financial_calculations.py`). Elles sont portées par `BeneishComponents.interpretation` / `AltmanComponents.interpretation` et substituées via `asdict()` dans `_injecter_scores`.
3. **Substitution F/C existante (Sprint 142)** — `_injecter_scores` écrit déjà `f_score`/`c_score` + `criteria`/`signaux` sous le gate `if scores.f_criteria is not None` / `if scores.c_signaux is not None` (`app/skills/tier2/earnings_quality/skill.py:183-190`). Le score agrégé est dérivé dans `_scores_depuis_ratios` (`f_score=None if f_criteria is None else sum(...)`).
4. **Seuils (références `.claude/skills/earnings-quality-fraud-detection/references/piotroski-f-score.md` et `montier-c-score.md`)** : F-Score 8-9 forte qualité · 7 bon · 4-6 moyen · 0-3 qualité dégradée ; C-Score 0-1 propre · 2-3 surveiller · 4-6 manipulation probable.
5. **Vocabulaire existant à RESPECTER** — la fixture `earnings_output_msft` (`tests/conftest.py`) utilise `interpretation="forte_qualite"` (F=8) et `"propre"` (C=0). **Réconcilier les chaînes exactes** avec le golden `tests/evals/fixtures/earnings_golden.json` et le rendu frontend `frontend/src/components/EarningsQualitySection.tsx` AVANT de figer les libellés (un libellé divergent casserait le golden ou l'affichage).

### Spécification

1. **Fonctions pures** : ajouter `_piotroski_interpretation(f_score: int | None) -> str` et `_montier_interpretation(c_score: int | None) -> str` dans `financial_calculations.py`, calquées sur `_beneish_interpretation` (signature, gestion `None → "DONNEES_MANQUANTES"`, libellé par seuil). Réutiliser le vocabulaire existant identifié au point 5.
2. **Portage** : calculer l'interprétation dans `_scores_depuis_ratios` à partir du score agrégé déjà dérivé (voie la plus simple — le score est déjà calculé), et la stocker dans `_ScoresDeterministes` (nouveaux champs `f_interpretation` / `c_interpretation: str | None`). `None` quand le score agrégé est `None` (financière / donnée manquante), exactement comme le score.
3. **Substitution** : dans `_injecter_scores`, sous le **même gate** que `criteria`/`signaux`, écrire `data["f_score"]["interpretation"]` / `data["c_score"]["interpretation"]`. Financière → F conservé du LLM (gate None), C substitué (pas de gate sectoriel, parité Sprint 142).
4. **Périmètre** : interprétation F/C **uniquement**. Ne pas retoucher `criteria`/`signaux`/scores (Sprint 142) ni M/Z (Sprint 131). Prompt de skill inchangé.

### Tests obligatoires (pyramide)
- Unitaire `financial_calculations` : `_piotroski_interpretation` / `_montier_interpretation` par seuil (8-9 / 7 / 4-6 / 0-3 ; 0-1 / 2-3 / 4-6 ; `None → "DONNEES_MANQUANTES"`), à l'image de `TestInterpretationsDeterministes`.
- Intégration `skill.py` (Claude mocké) : `_injecter_scores` écrase `f_score.interpretation` / `c_score.interpretation` du bloc LLM (poison) ; financière → interprétation F LLM conservée, C substituée.
- Non-régression : `pytest` (hors e2e/evals) + `ruff` complets ; frontend inchangé sauf si les libellés exigent un ajustement d'affichage (alors test composant).

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals Claude réelles non exécutables en web (à faire en local). Stack Docker non démarrée ; pas de test navigateur live. Sprint backend pur (sauf réconciliation de libellés côté frontend). **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes** (flush sporadique observé en session web — les complétions de tâches en arrière-plan déclenchent le flush).

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 144 — Traçabilité source+date earnings/valuation dans le PDF
**Objectif** : afficher la source+date des ratios `EarningsQualityRatios` / `ValuationRatios` dans les rapports PDF (le PDF ne rend aujourd'hui que la ligne « Source des ratios » **Graham**).
**Complexité** : Moyenne (dépendance de reconstruction à vérifier — pas Faible).
**Justification** : suite du Sprint 138 (les champs `ratios_fetched_at`/`ratios_source` existent sur ces schemas), complète la parité de traçabilité côté rapport.
**Référence** : EXISTANT (vérifié cette session) — helper générique `_fmt_ratios_source(source, fetched_at)` `app/services/pdf_report_service.py:150` (réutilisable tel quel) ; `_build_ratios_rows(r: GrahamRatios)` `:228` + ligne « Source des ratios » `:244-245` (**Graham uniquement**) ; champs `EarningsQualityRatios.ratios_fetched_at/source` `earnings_quality/schemas.py:69/73`, `ValuationRatios` `stock_valuation/schemas.py:32/36`. À CRÉER / À VÉRIFIER — la reconstruction des ratios d'entrée pour le PDF ne couvre que Graham (`_extract_ratios(row) -> GrahamRatios | None` `app/api/endpoints/ticker_report.py:190`) ; **vérifier d'abord** si les ratios earnings/valuation (avec leur source/date) sont persistés dans `input_data` et reconstructibles — sinon le sprint doit d'abord les threader/persister (d'où la complexité Moyenne).

### Sprint 145 — Affichage de la traçabilité earnings sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios`, sous la carte Earnings Quality.
**Complexité** : Moyenne (threading backend jusqu'à `AnalyzeResponse`).
**Justification** : parité d'affichage avec Graham ; les champs existent sur le schema mais ne sont ni threadés jusqu'à `AnalyzeResponse` ni affichés.
**Référence** : EXISTANT (vérifié cette session) — `EarningsQualityRatios.ratios_fetched_at` `earnings_quality/schemas.py:69` / `ratios_source` `:73` ; pattern de threading Graham déjà fait (`AnalyzeResponse.ratios_fetched_at/source` `app/orchestrator/core.py:274/278`, helper `_graham_ratios_trace` `:284`). À CRÉER — un `_earnings_ratios_trace` analogue + champ(s) sur `AnalyzeResponse` + reconstruction historique + affichage `EarningsQualitySection`.

### Sprint 146 — Provenance par ratio sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage signal-only de la provenance (posé pour `AnalyzeForm` au Sprint 141) à `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (comme la source+date au Sprint 139).
**Complexité** : Moyenne (backend : `AnalyzeResponse` + reconstruction historique).
**Justification** : le Sprint 141 s'est limité au frontend (`/extract`) ; `AnalysisResult` reconstruit depuis l'historique n'a pas la provenance.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance` `app/skills/tier2/graham_analysis/schemas.py:42` ; threading source+date Graham déjà en place (`core.py:274/278/284`) ; helper d'affichage à cloner `frontend/src/components/AnalyzeForm.tsx` (`ratiosEnRepli`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` + reconstruction historique + affichage.

### Sprint 147 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre **désormais** la cardinalité (« au plus un à deux signaux mineurs réellement matériels ») — fix déjà livré, pas absent comme le supposait l'ancienne carte. Reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — consigne de cardinalité `app/skills/tier2/earnings_quality/prompts/system.md:195` (et `:291`) ; golden `tests/evals/fixtures/earnings_golden.json` (`"drapeaux_rouges_max": 2` aux cas, lignes 47/96/145/193/241) ; schema `EarningsQualityOutput.drapeaux_rouges: list[str]` `earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.28.0), .claude/rules/api-skills-tier2.md et donnees-financieres.md avant de commencer.
Sprint actif : 143 — Interprétations déterministes F-Score / C-Score (parité M/Z).
Objectif : rendre déterministes f_score.interpretation (schemas.py:141) et c_score.interpretation (:153), aujourd'hui produits par le LLM, en les dérivant du score agrégé déjà déterministe — exactement comme _beneish_interpretation/_altman_interpretation (Sprint 131).
Point de départ vérifié : _injecter_scores substitue déjà criteria/signaux/scores sous gate None (skill.py:183-190) ; ajouter _piotroski_interpretation/_montier_interpretation dans financial_calculations.py + champs f_interpretation/c_interpretation sur _ScoresDeterministes.
RÉCONCILIER les libellés exacts avec la fixture (forte_qualite/propre), le golden earnings_golden.json et EarningsQualitySection.tsx AVANT de figer les chaînes.
Evals : la substitution change l'output earnings_quality → relancer les evals ciblées si ANTHROPIC_API_KEY dispo, sinon le dire explicitement.
```
