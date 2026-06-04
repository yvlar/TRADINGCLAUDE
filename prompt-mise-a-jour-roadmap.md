# Sprint 147 — Consolider la reconstruction d'`AnalyzeResponse` (`/report` vs `/ticker-report`)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.32.0 — Sprint 146 complété)

Le Sprint 146 a threadé la source+date des ratios earnings/valuation jusqu'à `AnalyzeResponse` et l'a affichée sous les cartes Qualité bénéfices/Valorisation de `AnalysisResult`. La revue PR a ensuite centralisé l'extraction `input_data` + les helpers `_*_ratios_trace` dans `app/services/ratios_recon.py` (`reconstruct_ratios_traces`, `parse_input_data`) et harmonisé la note source+date (composant partagé `RatiosSourceNote`).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Refactor backend pur** — comportement observable **inchangé**, à une exception près : le correctif du bug latent (`/report` reconstruira désormais `esg`). Aucun changement d'output de skill → **pas d'evals requises**. Stack Docker non démarrée ; pas de test navigateur live.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.32.0, Sprint 146 ✅
3. `.claude/rules/api-architecture.md` — cœur du sprint : layering `app/` (un module service ne doit pas importer les endpoints), `cost_usd` persisté, contraintes API.
4. `.claude/rules/tests-pyramide.md` — niveaux de test, fixture `client`, règle absolue de patch `call_claude_with_retry` (ici : tests d'intégration sur reconstruction).

---

## TÂCHE — Sprint 147 : fusionner les deux reconstructeurs d'`AnalyzeResponse`

**Objectif** : deux fonctions reconstruisent une `AnalyzeResponse` depuis une ligne `analysis_history`, avec ~80 % de logique commune (parsing `result`/`skills_used`/`created_at` + skill-map + traçabilité ratios). Extraire le cœur partagé dans `app/services/analysis_reconstruction.py`, **en corrigeant le bug latent** : `report.py` ne reconstruit pas `esg`. **Sprint backend pur** (frontend non touché ; aucun prompt de skill, aucune migration).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Reconstructeur A** — `_reconstruct_response(row) -> AnalyzeResponse` `app/api/endpoints/report.py:123` : `result` parsé sans garde (laisse propager), **lève `ValueError` si `graham` absent** `:187`, mapping skills **inline** via `_try_parse` `:152` (**15 skills — `esg` MANQUANT → bug latent**), traçabilité via `**reconstruct_ratios_traces(row)`.
2. **Reconstructeur B** — `_reconstruct_analyze_response(row) -> AnalyzeResponse | None` `app/api/endpoints/ticker_report.py:248` : `result` illisible → **`None` + warning**, `graham` **toléré** (champ None), mapping via `_result_skill_map()` `:210` (**16 skills, `esg` inclus**), skill invalide ignoré (warning, pas d'échec global), traçabilité via `**reconstruct_ratios_traces(row)` + `**parsed_fields`.
3. **Déjà partagé (réutiliser, ne PAS dupliquer)** — `reconstruct_ratios_traces(row)` `app/services/ratios_recon.py:100`, `parse_input_data(row)` `:55`.
4. **Tests qui PINNENT l'API publique** (doivent rester importables, ré-export si déplacement) — `tests/services/test_pdf_report_service.py:22` importe `_reconstruct_analyze_response` + `_result_skill_map` ; `tests/services/test_report.py` importe `_reconstruct_response`.

### ⚠️ Contrats DIVERGENTS à PRÉSERVER (ne pas aplatir)

| Aspect | `report.py` (A) | `ticker_report.py` (B) |
|---|---|---|
| Retour | `AnalyzeResponse` (jamais None) | `AnalyzeResponse \| None` |
| Graham absent | **lève `ValueError`** | toléré (champ None) |
| `result` illisible | laisse propager | retourne `None` + warning |
| Mapping skills | 15 inline (**esg manquant**) | 16 via `_result_skill_map` (esg inclus) |

### Spécification

1. **`app/services/analysis_reconstruction.py`** (nouveau) : déplacer `_result_skill_map()` ici (source unique, 16 skills esg inclus) ; exposer un cœur **paramétrable** (p. ex. `reconstruct(row, *, require_graham: bool)`) qui parse `result`/`skills_used`/`created_at`, applique le skill-map + `reconstruct_ratios_traces`, et construit l'`AnalyzeResponse`. **Pas de cycle** : ce module n'importe pas les endpoints (il importe `core` pour `AnalyzeResponse` + les schémas skill, comme `ratios_recon`).
2. **`report.py`** : `_reconstruct_response` réexprimé par-dessus le cœur avec `require_graham=True` (conserve `ValueError` si graham absent + retour non-Optional) ; **gagne `esg`** via le skill-map partagé.
3. **`ticker_report.py`** : `_reconstruct_analyze_response` réexprimé avec `require_graham=False` (conserve `None` si result illisible + tolérance graham) ; `_result_skill_map` ré-exporté (`from app.services.analysis_reconstruction import _result_skill_map`) pour ne pas casser les imports de tests.
4. **Périmètre** : reconstruction depuis `analysis_history` uniquement. Pas de changement d'API HTTP, de schéma, ni de frontend. Seul changement observable : `/report` reconstruit désormais `esg`.

### Tests obligatoires (pyramide)
- **Régression du bug latent** : test sur `_reconstruct_response` (report) avec un `result` contenant `esg_simplified` → `resp.esg is not None` (échouerait avant le sprint).
- **Préservation des contrats** : `_reconstruct_response` lève toujours `ValueError` si `graham` absent ; `_reconstruct_analyze_response` renvoie toujours `None` si `result` illisible et tolère `graham` absent.
- **Parité skill-map** : les deux reconstructeurs reconnaissent les 16 skills (vérifier qu'un skill optionnel non-graham présent est reconstruit par les deux).
- **Non-régression** : `pytest` (hors e2e/evals) + `ruff` verts ; frontend inchangé → `tsc`/`vitest`/ESLint restent verts **sans modification**.

### Note d'environnement (session web)
Refactor backend pur, output inchangé (hors correctif esg) → **pas d'evals**. `ANTHROPIC_API_KEY` non requise. Stack Docker non démarrée. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 148 — Interprétation déterministe `sloan.interpretation` (parité finale M/Z/F/C/Sloan) ⭐ prêt à lancer
**Objectif** : `sloan.interpretation` est le **dernier libellé d'interprétation encore produit par le LLM**. Les interprétations M/Z (Sprint 131) et F/C (Sprint 143) sont déjà dérivées du score déterministe et substituées post-parse ; dériver l'interprétation Sloan de l'`accrual_ratio` déjà calculé en Python et la substituer post-parse. **Sprint backend pur** (frontend rend déjà le libellé verbatim ; aucun prompt de skill, aucune migration).
**Complexité** : Faible.
**Justification** : ferme la parité des 5 cadres ; supprime le dernier point où un libellé peut diverger du chiffre déterministe.
**Référence** : EXISTANT (vérifié session précédente — fichiers `earnings_quality` non touchés depuis) — champ LLM `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (jamais substitué) ; `_injecter_scores` pose seulement `sloan.accrual_ratio` `app/skills/tier2/earnings_quality/skill.py:190` ; `accrual_ratio` via `sloan_accrual_ratio(...)` `skill.py:155` dans `_scores_depuis_ratios` `skill.py:70`, sur `_ScoresDeterministes.accrual_ratio` `skill.py:61` ; clones `_piotroski_interpretation` `app/services/financial_calculations.py:108` / `_montier_interpretation` `:126` ; seuils canoniques `app/skills/tier2/earnings_quality/prompts/system.md:163-165` (`≤ −0.05` → `qualite_elevee` ; `−0.05..0.05` → `neutre` ; `> 0.05` → `qualite_degradee`). À CRÉER — `_sloan_interpretation(accrual_ratio)` (clone, `None → "DONNEES_MANQUANTES"`) + champ `_ScoresDeterministes.sloan_interpretation` dérivé + substitution sous gate dans `_injecter_scores`. **Evals à relancer en local** (output `earnings_quality` change) ; `ANTHROPIC_API_KEY` absente du conteneur web → non exécutables ici.

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre désormais la cardinalité et tous les libellés d'interprétation sont déterministes (M/Z/F/C, + Sloan au Sprint 148) — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié session précédente) — golden `tests/evals/fixtures/earnings_golden.json` ; `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 150 — Provenance par ratio (`ratios_provenance`) jusqu'à `AnalysisResult`
**Objectif** : étendre l'affichage signal-only de la provenance par ratio (clé yfinance de repli) — posé sur `AnalyzeForm` au Sprint 141 — à l'analyse rendue/rechargée `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne (threading backend + reconstruction historique + affichage).
**Justification** : le Sprint 141 a explicitement **différé** la provenance sur `AnalysisResult` « tant qu'elle n'est pas threadée dans `AnalyzeResponse` ». Même mécanique que le Sprint 146 (threading aux 4 sites + reconstruction), réutilisable juste après.
**Référence** : EXISTANT (vérifié session précédente) — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` ; affichage existant sur `AnalyzeForm` (`ratiosEnRepli` `frontend/src/components/AnalyzeForm.tsx:50`, badge `data-testid="ratios-provenance"` `:206`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` (backend + TS) + peuplage aux 4 sites de construction + reconstruction historique + bloc d'affichage sur `AnalysisResult`.

### Sprint 151 — Centraliser le gate « honnête-None » des lignes source+date (consolidation reuse)
**Objectif** : extraire le prédicat dupliqué « ratio présent ET porte source ou date » en un helper backend partagé, pour les rendus source+date PDF (Sprint 145) et le threading (Sprints 139/146).
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 145. Le motif est répété (Graham + earnings + valuation côté PDF). Côté frontend, le gate est déjà unifié (`RatiosSourceNote`).
**Référence** : EXISTANT (vérifié cette session) — gate Graham PDF `app/services/pdf_report_service.py:246` ; helpers de trace `_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace` désormais dans `app/services/ratios_recon.py:23`/`:31`/`:39` (déplacés depuis `core.py` lors de la revue PR Sprint 146 ; `core` les ré-exporte) ; côté frontend gate déjà unifié dans `frontend/src/components/RatiosSourceNote.tsx` (`if (!fetchedAt && !source)`). À CRÉER — prédicat/helper backend partagé (PDF + trace) + remplacement aux sites + test isolé.

---

## Template de démarrage

```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md (v10.32.0), .claude/rules/api-architecture.md et .claude/rules/tests-pyramide.md.
Sprint actif : 147 — Consolider la reconstruction d'AnalyzeResponse (/report vs /ticker-report).

TÂCHE : fusionner la logique ~80 % dupliquée de
app/api/endpoints/report.py:_reconstruct_response (:123) et
app/api/endpoints/ticker_report.py:_reconstruct_analyze_response (:248)
dans un cœur partagé app/services/analysis_reconstruction.py (parsing
result/skills_used/created_at + skill-map + reconstruct_ratios_traces déjà dans
app/services/ratios_recon.py:100). Déplacer _result_skill_map (ticker_report:210)
là ; ticker_report le ré-exporte.

PRÉSERVER les contrats divergents (paramétrer require_graham, ne pas aplatir) :
- report.py : graham obligatoire → ValueError ; retour non-Optional ;
- ticker_report : result illisible → None ; graham toléré.
CORRIGER le bug latent : report.py reconstruit désormais aussi `esg` (15→16 skills).
GARDER importables (ré-export si déplacés) : _reconstruct_response,
_reconstruct_analyze_response, _result_skill_map (tests les importent).
PAS de cycle (le service n'importe pas les endpoints).

TEST à ajouter : /report reconstruit `esg` (régression du bug latent) + préservation
des contrats (ValueError graham absent ; None si result illisible).
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  (frontend non touché : tsc/vitest/eslint restent verts sans modif)
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée, PR base = dev. Confirmer avant git push / ouverture de PR.
```
