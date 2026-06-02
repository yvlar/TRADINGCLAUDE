# Sprint 144 — Traçabilité source+date earnings/valuation dans le PDF

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.29.0 — Sprint 143 complété)

Le Sprint 143 a rendu déterministes les **libellés d'interprétation au niveau cadre** F/C : `f_score.interpretation` et `c_score.interpretation` sont désormais dérivés en Python du score agrégé déjà déterministe (`_piotroski_interpretation`/`_montier_interpretation`) et substitués post-parse — parité complète avec M/Z (Sprint 131). Plus aucun chiffre ni libellé de score produit par le LLM dans `earnings_quality`.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals différées** — `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutables ici. **Pertinent pour CE sprint** : Sprint 144 est un sprint **PDF/reconstruction pur** (aucun prompt de skill, aucun changement d'output de skill) → **evals non concernées**.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.29.0, Sprint 143 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : « une donnée sans date est inutilisable » ; toute analyse/rapport doit préciser **source + date**. Le PDF ne rend cette ligne que pour Graham — l'étendre à earnings/valuation.
4. `.claude/rules/tests-pyramide.md` — couverture obligatoire par livrable (unitaire `pdf_report_service` + intégration endpoint `ticker_report`).

---

## TÂCHE — Sprint 144 : afficher la source+date des ratios earnings/valuation dans le rapport PDF

**Objectif** : le rapport PDF par ticker n'affiche aujourd'hui la ligne « Source des ratios » **que pour Graham** (`_build_ratios_rows(r: GrahamRatios)`). Les ratios `EarningsQualityRatios` et `ValuationRatios` portent depuis le Sprint 138 des champs `ratios_fetched_at`/`ratios_source`, mais ces traces n'apparaissent nulle part dans le PDF. Compléter la parité de traçabilité côté rapport : afficher la source+date des ratios earnings et valuation dans leurs sections respectives du PDF.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Helper générique réutilisable tel quel** — `_fmt_ratios_source(source: str | None, fetched_at: datetime | None) -> str` `app/services/pdf_report_service.py:150` (formate « Source : … · récupéré le … » — pas besoin de le réécrire).
2. **Ligne Graham existante (modèle à cloner)** — `_build_ratios_rows(r: GrahamRatios)` `app/services/pdf_report_service.py:228` ajoute `("Source des ratios", _fmt_ratios_source(r.ratios_source, r.ratios_fetched_at))` `:245`. **Graham uniquement** aujourd'hui.
3. **Champs source/date EXISTANTS sur les schemas** — `EarningsQualityRatios.ratios_fetched_at` `earnings_quality/schemas.py:69` / `ratios_source` `:73` ; `ValuationRatios.ratios_fetched_at` `stock_valuation/schemas.py:32` / `ratios_source` `:36` (posés au Sprint 138).
4. **Reconstruction PDF actuelle** — `ticker_report.py` reconstruit le rapport multi-skills ; `_extract_ratios(row) -> GrahamRatios | None` `app/api/endpoints/ticker_report.py:190` ne reconstruit **que** les ratios Graham depuis `input_data` (sélectionné par la requête `:22`). Les sorties skills sont reconstruites via la table `(skill_id, clé, OutputClass)` `:230/:233` (earnings_quality, stock_valuation présents).

### À VÉRIFIER EN PREMIER (Phase A — réconciliation, détermine la complexité)

**Prémisse non garantie** : les ratios **d'entrée** earnings/valuation (avec leur `ratios_fetched_at`/`ratios_source`) sont-ils **persistés dans `input_data`** et reconstructibles au moment du rendu PDF ?

- `input_data` ne contient peut-être que les ratios Graham (point d'entrée `/analyze`), pas les `EarningsQualityRatios`/`ValuationRatios` (souvent auto-extraits par l'orchestrateur en cours d'analyse).
- **Si la source/date earnings/valuation N'EST PAS dans `input_data`** → le sprint doit d'abord les **threader/persister** (complexité Moyenne, pas Faible) ; ne pas inventer une ligne « Source » à partir de données absentes (cela violerait `donnees-financieres.md` : une source non vérifiable est pire que pas de source).
- **Si elle Y EST** → l'ajout est local : reconstruire les ratios earnings/valuation depuis `input_data`, et appeler `_fmt_ratios_source` dans les sections PDF correspondantes.
- **STOP et signaler** si la reconstruction n'est pas possible sans threading backend lourd — proposer le découpage (sous-sprint de persistance d'abord).

### Spécification (conditionnée à la vérification ci-dessus)

1. Étendre le rendu PDF des sections Earnings Quality et Valuation pour inclure une ligne « Source des ratios » via le helper `_fmt_ratios_source` **déjà existant** (réutilisation, pas de duplication).
2. Reconstruire `EarningsQualityRatios`/`ValuationRatios` (ou au minimum leurs champs source/date) depuis `input_data` de façon **défensive** : None/illisible → ligne omise, jamais de crash (cf. pattern `_reconstruct_ratios_trace` Sprint 139).
3. **Périmètre** : affichage PDF uniquement. Ne pas retoucher les schemas (champs déjà là), ni les prompts de skill, ni l'orchestrateur (sauf si la vérification impose un threading de persistance — alors le délimiter explicitement).

### Tests obligatoires (pyramide)
- Unitaire `pdf_report_service` : la (ou les) nouvelle(s) ligne(s) « Source des ratios » earnings/valuation sont rendues quand source+date présentes ; omises quand `None`.
- Intégration `ticker_report` : un PDF reconstruit avec earnings/valuation horodatés contient la trace ; `input_data` sans ces champs (ancienne analyse) → PDF rendu sans crash, sans ligne trompeuse.
- Non-régression : `pytest` (hors e2e/evals) + `ruff` complets.

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals non exécutables en web (sprint PDF pur → **evals non concernées**). Stack Docker non démarrée ; pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes** (flush sporadique observé en session web).

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 145 — Affichage de la traçabilité earnings sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios `EarningsQualityRatios`, sous la carte Earnings Quality.
**Complexité** : Moyenne (threading backend jusqu'à `AnalyzeResponse`).
**Justification** : parité d'affichage avec Graham ; les champs existent sur le schema mais ne sont ni threadés jusqu'à `AnalyzeResponse` ni affichés.
**Référence** : EXISTANT (vérifié cette session) — `EarningsQualityRatios.ratios_fetched_at` `earnings_quality/schemas.py:69` / `ratios_source` `:73` ; pattern de threading Graham déjà fait (`AnalyzeResponse.ratios_fetched_at/source` `app/orchestrator/core.py:274/278`, helper `_graham_ratios_trace` `:284`). À CRÉER — un `_earnings_ratios_trace` analogue + champ(s) sur `AnalyzeResponse` + reconstruction historique + affichage `EarningsQualitySection`.

### Sprint 146 — Provenance par ratio sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage signal-only de la provenance (posé pour `AnalyzeForm` au Sprint 141) à `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (comme la source+date au Sprint 139).
**Complexité** : Moyenne (backend : `AnalyzeResponse` + reconstruction historique).
**Justification** : le Sprint 141 s'est limité au frontend (`/extract`) ; `AnalysisResult` reconstruit depuis l'historique n'a pas la provenance.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance` `app/skills/tier2/graham_analysis/schemas.py:42` ; threading source+date Graham déjà en place (`core.py:274/278/284`) ; helper d'affichage à cloner `frontend/src/components/AnalyzeForm.tsx` (`ratiosEnRepli`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` + reconstruction historique + affichage.

### Sprint 147 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre **désormais** la cardinalité (« au plus un à deux signaux mineurs réellement matériels ») — fix déjà livré, pas absent. Reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — consigne de cardinalité `app/skills/tier2/earnings_quality/prompts/system.md:195` ; golden `tests/evals/fixtures/earnings_golden.json` (`f_score_min`/`drapeaux_rouges_max` aux cas) ; schema `EarningsQualityOutput.drapeaux_rouges: list[str]` `earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 148 — Audit de cohérence des libellés d'interprétation (frontend ↔ Python)
**Objectif** : vérifier que les libellés d'interprétation déterministes (M/Z/F/C/Sloan, snake_case ex. `forte_qualite`/`manipulation_probable`) sont rendus lisiblement côté frontend (mapping libellé → texte humain + couleur), plutôt qu'affichés bruts en italique.
**Complexité** : Faible (frontend pur).
**Justification** : depuis le Sprint 143, les 5 cadres ont des libellés Python canoniques figés ; le frontend les rend en texte libre (`<p italic>{interpretation}</p>`) sans traduction ni signal visuel. Un mapping centralisé améliore l'UX et verrouille le contrat.
**Référence** : EXISTANT (vérifié cette session) — rendu brut `frontend/src/components/EarningsQualitySection.tsx:47/77/124/168/202` (`{fscore.interpretation}` etc.) ; libellés source `app/services/financial_calculations.py` (`_piotroski_interpretation`/`_montier_interpretation`, Sprint 143). À CRÉER — table de mapping TS libellé → `{texte, ton}` + tests composant.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.29.0), .claude/rules/donnees-financieres.md et tests-pyramide.md avant de commencer.
Sprint actif : 144 — Traçabilité source+date earnings/valuation dans le PDF.
Objectif : afficher la ligne « Source des ratios » pour earnings/valuation dans le PDF (aujourd'hui Graham uniquement, _build_ratios_rows pdf_report_service.py:228/245), via le helper existant _fmt_ratios_source (:150).
VÉRIFIER D'ABORD (réconciliation) : les champs ratios_fetched_at/ratios_source earnings (schemas.py:69/73) et valuation (schemas.py:32/36) sont-ils persistés dans input_data et reconstructibles côté ticker_report.py (où _extract_ratios:190 ne reconstruit que Graham) ? Si NON → threading de persistance d'abord (complexité Moyenne), STOP et signaler le découpage.
Evals : sprint PDF pur, aucun prompt de skill modifié → evals non concernées.
```
