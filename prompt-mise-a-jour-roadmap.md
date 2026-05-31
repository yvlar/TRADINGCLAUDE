# Sprint 141 — Propagation frontend de la provenance par ratio

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.26.0 — Sprint 140 complété)

Le Sprint 140 a exposé côté **backend** la provenance par ratio : `GrahamRatios` porte désormais `ratios_provenance: dict[str, str] | None` (nom de ratio → clé yfinance effective, peuplé dans `extract()` depuis la `clé_retenue` de `_resolve_ratio` jusque-là jetée). Le champ transite déjà dans le payload `/extract` mais n'est **ni typé ni affiché** côté frontend.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint 140 — vérification partielle** : la session web qui l'a livré avait un canal d'exécution dégradé (flush sporadique). `ruff` et les tests `test_yahoo_finance.py`/`test_analysis_cache.py` ont été constatés verts ; la **suite backend complète + revue indépendante restent à reconstater en local**. Phase A de ce sprint : relancer `pytest`/`ruff` complets avant d'empiler.

> **Sprint 137 différé** — Les evals ciblées (Claude réel) `earnings_quality`/`stock_valuation` exigent `ANTHROPIC_API_KEY`, absente du conteneur web → à exécuter en local. Voir SPRINTS SUGGÉRÉS.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.26.0, Sprint 140 ✅
3. `.claude/rules/conventions-frontend.md` — cœur du sprint : React 18 + TS strict (zéro `any`), `data-testid` obligatoire sur les éléments testés, test composant happy path + cas d'erreur.
4. `.claude/rules/variables-financieres.md` — nommage snake_case (backend) ↔ camelCase (TS) : le payload `GrahamRatios` transite **en snake_case** côté TS (cf. `ratios_fetched_at`/`ratios_source` déjà déclarés ainsi dans l'interface). Respecter cette convention pour `ratios_provenance`.

---

## TÂCHE — Sprint 141 : typer et afficher la provenance par ratio

**Objectif** : rendre visible et vérifiable, côté frontend, la provenance que le Sprint 140 expose déjà dans le payload backend — sans bruit : ne signaler que lorsqu'un **repli réel** a eu lieu (clé effective ≠ clé primaire).

### Point de départ exact (vérifié — `fichier:ligne`)

1. **Backend déjà en place** — `GrahamRatios.ratios_provenance: dict[str, str] | None = None` à `app/skills/tier2/graham_analysis/schemas.py` (Sprint 140) ; peuplé dans `extract()` à `app/skills/tier1/yahoo_finance.py` (clés effectives pour `pb`/`debt_equity`/`book_value`).
2. **Interface TS `GrahamRatios`** — `frontend/src/types/index.ts:50` ; porte déjà `ratios_fetched_at?`/`ratios_source?` en **snake_case** (lignes 63-64). **À CRÉER** : champ `ratios_provenance?: Record<string, string> | null`.
3. **Affichage source/date existant à cloner** — `AnalyzeForm.tsx` lignes 172-177 (`data-testid="ratios-source"`) et `AnalysisResult.tsx` lignes 212-213 (`data-testid="result-ratios-source"`).

### Spécification

1. **Type TS** : ajouter `ratios_provenance?: Record<string, string> | null` à l'interface `GrahamRatios` (`types/index.ts`), zéro `any`, miroir snake_case du payload.
2. **Affichage signal-only** : sous la carte Graham (au moins dans `AnalyzeForm` après auto-fill ; idéalement aussi `AnalysisResult`), n'afficher la provenance **que pour les ratios dont la clé effective diffère de la clé primaire attendue** (`pb`→`priceToBook`, `debt_equity`→`debtToEquity`, `book_value`→`bookValue`). Ex. badge/tooltip discret « P/B via `priceToBookRatio` (repli) ». Si `ratios_provenance` est `null` ou ne contient que des clés primaires → ne rien afficher (pas de bruit). `data-testid` obligatoire.
3. **Décision de périmètre** : se limiter aux 3 ratios Graham instrumentés au Sprint 140. Documenter que `AnalysisResult` reconstruit depuis l'historique n'a pas la provenance tant qu'elle n'est pas threadée dans `AnalyzeResponse` (à trancher : étendre comme au Sprint 139, ou rester sur l'affichage `/extract` uniquement).

### Tests obligatoires (pyramide)
- Composant `AnalyzeForm` : provenance avec une clé de repli → badge affiché avec la clé ; provenance toute-primaire ou `null` → rien affiché.
- (Si threadé) Composant `AnalysisResult` : idem.
- Non-régression : `cd frontend && npm test` (Vitest) + `npm run typecheck` (tsc 0 erreur) + ESLint 0 ; backend inchangé → `pytest`/`ruff` rapides de confirmation.

### Note d'environnement (session web)
`node_modules` frontend absent à l'amorçage → `npm install`. Sprint frontend pur → **evals non concernées**. Stack Docker non démarrée. Pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes** (le Sprint 140 a souffert d'un flush sporadique).

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 137 ✅ exécuté (2026-05-31) — evals déterministes lancées
Les evals Claude réelles ont tourné (clé temporaire en session) : `valuation` 15/15 (DCF déterministe confirmé), `earnings` 81 passed / 10 failed (scores déterministes ✅, drift sur champs LLM libres). Détail dans `ROADMAP.md`. Reste : le **drift earnings ci-dessous**.

### Sprint 141bis — Calibrer le drift `earnings_quality` (drapeaux_rouges + verdict)
**Objectif** : résoudre les 10 échecs d'evals `earnings` révélés au Sprint 137 — 8 × `drapeaux_rouges_cardinalite` (le modèle dépasse le `max` du golden) + 2 × `verdict_dans_valeurs_attendues` (005 KO, 020 MRO).
**Complexité** : Moyenne (point de jugement métier + re-run evals payant)
**Justification** : contrat sous-spécifié — le prompt n'impose aucune borne de cardinalité sur `drapeaux_rouges` alors que le golden en attend une. Deux pistes à trancher AVANT de coder : (a) **resserrer le prompt** (« liste au plus N drapeaux les plus matériels, par sévérité décroissante ») — touche un prompt de skill, exige re-run evals ; OU (b) **élargir/corriger les bornes du golden** si elles sont irréalistes (ex. MRO post-COVID, énergie cyclique : max=2 est-il défendable ?). Commencer par auditer les 8 cas : les drapeaux émis par le modèle sont-ils faux/redondants (→ prompt) ou légitimes mais sur-comptés par un golden trop strict (→ golden) ?
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` (champ `drapeaux_rouges_max` par cas, valeurs 1-4) ; prompt `app/skills/tier2/earnings_quality/prompts/system.md` (schéma de sortie `"drapeaux_rouges": []` ligne ~267, AUCUNE consigne de cardinalité) ; schéma `app/skills/tier2/earnings_quality/schemas.py:85,169` (`drapeaux_rouges: list[str]` nu). Tests : `tests/evals/test_earnings_evals.py::test_earnings_drapeaux_rouges_cardinalite` + `::test_earnings_verdict_dans_valeurs_attendues`. **Contrainte** : re-run evals exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min).

### Sprint 142 — Calculs déterministes : signaux détaillés F-Score / C-Score
**Objectif** : rendre déterministes (calcul Python + substitution post-parse) les signaux détaillés du F-Score (`criteria[].passe`) et du C-Score (`signaux[].present`), aujourd'hui encore interprétés par le LLM.
**Complexité** : Moyenne
**Justification** : limite connue (Sprint 131) — seuls les *scores agrégés* F/C sont déterministes (Sprint 128) ; les signaux individuels restent produits par le LLM. Web-compatible (mockable).
**Référence** : EXISTANT (vérifié session 139) — `app/skills/tier2/earnings_quality/schemas.py` (`class FScoreCriterion`, `class CScoreSignal`) ; pattern de substitution `_injecter_scores` dans `app/skills/tier2/earnings_quality/skill.py`. À CRÉER — fonctions pures par signal dans `app/services/financial_calculations.py` + extension de `_injecter_scores`.

### Sprint 143 — Traçabilité source+date dans le PDF earnings/valuation
**Objectif** : afficher la source+date des ratios `EarningsQualityRatios`/`ValuationRatios` dans les rapports PDF (le PDF ne couvre aujourd'hui que la ligne « Source des ratios » Graham).
**Complexité** : Faible
**Justification** : suite naturelle du Sprint 138 (les champs existent désormais sur ces schemas) ; complète la parité de traçabilité côté rapport.
**Référence** : EXISTANT (vérifié session 139) — `_fmt_ratios_source` et `_build_ratios_rows(r: GrahamRatios)` (Graham uniquement) dans `app/services/pdf_report_service.py`. À CRÉER — rows source+date pour earnings/valuation quand ces ratios sont reconstruits dans le PDF.

### Sprint 144 — Affichage de la traçabilité earnings sur l'analyse rendue
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios` sous la carte Earnings Quality.
**Complexité** : Faible
**Justification** : parité d'affichage avec Graham ; les champs `ratios_fetched_at`/`ratios_source` existent déjà sur `EarningsQualityRatios` (Sprint 138) mais ne sont pas threadés jusqu'à `AnalyzeResponse` ni affichés.
**Référence** : EXISTANT (vérifié session 139) — `EarningsQualityRatios` porte `ratios_fetched_at`/`ratios_source` (Sprint 138). À CRÉER — threading jusqu'à `AnalyzeResponse` + affichage `EarningsQualitySection`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.26.0), .claude/rules/conventions-frontend.md et variables-financieres.md avant de commencer.
Sprint actif : 141 — Propagation frontend de la provenance par ratio.
Phase A : reconstater pytest/ruff complets verts (le Sprint 140 web n'a pu confirmer que partiellement).
Backend déjà fait au Sprint 140 : GrahamRatios.ratios_provenance (dict ratio→clé yfinance) ; payload /extract le transporte.
Frontend : ajouter ratios_provenance?: Record<string,string>|null à l'interface TS GrahamRatios (snake_case), afficher SIGNAL-ONLY (uniquement si une clé effective diffère de la clé primaire), data-testid + test composant.
Point de départ vérifié : interface GrahamRatios types/index.ts:50 ; affichage à cloner AnalyzeForm.tsx:172-177 et AnalysisResult.tsx:212-213.
```
