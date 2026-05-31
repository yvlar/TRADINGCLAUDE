# Sprint 139 — Affichage de la traçabilité sur l'analyse persistée (AnalysisResult)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.24.0 — Sprint 138 complété)

Le Sprint 138 a étendu la traçabilité source+date (posée sur `GrahamRatios` au Sprint 134) à `ValuationRatios` et `EarningsQualityRatios` (schemas + extracteurs tier1 + type/affichage earnings côté frontend). La source+date d'une analyse n'est toutefois visible que sur le **formulaire d'entrée** (`AnalyzeForm`, après auto-fill) et dans le PDF — **pas sur le dossier d'analyse rendu/rechargé** (`AnalysisResult`), car `AnalyzeResponse` ne porte pas les ratios.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint 137 différé** — Les evals ciblées (Claude réel) `earnings_quality`/`stock_valuation` exigent `ANTHROPIC_API_KEY`, absente du conteneur web → à exécuter en local (le harnais `tests/evals/test_valuation_evals.py` existe déjà, créé par un PR mergé post-Sprint 136). Voir SPRINTS SUGGÉRÉS.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.24.0, Sprint 138 ✅
3. `.claude/rules/api-orchestrator.md` — cœur du sprint backend : structure `AnalyzeResponse` dans `core.py`, persistance (`_persist`) et rechargement (`report.py`). Le sprint thread un nouveau champ jusqu'à `AnalyzeResponse`.
4. `.claude/rules/conventions-frontend.md` — affichage React/TS strict (le sprint ajoute l'affichage source+date sous la carte Graham de `AnalysisResult`).

---

## TÂCHE — Sprint 139 : exposer la traçabilité sur l'analyse rendue

**Objectif** : rendre la source + date de récupération des ratios visible **aussi sur l'analyse rendue** (`AnalysisResult`), pas seulement sur le formulaire d'entrée et le PDF. Aujourd'hui `AnalyzeResponse` ne transporte pas les ratios d'entrée : la traçabilité posée aux Sprints 134/138 est donc invisible une fois l'analyse lancée ou rechargée depuis l'historique. Threader la traçabilité jusqu'à `AnalyzeResponse` puis l'afficher.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **`AnalyzeResponse` ne porte pas les ratios** — `class AnalyzeResponse(BaseModel)` à `app/orchestrator/core.py:237` ; aucun champ `ratios` (le `ratios: GrahamRatios | None` à `core.py:213` appartient à `AnalyzeRequest`, pas à la réponse). Côté frontend, `interface AnalyzeResponse` à `frontend/src/types/index.ts:446` (idem, pas de `ratios`).
2. **La traçabilité existe déjà sur les schemas d'entrée** — `GrahamRatios.ratios_fetched_at`/`ratios_source` (`app/skills/tier2/graham_analysis/schemas.py:34-41`, Sprint 134) ; idem `ValuationRatios`/`EarningsQualityRatios` (Sprint 138).
3. **Affichage de référence** — `AnalyzeForm.tsx` affiche déjà « Source : … · récupéré le AAAA-MM-JJ » (`data-testid="ratios-source"`) sous les ratios après auto-fill ; le PDF a `_fmt_ratios_source` (`app/services/pdf_report_service.py:150`). À CLONER pour `AnalysisResult`.

### Spécification

1. **Backend — threader la traçabilité dans `AnalyzeResponse`** : ajouter un champ portant la source + date des ratios Graham (a minima `ratios_fetched_at` / `ratios_source`, ou un sous-objet de traçabilité). Le peupler depuis `request.ratios` lors de la construction de la réponse, ET le reconstruire au rechargement d'une analyse persistée (depuis `input_data` JSONB en DB / cache) pour que l'historique affiche aussi la traçabilité. **Rétrocompatible** : champ optionnel `None` pour les analyses anciennes sans horodatage.
2. **Décision de périmètre** : se limiter à la traçabilité **Graham** (les ratios d'entrée du workflow `value_graham`), cohérent avec l'affichage existant ; documenter si valuation/earnings sont hors périmètre de CE sprint.
3. **Frontend — type + affichage** : étendre `interface AnalyzeResponse` (`types/index.ts`) du champ (optionnel) ; afficher « Source : … · récupéré le AAAA-MM-JJ » sous la carte Graham de `AnalysisResult` (`data-testid` dédié), rien si `None`. Zéro `any`.
4. **Vérifier le hazard de sérialisation** : tout nouveau champ `datetime` threadé dans `AnalyzeResponse` est sérialisé via `response.model_dump()` / `model_dump_json()` (SSE `complete`, persistance, cache `model_dump_json`). Confirmer qu'aucun chemin ne fait `json.dumps(model_dump())` brut sur la réponse (cf. correctif Sprint 134 sur `_cache_key`/`_persist`). Utiliser `mode="json"` si un `json.dumps` brut est sur le chemin.

### Tests obligatoires (pyramide)
- Unitaire/schema : `AnalyzeResponse` accepte le nouveau champ + défaut `None` (rétrocompat).
- Intégration : une analyse renvoie la traçabilité quand `request.ratios` la porte ; une analyse rechargée (historique) la reconstruit ; analyse ancienne sans horodatage → champ `None`, pas de crash.
- Composant : `AnalysisResult` affiche la source+date quand présente, rien sinon.
- Non-régression : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/` + Vitest + `tsc --noEmit` + ESLint.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps backend préparées par `SessionStart` → `scripts/setup-web-session.sh`. `node_modules` frontend absent à l'amorçage → `npm install`. Aucun prompt de skill ni l'orchestrateur (logique de routing) modifié dans la logique de décision → **evals non concernées** (sprint de threading/affichage). Stack Docker non démarrée. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 137 (différé) — Exécuter et documenter les evals déterministes (earnings_quality, stock_valuation)
**Objectif** : lancer les `evals` ciblées (Claude réel) confirmant que les prompts rendus déterministes (Sprints 128/131/132) n'ont pas dérivé qualitativement, et consigner drift/coût/verdicts.
**Complexité** : Faible (exécution + doc) — **MAIS bloqué en web**.
**Justification** : `pytest` mocké ne prouve rien sur la qualité réelle du prompt. À exécuter en local.
**Référence** : EXISTANT (vérifié cette session) — harnais `tests/evals/` avec `test_earnings_evals.py` ET `test_valuation_evals.py` (ce dernier créé par un PR mergé post-Sprint 136 ; la carte du Sprint 137 le disait « à créer » — désormais obsolète). **Contrainte** : exige `ANTHROPIC_API_KEY`, absente du conteneur web.

### Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`)
**Objectif** : capitaliser sur la `clé_retenue` que `_resolve_ratio` retourne déjà mais qui est aujourd'hui ignorée (`_`) : exposer, par ratio replié, quelle source yfinance a effectivement fourni la valeur.
**Complexité** : Moyenne
**Justification** : le Sprint 135 a posé l'abstraction mais n'expose la provenance que dans les logs. Pertinent surtout une fois que des clés de repli réelles existent (aujourd'hui les appels passent zéro clé de repli).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:87` `_resolve_ratio(...)` retourne `(valeur | None, clé_retenue)` ; les appels dans `extract()` ignorent la clé. À CRÉER — un véhicule de provenance + propagation type/UI ; définir d'abord des clés de repli réelles.

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

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.24.0), .claude/rules/api-orchestrator.md et conventions-frontend.md avant de commencer.
Sprint actif : 139 — Affichage de la traçabilité sur l'analyse persistée (AnalysisResult).
Backend : threader la source+date des ratios jusqu'à AnalyzeResponse (champ optionnel, rétrocompatible) + reconstruction au rechargement depuis l'historique.
Frontend : afficher « Source : … · récupéré le AAAA-MM-JJ » sous la carte Graham de AnalysisResult.
Vérifier le hazard json.dumps-sur-datetime (cf. correctif Sprint 134 sur _cache_key/_persist).
Point de départ vérifié : AnalyzeResponse à core.py:237 (sans champ ratios) ; interface AnalyzeResponse à types/index.ts:446.
```
