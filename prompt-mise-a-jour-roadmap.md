# Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.25.0 — Sprint 139 complété)

Le Sprint 139 a threadé la traçabilité source+date des ratios Graham jusqu'à `AnalyzeResponse` (champs optionnels `ratios_fetched_at`/`ratios_source`) et l'affiche sous la carte Graham de `AnalysisResult` (rendu live + reconstruction depuis l'historique). La traçabilité reste **globale au bloc de ratios** : on sait *quand* et *de quelle source* l'ensemble a été récupéré, mais pas *quelle clé yfinance* a réellement fourni chaque ratio quand un repli a joué.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint 137 différé** — Les evals ciblées (Claude réel) `earnings_quality`/`stock_valuation` exigent `ANTHROPIC_API_KEY`, absente du conteneur web → à exécuter en local. Voir SPRINTS SUGGÉRÉS.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.25.0, Sprint 139 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : traçabilité obligatoire (source + date), validation None/0.0, `current_ratio=None` pour les banques. Le sprint expose la **provenance par ratio** déjà calculée mais aujourd'hui jetée.
4. `.claude/rules/variables-financieres.md` — nommage standardisé snake_case (backend) ↔ camelCase (TS) : tout nouveau véhicule de provenance doit respecter le tableau et la convention de casse.

---

## TÂCHE — Sprint 140 : exposer la source de repli effective par ratio

**Objectif** : capitaliser sur la `clé_retenue` que `_resolve_ratio` retourne déjà mais qui est aujourd'hui **ignorée** (`_`) côté appelants. Exposer, pour chaque ratio susceptible de repli, **quelle clé yfinance a effectivement fourni la valeur** — utile dès qu'un repli réel existe (provenance vérifiable plutôt que seulement loggée).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **`_resolve_ratio` retourne déjà la provenance** — `def _resolve_ratio(...)` à `app/skills/tier1/yahoo_finance.py:87` retourne `(valeur | None, clé_retenue)` (clé primaire ou clé de repli retenue, `None` si aucune source). `_finite_float` à `:76`.
2. **Les appelants jettent la clé** — `extract()` ignore la clé retournée : `raw_de, _ = _resolve_ratio(info, ticker, "debtToEquity")` (`:257`), `pb, _ = _resolve_ratio(info, ticker, "priceToBook")` (`:261`), `book_value, _ = _resolve_ratio(info, ticker, "bookValue")` (`:262`). La provenance n'existe aujourd'hui que dans les logs (`logger.info` dans `_resolve_ratio`).
3. **Limite documentée** — Sprint 135 a posé l'abstraction `_resolve_ratio` mais n'expose la provenance que dans les logs ; aujourd'hui les appels passent **zéro clé de repli réelle** (un seul argument de clé primaire) → la provenance est toujours = clé primaire tant que des clés de repli ne sont pas définies. **Pré-requis du sprint** : décider d'abord 1-2 clés de repli réelles par ratio (ex. `debtToEquity` ← `debtToEquityRatio`, etc.) pour que l'exposition ait une valeur observable, sinon le champ est trivialement constant.

### Spécification

1. **Définir des clés de repli réelles** : pour au moins `pb`, `debt_equity`, `book_value`, passer ≥ 1 clé de repli plausible à `_resolve_ratio` (aujourd'hui appelé avec la seule clé primaire). Documenter le choix des clés.
2. **Véhicule de provenance** : ajouter au schema `GrahamRatios` (`app/skills/tier2/graham_analysis/schemas.py`) un champ optionnel portant, par ratio replié, la clé yfinance retenue (ex. sous-objet `ratios_provenance: dict[str, str] | None = None`, ou champs dédiés). **Rétrocompatible** : défaut `None`. Le peupler dans `extract()` depuis les `clé_retenue` aujourd'hui jetées.
3. **Décision de périmètre** : se limiter aux ratios Graham passant par `_resolve_ratio` (cohérent avec l'abstraction Sprint 135). Documenter si `pe`/`eps_growth` sont hors périmètre.
4. **Propagation type + UI (optionnelle, à trancher)** : si la provenance est exposée au frontend, étendre le type TS `GrahamRatios` (camelCase, zéro `any`) et l'afficher discrètement (ex. tooltip « via {clé} » sur le ratio concerné). Sinon, documenter que la provenance reste backend/PDF.
5. **Hazard de sérialisation** : un `dict` de provenance est JSON-safe (pas de `datetime`) ; vérifier néanmoins qu'il transite proprement par `model_dump(mode="json")` (`_persist`/`_cache_key`) et qu'il est **exclu de la clé de cache** (la provenance ne change pas l'identité financière — comme `ratios_source` au Sprint 134).

### Tests obligatoires (pyramide)
- Unitaire : `_resolve_ratio` avec clé de repli → retourne la bonne `clé_retenue` (primaire vs repli) ; `extract()` peuple la provenance avec la clé effective.
- Schema : `GrahamRatios` accepte le champ provenance + défaut `None` (rétrocompat).
- Intégration : un repli simulé (clé primaire absente, clé de repli présente dans `info`) → provenance = clé de repli ; primaire présente → provenance = clé primaire.
- (Si UI) Composant : affichage de la provenance quand présente, rien sinon.
- Non-régression : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/` + Vitest + `tsc --noEmit` + ESLint.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps backend préparées par `SessionStart` → `scripts/setup-web-session.sh`. `node_modules` frontend absent à l'amorçage → `npm install`. Extraction tier1 = données brutes, **aucun prompt de skill ni l'orchestrateur (routing) modifié → evals non concernées**. Stack Docker non démarrée. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 137 (différé) — Exécuter et documenter les evals déterministes (earnings_quality, stock_valuation)
**Objectif** : lancer les `evals` ciblées (Claude réel) confirmant que les prompts rendus déterministes (Sprints 128/131/132) n'ont pas dérivé qualitativement, et consigner drift/coût/verdicts.
**Complexité** : Faible (exécution + doc) — **MAIS bloqué en web**.
**Justification** : `pytest` mocké ne prouve rien sur la qualité réelle du prompt. À exécuter en local.
**Référence** : EXISTANT (vérifié cette session) — harnais `tests/evals/` avec `test_earnings_evals.py` ET `test_valuation_evals.py`. **Contrainte** : exige `ANTHROPIC_API_KEY`, absente du conteneur web.

### Sprint 141 — Calculs déterministes : signaux détaillés F-Score / C-Score
**Objectif** : rendre déterministes (calcul Python + substitution post-parse) les signaux détaillés du F-Score (`criteria[].passe`) et du C-Score (`signaux[].present`), aujourd'hui encore interprétés par le LLM.
**Complexité** : Moyenne
**Justification** : limite connue (Sprint 131) — seuls les *scores agrégés* F/C sont déterministes (Sprint 128) ; les signaux individuels restent produits par le LLM, dernière poche de non-déterminisme dans `earnings_quality`. Web-compatible (mockable).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/earnings_quality/schemas.py:132` (`class FScoreCriterion`), `:144` (`class CScoreSignal`) ; pattern de substitution `_injecter_scores` à `app/skills/tier2/earnings_quality/skill.py:154`. À CRÉER — fonctions pures par signal dans `app/services/financial_calculations.py` + extension de `_injecter_scores`.

### Sprint 142 — Traçabilité source+date dans le PDF earnings/valuation
**Objectif** : afficher la source+date des ratios `EarningsQualityRatios`/`ValuationRatios` dans les rapports PDF (le PDF ne couvre aujourd'hui que la ligne « Source des ratios » Graham).
**Complexité** : Faible
**Justification** : suite naturelle du Sprint 138 (les champs existent désormais sur ces schemas) ; complète la parité de traçabilité côté rapport.
**Référence** : EXISTANT (vérifié cette session) — `_fmt_ratios_source` à `app/services/pdf_report_service.py:150` et `_build_ratios_rows(r: GrahamRatios)` à `:228` (Graham uniquement). À CRÉER — rows source+date pour earnings/valuation quand ces ratios sont reconstruits dans le PDF.

### Sprint 143 — Affichage de la traçabilité earnings sur l'analyse rendue
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios` sous la carte Earnings Quality.
**Complexité** : Faible
**Justification** : parité d'affichage avec Graham ; les champs `ratios_fetched_at`/`ratios_source` existent déjà sur `EarningsQualityRatios` (Sprint 138) mais ne sont pas threadés jusqu'à `AnalyzeResponse` ni affichés sur le dossier rendu.
**Référence** : EXISTANT (vérifié cette session) — `EarningsQualityRatios` porte `ratios_fetched_at`/`ratios_source` (Sprint 138) ; `AnalyzeResponse` porte la traçabilité Graham depuis le Sprint 139 (`core.py` `ratios_fetched_at`/`ratios_source`). À CRÉER — `AnalyzeRequest.earnings_ratios` n'est pas threadé jusqu'à `AnalyzeResponse` (vérifier : `AnalyzeRequest.earnings_ratios` à `app/orchestrator/core.py:220`) ; nouveau véhicule + affichage `EarningsQualitySection`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.25.0), .claude/rules/donnees-financieres.md et variables-financieres.md avant de commencer.
Sprint actif : 140 — Exposition par ratio de la source de repli (_resolve_ratio).
Pré-requis : définir 1-2 clés de repli réelles par ratio (pb/debt_equity/book_value) — sinon la provenance est trivialement = clé primaire.
Backend : peupler un champ provenance optionnel sur GrahamRatios depuis la clé_retenue aujourd'hui jetée (_) dans extract().
Exclure la provenance de la clé de cache (comme ratios_source au Sprint 134).
Point de départ vérifié : _resolve_ratio à yahoo_finance.py:87 (retourne (valeur, clé_retenue)) ; appelants jettent la clé à :257/:261/:262.
```
