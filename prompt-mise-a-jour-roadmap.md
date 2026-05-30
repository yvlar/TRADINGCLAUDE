# Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.18.0 — Sprint 131 complété)

**Origine de ce sprint** — Suite de la file issue de la revue expert FinTech (`docs/revue-expert-fintech.md` §1). Les Sprints 128 + 131 ont rendu déterministes les scores `earnings_quality` ET leurs sous-composantes (le LLM interprète, il ne produit plus les chiffres). Le skill `stock_valuation_triangulation` reste le dernier producteur de **valeurs numériques critiques par le LLM** : l'ossature DCF (WACC, valeur actualisée) et la matrice de sensibilité sont entièrement générées par le modèle — même défaut de fiabilité numérique que les scores avant Sprint 128. Sprint 132 rapatrie cette ossature en Python.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.18.0, Sprint 131 ✅ (voir blocs Sprint 128 + 131 pour le contrat du déterminisme : calcul Python + substitution post-parse)
3. `.claude/rules/api-skills-tier2.md` — SkillBase, substitution post-parse, schemas Pydantic font foi (cœur du sprint : reproduire le pattern `_injecter_scores` d'`earnings_quality` sur `stock_valuation`)
4. `.claude/skills/stock-valuation-triangulation/references/dcf.md` — formules exactes du DCF (WACC = CMPC, actualisation des FCF, valeur terminale, matrice de sensibilité WACC×croissance) à recopier fidèlement en Python
5. `.claude/rules/donnees-financieres.md` — validation None/div0, jamais d'exception sur donnée manquante (contrat des fonctions pures, comme Sprint 128/131)

---

## TÂCHE — Sprint 132 : ossature DCF déterministe

**Objectif** : calculer EN PYTHON l'ossature numérique du DCF (WACC, FCF actualisés, valeur terminale, valeur intrinsèque DCF, et la matrice de sensibilité WACC×croissance) — aujourd'hui produite par le LLM — puis la substituer post-parse (les valeurs Python priment), comme les scores `earnings_quality`. Le LLM conserve la **narrative** (hypothèses, choix de scénario, commentaire de la fourchette), pas l'arithmétique.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Skill sans calcul déterministe** — `app/skills/tier2/stock_valuation/skill.py:181` `data = dict(tool_use_block.input)` puis `:218` `StockValuationOutput.model_validate(data)` — **aucun** `_injecter_scores`, **aucun** import de `financial_calculations` (vérifié : le skill ne calcule rien en Python aujourd'hui). C'est le point d'insertion de la substitution post-parse.
2. **Schémas cibles EXISTANTS** — `app/skills/tier2/stock_valuation/schemas.py:78` `class SensitivityMatrix` ; `wacc_range` l.79 ; `matrice_sensibilite` l.91 (champ de l'output, validé par un `@model_validator` lignes ~109-115 qui vérifie déjà la cohérence lignes/colonnes). Champ `wacc: float | None` présent l.27.
3. **Pattern de référence à cloner** — `app/skills/tier2/earnings_quality/skill.py` (`_scores_depuis_ratios` + `_injecter_scores` via `asdict().update()`, Sprint 131) et `app/services/financial_calculations.py` (fonctions pures `float | None`, jamais d'exception).

### Spécification

1. **Calcul Python du DCF** — dans `financial_calculations.py` (ou un nouveau module `valuation_calculations.py` si la cohésion le justifie — justifier le choix), fonctions pures, typées, `float | None`, **jamais d'exception** sur donnée manquante / div0 : WACC (CMPC), actualisation des FCF projetés, valeur terminale (Gordon), valeur intrinsèque par action, et génération de la `SensitivityMatrix` (grille WACC×croissance). Formules RECOPIÉES depuis `references/dcf.md`.
2. **Substitution post-parse** — ajouter `_injecter_dcf` (analogue à `_injecter_scores`) dans `stock_valuation/skill.py` : écraser les champs numériques DCF + `matrice_sensibilite` du bloc LLM par les valeurs Python. Conserver la narrative LLM (hypothèses, interprétation). Exposer aussi les valeurs au LLM dans le message (« calculées en amont, interprète-les »).
3. **Garde-fous** — réutiliser `FiniteFloatOrNone` (`app/utils/numeric_validation.py`) sur les nouveaux champs numériques exposés si pertinent ; respecter le `@model_validator` existant de cohérence de la matrice.
4. **Persistance/rejouabilité** — vérifier (`grep`) que la matrice + l'ossature DCF sont bien sérialisées dans l'output persisté (`analysis_history.result` via `valuation_output.model_dump()`, `core.py` ~l.1702) — aucune migration attendue ; CONFIRMER en début de sprint.

### Tests obligatoires (pyramide)
- **Unitaire** : chaque fonction DCF sur vecteurs calculés à la main (WACC connu, FCF actualisés, valeur terminale) + None/div0 (WACC=0, FCF manquant) + cohérence matrice (dimensions WACC×croissance).
- **Intégration** (`tests/skills/test_stock_valuation*.py`) : l'ossature DCF Python prime sur un bloc LLM aberrant (injecter une valeur intrinsèque/matrice fantaisiste, vérifier l'écrasement) ; narrative LLM préservée.
- Aucune régression Vitest / pytest ; mettre à jour les fixtures golden qui figent la matrice si présentes (`grep` d'abord).

### ⚠️ Evals concernées
Le prompt `stock_valuation` passe en mode « interprète des chiffres calculés » — **vérifier** si la note « scores calculés en amont » doit y être ajoutée (comme `earnings_quality`). Si le prompt change → evals `stock_valuation` ciblées recommandées. (Aucune clé Anthropic dans le conteneur web → généralement non lançables : le constater.)

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être absent → `cd frontend && npm install` si types manquants.
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 133 — Disclaimer : couverture des surfaces restantes (Screener, Comparer)
**Objectif** : étendre le composant `Disclaimer` (Sprint 129) aux pages qui présentent des verdicts hors `AnalysisResult` — résultats Screener et vue Comparer.
**Complexité** : Faible
**Justification** : le Sprint 129 couvre `AnalysisResult` + pied de page global, mais les verdicts du Screener/Comparer sont aussi actionnables et méritent le bandeau inline au plus près du verdict.
**Référence** : EXISTANT (vérifié cette session) — `frontend/src/components/Disclaimer.tsx` + `frontend/src/constants/disclaimer.ts` réutilisables tels quels. Surfaces à câbler : `frontend/src/components/ScreenerTable.tsx`, `frontend/src/components/TickerComparisonChart.tsx`.

### Sprint 134 — Traçabilité source+date des ratios dans l'UI/PDF
**Objectif** : afficher systématiquement la source (Yahoo Finance) et la date de récupération des ratios à côté des chiffres, comme l'exige `donnees-financieres.md` (« une donnée sans date est inutilisable »).
**Complexité** : Moyenne
**Justification** : `donnees-financieres.md` impose source+date ; aujourd'hui les ratios sont affichés sans horodatage de récupération côté UI/PDF — risque de décision sur une donnée périmée.
**Référence** : à CRÉER — aucun champ `data_fetched_at` localisé cette session (`grep` confirmé absent dans `app/skills/tier1/` et `graham_analysis/schemas.py`). Ajouter le champ tier1 → schema → UI/PDF.

### Sprint 135 — Repli multi-sources généralisé (au-delà d'eps_growth)
**Objectif** : généraliser le pattern de repli du Sprint 130 (source primaire yfinance → repli tracé) aux autres ratios critiques sujets au SPOF.
**Complexité** : Moyenne
**Justification** : le Sprint 130 n'a traité que `eps_growth` ; les autres ratios restent dépendants d'une source unique retardée.
**Référence** : EXISTANT (vérifié cette session) — pattern de repli dans `app/skills/tier1/yahoo_finance.py` (`extract()` l.182, repli `info.earningsGrowth` l.66). À CRÉER — abstraction du repli réutilisable + champ de traçabilité de source par ratio.

### Sprint 136 — UI : affichage des sous-composantes auditables (X1-X5, et matrice DCF)
**Objectif** : surfacer dans l'UI les intermédiaires désormais persistés mais non encore affichés — termes X1-X5 du Z-Score (Sprint 131) et, après Sprint 132, la matrice de sensibilité DCF déterministe.
**Complexité** : Faible
**Justification** : le M-Score affiche déjà ses 8 indices ; les X1-X5 du Z sont persistés (Sprint 131) mais invisibles — asymétrie d'auditabilité dans l'UI.
**Référence** : EXISTANT (vérifié cette session) — `frontend/src/components/EarningsQualitySection.tsx` (`MScoreCard` affiche déjà les indices l.106-115 ; `ZScoreCard` n'affiche pas X1-X5). Champs `x1`-`x5` ajoutés à `ZScoreDetail` (Sprint 131, `app/skills/tier2/earnings_quality/schemas.py`) — à ajouter au type TS `frontend/src/types/index.ts:112` `ZScoreDetail` puis au rendu.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.18.0), .claude/rules/api-skills-tier2.md, .claude/rules/donnees-financieres.md
et .claude/skills/stock-valuation-triangulation/references/dcf.md avant de commencer.
Sprint actif : 132 — Calculs déterministes : ossature DCF. Calculer EN PYTHON le DCF de
stock_valuation (WACC, FCF actualisés, valeur terminale, valeur intrinsèque, matrice de
sensibilité WACC×croissance) aujourd'hui produit par le LLM, ajouter _injecter_dcf pour
substituer les valeurs Python post-parse (elles priment ; la narrative LLM est préservée),
et confirmer leur persistance dans analysis_history. Cloner le pattern _scores_depuis_ratios /
_injecter_scores d'earnings_quality (Sprint 131). Tests unitaires (DCF + None/div0 + matrice) +
intégration (substitution prime sur LLM) obligatoires. Vérifier si le prompt stock_valuation doit
recevoir la note « calculés en amont » → evals concernées (constater si non lançables sans clé).
```
