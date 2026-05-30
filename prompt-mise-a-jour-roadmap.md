# Sprint 135 — Repli multi-sources généralisé (au-delà d'eps_growth)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.21.0 — Sprint 134 complété)

Le Sprint 134 a ajouté la traçabilité **source + date de récupération** aux ratios Graham (`ratios_fetched_at` UTC + `ratios_source` posés par l'extraction tier1, propagés au schema → type TS → affichage `AnalyzeForm` + ligne PDF). La file « traçabilité des données » avance ; reste à **généraliser le repli de source** (un seul ratio, `eps_growth`, en bénéficie aujourd'hui).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.21.0, Sprint 134 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : validation None/div0, **valeurs aberrantes à signaler**, traçabilité source (un `0.0` silencieux pour une donnée absente est exactement le piège à éliminer)

---

## TÂCHE — Sprint 135 : généraliser le repli de source aux ratios critiques

**Objectif** : le Sprint 130 a introduit un repli de source **uniquement pour `eps_growth`** (`_resolve_eps_growth` : source primaire `income_stmt` → repli tracé sur `info.earningsGrowth`, sinon `(0.0, None)`). Les autres ratios Graham extraits de yfinance retombent **silencieusement à `0.0`** quand le champ primaire est absent (`info.get("priceToBook") or 0.0`, `info.get("bookValue") or 0.0`, `debt_equity = 0.0` si `debtToEquity` absent) — un `0.0` faux est indiscernable d'un vrai `0.0` et fausse le scoring Graham en aval. Généraliser le pattern : une donnée primaire absente doit produire `None` (donnée manquante honnête) **et être tracée**, jamais un `0.0` trompeur.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Pattern de repli existant (à généraliser)** — `app/skills/tier1/yahoo_finance.py:54` `_resolve_eps_growth(...)` : tente la source primaire, sinon `fallback = info.get("earningsGrowth")` (`:66`) tracé par `logger.info`, sinon `(0.0, None)`. C'est le SEUL ratio avec repli aujourd'hui.
2. **Ratios qui retombent à `0.0` silencieusement (à corriger)** — dans `extract()` : `pb=info.get("priceToBook") or 0.0` (`yahoo_finance.py:237`), `book_value=info.get("bookValue") or 0.0` (`:243`), `debt_equity = raw_de / 100.0 if raw_de is not None else 0.0` (`:223` env.). `pe` (`:219`) a déjà un repli calculé (`price/eps_ttm`) — le conserver.
3. **`current_ratio`** (`yahoo_finance.py:238`) : `None` est **normal** pour les banques (`is_financial`) — ne pas le « réparer », c'est un None légitime documenté (`donnees-financieres.md`).
4. **Schema** — `app/skills/tier2/graham_analysis/schemas.py:17` `pb: float` et `:19` `debt_equity: float`, `:28` `book_value: float` sont **non-optionnels** aujourd'hui (défaut implicite via `0.0`). Les passer à `float | None` casse la rétrocompatibilité des analyses persistées : à arbitrer (voir Spécification — option recommandée : garder le type mais cesser le `or 0.0` muet en traçant le None via un champ de provenance, OU rendre optionnel avec migration douce). **STOP et demander** si l'arbitrage type-vs-rétrocompat est ambigu.

### Spécification

1. **Abstraction de repli réutilisable** — extraire une fonction pure (style `_resolve_eps_growth`) prenant (clé primaire, clés de repli, `info`, `ticker`) et retournant `(valeur | None, source_utilisée)` avec `logger.info` tracé quand le repli sert. Ne PAS disperser la logique `or 0.0`.
2. **Cesser le `0.0` trompeur** — un ratio primaire absent → `None` (pas `0.0`). Vérifier que le scoring Graham en aval (`graham_analysis/skill.py`) traite déjà `None` proprement (critères `DONNÉES_MANQUANTES` — confirmer par lecture avant de changer le type).
3. **Traçabilité de source par ratio (optionnel, si le temps)** — capitaliser sur `ratios_source` (Sprint 134) : si pertinent, exposer quelle source a fourni chaque ratio replié. Si hors budget, le documenter comme sprint suivant.
4. **Zéro régression** — `pytest` + `ruff` ; `tsc`/ESLint/Vitest si le type TS `GrahamRatios` bouge ; banques (`current_ratio=None`) toujours acceptées par Graham.

### Tests obligatoires (pyramide)
- **Unitaire** : la fonction de repli (primaire présent → primaire ; primaire absent + repli présent → repli tracé ; tout absent → `None`).
- **Intégration** : `extract()` avec `priceToBook`/`bookValue`/`debtToEquity` absents → `None` (PAS `0.0`) ; banque → `current_ratio=None` inchangé.
- **Non-régression scoring** : un ratio `None` ne fait pas planter `graham_analysis` (critère marqué `DONNÉES_MANQUANTES`).
- Backend `pytest` + `ruff` ; frontend si type touché.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être **absent** → `cd frontend && npm install`.
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/`
- Frontend (si type TS touché) : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Extraction tier1 = données brutes, pas de prompt conceptuel → **evals non concernées** (sauf si le prompt `graham_analysis` est modifié pour le traitement des `None`, auquel cas le dire). Stack Docker non démarrée → extraction yfinance sur mocks. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 136 — UI : affichage des sous-composantes auditables (X1-X5 Z-Score)
**Objectif** : surfacer dans l'UI les intermédiaires persistés mais non affichés — termes X1-X5 du Z-Score (Sprint 131).
**Complexité** : Faible
**Justification** : le M-Score affiche déjà ses indices ; les X1-X5 du Z sont persistés et auditables côté backend mais invisibles dans l'UI — asymétrie d'auditabilité.
**Référence** : EXISTANT (vérifié cette session) — backend `app/skills/tier2/earnings_quality/schemas.py:106-107` (`x1`/`x2`… `FiniteFloatOrNone`, peuplés par Python depuis Sprint 131) ; UI `frontend/src/components/EarningsQualitySection.tsx:97` `MScoreCard` (affiche déjà les indices), `:139` `ZScoreCard` (n'affiche pas X1-X5). À CRÉER côté TS — `frontend/src/types/index.ts:114` `ZScoreDetail` n'a que `variante`/`z_score`/`interpretation` : ajouter `x1`-`x5` (`number | null`) pour matcher le backend, puis les rendre dans `ZScoreCard`.

### Sprint 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation)
**Objectif** : exécuter (hors session web, avec clé Anthropic) les `evals` des skills dont le prompt a basculé en mode « interprète des chiffres calculés » (Sprints 128/131/132) pour confirmer l'absence de dégradation qualitative silencieuse.
**Complexité** : Faible
**Justification** : `pytest` reste vert avec Claude mocké sans rien prouver sur la qualité réelle du prompt ; les notes « calculés en amont » n'ont jamais été validées contre Claude réel (aucune clé dans le conteneur web).
**Référence** : EXISTANT (vérifié cette session) — répertoire `tests/evals/` (`__init__.py`, `conftest.py`, `eval_runner.py`, `test_earnings_evals.py`… ; exclu du CI standard via `--ignore=tests/evals`).

### Sprint 138 — Traçabilité source+date étendue aux autres extracteurs
**Objectif** : appliquer le pattern source+date du Sprint 134 (posé sur `GrahamRatios`) aux autres ratios extraits — `ValuationRatios` et `EarningsQualityRatios`.
**Complexité** : Faible
**Justification** : le Sprint 134 ne couvre que `GrahamRatios` ; les ratios de valorisation et de qualité comptable restent sans horodatage de récupération, même exigence `donnees-financieres.md`.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:266` `extract_earnings_quality()` et `:404` `extract_valuation()` ; constante `RATIOS_SOURCE` + champs `ratios_fetched_at`/`ratios_source` déjà posés au Sprint 134 (`yahoo_finance.py:130`, `graham_analysis/schemas.py:34-41`). À CRÉER — réutiliser la constante/champs sur ces deux chemins + leurs schemas (`stock_valuation`/`earnings_quality`)/types/affichages.

### Sprint 139 — Affichage de la traçabilité sur l'analyse persistée (AnalysisResult)
**Objectif** : rendre la source+date visible aussi sur l'analyse rendue (pas seulement le formulaire d'entrée et le PDF), en threadant `GrahamRatios` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne
**Justification** : au Sprint 134, l'affichage UI a été posé dans `AnalyzeForm` (où vivent les ratios d'entrée) car `AnalyzeResponse` ne porte pas les ratios ; le dossier persisté n'expose la traçabilité que via le PDF. La rendre visible sur `AnalysisResult` demande un threading backend assumé.
**Référence** : EXISTANT (vérifié cette session) — `app/orchestrator/core.py:237` `class AnalyzeResponse` (sans champ `ratios`) ; `frontend/src/types/index.ts:440` `AnalyzeResponse` (idem) ; `frontend/src/components/AnalysisResult.tsx:160` (bloc Graham, rend `result.graham` = `GrahamAnalysisOutput`, pas les ratios d'entrée). À CRÉER — champ `ratios` sur `AnalyzeResponse` (backend + reconstruction au reload depuis DB/cache + type TS) puis affichage sous la carte Graham.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.21.0) et .claude/rules/donnees-financieres.md avant de commencer.
Sprint actif : 135 — Repli multi-sources généralisé. Extraire une fonction de repli réutilisable
(style _resolve_eps_growth, yahoo_finance.py:54) prenant clé primaire + clés de repli + info + ticker,
retournant (valeur | None, source) avec logger.info tracé. Remplacer les `or 0.0` muets de extract()
(pb yahoo_finance.py:237, book_value :243, debt_equity :223) par None tracé — un 0.0 faux fausse le
scoring Graham. Conserver current_ratio=None pour les banques (légitime) et le repli calculé de pe (:219).
Vérifier d'abord que graham_analysis traite déjà None (DONNÉES_MANQUANTES) avant de changer un type ;
STOP et demander si l'arbitrage type float vs float|None (rétrocompat analyses persistées) est ambigu.
Tests : unitaire repli, intégration extract() (None pas 0.0 ; banque inchangée), non-régression scoring.
evals non concernées (données brutes) sauf si le prompt graham_analysis bouge.
```
