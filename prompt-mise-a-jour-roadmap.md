# Sprint 142 — Calculs déterministes : signaux détaillés F-Score / C-Score

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.27.0 — Sprint 141 complété)

Le Sprint 141 a propagé côté **frontend** la provenance par ratio exposée au Sprint 140 : `interface GrahamRatios` porte `ratios_provenance?: Record<string, string> | null`, et `AnalyzeForm` affiche un badge **signal-only** sous la carte Graham (uniquement quand la clé yfinance effective ≠ clé primaire).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint 137 différé** — les evals ciblées (Claude réel) exigent `ANTHROPIC_API_KEY`, absente du conteneur web → à exécuter en local. **Pertinent pour CE sprint** : la substitution déterministe des signaux F/C modifie l'output du skill `earnings_quality` → les evals ciblées doivent être relancées (ou le constat « non exécutées faute de clé » explicité). Voir SPRINTS SUGGÉRÉS (141bis).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.27.0, Sprint 141 ✅
3. `.claude/rules/api-skills-tier2.md` — cœur du sprint : skill tier2 `earnings_quality`, schemas Pydantic font foi, substitution post-parse `model_validate()`. Pattern existant `_injecter_scores` à étendre.
4. `.claude/rules/donnees-financieres.md` — les fonctions pures par signal doivent valider `None`/division par zéro avant tout calcul (un signal indéterminable = pas de substitution, on conserve la valeur LLM ; jamais un `False` trompeur).

---

## TÂCHE — Sprint 142 : rendre déterministes les signaux détaillés F-Score / C-Score

**Objectif** : aujourd'hui seuls les **scores agrégés** F-Score (0-9) et C-Score (0-6) sont déterministes (calcul Python + substitution post-parse, Sprints 128/131). Les **signaux individuels** — `f_score.criteria[].passe` (9 critères Piotroski) et `c_score.signaux[].present` (6 signaux Montier) — restent **interprétés par le LLM**, donc non rejouables et susceptibles de dériver du score agrégé qu'ils sont censés composer. Calculer ces booléens en Python et les substituer, en cohérence stricte avec le score agrégé déjà déterministe.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Schemas** — `class FScoreCriterion(BaseModel)` (`nom`/`passe`/`detail`) à `app/skills/tier2/earnings_quality/schemas.py:132` ; `class CScoreSignal(BaseModel)` (`nom`/`present`/`detail`) à `:144`. Conteneurs `FScoreDetail.criteria` `:138`, `CScoreDetail.signaux` `:150`.
2. **Substitution existante** — `_injecter_scores(data, scores)` à `app/skills/tier2/earnings_quality/skill.py:154` : substitue déjà `m_score`/`z_score` en bloc (`asdict`), `sloan.accrual_ratio`, et **seulement l'entier** `f_score.f_score` (`:169`) / `c_score.c_score` (`:171`). **À ÉTENDRE** : substituer aussi les listes `criteria`/`signaux`.
3. **Calculs déterministes existants** — `app/services/financial_calculations.py` (fichier présent) contient déjà les fonctions de scoring agrégé F/C (Sprint 128) à partir de `EarningsQualityRatios`. **À CRÉER** : fonctions pures par signal (ou retour structuré listant chaque critère + son booléen + son détail) réutilisant les mêmes entrées, de sorte que `sum(passe) == f_score` par construction.

### Spécification

1. **Calcul Python par signal** : pour les 9 critères Piotroski et 6 signaux Montier, produire en Python `(nom, passe/present, detail)` à partir des `EarningsQualityRatios`. La somme des booléens **doit** égaler le score agrégé déjà calculé (invariant testable). Réutiliser les seuils/formules déjà encodés pour le score agrégé — ne pas dupliquer une logique divergente.
2. **Substitution** : étendre `_injecter_scores` pour écraser `data["f_score"]["criteria"]` et `data["c_score"]["signaux"]` par les listes Python. **Cohérence None/financière** : si le calcul ne peut aboutir (donnée manquante, banque `is_financial` pour les signaux inapplicables), conserver la sortie LLM existante plutôt que d'injecter un `False` trompeur — exactement comme `f_score`/`c_score` entiers conservent la valeur LLM si le calcul Python est `None` (`skill.py:168-171`).
3. **Décision de périmètre** : se limiter aux signaux F/C. M-Score (8 indices) et Z-Score (X1-X5) sont déjà déterministes (Sprint 131) ; ne pas y toucher.

### Tests obligatoires (pyramide)
- Unitaire `financial_calculations` : un jeu de ratios connu → les 9 critères F / 6 signaux C avec les booléens attendus ; **invariant** `sum(passe) == f_score` et `sum(present) == c_score` ; cas donnée manquante → signal non calculable (None/skip).
- Intégration `skill.py` (`call_claude_with_retry` mocké, cf. `tests-pyramide.md`) : `_injecter_scores` écrase bien les `criteria[].passe`/`signaux[].present` du bloc LLM ; cas financière/donnée manquante → valeurs LLM conservées sans crash.
- **Evals** : la substitution change l'output `earnings_quality` → relancer les evals ciblées si `ANTHROPIC_API_KEY` disponible ; sinon **le dire explicitement** (non exécutées en conteneur web).
- Non-régression : `pytest`/`ruff` complets ; frontend inchangé.

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente du conteneur → evals Claude réelles non exécutables en web (à faire en local). Stack Docker non démarrée. Pas de test navigateur live. Sprint backend pur → `node_modules`/Vitest non concernés. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 141bis — Calibrer le drift `earnings_quality` (drapeaux_rouges + verdict)
**Objectif** : résoudre les 10 échecs d'evals `earnings` révélés au Sprint 137 — 8 × `drapeaux_rouges_cardinalite` (le modèle dépasse le `max` du golden) + 2 × `verdict_dans_valeurs_attendues` (005 KO, 020 MRO).
**Complexité** : Moyenne (point de jugement métier + re-run evals payant)
**Justification** : contrat sous-spécifié — le prompt n'impose aucune borne de cardinalité sur `drapeaux_rouges` alors que le golden en attend une. Deux pistes à trancher AVANT de coder : (a) **resserrer le prompt** (« liste au plus N drapeaux les plus matériels ») — touche un prompt de skill, exige re-run evals ; OU (b) **élargir/corriger les bornes du golden** si elles sont irréalistes. Commencer par auditer les 8 cas.
**Référence** : EXISTANT (vérifié session 140) — golden `tests/evals/fixtures/earnings_golden.json` (champ `drapeaux_rouges_max`) ; prompt `app/skills/tier2/earnings_quality/prompts/system.md` (schéma `"drapeaux_rouges": []`, aucune consigne de cardinalité) ; schéma `app/skills/tier2/earnings_quality/schemas.py` (`drapeaux_rouges: list[str]`). **Contrainte** : re-run evals exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min).

### Sprint 143 — Traçabilité source+date dans le PDF earnings/valuation
**Objectif** : afficher la source+date des ratios `EarningsQualityRatios`/`ValuationRatios` dans les rapports PDF (le PDF ne couvre aujourd'hui que la ligne « Source des ratios » Graham).
**Complexité** : Faible
**Justification** : suite naturelle du Sprint 138 (les champs existent désormais sur ces schemas) ; complète la parité de traçabilité côté rapport.
**Référence** : EXISTANT (vérifié cette session) — `_fmt_ratios_source` `app/services/pdf_report_service.py:150` et `_build_ratios_rows(r: GrahamRatios)` `:228` (Graham uniquement). À CRÉER — rows source+date pour earnings/valuation quand ces ratios sont reconstruits dans le PDF.

### Sprint 144 — Affichage de la traçabilité earnings sur l'analyse rendue
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios` sous la carte Earnings Quality.
**Complexité** : Faible
**Justification** : parité d'affichage avec Graham ; les champs `ratios_fetched_at`/`ratios_source` existent déjà sur `EarningsQualityRatios` (Sprint 138) mais ne sont pas threadés jusqu'à `AnalyzeResponse` ni affichés.
**Référence** : EXISTANT (vérifié cette session) — `EarningsQualityRatios` porte `ratios_fetched_at` `app/skills/tier2/earnings_quality/schemas.py:69` / `ratios_source` `:73`. À CRÉER — threading jusqu'à `AnalyzeResponse` + affichage `EarningsQualitySection`.

### Sprint 145 — Provenance par ratio sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage signal-only de la provenance (posé pour `AnalyzeForm` au Sprint 141) à `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (comme la source+date au Sprint 139).
**Complexité** : Moyenne (touche le backend : `AnalyzeResponse` + reconstruction depuis l'historique)
**Justification** : le Sprint 141 s'est délibérément limité au frontend (`/extract`) ; `AnalysisResult` reconstruit depuis l'analyse/historique n'a pas la provenance. Parité d'affichage avec la source+date Graham déjà threadée.
**Référence** : EXISTANT (vérifié session 141) — backend `GrahamRatios.ratios_provenance` `app/skills/tier2/graham_analysis/schemas.py:42` ; threading source+date Graham déjà fait au Sprint 139 (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, `app/orchestrator/core.py`) ; helper d'affichage à cloner `frontend/src/components/AnalyzeForm.tsx` (`ratiosEnRepli`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` + reconstruction history + affichage `AnalysisResult`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.27.0), .claude/rules/api-skills-tier2.md et donnees-financieres.md avant de commencer.
Sprint actif : 142 — Calculs déterministes : signaux détaillés F-Score / C-Score.
Objectif : rendre déterministes f_score.criteria[].passe (9 Piotroski) et c_score.signaux[].present (6 Montier), aujourd'hui produits par le LLM.
Point de départ vérifié : schemas FScoreCriterion schemas.py:132 / CScoreSignal :144 ; substitution _injecter_scores skill.py:154 (substitue déjà f_score/c_score entiers, PAS les listes) ; calculs agrégés existants app/services/financial_calculations.py.
Invariant à tester : sum(passe)==f_score et sum(present)==c_score. Cohérence None : donnée manquante/financière → conserver la valeur LLM, jamais un False trompeur.
Evals : la substitution change l'output earnings_quality → relancer les evals ciblées si ANTHROPIC_API_KEY dispo, sinon le dire explicitement.
```
