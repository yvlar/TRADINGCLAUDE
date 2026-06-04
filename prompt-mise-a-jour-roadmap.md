# Sprint 147 — Interprétation déterministe Sloan (dernier cadre LLM)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.32.0 — Sprint 146 complété)

Le Sprint 146 a threadé la source+date des ratios earnings/valuation jusqu'à `AnalyzeResponse` (analyse live aux 4 sites + reconstruction historique, calque `_graham_ratios_trace`) et l'a affichée sous les cartes Qualité bénéfices et Valorisation de `AnalysisResult` — parité avec Graham (Sprint 139).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals : CE sprint change l'output `earnings_quality`** (`sloan.interpretation` devient déterministe) → **evals ciblées à relancer en local** ; `ANTHROPIC_API_KEY` absente du conteneur web → non exécutables ici (le dire explicitement, ne pas prétendre les avoir passées). Le **prompt de skill et l'orchestrateur ne sont PAS modifiés** (substitution post-parse uniquement, comme Sprints 131/143).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.32.0, Sprint 146 ✅
3. `.claude/rules/conventions-python.md` — cœur du sprint : type hints partout, docstring FR une ligne, fonction pure. Le pattern de substitution déterministe (`_scores_depuis_ratios` → `_ScoresDeterministes` → `_injecter_scores`) est l'ossature à étendre.
4. `.claude/rules/base-connaissances-skills.md` — protocole obligatoire : lire `.claude/skills/earnings-quality-fraud-detection/SKILL.md` + references avant de toucher la logique du skill ; confirmer les seuils Sloan canoniques.

---

## TÂCHE — Sprint 147 : rendre déterministe `sloan.interpretation` (parité finale M/Z/F/C/Sloan)

**Objectif** : `sloan.interpretation` est le **dernier libellé d'interprétation encore produit par le LLM**. Les interprétations M/Z (Sprint 131) et F/C (Sprint 143) sont déjà dérivées du score déterministe et substituées post-parse ; `_injecter_scores` substitue déjà `sloan.accrual_ratio` mais **pas** son interprétation — seul cadre où le libellé peut diverger du chiffre déterministe. Dériver l'interprétation Sloan de l'`accrual_ratio` déjà calculé en Python et la substituer post-parse. **Sprint backend pur** (frontend rend déjà le libellé verbatim, aucun changement requis ; aucun prompt de skill, aucune migration).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Champ LLM à substituer** — `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (jamais substitué à ce jour).
2. **Substitution actuelle Sloan = accrual_ratio seul** — `_injecter_scores` pose `data.setdefault("sloan", {})["accrual_ratio"] = scores.accrual_ratio` `app/skills/tier2/earnings_quality/skill.py:190` (pas l'interprétation).
3. **`accrual_ratio` déjà calculé en Python** — via `sloan_accrual_ratio(...)` `skill.py:155` dans `_scores_depuis_ratios` `skill.py:70`, posé sur `_ScoresDeterministes.accrual_ratio: float | None` `skill.py:61`.
4. **Pattern à cloner** — `_piotroski_interpretation(f_score)` `app/services/financial_calculations.py:108` / `_montier_interpretation(c_score)` `:126` (eux-mêmes clones de `_beneish_interpretation` `:91`) ; déjà câblés sur `_ScoresDeterministes.f_interpretation`/`c_interpretation` `skill.py:64/65`, dérivés `skill.py:163/164`, substitués sous gate `skill.py:202/207`.
5. **Seuils canoniques Sloan** — `app/skills/tier2/earnings_quality/prompts/system.md:163-165` : `≤ −0.05` → `qualite_elevee` ; `−0.05 à 0.05` → `neutre` ; `> 0.05` → `qualite_degradee`. Vocabulaire du décompte verdict global : `system.md:175` (Sloan défaillant = `qualite_degradee`).

### Spécification

1. **`app/services/financial_calculations.py`** : ajouter `_sloan_interpretation(accrual_ratio: float | None) -> str`, calque exact de `_piotroski_interpretation`/`_montier_interpretation` — `None` → `"DONNEES_MANQUANTES"` (ASCII, parité avec les clones existants), sinon libellé par seuil : `accrual_ratio <= -0.05` → `"qualite_elevee"` ; `-0.05 < accrual_ratio <= 0.05` (ou `< 0.05`, **confirmer la borne dans `system.md`**) → `"neutre"` ; `> 0.05` → `"qualite_degradee"`. Aucun gate sectoriel (le gate `None` est porté au niveau du ratio, comme F/C).
2. **`app/skills/tier2/earnings_quality/skill.py`** : `_ScoresDeterministes` gagne `sloan_interpretation: str | None` ; `_scores_depuis_ratios` le dérive (`None if accrual_ratio is None else _sloan_interpretation(accrual_ratio)`, en réutilisant l'`accrual_ratio` déjà calculé `skill.py:155` — **ne pas recalculer**). `_injecter_scores` écrit `data.setdefault("sloan", {})["interpretation"] = scores.sloan_interpretation` **sous gate** `if scores.sloan_interpretation is not None` (parité avec le gate accrual_ratio voisin et F/C).
3. **Périmètre** : `sloan.interpretation` uniquement. M/Z (Sprint 131), F/C (Sprint 143), `sloan.accrual_ratio` (déjà substitué) **inchangés**. Prompt de skill et `_build_user_message` **inchangés** (le LLM produit toujours l'interprétation, écrasée post-parse comme M/Z/F/C). Frontend inchangé (rend le libellé verbatim).

### Tests obligatoires (pyramide)
- Unitaire `financial_calculations` : `_sloan_interpretation` par seuil (≤ −0.05 → `qualite_elevee` ; 0.0 → `neutre` ; > 0.05 → `qualite_degradee` ; bornes exactes −0.05 et 0.05) + `None → DONNEES_MANQUANTES`.
- Intégration `skill.py` : mock Claude avec `sloan.interpretation` empoisonnée → écrasée par le libellé dérivé de l'`accrual_ratio` ; `accrual_ratio` None (donnée manquante) → interprétation LLM conservée (gate None). Réutiliser le paramètre `data=` de `_earnings_tool_use_response` (ajouté Sprint 143) pour injecter le payload empoisonné.
- Non-régression : `pytest` (hors e2e/evals) + `ruff` ; frontend inchangé → `vitest` + `tsc` + ESLint doivent rester verts sans modification.

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals non exécutables ici ; l'output `earnings_quality` change (`sloan.interpretation` déterministe) → **evals ciblées à relancer en local** (le dire explicitement). Stack Docker non démarrée ; pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 148 — Mutualiser `_parse_input_data` entre `ticker_report` et `report.py`
**Objectif** : factoriser le parsing défensif de `input_data` (raw JSONB → dict) dans un utilitaire partagé, supprimant la copie inline de `report.py`.
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 144 (hors périmètre alors) ; maintenant que les reconstructeurs sont actifs (câblés au PDF Sprint 145, à `AnalysisResult` Sprint 146), le bon moment pour lever le helper. Évite qu'un 3ᵉ endpoint ajoute une 4ᵉ variante du même garde.
**Référence** : EXISTANT (vérifié cette session) — `_parse_input_data` `app/api/endpoints/ticker_report.py:198` (créé Sprint 144) ; duplication inline `_reconstruct_ratios_trace` `app/api/endpoints/report.py:123` (`GrahamRatios.model_validate(data)` `:140`). À CRÉER — module partagé (ex. `app/utils/input_data.py`) + import dans les deux endpoints + test du helper isolé.

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre désormais la cardinalité et tous les libellés d'interprétation sont déterministes (M/Z/F/C, + Sloan au Sprint 147) — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` ; `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 150 — Provenance par ratio (`ratios_provenance`) jusqu'à `AnalysisResult`
**Objectif** : étendre l'affichage signal-only de la provenance par ratio (clé yfinance de repli) — posé sur `AnalyzeForm` au Sprint 141 — à l'analyse rendue/rechargée `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne (threading backend + reconstruction historique + affichage).
**Justification** : le Sprint 141 a explicitement **différé** la provenance sur `AnalysisResult` « tant qu'elle n'est pas threadée dans `AnalyzeResponse` ». Même mécanique que le Sprint 146 (threading source+date aux 4 sites + reconstruction), réutilisable juste après.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` ; affichage existant sur `AnalyzeForm` (`ratiosEnRepli` `frontend/src/components/AnalyzeForm.tsx:50`, badge `data-testid="ratios-provenance"` `:206`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` (backend + TS) + peuplage aux 4 sites de construction + reconstruction historique + bloc d'affichage sur `AnalysisResult` (clone du badge `AnalyzeForm`).

### Sprint 151 — Centraliser le gate « honnête-None » des lignes source+date (consolidation reuse)
**Objectif** : extraire le prédicat dupliqué « ratio présent ET porte source ou date » en un helper partagé, pour les rendus source+date PDF (Sprint 145) et le threading (Sprints 139/146).
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 145 (toucher le gate Graham violait alors le périmètre). Le motif `r.ratios_fetched_at is not None or r.ratios_source is not None` est maintenant répété (Graham + earnings + valuation côté PDF, + les helpers `_*_ratios_trace` côté core). Un sprint de consolidation dédié peut lever le prédicat sans contrainte de périmètre.
**Référence** : EXISTANT (vérifié cette session) — gate Graham PDF `app/services/pdf_report_service.py:246` ; helpers de trace `_graham_ratios_trace` `app/orchestrator/core.py:284`, `_earnings_ratios_trace` `:308`, `_valuation_ratios_trace` `:318` (Sprint 146). À CRÉER — prédicat/helper partagé + remplacement aux sites + test isolé.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.32.0), .claude/rules/conventions-python.md et base-connaissances-skills.md avant de commencer.
Sprint actif : 147 — Interprétation déterministe Sloan (dernier cadre LLM).
Objectif : dériver sloan.interpretation de l'accrual_ratio déjà calculé en Python (calque _piotroski_interpretation/_montier_interpretation) et la substituer post-parse dans _injecter_scores — parité finale des 5 cadres M/Z/F/C/Sloan.
Point de départ vérifié : SloanDetail.interpretation schemas.py:158 (LLM, jamais substitué) ; _injecter_scores pose seulement sloan.accrual_ratio skill.py:190 ; accrual_ratio via sloan_accrual_ratio skill.py:155 dans _scores_depuis_ratios skill.py:70 ; clones _piotroski_interpretation financial_calculations.py:108 / _montier_interpretation :126 ; seuils Sloan system.md:163-165 (≤−0.05 qualite_elevee, −0.05..0.05 neutre, >0.05 qualite_degradee).
Périmètre : sloan.interpretation uniquement ; prompt de skill et frontend inchangés.
Evals : l'output earnings_quality change (sloan.interpretation déterministe) → evals ciblées à relancer en local ; ANTHROPIC_API_KEY absente du conteneur web → non exécutables ici.
```
