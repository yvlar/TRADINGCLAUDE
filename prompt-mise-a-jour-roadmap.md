# Sprint 131 — Auditabilité : persistance des sous-composantes déterministes

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.17.0 — Sprint 130 complété)

**Origine de ce sprint** — Suite de la file issue de la revue expert FinTech (`docs/revue-expert-fintech.md` §1). Le Sprint 128 a rendu déterministes les **scores agrégés** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan) en les calculant en Python. Mais leurs **sous-composantes** (`*Detail` : dsri, gmi… du M ; X1-X5 du Z) restent produites par le LLM — l'auditabilité est donc incomplète (cf. « Limites connues » du bloc Sprint 128 dans `ROADMAP.md`). Sprint 131 calcule ces intermédiaires en Python et les persiste pour qu'une analyse soit rejouable et explicable.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.17.0, Sprint 130 ✅ (voir bloc Sprint 128 pour le contrat du déterminisme)
3. `.claude/rules/api-skills-tier2.md` — SkillBase, substitution post-parse, schemas Pydantic font foi (cœur du sprint : étendre l'injection déterministe de `earnings_quality`)
4. `.claude/skills/earnings-quality-fraud-detection/references/*.md` — formules exactes des indices intermédiaires (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA pour le M ; X1-X5 pour le Z) à recopier fidèlement en Python

---

## TÂCHE — Sprint 131 : persistance des sous-composantes déterministes

**Objectif** : remplir EN PYTHON les sous-composantes des scores du Sprint 128 (les indices du M-Score, les X1-X5 du Z-Score, et les signaux détaillés du F/C/Sloan le cas échéant) — aujourd'hui encore issues du LLM — puis les substituer (post-parse, comme le score agrégé) pour qu'une analyse soit entièrement rejouable et auditable.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Calculs déterministes EXISTANTS** — `app/services/financial_calculations.py:1` : `altman_z_score`, `beneish_m_score`, `piotroski_f_score`, `montier_c_score`, `sloan_accrual_ratio` (Sprint 128) calculent le **score agrégé**. À ÉTENDRE : exposer aussi les intermédiaires (soit en retournant un dataclass/dict, soit via des fonctions dédiées par indice).
2. **Schémas cibles des intermédiaires EXISTANTS** — `app/skills/tier2/earnings_quality/schemas.py:86` `class MScoreDetail` ; champs `dsri` l.88, `gmi` l.89 (et suivants). Les `*Detail` sont aujourd'hui peuplés par le LLM.
3. **Injection post-parse EXISTANTE à étendre** — `app/skills/tier2/earnings_quality/skill.py` : helpers `_scores_depuis_ratios` + `_injecter_scores` (Sprint 128) substituent déjà les scores agrégés. Étendre la substitution aux `*Detail`.

### Spécification

1. **Calcul Python des intermédiaires** — dans `financial_calculations.py`, calculer chaque sous-composante (8 indices Beneish, 5 termes Altman, etc.) à partir des `EarningsQualityRatios`, avec le même contrat que le Sprint 128 : fonctions pures, typées, `float | None`, **jamais d'exception** sur donnée manquante / div0 (cf. `donnees-financieres.md`). Coefficients/formules RECOPIÉS depuis les `references/`.
2. **Substitution post-parse** — étendre `_injecter_scores` pour écraser les `*Detail` LLM par les valeurs Python (qui priment), comme pour les scores agrégés. Gate sectoriel `is_financial` conservé.
3. **Persistance/rejouabilité** — vérifier que les `*Detail` déterministes sont bien sérialisés dans l'output persisté (`analysis_history`) — la table est EXISTANTE (aucune migration attendue, l'output JSON la porte déjà ; CONFIRMER par `grep` en début de sprint).

### Tests obligatoires (pyramide)
- **Unitaire** (`tests/services/test_financial_calculations.py`) : chaque intermédiaire sur vecteurs calculés à la main + None/div0 + cas banque (`is_financial`).
- **Intégration** (`tests/skills/test_earnings_quality.py`) : les `*Detail` Python priment sur le bloc LLM (injecter un détail aberrant, vérifier l'écrasement) ; financière → indices M/Z annulés.
- Aucune régression Vitest / pytest ; mettre à jour les fixtures golden qui figent les `*Detail`.

### ⚠️ Evals concernées
Le prompt `earnings_quality` mentionne les indices — **vérifier** si le passage en déterministe nécessite d'ajuster la note « scores calculés en amont, interprète-les » pour couvrir aussi les intermédiaires. Si le prompt change → evals `earnings_quality` ciblées recommandées. (Aucune clé Anthropic dans le conteneur web → généralement non lançables : le constater.)

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être partiel → `cd frontend && npm install` si types manquants.
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation)
**Objectif** : étendre l'approche Sprint 128 à la valorisation — calculer en Python l'ossature DCF (WACC, valeur actualisée, matrice de sensibilité) et laisser le LLM commenter la narrative.
**Complexité** : Élevée
**Justification** : `stock_valuation` produit encore une matrice de sensibilité entièrement LLM — même défaut de fiabilité numérique que les scores avant Sprint 128.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/stock_valuation/schemas.py:80` (`class SensitivityMatrix`), `wacc_range` l.81, `matrice_sensibilite` l.82. À CRÉER — fonction DCF déterministe dans `app/services/financial_calculations.py` + recâblage du skill.

### Sprint 133 — Disclaimer : couverture des surfaces restantes (Screener, Comparer)
**Objectif** : étendre le composant `Disclaimer` (Sprint 129) aux pages qui présentent des verdicts hors `AnalysisResult` — résultats Screener et vue Comparer.
**Complexité** : Faible
**Justification** : le Sprint 129 couvre `AnalysisResult` + pied de page global, mais les verdicts du Screener/Comparer sont aussi actionnables et méritent le bandeau inline au plus près du verdict.
**Référence** : EXISTANT (vérifié cette session) — `frontend/src/components/Disclaimer.tsx` + `frontend/src/constants/disclaimer.ts` réutilisables tels quels. Surfaces à câbler : `frontend/src/components/ScreenerTable.tsx`, `frontend/src/components/TickerComparisonChart.tsx`.

### Sprint 134 — Traçabilité source+date des ratios dans l'UI/PDF
**Objectif** : afficher systématiquement la source (Yahoo Finance) et la date de récupération des ratios à côté des chiffres, comme l'exige `donnees-financieres.md` (« une donnée sans date est inutilisable »).
**Complexité** : Moyenne
**Justification** : la règle `donnees-financieres.md` impose source+date ; aujourd'hui les ratios sont affichés sans horodatage de récupération côté UI/PDF — risque de décision sur une donnée périmée. Complémentaire du Sprint 130 qui a fiabilisé *l'horizon* des données mais pas leur *date de récupération*.
**Référence** : à CRÉER — aucun champ `data_fetched_at` localisé cette session sur le payload ratios (`grep` confirmé absent dans `app/skills/tier1/` et `graham_analysis/schemas.py`). Ajouter le champ tier1 → schema → UI/PDF.

### Sprint 135 — Repli multi-sources généralisé (au-delà d'eps_growth)
**Objectif** : généraliser le pattern de repli du Sprint 130 (source primaire yfinance → repli tracé) aux autres ratios critiques sujets au SPOF (ratios manquants → source secondaire ou note explicite).
**Complexité** : Moyenne
**Justification** : le Sprint 130 n'a traité que `eps_growth` ; les autres ratios restent dépendants d'une source unique retardée.
**Référence** : EXISTANT (vérifié cette session) — pattern de repli dans `app/skills/tier1/yahoo_finance.py` (`extract()`, repli `info.earningsGrowth`). À CRÉER — abstraction du repli réutilisable + champ de traçabilité de source par ratio.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.17.0), .claude/rules/api-skills-tier2.md et les
references de .claude/skills/earnings-quality-fraud-detection/ avant de commencer.
Sprint actif : 131 — Auditabilité : calculer EN PYTHON les sous-composantes des scores
earnings_quality (indices Beneish DSRI/GMI/…, termes Altman X1-X5) aujourd'hui produites
par le LLM, étendre _injecter_scores pour substituer les *Detail post-parse (les valeurs
Python priment), et confirmer leur persistance dans analysis_history. Tests unitaires
(chaque intermédiaire + None/div0 + banque) + intégration (substitution prime sur LLM)
obligatoires. Vérifier si le prompt earnings_quality doit être ajusté → evals concernées
(constater si non lançables sans clé).
```
