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

### Sprint 148 — Consolider la reconstruction d'`AnalyzeResponse` (`/report` vs `/ticker-report`) ⭐ prêt à lancer
**Objectif** : fusionner la logique ~80 % dupliquée des deux reconstructeurs d'`AnalyzeResponse` depuis `analysis_history` dans un cœur partagé, **en corrigeant le bug latent** : `report.py` ne reconstruit pas `esg`.
**Complexité** : Moyenne (transverse à 2 endpoints, contrats différents à préserver).
**Justification** : finding *reuse* signalé par la revue PR du Sprint 146 et laissé hors périmètre. La traçabilité ratios (`reconstruct_ratios_traces`) et l'extraction `input_data` (`parse_input_data`) sont **déjà** centralisées dans `app/services/ratios_recon.py` (cette session) — il reste le squelette de reconstruction (parsing `result`/`skills_used`/`created_at` + skill-map) à mutualiser. Repousser laisse 2 copies dériver (ex. un nouveau skill ajouté à un seul mapping).

**⚠️ Contrats DIFFÉRENTS à préserver (ne pas fusionner naïvement)** :
| Aspect | `report.py::_reconstruct_response` `:123` | `ticker_report.py::_reconstruct_analyze_response` `:248` |
|---|---|---|
| Retour | `AnalyzeResponse` (jamais None) | `AnalyzeResponse \| None` |
| Graham absent | **lève `ValueError`** `:187` env. | toléré (champ None) |
| `result` illisible | laisse propager | retourne `None` + warning |
| Mapping skills | liste **inline** (`_try_parse` `:152`, **15 skills, `esg` MANQUANT** → bug) | `_result_skill_map()` `:210` (**16 skills, esg inclus**) |

**Référence** : EXISTANT (vérifié cette session) — les deux fonctions ci-dessus ; `_result_skill_map()` `app/api/endpoints/ticker_report.py:210` ; helper partagé déjà en place `reconstruct_ratios_traces` / `parse_input_data` `app/services/ratios_recon.py:100`/`:55`. Tests qui PINNENT l'API publique (doivent rester importables, ré-export si déplacement) : `tests/services/test_pdf_report_service.py:22` (`_reconstruct_analyze_response`, `_result_skill_map`), `tests/services/test_report.py` (`_reconstruct_response`). À CRÉER — `app/services/analysis_reconstruction.py` (cœur paramétrable, p. ex. `require_graham: bool`) + déplacer `_result_skill_map` là (ticker_report le ré-exporte) + réexprimer les 2 endpoints par-dessus + test de régression « `/report` reconstruit `esg` ». **Sans cycle** : le module service n'importe pas les endpoints.

**Template de démarrage (copier dans une nouvelle fenêtre)** :
```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md, .claude/rules/api-architecture.md et .claude/rules/tests-pyramide.md.

TÂCHE : consolider la reconstruction d'AnalyzeResponse dupliquée entre
app/api/endpoints/report.py:_reconstruct_response (:123) et
app/api/endpoints/ticker_report.py:_reconstruct_analyze_response (:248).
Extraire le cœur commun dans app/services/analysis_reconstruction.py (parsing
result/skills_used/created_at + skill-map + reconstruct_ratios_traces déjà dans
app/services/ratios_recon.py). Déplacer _result_skill_map (ticker_report:210) là,
ticker_report le ré-exporte.

PRÉSERVER les contrats divergents (paramétrer, ne pas aplatir) :
- report.py : graham obligatoire → ValueError ; retour non-Optional ;
- ticker_report : result illisible → None ; graham toléré.
CORRIGER le bug latent : report.py reconstruit désormais aussi `esg`.
GARDER importables (ré-export si déplacés) : _reconstruct_response,
_reconstruct_analyze_response, _result_skill_map (tests les importent).
PAS de cycle (le service n'importe pas les endpoints).

TEST à ajouter : /report reconstruit `esg` (régression du bug latent).
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  (frontend non touché : tsc/vitest/eslint restent verts sans modif)
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée (ex. claude/refactor-reconstruction), PR base = dev.
Confirmer avant git push / ouverture de PR.
```

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
**Référence** : EXISTANT (vérifié cette session) — gate Graham PDF `app/services/pdf_report_service.py:246` ; helpers de trace `_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace` désormais dans `app/services/ratios_recon.py:23`/`:31`/`:39` (déplacés depuis `core.py` lors de la revue PR Sprint 146 ; `core` les ré-exporte) ; côté frontend le gate est déjà unifié dans `frontend/src/components/RatiosSourceNote.tsx` (`if (!fetchedAt && !source)`). À CRÉER — prédicat/helper backend partagé (PDF + trace) + remplacement aux sites + test isolé.

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
