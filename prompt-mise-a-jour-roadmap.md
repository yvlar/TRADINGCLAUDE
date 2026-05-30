# Sprint 134 — Traçabilité source+date des ratios dans l'UI/PDF

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.20.0 — Sprint 133 complété)

Le Sprint 133 a étendu le composant `Disclaimer` (Sprint 129) aux deux dernières surfaces actionnables hors `AnalysisResult` : les résultats du Screener et la vue Comparer affichent désormais l'avertissement réglementaire `inline`, conditionné à la présence de résultats. La file « conformité » de la revue FinTech est close ; reste la file **traçabilité des données** (source + date des ratios).

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.20.0, Sprint 133 ✅
3. `.claude/rules/donnees-financieres.md` — cœur du sprint : exigence « source + date » (« une donnée sans date est inutilisable »), validation None/div0, suffixe `.TO`
4. `.claude/rules/variables-financieres.md` — nommage standardisé du nouveau champ de traçabilité (snake_case Python ↔ camelCase TS)

---

## TÂCHE — Sprint 134 : afficher source + date de récupération des ratios

**Objectif** : `donnees-financieres.md` impose que toute donnée financière soit accompagnée de sa source et de sa date de récupération (« une donnée sans date est inutilisable »). Aujourd'hui les ratios extraits de Yahoo Finance sont affichés sans horodatage de récupération — risque de décision sur une donnée périmée. Ajouter un champ de traçabilité (date de récupération + source) à l'extraction tier1, le propager au schema → type TS → UI/PDF, et l'afficher à côté des ratios.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Aucun champ de traçabilité aujourd'hui** — `grep` confirmé : ni `fetched_at`, ni `data_fetched_at`, ni `fetched_date` dans `app/skills/`. Le champ est donc **à CRÉER** de bout en bout.
2. **Extraction tier1** — `app/skills/tier1/yahoo_finance.py:182` `async def extract(self, ticker) -> GrahamRatios` construit l'objet de ratios Graham. C'est ici que l'horodatage (`datetime.now(UTC)` au moment de l'extraction) et la source (`"Yahoo Finance"`) doivent être posés.
3. **Schema backend** — `app/skills/tier2/graham_analysis/schemas.py:13` `class GrahamRatios(BaseModel)` — ajouter `ratios_fetched_at: datetime | None = None` (+ source, voir Spécification). `None` par défaut → rétrocompatible avec les analyses persistées avant ce sprint.
4. **Type TS** — `frontend/src/types/index.ts:47` `interface GrahamRatios` — ajouter le champ camelCase correspondant (`ratiosFetchedAt?: string | null`).
5. **PDF** — `app/services/pdf_report_service.py:220` `_build_ratios_rows(r: GrahamRatios)` (appelé `:315`) — y ajouter une ligne « Source / récupéré le ».
6. **UI** — `frontend/src/components/AnalysisResult.tsx` (bloc Graham) — afficher la source + la date de récupération discrètement sous les ratios.

### Spécification

1. **Tier1** — `extract()` pose `ratios_fetched_at = datetime.now(UTC)` et une source littérale (`RATIOS_SOURCE = "Yahoo Finance"` constante module, jamais un littéral dispersé). Le repli de source existant (`yahoo_finance.py:66-72`, `info.earningsGrowth` faute d'`income_stmt`) ne change pas l'horodatage : la date reste celle de l'extraction. Ne pas confondre la date de récupération (quand on a appelé l'API) avec une éventuelle date de la donnée elle-même (hors scope).
2. **Schema + type TS** — champ optionnel `None`/`null` par défaut (rétrocompatibilité des analyses persistées). Respecter `variables-financieres.md` : snake_case côté Python, camelCase côté TS.
3. **Affichage** — UI (`AnalysisResult.tsx`) + PDF (`_build_ratios_rows`) : « Source : Yahoo Finance · récupéré le AAAA-MM-JJ ». Si `None` (analyse ancienne), ne rien afficher ou « source n.d. » — pas de plantage, pas de date factice.
4. **Zéro régression** — `tsc --noEmit` 0 erreur, ESLint 0, pas de `any`. Périmètre = `GrahamRatios` (ratios principaux affichés) ; `ValuationRatios`/`EsgInput`/`EarningsQualityRatios` sont hors scope (sprint suggéré 138).

### Tests obligatoires (pyramide)
- **Unitaire** : `extract()` pose un `ratios_fetched_at` non-`None` et la source attendue (mocker `datetime`/`yfinance`) ; schema `GrahamRatios` accepte le champ et reste valide à `None`.
- **PDF** : `_build_ratios_rows` produit la ligne source+date quand le champ est présent, et l'omet proprement quand `None`.
- **Composant** : `AnalysisResult` affiche source+date quand présent (`data-testid` dédié), rien quand `None`.
- Backend `pytest` + `ruff` ; frontend Vitest + tsc + ESLint.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être **absent** → `cd frontend && npm install`.
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Aucun prompt de skill modifié (extraction tier1 = données brutes, pas de prompt conceptuel) → **evals non concernées**. Stack Docker non démarrée → extraction yfinance exercée sur mocks (pas d'appel réseau live). Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 135 — Repli multi-sources généralisé (au-delà d'eps_growth)
**Objectif** : généraliser le pattern de repli du Sprint 130 (source primaire yfinance → repli tracé) aux autres ratios critiques sujets au SPOF.
**Complexité** : Moyenne
**Justification** : le Sprint 130 n'a traité que `eps_growth` ; les autres ratios restent dépendants d'une source unique.
**Référence** : EXISTANT (vérifié cette session) — pattern de repli dans `app/skills/tier1/yahoo_finance.py:66-72` (`fallback = info.get("earningsGrowth")` + `logger.info` de traçabilité + retour `(float(fallback), 1)`). À CRÉER — abstraction du repli réutilisable + champ de traçabilité de source par ratio.

### Sprint 136 — UI : affichage des sous-composantes auditables (X1-X5 Z-Score)
**Objectif** : surfacer dans l'UI les intermédiaires désormais persistés mais non affichés — termes X1-X5 du Z-Score (Sprint 131).
**Complexité** : Faible
**Justification** : le M-Score affiche déjà ses indices ; les X1-X5 du Z sont persistés et auditables côté backend mais invisibles dans l'UI — asymétrie d'auditabilité.
**Référence** : EXISTANT (vérifié cette session) — backend `app/skills/tier2/earnings_quality/schemas.py:106-110` (`x1`…`x5: FiniteFloatOrNone`, peuplés par Python depuis Sprint 131) ; UI `frontend/src/components/EarningsQualitySection.tsx:97` `MScoreCard` (affiche déjà les indices), `:139` `ZScoreCard` (n'affiche pas X1-X5). À CRÉER côté TS — `frontend/src/types/index.ts:112` `ZScoreDetail` n'a que `variante`/`z_score`/`interpretation` : ajouter `x1`-`x5` (`number | null`) pour matcher le backend, puis les rendre dans `ZScoreCard`.

### Sprint 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation)
**Objectif** : exécuter (hors session web, avec clé Anthropic) les `evals` des skills dont le prompt a basculé en mode « interprète des chiffres calculés » (Sprints 128/131/132) pour confirmer l'absence de dégradation qualitative silencieuse.
**Complexité** : Faible
**Justification** : `pytest` reste vert avec Claude mocké sans rien prouver sur la qualité réelle du prompt ; les notes « calculés en amont » n'ont jamais été validées contre Claude réel (aucune clé dans le conteneur web).
**Référence** : EXISTANT (vérifié cette session) — répertoire `tests/evals/` (`__init__.py`, `conftest.py`, `eval_runner.py` ; exclu du CI standard via `--ignore=tests/evals`) ; prompts modifiés `app/skills/tier2/stock_valuation/prompts/system.md` (note Sprint 132) et `app/skills/tier2/earnings_quality/prompts/system.md` (notes Sprints 128/131).

### Sprint 138 — Traçabilité source+date étendue aux autres extracteurs
**Objectif** : appliquer le pattern source+date du Sprint 134 (posé sur `GrahamRatios`) aux autres ratios extraits — `ValuationRatios` et `EarningsQualityRatios`.
**Complexité** : Faible
**Justification** : le Sprint 134 ne couvre que `GrahamRatios` (ratios principaux affichés) ; les ratios de valorisation et de qualité comptable restent sans horodatage de récupération, même exigence `donnees-financieres.md`.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:261` `extract_earnings_quality()` et `:399` `extract_valuation()`. À CRÉER — réutiliser la constante/champ posés au Sprint 134 sur ces deux chemins d'extraction + leurs schemas/types/affichages.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.20.0), .claude/rules/donnees-financieres.md
et .claude/rules/variables-financieres.md avant de commencer.
Sprint actif : 134 — Traçabilité source+date des ratios. Ajouter un champ de récupération
(ratios_fetched_at = datetime.now(UTC) + source "Yahoo Finance" en constante) dans
app/skills/tier1/yahoo_finance.py:182 extract(), le propager au schema GrahamRatios
(schemas.py:13, défaut None rétrocompatible) → type TS (index.ts:47, camelCase) → PDF
(_build_ratios_rows pdf_report_service.py:220) → UI (AnalysisResult.tsx bloc Graham).
Afficher « Source : Yahoo Finance · récupéré le AAAA-MM-JJ », rien si None. Périmètre =
GrahamRatios uniquement (Valuation/Esg/EarningsQuality = sprint 138). Tests : unitaire
extract()+schema, PDF (ligne présente/omise), composant (affiché/absent). evals non concernées.
```
