# Sprint 151 — Centraliser le gate « honnête-None » des lignes source+date (consolidation reuse)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.34.0 — Sprint 148 complété)

Le Sprint 148 a rendu `sloan.interpretation` déterministe (dérivé de l'`accrual_ratio`, substitué post-parse), fermant la parité des 5 cadres M/Z/F/C/Sloan — plus aucun libellé d'interprétation `earnings_quality` n'est produit par le LLM.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint backend pur** — refactor reuse à comportement **inchangé** (aucun output observable ne bouge ; on remplace deux prédicats inline par un helper partagé). Aucun prompt de skill, aucune migration → **pas d'evals**. Stack Docker non démarrée ; pas de test navigateur live.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.34.0, Sprint 148 ✅
3. `.claude/rules/api-architecture.md` — cœur du sprint : layering `app/` (un service ne doit pas importer les endpoints), contraintes API.
4. `.claude/rules/tests-pyramide.md` — niveaux de test, fixture `client`, test unitaire isolé pour le helper.

---

## TÂCHE — Sprint 151 : helper partagé pour le gate « honnête-None » source+date

**Objectif** : le prédicat « ce ratio porte une source OU une date » est **dupliqué inline** côté backend pour décider d'afficher la ligne « Source des ratios » dans le PDF. Extraire ce prédicat en **un helper backend partagé** et l'appeler aux deux sites PDF. Finding *reuse* explicitement **différé au Sprint 145** (« à mutualiser dans un futur sprint de consolidation reuse »). **Sprint backend pur** (comportement inchangé ; aucun frontend, prompt de skill, ni migration).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Gate Graham PDF** — `app/services/pdf_report_service.py:246` : `if r.ratios_fetched_at is not None or r.ratios_source is not None:` (ici `r: GrahamRatios` est garanti non-None).
2. **Gate earnings/valuation PDF** — `app/services/pdf_report_service.py:261` : `if r is not None and (r.ratios_fetched_at is not None or r.ratios_source is not None):` (boucle sur earnings/valuation `| None`).
3. **Home naturel du helper** — `app/services/ratios_recon.py` possède déjà les helpers de trace `_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace` (`:22`/`:30`/`:40`) et `reconstruct_ratios_traces` (`:100`). Pas de cycle : `ratios_recon` n'importe pas les endpoints ni `pdf_report_service`.
4. **Miroir frontend (déjà unifié — NE PAS toucher)** — `frontend/src/components/RatiosSourceNote.tsx:11` : `if (!fetchedAt && !source) return null` (négation du même prédicat ; le frontend est déjà DRY, périmètre backend uniquement).
5. **Schémas portant les champs** — `ratios_fetched_at`/`ratios_source` sur `GrahamRatios`, `EarningsQualityRatios` (`earnings_quality/schemas.py:69/73`), `ValuationRatios` (`stock_valuation/schemas.py:32/36`).

### Spécification

1. **`app/services/ratios_recon.py`** : ajouter `has_ratios_source(ratios) -> bool` :
   ```python
   def has_ratios_source(ratios) -> bool:
       """True si le ratio porte une source OU une date (gate d'affichage « honnête-None »)."""
       return ratios is not None and (
           ratios.ratios_fetched_at is not None or ratios.ratios_source is not None
       )
   ```
   Le `ratios is not None` rend le helper sûr pour les deux sites (Graham non-None inclus). Typage : accepter un objet portant `ratios_fetched_at`/`ratios_source` — utiliser un `Protocol` minimal OU `BaseModel | None` (mypy `app/` doit rester vert ; vérifier que les trois schémas satisfont l'annotation choisie).
2. **`app/services/pdf_report_service.py`** : remplacer les deux prédicats inline (`:246`, `:261`) par `has_ratios_source(r)`. Importer depuis `ratios_recon`. Aucun changement de sortie (byte-for-byte : le helper est exactement `r is not None and (… or …)`, et au site Graham `r` est non-None donc le `r is not None` ne change rien).
3. **Périmètre** : backend uniquement. Le frontend (`RatiosSourceNote`) est déjà unifié — **ne pas toucher**. Ne pas modifier les helpers de trace `_*_ratios_trace` (forme différente : ils renvoient `(date, source)`, pas un bool) sauf si l'un peut réutiliser le prédicat sans changer son contrat — à évaluer, **ne pas forcer**.

### Tests obligatoires (pyramide)
- **Unitaire** `ratios_recon` : `has_ratios_source` — `None → False` ; ratio sans source ni date → `False` ; source seule → `True` ; date seule → `True` ; les deux → `True` (utiliser un petit objet/`GrahamRatios` de test).
- **Non-régression PDF** : les tests existants `_build_ratios_rows`/`_build_ratios_source_rows` (`tests/services/test_pdf_report_service.py`) restent verts **sans modification** (preuve du comportement inchangé), y compris le test d'acceptation `pypdf` (Sprint 145).
- **Gates** : `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports` verts ; frontend inchangé → `tsc`/`vitest`/ESLint restent verts **sans modification**.

### Note d'environnement (session web)
Refactor backend pur, comportement inchangé → **pas d'evals**, `ANTHROPIC_API_KEY` non requise. Stack Docker non démarrée. **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint 152 — Test d'intégration de l'endpoint `GET /report/{analysis_id}` (couverture du cœur consolidé) ⭐ prêt, exécutable en web
**Objectif** : ajouter un test d'intégration HTTP exerçant `GET /report/{analysis_id}` de bout en bout (DB mockée → `reconstruct(require_graham=True)` → PDF), vérifiant 200 + `application/pdf` ; le 404 est déjà couvert.
**Complexité** : Faible.
**Justification** : `reconstruct` (Sprint 147) est le chemin partagé des deux endpoints PDF ; `/report/{id}` n'a pas de test d'intégration du chemin 200 reconstruit (souligné par la revue Staff-Eng du Sprint 147).
**Référence** : EXISTANT (vérifié cette session) — endpoint `get_report` `app/api/endpoints/report.py:80` appelle `_reconstruct_response(row)` `:105` ; le 404 existe `tests/services/test_report.py:179` (`test_get_report_analysis_inconnu_404`). À CRÉER — test `client.get("/report/{id}")` avec `db_pool.fetchrow` mocké renvoyant une ligne valide (graham + ≥1 skill) → 200 + `application/pdf`.

### Sprint 150 — Provenance par ratio (`ratios_provenance`) jusqu'à `AnalysisResult`
**Objectif** : étendre l'affichage signal-only de la provenance par ratio (clé yfinance de repli) — posé sur `AnalyzeForm` au Sprint 141 — à l'analyse rendue/rechargée `AnalysisResult`, en threadant `ratios_provenance` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne (threading backend + reconstruction historique + affichage frontend).
**Justification** : le Sprint 141 a explicitement **différé** la provenance sur `AnalysisResult` ; même mécanique que le Sprint 146, désormais centralisée dans `analysis_reconstruction`/`ratios_recon`.
**Référence** : EXISTANT (vérifié cette session) — `GrahamRatios.ratios_provenance: dict[str, str] | None` `app/skills/tier2/graham_analysis/schemas.py:42` ; affichage `AnalyzeForm` (`ratiosEnRepli` `frontend/src/components/AnalyzeForm.tsx:50`, badge `data-testid="ratios-provenance"` `:206`). À CRÉER — champ `ratios_provenance` sur `AnalyzeResponse` (backend + TS) + peuplage aux sites de construction + reconstruction historique + bloc d'affichage sur `AnalysisResult`.

### Sprint 149 — Confirmer (evals) le calibrage du drift `earnings_quality` ⚠️ nécessite `ANTHROPIC_API_KEY` (hors conteneur web)
**Objectif** : confirmer par un re-run d'evals que la sur-génération de `drapeaux_rouges` (10 échecs golden au Sprint 137) est résolue, maintenant que la cardinalité est encadrée par le prompt et que **tous** les libellés d'interprétation sont déterministes (M/Z/F/C + Sloan au Sprint 148).
**Complexité** : Faible en code / coûteuse en exécution (re-run evals, ~33 min, ~100 appels Haiku).
**Justification** : ferme la boucle ouverte au Sprint 137 — reste à **mesurer** que `drapeaux_rouges_cardinalite` passe sous le golden.
**Référence** : EXISTANT (vérifié cette session) — golden `tests/evals/fixtures/earnings_golden.json` ; `EarningsQualityOutput.drapeaux_rouges: list[str]` `app/skills/tier2/earnings_quality/schemas.py:169`. **Contrainte** : re-run exige `ANTHROPIC_API_KEY` → **non exécutable dans le conteneur web** ; à lancer en local.

### Sprint 153 — Helper de formatage source+date unifié backend/PDF (suite du Sprint 151)
**Objectif** : après avoir unifié le *gate* (Sprint 151), évaluer si le *formatage* de la ligne (`_fmt_ratios_source`) et la dérivation `(date, source)` des trois `_*_ratios_trace` peuvent partager un cœur commun sans aplatir les contrats.
**Complexité** : Faible.
**Justification** : continuation naturelle de la consolidation reuse ; à ne lancer qu'après mesure que le Sprint 151 n'a pas déjà suffi.
**Référence** : EXISTANT (vérifié cette session) — `_fmt_ratios_source` `app/services/pdf_report_service.py:150` ; `_graham_ratios_trace`/`_earnings_ratios_trace`/`_valuation_ratios_trace` `app/services/ratios_recon.py:22/:30/:40` (clones quasi-identiques, conservés au Sprint 146 par style maison). À CRÉER / À ÉVALUER — un cœur de trace paramétré **seulement si** le gain dépasse le coût de l'abstraction (sinon documenter le rejet).

---

## Template de démarrage

```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md (v10.34.0), .claude/rules/api-architecture.md et .claude/rules/tests-pyramide.md.
Sprint actif : 151 — Centraliser le gate « honnête-None » des lignes source+date.

TÂCHE : extraire le prédicat dupliqué « ratio porte source OU date » en un helper backend partagé.
- app/services/ratios_recon.py : has_ratios_source(ratios) -> bool
    return ratios is not None and (ratios.ratios_fetched_at is not None or ratios.ratios_source is not None)
- app/services/pdf_report_service.py : remplacer les prédicats inline :246 (Graham) et :261
  (earnings/valuation) par has_ratios_source(r). Import depuis ratios_recon. Sortie inchangée.
PÉRIMÈTRE : backend uniquement ; frontend RatiosSourceNote déjà unifié (ne pas toucher) ;
ne pas modifier les helpers de trace _*_ratios_trace (contrat (date, source) différent).
TESTS : unitaire has_ratios_source (None/sans/source seule/date seule/les deux) ;
les tests PDF existants (_build_ratios_rows, _build_ratios_source_rows, acceptation pypdf) restent verts SANS modif.
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  .venv/bin/mypy app/ --ignore-missing-imports   # le CI le lance — ruff ne typecheck PAS
  (frontend non touché : tsc/vitest/eslint restent verts sans modif)
Refactor backend pur, comportement inchangé → pas d'evals.
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée, PR base = dev. Confirmer avant git push / ouverture de PR.
```
