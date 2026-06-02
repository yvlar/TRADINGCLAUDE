# Sprint 145 — Affichage PDF de la source+date earnings/valuation

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.30.0 — Sprint 144 complété)

Le Sprint 144 a **persisté de façon reconstructible** les ratios `EarningsQualityRatios`/`ValuationRatios` horodatés dans `analysis_history.input_data` (sous clés dédiées, Graham reste à plat → rétrocompat) et exposé les reconstructeurs `_extract_earnings_ratios`/`_extract_valuation_ratios` — la donnée source+date earnings/valuation est désormais **disponible** pour le PDF. Sprint 144 était un re-cadrage en **persistance pure** (la prémisse « déjà reconstructible » était fausse) ; l'affichage PDF était volontairement différé à CE sprint.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals différées** — `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutables ici. **CE sprint touche le rendu PDF (Python, depuis l'output persisté), pas un prompt de skill ni l'orchestrateur → evals non concernées.**

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.30.0, Sprint 144 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : « une donnée sans date est inutilisable » ; traçabilité source+date obligatoire sur tout rapport.
4. `.claude/rules/tests-pyramide.md` — niveau unitaire `pdf_report_service` + intégration `ticker_report` exigés par livrable.

---

## TÂCHE — Sprint 145 : rendre la ligne « Source des ratios » pour earnings/valuation dans le PDF par ticker

**Objectif** : le rapport PDF par ticker ne rend la ligne « Source des ratios » **que pour Graham** (`_build_ratios_rows(r: GrahamRatios)`). Le Sprint 144 a rendu les ratios earnings/valuation horodatés **reconstructibles** ; il reste à les **câbler dans le PDF** et à rendre une ligne « Source des ratios (Qualité bénéfices) » et/ou « Source des ratios (Valorisation) » via le helper `_fmt_ratios_source` **existant** (réutiliser, ne pas dupliquer le formatage).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Reconstructeurs déjà livrés (Sprint 144)** — `_extract_earnings_ratios(row) -> EarningsQualityRatios | None` `app/api/endpoints/ticker_report.py:234` et `_extract_valuation_ratios(row) -> ValuationRatios | None` `:241` (cœur générique `_extract_sub_ratios` `:220`). **Non encore câblés** — c'est le travail de ce sprint.
2. **Site de câblage** — `get_ticker_report` reconstruit `ratios = _extract_ratios(row)` `ticker_report.py:111` puis le passe `ratios=ratios` `:124` à `generate_ticker_report`. Ajouter ici la reconstruction earnings/valuation et leur passage au service PDF.
3. **Helper de formatage réutilisable** — `_fmt_ratios_source(source, fetched_at) -> str` `app/services/pdf_report_service.py:150` (réutiliser tel quel).
4. **Rendu Graham à cloner** — `_build_ratios_rows(r: GrahamRatios)` ligne « Source des ratios » `pdf_report_service.py:245` ; section « Ratios clés » rendue `:327`. `generate_ticker_report` signature `:250` (ajouter les params `earnings_ratios`/`valuation_ratios`, `None` par défaut → rétrocompat).
5. **Champs source+date** — portés par `EarningsQualityRatios.ratios_fetched_at`/`ratios_source` `earnings_quality/schemas.py:69/73` et `ValuationRatios` `stock_valuation/schemas.py:32/36`.

### Spécification

1. **`ticker_report.py`** : dans `get_ticker_report`, reconstruire `earnings_ratios = _extract_earnings_ratios(row)` et `valuation_ratios = _extract_valuation_ratios(row)` (sous le même gate `if row is not None` que `ratios`), et les passer à `generate_ticker_report`.
2. **`pdf_report_service.py`** : `generate_ticker_report` gagne `earnings_ratios: EarningsQualityRatios | None = None` et `valuation_ratios: ValuationRatios | None = None`. Rendre une ligne « Source des ratios (Qualité bénéfices) » / « Source des ratios (Valorisation) » via `_fmt_ratios_source` — soit dans la section « Ratios clés » existante, soit dans un petit bloc dédié. **Réutiliser `_fmt_ratios_source`, ne pas dupliquer.**
3. **Honnêteté None** : ratio earnings/valuation absent (`None`) **ou** sans source/date → **ne pas** afficher de ligne trompeuse (parité avec le comportement Graham `None` → ligne omise, `_build_ratios_rows:244`).
4. **Périmètre** : affichage PDF earnings/valuation **uniquement**. Ne pas retoucher l'affichage Graham, le threading `AnalyzeResponse` (Sprints 139/143), ni les reconstructeurs (Sprint 144). Pas de changement de prompt de skill.

### Tests obligatoires (pyramide)
- Unitaire `pdf_report_service` : la/les nouvelle(s) ligne(s) source+date earnings/valuation rendues quand présentes, omises sinon (parité avec le comportement Graham `None`).
- Intégration `ticker_report.py` : `get_ticker_report` passe bien les ratios earnings/valuation reconstruits au service PDF (mock du service) ; `input_data` ancien (sans sous-clés) → pas de ligne earnings/valuation, pas de crash.
- Non-régression : `pytest` (hors e2e/evals) + `ruff` complets ; frontend inchangé (sprint backend pur).

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals non exécutables, **mais ce sprint ne touche aucun prompt de skill ni l'orchestrateur → evals non concernées** (rendu PDF Python pur). Stack Docker non démarrée ; pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 146 — Affichage earnings/valuation source+date sur l'analyse rendue (AnalysisResult)
**Objectif** : étendre l'affichage source+date de `AnalysisResult` (posé pour Graham au Sprint 139) aux ratios earnings/valuation, sous les cartes correspondantes.
**Complexité** : Moyenne (threading backend jusqu'à `AnalyzeResponse` + reconstruction historique).
**Justification** : parité d'affichage avec Graham ; la persistance reconstructible existe désormais (Sprint 144), il manque le threading jusqu'à la réponse rendue.
**Référence** : EXISTANT (vérifié cette session) — pattern Graham `AnalyzeResponse.ratios_fetched_at` `app/orchestrator/core.py:274` / `ratios_source` `:278`, helper `_graham_ratios_trace` `:284` ; reconstruction historique earnings/valuation déjà disponible `_extract_earnings_ratios`/`_extract_valuation_ratios` `app/api/endpoints/ticker_report.py:234/241` (Sprint 144). À CRÉER — `_earnings_ratios_trace`/`_valuation_ratios_trace` analogues + champ(s) sur `AnalyzeResponse` + reconstruction + affichage frontend (`AnalysisResult.tsx`).

### Sprint 147 — Interprétation déterministe Sloan (dernier cadre LLM)
**Objectif** : rendre déterministe `sloan.interpretation` (dernier libellé d'interprétation encore produit par le LLM après les Sprints 131/143), dérivé du `accrual_ratio` déjà calculé en Python — parité finale des 5 cadres M/Z/F/C/Sloan.
**Complexité** : Faible (calque exact du pattern Sprint 143).
**Justification** : `_injecter_scores` substitue déjà `sloan.accrual_ratio` mais **pas** `sloan.interpretation` → seul cadre où le libellé peut diverger du chiffre déterministe.
**Référence** : EXISTANT (vérifié cette session) — `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (LLM, jamais substitué) ; `_injecter_scores` ne pose que `data["sloan"]["accrual_ratio"]` `app/skills/tier2/earnings_quality/skill.py:190` ; `accrual_ratio` déjà calculé via `sloan_accrual_ratio` `skill.py:155`. À CRÉER — `_sloan_interpretation(accrual_ratio: float | None) -> str` (calque `_piotroski_interpretation`) + champ sur `_ScoresDeterministes` + substitution sous gate `accrual_ratio is not None` ; seuils canoniques à confirmer dans `prompts/system.md` (fichier:ligne à vérifier en début de sprint).

### Sprint 148 — Mutualiser `_parse_input_data` entre `ticker_report` et `report.py`
**Objectif** : factoriser le parsing défensif de `input_data` (raw JSONB → dict) dans un utilitaire partagé, supprimant la copie inline de `report.py`.
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 144 (hors périmètre alors) ; maintenant que les reconstructeurs sont actifs, le bon moment pour lever le helper. Évite qu'un 3ᵉ endpoint ajoute une 4ᵉ variante du même garde.
**Référence** : EXISTANT (vérifié cette session) — `_parse_input_data` `app/api/endpoints/ticker_report.py:192` (créé Sprint 144) ; duplication inline `_reconstruct_ratios_trace` `app/api/endpoints/report.py:123` (`GrahamRatios.model_validate(data)` `:140`). À CRÉER — module partagé (ex. `app/utils/input_data.py`) + import dans les deux endpoints + test du helper isolé.

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre désormais la cardinalité — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT — golden `tests/evals/fixtures/earnings_golden.json` ; schema `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.30.0), .claude/rules/donnees-financieres.md et tests-pyramide.md avant de commencer.
Sprint actif : 145 — Affichage PDF de la source+date earnings/valuation.
Objectif : câbler les reconstructeurs _extract_earnings_ratios/_extract_valuation_ratios (créés au Sprint 144) dans le PDF par ticker et rendre une ligne « Source des ratios (Qualité bénéfices/Valorisation) » via le helper _fmt_ratios_source existant.
Point de départ vérifié : reconstructeurs ticker_report.py:234/241 (non câblés) ; site de câblage ratios=_extract_ratios(row) ticker_report.py:111 passé :124 ; _fmt_ratios_source pdf_report_service.py:150 ; rendu Graham à cloner :245/:327 ; generate_ticker_report signature :250.
Honnêteté None : ratio absent ou sans source/date → ligne omise (parité Graham).
Evals : ce sprint ne touche aucun prompt de skill ni l'orchestrateur → evals non concernées.
```
