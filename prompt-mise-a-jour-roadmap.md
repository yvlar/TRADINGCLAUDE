# Sprint 146 — Affichage earnings/valuation source+date sur l'analyse rendue (AnalysisResult)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.31.0 — Sprint 145 complété)

Le Sprint 145 a **câblé dans le PDF par ticker** la traçabilité source+date des ratios earnings/valuation (bloc « Sources des ratios complémentaires » via le helper `_fmt_ratios_source`, ligne omise si absente — parité Graham), en réutilisant les reconstructeurs `_extract_earnings_ratios`/`_extract_valuation_ratios` du Sprint 144. Reste l'angle écran : l'analyse **rendue** (`AnalysisResult`) n'affiche la source+date que pour Graham (Sprint 139) — pas pour earnings/valuation.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Evals différées** — `ANTHROPIC_API_KEY` absente du conteneur web. **CE sprint ne touche aucun prompt de skill ni la logique de routing de l'orchestrateur** (champs additifs sur l'enveloppe `AnalyzeResponse` + threading + affichage) → **evals non concernées** ; l'output de chaque skill est inchangé.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.31.0, Sprint 145 ✅
3. `.claude/rules/conventions-frontend.md` — cœur du sprint côté écran : React 18 + TS strict (zéro `any`), `data-testid` obligatoire, test composant Vitest par livrable.
4. `.claude/rules/donnees-financieres.md` — « une donnée sans date est inutilisable » ; honnêteté None (champ absent → ligne omise, jamais de date factice).

---

## TÂCHE — Sprint 146 : threader et afficher la source+date earnings/valuation sur `AnalysisResult`

**Objectif** : parité d'affichage avec Graham. Le bloc source+date Graham existe sur `AnalysisResult` (`result.ratios_fetched_at` → « Source : … · récupéré le AAAA-MM-JJ »). L'étendre aux ratios earnings/valuation, sous leurs cartes respectives. Cela exige de **threader** la source+date earnings/valuation jusqu'à `AnalyzeResponse` (analyse live **et** reconstruction historique), comme `_graham_ratios_trace` le fait déjà pour Graham. **Sprint backend (threading) + frontend (affichage)** — aucun prompt de skill, aucune migration.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Pattern Graham backend à cloner** — `_graham_ratios_trace(ratios) -> (fetched_iso, source)` `app/orchestrator/core.py:284` ; champs `AnalyzeResponse.ratios_fetched_at` `core.py:274` / `ratios_source` `:278` ; **peuplés à l'analyse** `core.py:537` (`_graham_ratios_trace(request.ratios)`) ; **reconstruction historique** `app/api/endpoints/ticker_report.py:334` (`_graham_ratios_trace(_extract_ratios(row))`) posée `:343`.
2. **Entrées déjà disponibles** — `AnalyzeRequest.earnings_ratios` `core.py:220` / `valuation_ratios` `:223` (déjà consommées `core.py:301-304` et `:441/:449`) ; reconstructeurs historiques `_extract_earnings_ratios` `ticker_report.py:234` / `_extract_valuation_ratios` `:241` (Sprint 144, déjà câblés au PDF au Sprint 145).
3. **Champs source+date sur les schémas d'entrée** — `EarningsQualityRatios.ratios_fetched_at`/`ratios_source` `app/skills/tier2/earnings_quality/schemas.py:69/73` ; `ValuationRatios` `app/skills/tier2/stock_valuation/schemas.py:32/36`.
4. **Affichage Graham frontend à cloner** — bloc source+date `frontend/src/components/AnalysisResult.tsx:211-216` (gate `result.ratios_fetched_at`, `data-testid="result-ratios-source"`) ; cartes `EarningsQualitySection` `:222-224` et `ValuationSection` `:227` ; interface `AnalyzeResponse` `frontend/src/types/index.ts:450`.

### Spécification

1. **`core.py`** : ajouter `_earnings_ratios_trace`/`_valuation_ratios_trace` (calque exact de `_graham_ratios_trace` : `(ratios.ratios_fetched_at.isoformat() if … else None, ratios.ratios_source)`, `(None, None)` si le ratio est `None`). Ajouter à `AnalyzeResponse` quatre champs `str | None` : `earnings_ratios_fetched_at`/`earnings_ratios_source`, `valuation_ratios_fetched_at`/`valuation_ratios_source`. Les peupler à l'analyse depuis `request.earnings_ratios`/`request.valuation_ratios` (au même site que le trace Graham `core.py:537`).
2. **`ticker_report.py`** : dans `_reconstruct_analyze_response`, peupler ces quatre champs depuis `_extract_earnings_ratios(row)` / `_extract_valuation_ratios(row)` (déjà reconstruits — parité avec le trace Graham `:334`).
3. **`types/index.ts`** : ajouter les quatre champs (snake_case, miroir backend, `string | null`) à `interface AnalyzeResponse`.
4. **`AnalysisResult.tsx`** : sous la carte earnings et sous la carte valuation, afficher un bloc source+date (clone de `:211-216`), gate sur le champ correspondant, `data-testid` distinct (ex. `earnings-ratios-source`, `valuation-ratios-source`). **Honnêteté None** : champ absent → rien affiché (parité Graham).
5. **Périmètre** : earnings/valuation source+date sur `AnalysisResult` **uniquement**. Ne pas retoucher l'affichage Graham (Sprint 139), le PDF (Sprint 145), ni les schémas de skill. Les nouveaux champs sont **additifs et optionnels** (`None` par défaut → rétrocompat des analyses anciennes et des consommateurs existants).

### Tests obligatoires (pyramide)
- Unitaire `core.py` : `_earnings_ratios_trace`/`_valuation_ratios_trace` (horodatage présent → ISO+source ; ratio `None` ou sans horodatage → `None`).
- Intégration `ticker_report.py` : `_reconstruct_analyze_response` peuple les quatre champs quand `input_data` porte les sous-clés horodatées ; ancien `input_data` plat (sans sous-clés) → quatre champs `None`, pas de crash.
- Composant `AnalysisResult` : source+date earnings/valuation affichées quand le champ est présent, omises sinon (happy path + None).
- Non-régression : `pytest` (hors e2e/evals) + `ruff` ; `vitest` + `tsc --noEmit` + ESLint (0/0).

### Note d'environnement (session web)
`ANTHROPIC_API_KEY` absente → evals non exécutables, **mais ce sprint ne touche aucun prompt de skill ni la logique de routing → evals non concernées**. `node_modules` frontend possiblement absent à l'amorçage → `npm install` si besoin. Stack Docker non démarrée ; pas de test navigateur live. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 147 — Interprétation déterministe Sloan (dernier cadre LLM)
**Objectif** : rendre déterministe `sloan.interpretation` (dernier libellé d'interprétation encore produit par le LLM après les Sprints 131/143), dérivé du `accrual_ratio` déjà calculé en Python — parité finale des 5 cadres M/Z/F/C/Sloan.
**Complexité** : Faible (calque exact du pattern Sprint 143).
**Justification** : `_injecter_scores` substitue déjà `sloan.accrual_ratio` mais **pas** `sloan.interpretation` → seul cadre où le libellé peut diverger du chiffre déterministe.
**Référence** : EXISTANT (vérifié cette session) — `SloanDetail.interpretation: str` `app/skills/tier2/earnings_quality/schemas.py:158` (LLM, jamais substitué) ; `_injecter_scores` ne pose que `data["sloan"]["accrual_ratio"]` `app/skills/tier2/earnings_quality/skill.py:190` ; `accrual_ratio` déjà calculé via `sloan_accrual_ratio` `skill.py:155` dans `_scores_depuis_ratios` `skill.py:68`. À CRÉER — `_sloan_interpretation(accrual_ratio: float | None) -> str` (calque `_piotroski_interpretation`) + champ sur `_ScoresDeterministes` + substitution sous gate `accrual_ratio is not None` ; seuils canoniques à confirmer dans `prompts/system.md` (`fichier:ligne` à vérifier en début de sprint).

### Sprint 148 — Mutualiser `_parse_input_data` entre `ticker_report` et `report.py`
**Objectif** : factoriser le parsing défensif de `input_data` (raw JSONB → dict) dans un utilitaire partagé, supprimant la copie inline de `report.py`.
**Complexité** : Faible.
**Justification** : finding *reuse* écarté au Sprint 144 (hors périmètre alors) ; maintenant que les reconstructeurs sont actifs (câblés au PDF au Sprint 145), le bon moment pour lever le helper. Évite qu'un 3ᵉ endpoint ajoute une 4ᵉ variante du même garde.
**Référence** : EXISTANT (vérifié cette session) — `_parse_input_data` `app/api/endpoints/ticker_report.py:198` (créé Sprint 144) ; duplication inline `_reconstruct_ratios_trace` `app/api/endpoints/report.py:123` (`GrahamRatios.model_validate(data)` `:140`). À CRÉER — module partagé (ex. `app/utils/input_data.py`) + import dans les deux endpoints + test du helper isolé.

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality`
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue.
**Complexité** : Faible en code / coûteuse en exécution (re-run evals).
**Justification** : le prompt encadre désormais la cardinalité — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` ; schema `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min) → hors conteneur web.

### Sprint 150 — Provenance par ratio (`ratios_provenance`) jusqu'à `AnalysisResult`
**Objectif** : étendre l'affichage signal-only de la provenance par ratio (clé yfinance de repli) — posé sur `AnalyzeForm` au Sprint 141 — à l'analyse rendue/rechargée `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne (threading backend + reconstruction historique + affichage).
**Justification** : le Sprint 141 a explicitement **différé** la provenance sur `AnalysisResult` « tant qu'elle n'est pas threadée dans `AnalyzeResponse` ». Même mécanique que le Sprint 146 (threading source+date), réutilisable juste après.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` ; affichage existant sur `AnalyzeForm` (`ratiosEnRepli` `frontend/src/components/AnalyzeForm.tsx:50`, badge `data-testid="ratios-provenance"` `:206`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` (backend + TS) + peuplage analyse/historique + bloc d'affichage sur `AnalysisResult` (clone du badge `AnalyzeForm`).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.31.0), .claude/rules/conventions-frontend.md et donnees-financieres.md avant de commencer.
Sprint actif : 146 — Affichage earnings/valuation source+date sur l'analyse rendue (AnalysisResult).
Objectif : threader la source+date earnings/valuation jusqu'à AnalyzeResponse (analyse live + reconstruction historique, calque _graham_ratios_trace) et l'afficher sous les cartes earnings/valuation de AnalysisResult — parité avec l'affichage Graham (Sprint 139).
Point de départ vérifié : _graham_ratios_trace core.py:284, champs AnalyzeResponse.ratios_fetched_at/source core.py:274/278 peuplés :537, reconstruction ticker_report.py:334/343 ; entrées request.earnings_ratios/valuation_ratios core.py:220/223 ; reconstructeurs _extract_earnings_ratios/_extract_valuation_ratios ticker_report.py:234/241 ; affichage Graham AnalysisResult.tsx:211-216, cartes :222-224/:227 ; AnalyzeResponse TS types/index.ts:450.
Honnêteté None : champ absent → bloc omis (parité Graham).
Evals : ce sprint ne touche aucun prompt de skill ni la logique de routing → evals non concernées.
```
