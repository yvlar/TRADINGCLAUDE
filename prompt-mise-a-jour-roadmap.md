# Sprint 154 — Provenance par ratio (clé yfinance de repli) dans le rapport PDF par ticker

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.39.0 — Sprints 148→153 complétés)

Le lot 148→153 a fermé la parité déterministe des 5 cadres `earnings_quality` (Sloan, Sprint 148), mesuré hors-ligne le déterminisme contre le golden + verrouillé la cause racine `drapeaux_rouges` (Sprint 149), étendu la provenance par ratio à l'analyse rendue `AnalysisResult` (Sprint 150), et consolidé la réutilisation (`has_ratios_source` Sprint 151, couverture endpoint `/report/{id}` Sprint 152, fusion des clones `_ratios_trace` Sprint 153).

> **État courant complet** (version, fonctionnalités, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint backend pur** (rendu PDF Python depuis l'output persisté) — **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. `ANTHROPIC_API_KEY` absente du conteneur web ; stack Docker non démarrée ; pas de test navigateur live. `frontend/node_modules` peut être absent → `npm install` dans `frontend/` avant tout gate frontend (mais ce sprint ne touche pas le frontend).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.39.0, Sprints 148→153 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : traçabilité obligatoire (source + date), honnêteté None (ratio absent ≠ 0.0).
4. `.claude/rules/gotchas-operationnels.md` — si le rendu PDF / services sont touchés.

---

## TÂCHE — Sprint 154 : afficher la provenance par ratio dans le PDF par ticker

**Objectif** : Le badge signal-only « P/B via `clé` (repli) » (clé yfinance effective ≠ clé primaire attendue) est affiché sur `AnalyzeForm` (Sprint 141) **et** sur l'analyse rendue/rechargée `AnalysisResult` (Sprint 150). Le **rapport PDF par ticker** n'en porte aucune trace, alors que la source+date des ratios y est déjà rendue (Sprint 145). Compléter la parité : rendre une ligne « Provenance des ratios (repli) » dans le PDF, sous le **même filtre signal-only** que le frontend. **Sprint backend pur** (aucun frontend, migration, ni prompt de skill).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Champ déjà persisté + reconstructible** — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` (exclu de la clé de cache). Persisté dans `input_data` (`_build_input_data` `model_dump(mode="json")`, Sprint 144) et reconstruit par `extract_graham_ratios(row)` `app/services/ratios_recon.py:78`.
2. **Le PDF a déjà l'objet ratios reconstruit** — `get_ticker_report` fait `ratios = _extract_ratios(row)` `app/api/endpoints/ticker_report.py:116` (un `GrahamRatios`, donc `ratios.ratios_provenance` est disponible) et le passe à `generate_ticker_report`.
3. **Site de rendu Graham** — `_build_ratios_rows(r: GrahamRatios)` `app/services/pdf_report_service.py:231` rend les ratios + (via `has_ratios_source(r)` `:247`) la ligne « Source des ratios » avec `_fmt_ratios_source`. C'est là (ou dans un helper voisin) qu'une ligne provenance s'insère.
4. **Filtre signal-only — UNIQUEMENT en frontend pour l'instant** — `RATIO_PRIMARY_KEYS` + `ratiosEnRepli` `frontend/src/components/RatiosProvenanceNote.tsx:3/19` (`pb→priceToBook`, `debt_equity→debtToEquity`, `book_value→bookValue` ; repli = clé effective ≠ primaire). **Le backend n'a aucun équivalent** → à porter en Python (constante + fonction pure) pour ne montrer que les vrais replis (pas tout le dict).
5. **⚠️ Source réelle des clés primaires (SSOT)** — les clés primaires « vraies » vivent dans l'**extracteur tier1** `app/skills/tier1/yahoo_finance.py:259,263` (`_resolve_ratio(info, ticker, "priceToBook", "priceToBookRatio")` → primaire `"priceToBook"`, repli `"priceToBookRatio"`). Le `RATIO_PRIMARY_KEYS` du frontend en est déjà un **miroir codé en dur** (dette pré-existante, revue PR §I1). Ajouter une 3ᵉ copie Python sans verrou aggraverait la dérive silencieuse écran↔PDF↔extracteur.

### Spécification

1. **`app/services/ratios_recon.py`** (ou un module dédié) : porter le filtre signal-only en Python — constante `_RATIO_PRIMARY_KEYS: dict[str, str]` + fonction pure `ratios_en_repli(provenance: dict[str, str] | None) -> list[tuple[str, str]]` (clé instrumentée ET effective ≠ primaire ; `None`/clés primaires → `[]`). **Idéalement, dériver `_RATIO_PRIMARY_KEYS` de la SSOT** (les clés primaires passées à `_resolve_ratio` dans `yahoo_finance.py`) plutôt qu'un 3ᵉ littéral — sinon, à défaut, verrou de parité **obligatoire** (voir Tests).
2. **`app/services/pdf_report_service.py`** : helper `_build_ratios_provenance_rows(provenance) -> list[tuple[str, str]]` (libellé « <ratio> » → « via `<clé>` (repli) », réutiliser `RATIO_LABELS` portés en Python) ; ligne(s) rendues seulement si `ratios_en_repli(...)` non vide (honnêteté None : aucune ligne sinon). Inséré près du bloc « Source des ratios » Graham. `generate_ticker_report` lit `ratios.ratios_provenance`.
3. **Périmètre** : PDF par ticker **uniquement**. Affichage écran (`AnalysisResult`/`AnalyzeForm`), threading `AnalyzeResponse` et reconstruction (Sprint 150) **inchangés**. Rétrocompat : `ratios_provenance` absent/None → aucune ligne (PDF byte-for-byte identique).

### Tests obligatoires (pyramide)
- **Unitaires** `ratios_en_repli` : repli détecté (clé ≠ primaire) ; clés primaires → `[]` ; `None` → `[]` ; clé non instrumentée ignorée.
- **Verrou de parité BIDIRECTIONNEL (obligatoire — résout la dette §I1)** : un test qui échoue si `_RATIO_PRIMARY_KEYS` (Python) diverge de (a) la map frontend `RatiosProvenanceNote.tsx:3` ET (b) les clés primaires de l'extracteur `yahoo_finance.py` (`_resolve_ratio(..., PRIMAIRE, repli)`). À défaut d'un import direct TS↔Python, asserter les **trois paires connues** (`pb→priceToBook`, `debt_equity→debtToEquity`, `book_value→bookValue`) contre chacune des trois sources, avec un commentaire pointant les fichiers:lignes à mettre à jour ensemble.
- **Unitaires** `_build_ratios_provenance_rows` : repli → ligne formatée ; pas de repli → `[]`.
- **Acceptation `pypdf`** : le texte du PDF rendu contient « (repli) » + la clé effective quand un repli existe ; omission vérifiée sinon.
- **Non-régression** : `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports` verts.

### Note d'environnement (session web)
Rendu PDF Python pur → evals non concernées. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 155 — Consolidation TS du formatage « source + date » (RatiosSourceNote ↔ AnalyzeForm)
**Objectif** : éliminer la duplication frontend du rendu « Source : … · récupéré le … » entre `RatiosSourceNote` et la ligne inline d'`AnalyzeForm` (gates et styles différents à réconcilier).
**Complexité** : Faible.
**Justification** : pendant TS de la consolidation backend Sprint 153 ; relevé en [LOW] par la revue indépendante du Sprint 153.
**Référence** : EXISTANT (vérifié cette session) — `RatiosSourceNote.tsx:13-16` (rend « Source : {source} · récupéré le {date} ») ; ligne inline d'`AnalyzeForm.tsx` (rend le même motif, gate `ratios.ratios_fetched_at &&` = date-only, classe `mt-3`, `data-testid="ratios-source"`). À CRÉER — réconcilier les deux gates (date-only vs source-or-date) avant extraction ; **attention** : un changement de gate modifie l'UX (afficher source sans date).

### Sprint 156 — Re-run des evals `earnings_quality` (mesure live de `drapeaux_rouges`)
**Objectif** : exécuter en local (clé requise) `tests/evals/test_earnings_evals.py -m evals` pour mesurer enfin la cardinalité `drapeaux_rouges` que le Sprint 149 a verrouillée hors-ligne, et reporter le résultat dans `ROADMAP.md` (note de drift).
**Complexité** : Faible en code / coûteuse en exécution (~100 appels Haiku, ~33 min).
**Justification** : ferme la boucle ouverte au Sprint 137/149 — la précondition (5 cadres déterministes + consigne de cardinalité) est en place et verrouillée ; reste à **mesurer le live**.
**Référence** : EXISTANT (vérifié cette session) — `test_earnings_drapeaux_rouges_cardinalite` `tests/evals/test_earnings_evals.py:146` (marqueur `evals`, skip si pas de clé) ; golden `tests/evals/fixtures/earnings_golden.json` (12 cas avec `drapeaux_rouges_max`). **Contrainte** : `ANTHROPIC_API_KEY` requise → hors conteneur web.

### Sprint 157 — Tooltip de provenance enrichi sur `AnalysisResult` (clé primaire attendue)
**Objectif** : au survol d'un badge de repli, afficher la clé **primaire attendue** (déjà dans le `title` côté `AnalyzeForm`) — uniformiser l'expérience entre le formulaire et l'analyse rendue.
**Complexité** : Faible.
**Justification** : le composant partagé `RatiosProvenanceNote` (Sprint 150) porte déjà le `title` ; vérifier qu'il s'affiche identiquement sur les deux surfaces (parité d'info-bulle).
**Référence** : EXISTANT (vérifié cette session) — `RatiosProvenanceNote.tsx` (badge + `title` « Clé yfinance de repli — la clé primaire « … » était absente ») utilisé par `AnalyzeForm` ET `AnalysisResult` (Sprint 150). À VÉRIFIER/AJUSTER — couverture de test du `title` sur `AnalysisResult`.

### Sprint 158 — Endpoint `GET /ticker-report/{ticker}` : test d'intégration du chemin 200 multi-skills
**Objectif** : étendre la couverture d'intégration faite pour `/report/{id}` (Sprint 152) au second endpoint PDF `/ticker-report/{ticker}` (200 + `application/pdf`, reconstruction `require_graham=False`).
**Complexité** : Faible.
**Justification** : `reconstruct(require_graham=False)` est le chemin de `/ticker-report` ; symétrie de couverture avec `/report/{id}`.
**Référence** : EXISTANT (vérifié cette session) — `_reconstruct_analyze_response` `app/api/endpoints/ticker_report.py:208` → `reconstruct(row, require_graham=False)` `:213`. À CRÉER — test `client.get("/ticker-report/{ticker}")` avec `db_pool` mocké (réutiliser `_make_result_row`).

---

## Template de démarrage

```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md (v10.39.0), .claude/rules/donnees-financieres.md.
Sprint actif : 154 — Provenance par ratio (clé yfinance de repli) dans le rapport PDF par ticker.

TÂCHE : rendre une ligne « Provenance des ratios (repli) » dans le PDF par ticker, sous le
même filtre signal-only que le frontend (clé effective ≠ clé primaire).
- ratios_recon.py : porter _RATIO_PRIMARY_KEYS (miroir EXACT de RatiosProvenanceNote.tsx:3) +
  ratios_en_repli(provenance) -> list[(ratio, clé)] (clés primaires/None → []).
- pdf_report_service.py : _build_ratios_provenance_rows(provenance) ; ligne rendue seulement
  si repli (honnêteté None) ; generate_ticker_report lit ratios.ratios_provenance
  (reconstruit via _extract_ratios(row) ticker_report.py:116, GrahamRatios.ratios_provenance:42).
PÉRIMÈTRE : PDF par ticker uniquement ; affichage écran / threading / reconstruction (Sprint 150) intacts.
TESTS : unitaires ratios_en_repli (+ parité de map avec le frontend) + _build_ratios_provenance_rows ;
acceptation pypdf (« (repli) » présent quand repli, omis sinon).
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  .venv/bin/mypy app/ --ignore-missing-imports   # le CI le lance — ruff ne typecheck PAS
  (frontend non touché : tsc/vitest/eslint restent verts sans modif)
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée, PR base = dev. Confirmer avant git push / ouverture de PR.
```
