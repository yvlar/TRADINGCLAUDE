# Sprint 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.23.0 — Sprint 136 complété)

Le Sprint 136 a comblé l'asymétrie d'auditabilité côté frontend : la carte Z-Score (Earnings Quality) affiche désormais ses termes X1-X5 en grille, en parité avec les 8 indices du M-Score (calculés en Python et persistés depuis le Sprint 131). Sprint frontend pur — type TS `ZScoreDetail` étendu + `ZScoreCard` enrichi.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.23.0, Sprint 136 ✅
3. `.claude/rules/tests-pyramide.md` — cœur du sprint : niveaux de la pyramide, **règle absolue du mock de `call_claude_with_retry`** (les evals sont l'EXCEPTION : elles appellent Claude réel et sont exclues du CI standard via `--ignore=tests/evals`)
4. `.claude/rules/base-connaissances-skills.md` — protocole de lecture des SKILL.md/references avant de juger la qualité d'un prompt de skill

---

## ⚠️ Contrainte d'environnement — bloquante pour ce sprint

Ce sprint **exige une vraie clé Anthropic** (`ANTHROPIC_API_KEY`) pour exécuter les evals contre Claude réel. **Le conteneur de session web n'en a pas** (vérifié de sprint en sprint : « aucune clé Anthropic dans le conteneur »). Conséquences :

- En session web sans clé : ce sprint **n'est pas exécutable** tel quel. Le signaler à Yves dès l'amorçage et lui proposer soit (a) exécuter ce sprint **localement** (machine avec clé), soit (b) choisir un autre sprint web-compatible parmi les suggestions ci-dessous (138, 139, 141 sont backend/frontend purs, mockés, donc exécutables en conteneur web).
- Ne **jamais** prétendre avoir « passé les evals » si la clé est absente — le dire explicitement (cf. `.claude/prompts/prompt-executer-sprint.md`, gate evals).

---

## TÂCHE — Sprint 137 : exécuter et documenter les evals des skills rendus déterministes

**Objectif** : depuis les Sprints 128/131/132, les prompts d'`earnings_quality` et `stock_valuation` ont basculé en mode « le LLM interprète des chiffres calculés en amont, il ne les produit plus ». `pytest` reste vert avec Claude mocké **sans rien prouver sur la qualité réelle du prompt** : un prompt peut se dégrader silencieusement (mauvaise interprétation, verdict incohérent avec les chiffres injectés). Ce sprint exécute les `evals` ciblées (Claude réel) de ces deux skills pour confirmer l'absence de dégradation qualitative, puis documente les résultats (drift, coût, verdicts) dans la roadmap.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Harnais d'evals EXISTANT** — `tests/evals/` contient `__init__.py`, `conftest.py`, `eval_runner.py`, `test_earnings_evals.py`, `test_graham_evals.py`, `test_buffett_evals.py`, `test_dorsey_evals.py`, `test_damodaran_evals.py`, `test_multi_model_evals.py`, `test_screener_evals.py`, `golden_screener_dataset.json`, `fixtures/`. Exclu du CI standard via `--ignore=tests/evals`.
2. **Pas d'eval `stock_valuation` dédiée aujourd'hui** — aucun `test_valuation_evals.py` dans `tests/evals/` (à CRÉER si le sprint veut couvrir `stock_valuation` ; sinon le sprint se limite à `test_earnings_evals.py` existant + une nouvelle suite valuation).
3. **Skills concernés** : `app/skills/tier2/earnings_quality/` (Sprints 128/131 — scores + sous-composantes déterministes) et `app/skills/tier2/stock_valuation/` (Sprint 132 — ossature DCF déterministe).

### Spécification

1. **Inventaire** : recenser ce que `test_earnings_evals.py` couvre déjà et identifier les cas manquants pour les prompts post-déterminisme (le LLM reçoit des scores/indices/DCF déjà calculés → vérifier que ses verdicts/interprétations restent cohérents avec ces valeurs).
2. **Exécution** (si clé présente) : lancer `.venv/bin/python -m pytest tests/evals/test_earnings_evals.py -v` (+ suite valuation si créée). Mesurer drift, coût USD, taux de réussite.
3. **Suite valuation** (optionnel mais recommandé) : créer `tests/evals/test_valuation_evals.py` sur le modèle de `test_earnings_evals.py` — golden cases vérifiant que le LLM reprend bien la valeur DCF + matrice injectées (ne les recalcule pas), narrative cohérente.
4. **Documentation** : consigner les résultats (drift/coût/verdicts) dans le bloc Sprint 137 de `ROADMAP.md` et dans la note d'environnement (honnêteté : si non exécuté faute de clé, le dire).

### Tests obligatoires (pyramide)
- Niveau **evals** (Claude réel) — l'objet même du sprint. Si une suite valuation est créée, ses golden cases sont le livrable testable.
- Non-régression : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` reste vert (les evals ne touchent pas le code de prod ; si le sprint ajoute un fichier de test, vérifier qu'il n'est pas collecté par le CI standard).
- `.venv/bin/ruff check app/ tests/`.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). **Clé Anthropic absente → evals NON lançables en web** (voir contrainte bloquante ci-dessus). `node_modules` frontend non requis (sprint backend pur). Stack Docker non démarrée. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 138 — Traçabilité source+date étendue aux autres extracteurs
**Objectif** : appliquer le pattern source+date du Sprint 134 (posé sur `GrahamRatios`) aux autres ratios extraits — `ValuationRatios` et `EarningsQualityRatios`.
**Complexité** : Faible
**Justification** : le Sprint 134 ne couvre que `GrahamRatios` ; les ratios de valorisation et de qualité comptable restent sans horodatage de récupération, même exigence `donnees-financieres.md`. Web-compatible (mockable).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:303` `extract_earnings_quality()` et `:441` `extract_valuation()` ; constante `RATIOS_SOURCE` (`yahoo_finance.py:164`) + champs `ratios_fetched_at`/`ratios_source` déjà posés au Sprint 134 sur `GrahamRatios` (`graham_analysis/schemas.py:34-41`). À CRÉER — réutiliser la constante/champs sur ces deux chemins + leurs schemas (`stock_valuation`/`earnings_quality`)/types/affichages.

### Sprint 139 — Affichage de la traçabilité sur l'analyse persistée (AnalysisResult)
**Objectif** : rendre la source+date visible aussi sur l'analyse rendue (pas seulement le formulaire d'entrée et le PDF), en threadant `GrahamRatios` jusqu'à `AnalyzeResponse`.
**Complexité** : Moyenne
**Justification** : au Sprint 134, l'affichage UI a été posé dans `AnalyzeForm` (où vivent les ratios d'entrée) car `AnalyzeResponse` ne porte pas les ratios ; le dossier persisté n'expose la traçabilité que via le PDF. La rendre visible sur `AnalysisResult` demande un threading backend assumé. Web-compatible.
**Référence** : EXISTANT (vérifié cette session) — `app/orchestrator/core.py:237` `class AnalyzeResponse` (sans champ `ratios`) ; `frontend/src/types/index.ts:446` `interface AnalyzeResponse` (idem). À CRÉER — champ `ratios` sur `AnalyzeResponse` (backend + reconstruction au reload depuis DB/cache + type TS) puis affichage sous la carte Graham.

### Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`)
**Objectif** : capitaliser sur la `clé_retenue` que `_resolve_ratio` (Sprint 135) retourne déjà mais qui est aujourd'hui ignorée (`_`) : exposer, par ratio replié, quelle source yfinance a effectivement fourni la valeur.
**Complexité** : Moyenne
**Justification** : le Sprint 135 a posé l'abstraction mais n'expose la provenance que dans les logs ; un champ de provenance par ratio rendrait l'analyse pleinement auditable côté API/UI. Pertinent seulement une fois que des replis multi-clés réels existent (aujourd'hui les appelants passent zéro clé de repli).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier1/yahoo_finance.py:87` `_resolve_ratio(...)` retourne `(valeur | None, clé_retenue)` ; les appels dans `extract()` ignorent la clé. À CRÉER — un véhicule de provenance (champ schema ou structure dédiée) + propagation type TS/UI ; définir d'abord des clés de repli réelles (sinon la provenance = toujours la clé primaire).

### Sprint 141 — Calculs déterministes : signaux détaillés F-Score / C-Score
**Objectif** : rendre déterministes (calcul Python + substitution post-parse) les signaux détaillés du F-Score (`criteria[].passe`) et du C-Score (`signaux[].present`), aujourd'hui encore interprétés par le LLM.
**Complexité** : Moyenne
**Justification** : limite connue documentée au Sprint 131 — seuls les *scores agrégés* F/C sont déterministes (Sprint 128) ; les signaux individuels restent produits par le LLM, dernière poche de non-déterminisme dans `earnings_quality`. Web-compatible (mockable).
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/earnings_quality/schemas.py:120` (`FScoreCriterion`), `:132` (`CScoreSignal`) ; pattern de substitution `_injecter_scores` à `app/skills/tier2/earnings_quality/skill.py:152` (Sprint 128/131). À CRÉER — fonctions pures par signal dans `app/services/financial_calculations.py` + extension de `_injecter_scores`.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.23.0), .claude/rules/tests-pyramide.md et base-connaissances-skills.md avant de commencer.
Sprint actif : 137 — Evals ciblées des prompts rendus déterministes (earnings_quality, stock_valuation).
⚠️ CONTRAINTE : ce sprint exige une clé Anthropic (Claude réel) ABSENTE du conteneur web → non exécutable en session web.
Si tu es en session web sans clé : signale-le à Yves AVANT d'implémenter et propose soit l'exécution locale,
soit un sprint web-compatible (138/139/141, tous mockables). Ne jamais prétendre avoir passé des evals non lancées.
Harnais existant : tests/evals/ (eval_runner.py, test_earnings_evals.py) ; pas encore de test_valuation_evals.py.
```
