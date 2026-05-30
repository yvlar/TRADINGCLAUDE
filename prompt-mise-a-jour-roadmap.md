# Sprint 130 — Données : honnêteté du label + repli multi-sources

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.16.0 — Sprint 129 complété)

**Origine de ce sprint** — Suite de la file issue de la revue expert FinTech (`docs/revue-expert-fintech.md` §2, §5). Le Sprint 129 a posé les disclaimers réglementaires. Sprint 130 attaque l'honnêteté des données : le champ `eps_growth_10y` annonce « 10 ans » mais calcule en réalité l'horizon max disponible (~4 ans) depuis `income_stmt` ; et `yfinance` est une source unique gratuite et retardée (SPOF). On corrige le label trompeur et on ajoute un repli quand la source primaire échoue.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.16.0, Sprint 129 ✅
3. `.claude/rules/donnees-financieres.md` — validation None/div0, source+date obligatoires, suffixe `.TO`, cas banques (cœur du sprint : extraction tier1 + repli de source)
4. `.claude/rules/variables-financieres.md` — tableau des identifiants standardisés backend/frontend (le renommage du champ doit rester cohérent Python ↔ TS)

---

## TÂCHE — Sprint 130 : honnêteté du label + repli multi-sources

**Objectif** : (1) corriger l'étiquette `eps_growth_10y` qui ment sur l'horizon réel du calcul, et (2) introduire un repli quand `yfinance` ne renvoie rien, pour réduire le SPOF de la source unique.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Calcul réel ~4 ans, label « 10y »** (EXISTANT) — `app/skills/tier1/yahoo_finance.py:18` `_compute_eps_growth` ; sa docstring l.20 admet « horizon max disponible, ~4 ans ». Câblé l.202 (`eps_growth_10y = _compute_eps_growth(...)`) et passé l.211 (`eps_growth_10y=...`). Le chemin `info`-only met `eps_growth_10y=None` l.407.
2. **Champ trompeur côté schema** (EXISTANT) — `app/skills/tier2/graham_analysis/schemas.py:20` (`eps_growth_10y: float`), validateur de plausibilité l.43-46 (> 500 % suspect).
3. **Type frontend** (EXISTANT) — `frontend/src/types/index.ts:52` (`eps_growth_10y: number | null`) et l.411 (variante optionnelle). Affichage PDF : `app/services/pdf_report_service.py` ligne « Croissance BPA 10 ans » (libellé à corriger aussi).

### Spécification

1. **Renommage cohérent du champ** — choisir un nom honnête (ex. `eps_growth_total` ou `eps_growth_period` + un champ `eps_growth_years: int | None` indiquant l'horizon réellement couvert). Propager le renommage de bout en bout : tier1 (`yahoo_finance.py`), schema (`graham_analysis/schemas.py`), type TS (`frontend/src/types/index.ts`), affichage (`AnalysisResult.tsx` + libellé PDF `pdf_report_service.py`). Mettre à jour `.claude/rules/variables-financieres.md` (le tableau référence `eps_growth_10y`).
2. **Horizon explicite** — `_compute_eps_growth` retourne aussi le nombre d'années réellement couvert (longueur de la série `income_stmt` utilisée), exposé dans le ratio pour que l'UI/PDF affiche « croissance BPA sur N ans » plutôt qu'un « 10 ans » faux.
3. **Repli de source** — quand `income_stmt` est absent/vide et que `info.get("earningsGrowth")` (déjà lu l.406 `eps_growth_5y`) est disponible, l'utiliser comme repli explicite (tracé : source + horizon), au lieu de tomber muettement à `None`/`0.0`. Respecter `donnees-financieres.md` : jamais d'exception sur donnée manquante, toujours tracer la source.

### Tests obligatoires (pyramide)
- **Unitaire** (`tests/skills/` ou `tests/services/`) : `_compute_eps_growth` retourne (croissance, horizon) correct sur série à 2 / 4 points ; 0.0 + horizon None/0 si série vide ; repli `info` utilisé quand `income_stmt` absent.
- **Schema** : le nouveau champ valide ; rétrocompat du validateur de plausibilité.
- **Composant** : `AnalysisResult` affiche le libellé honnête (« sur N ans »).
- Aucune régression Vitest / pytest. Mettre à jour les fixtures golden qui figent `eps_growth_10y`.

### ⚠️ Evals concernées
Le prompt `graham_analysis` mentionne le champ dans son message utilisateur — **vérifier** si le renommage touche le texte du prompt. Si oui, evals `graham_analysis` ciblées (Claude réel) recommandées ; sinon, le dire explicitement. (Aucune clé Anthropic dans le conteneur web → généralement non lançable : le constater.)

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). Le `node_modules` frontend peut être partiel à l'amorçage → `cd frontend && npm install` si types manquants.
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 131 — Auditabilité : persistance des sous-composantes déterministes
**Objectif** : remplir EN PYTHON les sous-composantes des scores du Sprint 128 (X1-X5 du Z, les indices du M) — aujourd'hui encore issues du LLM — et les persister pour qu'une analyse soit rejouable et explicable.
**Complexité** : Moyenne
**Justification** : le Sprint 128 ne rend déterministe que le score agrégé ; les `*Detail` restent LLM (cf. « Limites connues » du bloc Sprint 128 dans `ROADMAP.md`) — l'auditabilité n'est complète qu'avec la trace des intermédiaires.
**Référence** : DÉPEND du Sprint 128 — `app/services/financial_calculations.py` (EXISTANT, vérifié cette session). Champs cibles EXISTANTS : `MScoreDetail.dsri` `app/skills/tier2/earnings_quality/schemas.py:85`, `.gmi` l.86. Persistance via `analysis_history` (table EXISTANTE).

### Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation)
**Objectif** : étendre l'approche Sprint 128 à la valorisation — calculer en Python l'ossature DCF (WACC, valeur actualisée, matrice de sensibilité) et laisser le LLM commenter la narrative.
**Complexité** : Élevée
**Justification** : `stock_valuation` produit encore une matrice de sensibilité entièrement LLM — même défaut de fiabilité numérique que les scores avant Sprint 128.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/stock_valuation/schemas.py:78` (`SensitivityMatrix`, `wacc_range`:79), `matrice_sensibilite`:91, validateur de cohérence l.109-115. À CRÉER — fonction DCF déterministe dans `app/services/financial_calculations.py` + recâblage du skill.

### Sprint 133 — Disclaimer : couverture des surfaces restantes (Compare, Screener, Watchlist UI)
**Objectif** : étendre le composant `Disclaimer` (Sprint 129) aux pages qui présentent des verdicts hors `AnalysisResult` — résultats Screener, tableau Watchlist, vue Comparer.
**Complexité** : Faible
**Justification** : le Sprint 129 couvre `AnalysisResult` + pied de page global, mais les verdicts du Screener/Comparer sont aussi actionnables et méritent le bandeau inline au plus près du verdict.
**Référence** : EXISTANT (vérifié cette session) — composant `frontend/src/components/Disclaimer.tsx` + constante `frontend/src/constants/disclaimer.ts` réutilisables tels quels. Surfaces : `frontend/src/components/ScreenerTable.tsx`, `TickerComparisonChart.tsx` (à câbler).

### Sprint 134 — Traçabilité source+date des ratios dans l'UI/PDF
**Objectif** : afficher systématiquement la source (Yahoo Finance) et la date de récupération des ratios à côté des chiffres, comme l'exige `donnees-financieres.md` (« une donnée sans date est inutilisable »).
**Complexité** : Moyenne
**Justification** : la règle `donnees-financieres.md` impose source+date ; aujourd'hui les ratios sont affichés sans horodatage de récupération côté UI/PDF — risque de décision sur une donnée périmée.
**Référence** : à CRÉER — pas de champ `data_fetched_at` localisé cette session sur le payload ratios (`grep` à faire en début de sprint pour confirmer l'absence avant d'ajouter le champ tier1 → schema → UI/PDF).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.16.0), .claude/rules/donnees-financieres.md et
.claude/rules/variables-financieres.md avant de commencer.
Sprint actif : 130 — Honnêteté du label + repli multi-sources : renommer eps_growth_10y
(trompeur : ~4 ans réels, pas 10) de bout en bout (yahoo_finance.py → graham_analysis/schemas.py
→ frontend types + AnalysisResult + libellé PDF + variables-financieres.md), exposer l'horizon
réel (N années), et ajouter un repli info.earningsGrowth quand income_stmt est absent (tracé,
jamais d'exception). Tests unitaires + schema + composant obligatoires. Vérifier si le prompt
graham_analysis cite le champ → evals concernées (constater si non lançables sans clé).
```
