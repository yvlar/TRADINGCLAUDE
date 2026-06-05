# Sprint 148 — Interprétation déterministe `sloan.interpretation` (parité finale M/Z/F/C/Sloan)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.33.0 — Sprint 147 complété)

Le Sprint 147 a consolidé les deux reconstructeurs d'`AnalyzeResponse` (`/report` et `/ticker-report`) dans un cœur partagé `app/services/analysis_reconstruction.py` (`reconstruct(row, *, require_graham)`), corrigeant au passage le bug latent où `/report` ne reconstruisait pas `esg`.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint touchant un skill tier2** (`earnings_quality`) — substitution post-parse uniquement (prompt et orchestrateur **non modifiés**), mais l'output `earnings_quality` change (`sloan.interpretation` déterministe) → **evals ciblées à relancer en local** (`ANTHROPIC_API_KEY` absente du conteneur web → non exécutables ici). Stack Docker non démarrée ; pas de test navigateur live.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.33.0, Sprint 147 ✅
3. `.claude/rules/api-skills-tier2.md` — cœur du sprint : pattern `SkillBase`, schemas Pydantic font foi, substitution post-parse, `cost_usd`.
4. `.claude/rules/base-connaissances-skills.md` — protocole obligatoire avant de toucher un skill : lire `.claude/skills/earnings-quality-fraud-detection/SKILL.md` + `references/*.md` (formules/seuils Sloan).

---

## TÂCHE — Sprint 148 : rendre `sloan.interpretation` déterministe

**Objectif** : `sloan.interpretation` est le **dernier libellé d'interprétation encore produit par le LLM**. Les interprétations M/Z (Sprint 131) puis F/C (Sprint 143) sont déjà dérivées du score déterministe et substituées post-parse. Dériver l'interprétation Sloan de l'`accrual_ratio` **déjà calculé en Python** et la substituer post-parse — même remède, ferme la parité des 5 cadres. **Sprint backend pur** (le frontend rend déjà le libellé verbatim ; aucun prompt de skill, aucune migration).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Champ LLM à écraser** — `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (jamais substitué à ce jour ; le LLM le produit).
2. **`accrual_ratio` déjà déterministe** — `_ScoresDeterministes.accrual_ratio: float | None` `app/skills/tier2/earnings_quality/skill.py:61`, peuplé via `sloan_accrual_ratio(...)` `skill.py:155` dans `_scores_depuis_ratios` `skill.py:68`.
3. **Site de substitution** — `_injecter_scores(data, scores)` `skill.py:175` pose déjà `data.setdefault("sloan", {})["accrual_ratio"] = scores.accrual_ratio` `skill.py:190` (mais **pas** l'interprétation).
4. **Clones à calquer** — `_beneish_interpretation` `app/services/financial_calculations.py:91`, `_piotroski_interpretation` `:108`, `_montier_interpretation` `:126` (même forme : `None → "DONNEES_MANQUANTES"` ASCII, sinon libellé par seuil).
5. **Seuils canoniques Sloan** — `app/skills/tier2/earnings_quality/prompts/system.md:163-165` : `≤ −0.05` → `qualite_elevee` ; `−0.05 à 0.05` → `neutre` ; `> 0.05` → `qualite_degradee`. Libellés valides aussi listés `system.md:292`.

### Spécification

1. **`app/services/financial_calculations.py`** : ajouter la fonction pure `_sloan_interpretation(accrual_ratio: float | None) -> str`, calquée sur `_piotroski_interpretation`/`_montier_interpretation` :
   ```python
   if accrual_ratio is None: return "DONNEES_MANQUANTES"
   if accrual_ratio <= -0.05: return "qualite_elevee"
   if accrual_ratio <= 0.05:  return "neutre"
   return "qualite_degradee"
   ```
   Pas de gate sectoriel (le gate None est porté par `accrual_ratio`, comme pour les signaux F/C Sprint 142/143).
2. **`app/skills/tier2/earnings_quality/skill.py`** : `_ScoresDeterministes` gagne `sloan_interpretation: str | None` ; `_scores_depuis_ratios` le dérive de l'`accrual_ratio` **déjà calculé** (`None` quand l'accrual l'est) ; `_injecter_scores` écrit `data.setdefault("sloan", {})["interpretation"]` sous le **même gate** que `accrual_ratio` (parité avec M/Z/F/C). Sous le gate, accrual non-None ⟹ interprétation non-None (le schéma exige `str`).
3. **Périmètre** : `sloan.interpretation` **uniquement**. M/Z (Sprint 131), F/C (Sprint 143), signaux détaillés (Sprint 142) et le calcul `accrual_ratio` lui-même intacts. Prompt de skill et `_build_user_message` **inchangés** (le LLM produit toujours l'interprétation, écrasée post-parse comme les 4 autres cadres).

### Tests obligatoires (pyramide)
- **Unitaires** `financial_calculations` : `_sloan_interpretation` par seuil (`-0.10 → qualite_elevee`, `0.0 → neutre`, `0.10 → qualite_degradee`, bornes `-0.05`/`0.05`) + `None → DONNEES_MANQUANTES`.
- **Intégration** `skill.py` : un `interpretation` Sloan empoisonné par le LLM est **écrasé** par le libellé dérivé de l'`accrual_ratio` (réutiliser le helper `_earnings_tool_use_response(data=…)` ajouté au Sprint 143 pour injecter un payload empoisonné).
- **Non-régression** : `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports` verts (le CI lance mypy — `ruff` ne typecheck pas) ; frontend inchangé → `tsc`/`vitest`/ESLint restent verts **sans modification**.

### Note d'environnement (session web)
Substitution post-parse → l'output `earnings_quality` change → **evals ciblées à relancer en local** (non exécutables ici, `ANTHROPIC_API_KEY` absente). **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue, maintenant que la cardinalité est encadrée par le prompt et que **tous** les libellés d'interprétation sont déterministes (M/Z/F/C + Sloan au Sprint 148).
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : ferme la boucle ouverte au Sprint 137 — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` ; `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 150 — Provenance par ratio (`ratios_provenance`) jusqu'à `AnalysisResult`
**Objectif** : étendre l'affichage signal-only de la provenance par ratio (clé yfinance de repli) — posé sur `AnalyzeForm` au Sprint 141 — à l'analyse rendue/rechargée `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne (threading backend + reconstruction historique + affichage).
**Justification** : le Sprint 141 a explicitement **différé** la provenance sur `AnalysisResult` « tant qu'elle n'est pas threadée dans `AnalyzeResponse` ». Même mécanique que le Sprint 146 (threading + reconstruction), désormais centralisée dans `analysis_reconstruction`/`ratios_recon`.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` ; affichage existant sur `AnalyzeForm` (`ratiosEnRepli` `frontend/src/components/AnalyzeForm.tsx:50`, badge `data-testid="ratios-provenance"` `:206`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` (backend + TS) + peuplage aux sites de construction + reconstruction historique + bloc d'affichage sur `AnalysisResult`.

### Sprint 151 — Centraliser le gate « honnête-None » des lignes source+date (consolidation reuse)
**Objectif** : extraire le prédicat dupliqué « ratio présent ET porte source ou date » en un helper backend partagé, pour les rendus source+date PDF (Sprint 145) et le threading (Sprints 139/146).
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 145 (sur-abstraction à usage unique alors). Le motif est désormais répété (Graham + earnings + valuation côté PDF). Côté frontend, le gate est déjà unifié (`RatiosSourceNote`).
**Référence** : EXISTANT (vérifié cette session) — gate Graham PDF `app/services/pdf_report_service.py:246`, gate earnings/valuation PDF `:261` ; helpers de trace `_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace` dans `app/services/ratios_recon.py:22`/`:30`/`:40` ; côté frontend gate déjà unifié dans `frontend/src/components/RatiosSourceNote.tsx:11` (`if (!fetchedAt && !source)`). À CRÉER — prédicat/helper backend partagé (PDF + trace) + remplacement aux sites + test isolé.

### Sprint 152 — Test d'intégration de l'endpoint `GET /report/{analysis_id}` (couverture du cœur consolidé)
**Objectif** : ajouter un test d'intégration HTTP qui exerce `GET /report/{analysis_id}` de bout en bout (DB mockée → `reconstruct(require_graham=True)` → PDF), vérifiant le 200 + `application/pdf` et le 404 sur id inconnu — le cœur consolidé au Sprint 147 n'est couvert qu'au niveau unité (`_reconstruct_response`).
**Complexité** : Faible.
**Justification** : `reconstruct` est désormais le chemin partagé des deux endpoints PDF ; un test d'intégration sur `/report/{id}` (le seul des deux sans test d'intégration de reconstruction) verrouille la régression au niveau endpoint, pas seulement fonction.
**Référence** : EXISTANT (vérifié cette session) — endpoint `get_report` `app/api/endpoints/report.py:81` appelle `_reconstruct_response(row)` `:106` ; cœur `reconstruct` `app/services/analysis_reconstruction.py` ; le test existant `test_get_report_analysis_inconnu_404` `tests/services/test_report.py:179` couvre déjà le 404 mais **pas** le chemin 200 reconstruit. À CRÉER — test d'intégration `client.get("/report/{id}")` avec `db_pool.fetchrow` mocké renvoyant une ligne valide (graham + ≥1 skill) → 200 + `application/pdf`.

---

## Template de démarrage

```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md (v10.33.0), .claude/rules/api-skills-tier2.md et .claude/rules/base-connaissances-skills.md
(+ .claude/skills/earnings-quality-fraud-detection/SKILL.md et references pour les seuils Sloan).
Sprint actif : 148 — Interprétation déterministe sloan.interpretation (parité finale M/Z/F/C/Sloan).

TÂCHE : dériver sloan.interpretation de l'accrual_ratio déjà calculé en Python et la substituer
post-parse (parité avec M/Z Sprint 131, F/C Sprint 143).
- app/services/financial_calculations.py : _sloan_interpretation(accrual_ratio) clone de
  _piotroski_interpretation (:108)/_montier_interpretation (:126) — None → "DONNEES_MANQUANTES" ;
  ≤ -0.05 → qualite_elevee ; -0.05..0.05 → neutre ; > 0.05 → qualite_degradee (system.md:163-165).
- app/skills/tier2/earnings_quality/skill.py : _ScoresDeterministes.sloan_interpretation (:61 voisin),
  dérivé dans _scores_depuis_ratios (:68), substitué dans _injecter_scores (:175/:190) sous le gate accrual_ratio.
PÉRIMÈTRE : sloan.interpretation uniquement ; accrual_ratio, M/Z/F/C, signaux détaillés intacts ;
prompt et _build_user_message inchangés.
TESTS : unitaires _sloan_interpretation par seuil + None ; intégration skill.py (interpretation LLM
empoisonnée écrasée, helper _earnings_tool_use_response(data=…)).
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  .venv/bin/mypy app/ --ignore-missing-imports   # le CI le lance — ruff ne typecheck PAS
  (frontend non touché : tsc/vitest/eslint restent verts sans modif)
Evals earnings_quality à relancer EN LOCAL (output change) — non exécutables ici (clé absente).
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée, PR base = dev. Confirmer avant git push / ouverture de PR.
```
