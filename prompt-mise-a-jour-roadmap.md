# Sprint 133 — Disclaimer : couverture des surfaces restantes (Screener, Comparer)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.19.0 — Sprint 132 complété)

Le Sprint 132 a rendu déterministe la dernière source de valeurs numériques critiques produites par le LLM : l'ossature DCF de `stock_valuation` (WACC/CMPC, valeur intrinsèque par action, matrice de sensibilité WACC×g) est désormais calculée en Python (`app/services/valuation_calculations.py`) et substituée post-parse. La file « déterminisme LLM » de la revue FinTech est close ; reste la file **conformité + traçabilité des données**.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.19.0, Sprint 132 ✅ (voir le bloc Sprint 129 pour le contrat du composant `Disclaimer` : texte centralisé TS + Python, variantes `inline`/`footer`)
3. `.claude/rules/conventions-frontend.md` — React 18, TypeScript strict (zéro `any`), structure pages/composants, Vitest par composant (cœur du sprint : sprint frontend pur)
4. `.claude/rules/tests-pyramide.md` — test composant obligatoire (happy path + cas limite) par nouveau câblage UI

---

## TÂCHE — Sprint 133 : disclaimer sur Screener et Comparer

**Objectif** : étendre le composant `Disclaimer` (Sprint 129) aux deux surfaces qui présentent des verdicts actionnables hors `AnalysisResult` mais n'affichent encore aucun avertissement réglementaire : les **résultats du Screener** et la **vue Comparer**. Sprint d'affichage pur — aucun prompt de skill, aucun backend, aucune migration.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Composant + texte réutilisables tels quels** — `frontend/src/components/Disclaimer.tsx` (variantes `inline`/`footer`, `data-testid="disclaimer"`, `role="note"`) ; `frontend/src/constants/disclaimer.ts` (texte centralisé). Aujourd'hui montés uniquement dans `frontend/src/components/AnalysisResult.tsx` + pied de page global. **Ne pas dupliquer le texte** — importer la constante.
2. **Surface Screener** — `frontend/src/components/ScreenerTable.tsx` (tableau des verdicts composite) rendu dans `frontend/src/pages/ScreenerPage.tsx`. Insérer un `Disclaimer variant="inline"` au plus près du tableau de résultats (sous le tableau, visible seulement quand il y a des résultats).
3. **Surface Comparer** — `frontend/src/pages/ComparePage.tsx` + `frontend/src/components/TickerComparisonChart.tsx` (comparaison multi-skills 2-5 tickers). Insérer un `Disclaimer variant="inline"` sous la vue de comparaison quand des résultats sont présents.

### Spécification

1. **Screener** — `Disclaimer` inline rendu sous `ScreenerTable` (ou en pied de `ScreenerPage`), conditionné à la présence de résultats (pas de bandeau sur page vide). Réutiliser la constante de texte, jamais de littéral.
2. **Comparer** — `Disclaimer` inline rendu sous la comparaison dans `ComparePage`, conditionné à la présence de tickers comparés.
3. **Zéro régression** — ne pas toucher au pied de page global ni à `AnalysisResult` (déjà couverts). Pas de `any`. `tsc --noEmit` 0 erreur, ESLint 0.

### Tests obligatoires (pyramide)
- **Composant** : `ScreenerPage`/`ScreenerTable` — disclaimer présent quand résultats, absent quand vide (`getByTestId("disclaimer")` / `queryByTestId`). Idem `ComparePage` (présent avec ≥ 2 tickers, absent à vide).
- Aucune régression Vitest / tsc / ESLint. (Sprint frontend pur → suite `pytest` inchangée.)

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être **absent** → `cd frontend && npm install` (ce sprint est frontend pur, l'install est requise).
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- Backend (sanity, inchangé) : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Aucun prompt de skill modifié → **evals non concernées**. Stack Docker non démarrée. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 134 — Traçabilité source+date des ratios dans l'UI/PDF
**Objectif** : afficher systématiquement la source (Yahoo Finance) et la date de récupération des ratios à côté des chiffres, comme l'exige `donnees-financieres.md` (« une donnée sans date est inutilisable »).
**Complexité** : Moyenne
**Justification** : `donnees-financieres.md` impose source+date ; aujourd'hui les ratios sont affichés sans horodatage de récupération — risque de décision sur une donnée périmée.
**Référence** : à CRÉER — aucun champ `data_fetched_at`/`fetched_at` localisé cette session (`grep` confirmé absent dans `app/skills/` et `app/skills/tier1/`). Ajouter le champ à l'extraction tier1 (`app/skills/tier1/yahoo_finance.py:182` `extract()`) → schema → type TS → UI/PDF.

### Sprint 135 — Repli multi-sources généralisé (au-delà d'eps_growth)
**Objectif** : généraliser le pattern de repli du Sprint 130 (source primaire yfinance → repli tracé) aux autres ratios critiques sujets au SPOF.
**Complexité** : Moyenne
**Justification** : le Sprint 130 n'a traité que `eps_growth` ; les autres ratios restent dépendants d'une source unique.
**Référence** : EXISTANT (vérifié cette session) — pattern de repli dans `app/skills/tier1/yahoo_finance.py:66-69` (`fallback = info.get("earningsGrowth")` + `logger.info` de traçabilité). À CRÉER — abstraction du repli réutilisable + champ de traçabilité de source par ratio.

### Sprint 136 — UI : affichage des sous-composantes auditables (X1-X5 Z-Score, matrice DCF)
**Objectif** : surfacer dans l'UI les intermédiaires désormais persistés mais non affichés — termes X1-X5 du Z-Score (Sprint 131) et matrice de sensibilité DCF déterministe (Sprint 132).
**Complexité** : Faible
**Justification** : le M-Score affiche déjà ses indices ; les X1-X5 du Z et la matrice DCF sont persistés et auditables côté backend mais invisibles dans l'UI — asymétrie d'auditabilité.
**Référence** : EXISTANT (vérifié cette session) — `frontend/src/components/EarningsQualitySection.tsx:97` `MScoreCard` (affiche déjà les indices), `:139` `ZScoreCard` (n'affiche pas X1-X5) ; `frontend/src/components/ValuationSection.tsx` (rend la matrice). À CRÉER côté TS — `frontend/src/types/index.ts:112` `ZScoreDetail` n'a que `variante`/`z_score`/`interpretation` : ajouter `x1`-`x5` (`number | null`) pour matcher le backend (`app/skills/tier2/earnings_quality/schemas.py`), puis les rendre dans `ZScoreCard`.

### Sprint 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation)
**Objectif** : exécuter (hors session web, avec clé Anthropic) les `evals` des skills dont le prompt a basculé en mode « interprète des chiffres calculés » (Sprints 128/131/132) pour confirmer l'absence de dégradation qualitative silencieuse.
**Complexité** : Faible
**Justification** : `pytest` reste vert avec Claude mocké sans rien prouver sur la qualité réelle du prompt ; les notes « calculés en amont » n'ont jamais été validées contre Claude réel (aucune clé dans le conteneur web).
**Référence** : EXISTANT (vérifié cette session) — répertoire `tests/evals/` (exclu du CI standard via `--ignore=tests/evals`) ; prompts modifiés `app/skills/tier2/stock_valuation/prompts/system.md` (note Sprint 132) et `app/skills/tier2/earnings_quality/prompts/system.md` (notes Sprints 128/131).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.19.0), .claude/rules/conventions-frontend.md
et .claude/rules/tests-pyramide.md avant de commencer.
Sprint actif : 133 — Disclaimer sur Screener et Comparer. Câbler le composant Disclaimer
existant (variant="inline", texte centralisé frontend/src/constants/disclaimer.ts) sous le
tableau de résultats du Screener (ScreenerTable/ScreenerPage) et sous la vue Comparer
(ComparePage/TickerComparisonChart), conditionné à la présence de résultats. Réutiliser la
constante de texte (jamais de littéral), ne pas toucher au pied de page global ni à
AnalysisResult (déjà couverts). Tests composant obligatoires (présent avec résultats / absent
à vide). Sprint frontend pur : tsc 0 erreur, ESLint 0, Vitest vert ; evals non concernées.
```
