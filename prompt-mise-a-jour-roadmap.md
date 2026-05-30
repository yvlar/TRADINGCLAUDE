# Sprint 136 — UI : affichage des sous-composantes auditables (X1-X5 Z-Score)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.22.0 — Sprint 135 complété)

Le Sprint 135 a généralisé le repli de source aux ratios Graham : un ratio absent de yfinance produit désormais `None` (donnée manquante honnête) au lieu d'un `0.0` trompeur, via une abstraction de repli réutilisable (`_resolve_ratio`). Le Sprint 131 avait rendu déterministes et persisté les termes **X1-X5 du Z-Score** côté backend, mais l'UI ne les affiche pas encore (le M-Score affiche déjà ses 8 indices). Ce sprint corrige cette asymétrie d'auditabilité côté frontend.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.22.0, Sprint 135 ✅
3. `.claude/rules/conventions-frontend.md` — cœur du sprint : React 18, TypeScript strict (zéro `any`), `data-testid` obligatoire sur les éléments testés, test composant happy path + cas d'erreur

---

## TÂCHE — Sprint 136 : surfacer les termes X1-X5 du Z-Score dans l'UI

**Objectif** : les termes X1-X5 du Z-Score d'Altman sont calculés en Python et persistés depuis le Sprint 131 (`schemas.py` backend), mais le type TS `ZScoreDetail` ne les déclare pas et `ZScoreCard` ne les rend pas — alors que `MScoreCard` affiche déjà ses 8 indices via une grille. Combler l'asymétrie : ajouter `x1`-`x5` au type TS, puis les rendre dans `ZScoreCard` en clonant le pattern de grille de `MScoreCard`. Sprint frontend pur — aucun backend, aucune migration, aucun prompt de skill.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Backend déjà prêt (NE PAS retoucher)** — `app/skills/tier2/earnings_quality/schemas.py:106-110` : `ZScoreDetail.x1`…`x5` (`FiniteFloatOrNone = None`), peuplés par Python depuis Sprint 131 et sérialisés dans l'output JSON. Le payload porte donc déjà `x1`-`x5`.
2. **Type TS à étendre** — `frontend/src/types/index.ts:114-118` : `interface ZScoreDetail` ne déclare que `variante` / `z_score` / `interpretation`. Ajouter `x1`-`x5: number | null` (mirroir du backend). Le `MScoreDetail` voisin (`:101-112`) montre exactement le style attendu (`number | null` par champ).
3. **Composant à enrichir** — `frontend/src/components/EarningsQualitySection.tsx:139-161` : `ZScoreCard` rend le score + variante + interprétation mais **aucune grille de termes**. `MScoreCard` (`:97-137`) est le modèle à cloner : tableau `{label, value}[]` filtré sur `value !== null`, grille `grid-cols-2`, valeurs `.toFixed(3)`, rien si tous `None`.

### Spécification

1. **Type TS** — étendre `ZScoreDetail` avec `x1`-`x5: number | null` (snake_case côté payload brut, comme le backend ; zéro `any`).
2. **Rendu** — dans `ZScoreCard`, construire un tableau `[{label: 'X1', value: zscore.x1}, …, {label: 'X5', value: zscore.x5}]` filtré sur `value !== null` et le rendre en grille (cloner la grille de `MScoreCard:125-134`). Si tous les termes sont `None` (cas banque/`is_financial`), n'afficher aucune grille — exactement comme `MScoreCard`. Libellés X1-X5 explicités si pertinent (X1 = working capital/total assets, etc., voir `references/` du skill `earnings-quality-fraud-detection`) ; un libellé court `X1`…`X5` suffit si l'espace manque.
3. **Zéro régression** — `MScoreCard`, `FScoreCard`, `CScoreCard`, `SloanCard` non touchés ; le score Z + variante + interprétation déjà affichés restent inchangés.

### Tests obligatoires (pyramide)
- **Composant** (`EarningsQualitySection.test.tsx`) : Z-Score avec X1-X5 renseignés → les 5 termes rendus (vérifier valeurs ou `data-testid` dédié) ; Z-Score avec X1-X5 tous `null` (banque) → aucune grille de termes mais score + interprétation toujours présents (cas d'erreur/dégradé).
- `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`.
- Backend `pytest` inchangé (sprint frontend pur) — le lancer quand même pour prouver l'absence de régression.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). `node_modules` frontend peut être **absent** → `cd frontend && npm install`.
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- Backend (non-régression) : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` + `.venv/bin/ruff check app/ tests/`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Sprint d'affichage pur, aucun prompt conceptuel → **evals non concernées**. Stack Docker non démarrée. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation)
**Objectif** : exécuter (hors session web, avec clé Anthropic) les `evals` des skills dont le prompt a basculé en mode « interprète des chiffres calculés » (Sprints 128/131/132) pour confirmer l'absence de dégradation qualitative silencieuse.
**Complexité** : Faible
**Justification** : `pytest` reste vert avec Claude mocké sans rien prouver sur la qualité réelle du prompt ; les notes « calculés en amont » n'ont jamais été validées contre Claude réel (aucune clé dans le conteneur web).
**Référence** : EXISTANT (vérifié cette session) — `tests/evals/` (`__init__.py`, `conftest.py`, `eval_runner.py`, `test_earnings_evals.py`, … ; exclu du CI standard via `--ignore=tests/evals`).

### Sprint 138 — Traçabilité source+date étendue aux autres extracteurs
**Objectif** : appliquer le pattern source+date du Sprint 134 (posé sur `GrahamRatios`) aux autres ratios extraits — `ValuationRatios` et `EarningsQualityRatios`.
**Complexité** : Faible
**Justification** : le Sprint 134 ne couvre que `GrahamRatios` ; les ratios de valorisation et de qualité comptable restent sans horodatage de récupération, même exigence `donnees-financieres.md`. Le Sprint 135 a déjà routé ces extracteurs vers des `None` honnêtes — la source+date est la suite naturelle.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:266` `extract_earnings_quality()` et `:404` `extract_valuation()` ; constante `RATIOS_SOURCE` (`yahoo_finance.py:130`) + champs `ratios_fetched_at`/`ratios_source` déjà posés au Sprint 134 sur `GrahamRatios` (`graham_analysis/schemas.py:34-41`). À CRÉER — réutiliser la constante/champs sur ces deux chemins + leurs schemas (`stock_valuation`/`earnings_quality`)/types/affichages.

### Sprint 139 — Affichage de la traçabilité sur l'analyse persistée (AnalysisResult)
**Objectif** : rendre la source+date visible aussi sur l'analyse rendue (pas seulement le formulaire d'entrée et le PDF), en threadant `GrahamRatios` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne
**Justification** : au Sprint 134, l'affichage UI a été posé dans `AnalyzeForm` (où vivent les ratios d'entrée) car `AnalyzeResponse` ne porte pas les ratios ; le dossier persisté n'expose la traçabilité que via le PDF. La rendre visible sur `AnalysisResult` demande un threading backend assumé.
**Référence** : EXISTANT (vérifié cette session) — `app/orchestrator/core.py:237` `class AnalyzeResponse` (sans champ `ratios`) ; `frontend/src/types/index.ts:440` `interface AnalyzeResponse` (idem). À CRÉER — champ `ratios` sur `AnalyzeResponse` (backend + reconstruction au reload depuis DB/cache + type TS) puis affichage sous la carte Graham.

### Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`)
**Objectif** : capitaliser sur la `clé_retenue` que `_resolve_ratio` (Sprint 135) retourne déjà mais qui est aujourd'hui ignorée (`_`) : exposer, par ratio replié, quelle source yfinance a effectivement fourni la valeur (provenance fine au-delà du `logger.info`).
**Complexité** : Moyenne
**Justification** : le Sprint 135 a posé l'abstraction mais n'expose la provenance que dans les logs ; un champ de provenance par ratio rendrait l'analyse pleinement auditable côté API/UI. Pertinent seulement une fois que des replis multi-clés réels existent (aujourd'hui les appelants passent zéro clé de repli).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py` `_resolve_ratio(...)` retourne `(valeur | None, clé_retenue)` ; les 3 appels dans `extract()` ignorent la clé (`pb, _ = …`). À CRÉER — un véhicule de provenance (champ schema ou structure dédiée) + propagation type TS/UI ; définir d'abord des clés de repli réelles (sinon la provenance = toujours la clé primaire).

### Sprint 141 — Calculs déterministes : signaux détaillés F-Score / C-Score
**Objectif** : rendre déterministes (calcul Python + substitution post-parse) les signaux détaillés du F-Score (`criteria[].passe`) et du C-Score (`signaux[].present`), aujourd'hui encore interprétés par le LLM.
**Complexité** : Moyenne
**Justification** : limite connue documentée au Sprint 131 — seuls les *scores agrégés* F/C sont déterministes (Sprint 128) ; les signaux individuels restent produits par le LLM, dernière poche de non-déterminisme dans `earnings_quality`.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/earnings_quality/schemas.py:102` (`ZScoreDetail`) voisine des structures F/C-Score ; pattern de substitution `_injecter_scores` dans `app/skills/tier2/earnings_quality/skill.py` (Sprint 128/131). À CRÉER — fonctions pures par signal dans `app/services/financial_calculations.py` + extension de `_injecter_scores`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.22.0) et .claude/rules/conventions-frontend.md avant de commencer.
Sprint actif : 136 — Afficher les termes X1-X5 du Z-Score dans l'UI (auditabilité, parité avec le M-Score).
Backend déjà prêt depuis Sprint 131 (ZScoreDetail.x1-x5 dans earnings_quality/schemas.py:106-110, persistés).
À faire (frontend pur) : (1) ajouter x1-x5: number | null à l'interface ZScoreDetail (types/index.ts:114) ;
(2) dans ZScoreCard (EarningsQualitySection.tsx:139) rendre une grille X1-X5 filtrée sur value !== null,
en clonant le pattern de grille de MScoreCard (:106-134) — rien si tous None (cas banque). Zéro any.
Tests composant : X1-X5 rendus quand renseignés ; aucune grille mais score+interprétation présents quand tous null.
typecheck + lint + vitest ; pytest backend inchangé (non-régression). evals non concernées (affichage pur).
```
