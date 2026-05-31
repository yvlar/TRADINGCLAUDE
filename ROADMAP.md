# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-31 — Sprint 140 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.26.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 141 — Propagation frontend de la provenance par ratio (type TS + tooltip) |
| **Dernier sprint complété** | Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`) ✅ |

> **Sprint 137 exécuté (2026-05-31, evals Claude réelles)** — clé API temporaire fournie en session. `stock_valuation` (Sonnet, golden 5 cas) : **15 passed / 5 skipped / 0 failed** (8m50s) — la **substitution DCF déterministe (Sprint 132) survit à l'aller-retour tool-use réel** (valeur DCF + matrice = ossature Python), gate sectoriel financières/REIT correct. `earnings_quality` (Haiku, golden 20 cas) : **81 passed / 10 failed / 10 skipped** (33m45s) — **tous les scores déterministes M/Z/F/C/Sloan passent** (Sprints 128/131) et la concordance verdict globale ≥ 80 % tient ; les 10 échecs portent **uniquement sur des champs narratifs libres du LLM**, pas sur les calculs (voir « Drift earnings_quality » ci-dessous). Aucun lien avec le Sprint 140 (extraction tier1 uniquement).

> **Drift `earnings_quality` (à calibrer — sprint dédié)** — 8 échecs `drapeaux_rouges_cardinalite` (le modèle dépasse le `max` du golden : ex. MRO 7 vs max 2 ; cas 002/003/004/006/007/009/010/020) + 2 échecs `verdict_dans_valeurs_attendues` (005 KO, 020 MRO). Cause racine identifiée : **contrat sous-spécifié** — le prompt (`app/skills/tier2/earnings_quality/prompts/system.md`) n'impose **aucune borne de cardinalité** sur `drapeaux_rouges` (schéma = `list[str]` nu), alors que le golden encode une attente de sélectivité (`drapeaux_rouges_max` 1-4). Correctif = point de jugement métier (resserrer le prompt OU élargir les bornes du golden) → **Sprint de calibrage suggéré** dans `prompt-mise-a-jour-roadmap.md`. Non bloquant pour la PR Sprint 140.

> **Re-priorisation 2026-05-29** — La revue expert FinTech (`docs/revue-expert-fintech.md`) a identifié des correctifs P0 de sécurité, livrés au **Sprint 125** (complété). La suite de la file issue de la revue (déterminisme LLM, calculs déterministes, disclaimers, données multi-sources) est dans les sprints suggérés de `prompt-mise-a-jour-roadmap.md`.

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB) ; **scores financiers déterministes** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham) calculés en Python (`app/services/financial_calculations.py`) et substitués au bloc LLM — le modèle interprète, il ne produit plus les chiffres (Sprint 128) ; **sous-composantes auditables** (8 indices Beneish DSRI/GMI/… + termes X1-X5 Altman) également calculées en Python et persistées dans l'output — analyse entièrement rejouable (Sprint 131) ; **ossature DCF déterministe** (`stock_valuation`) — WACC (CMPC), valeur intrinsèque DCF par action et matrice de sensibilité WACC×g calculées en Python (`app/services/valuation_calculations.py`) et substituées au bloc LLM ; le modèle conserve comparables, sectoriel et verdict ; financières/REIT exclues du DCF (méthode sectorielle prime) (Sprint 132)
- `POST /screen` — screener multi-tickers (max 20, asyncio.gather + Semaphore) ; `ScreenEntry.analyzed_at` = date ISO de l'analyse sous-jacente (cache ou fraîche), None pour les échecs (Sprint 109)
- `DELETE /cache/{ticker}` — invalidation cache admin
- `GET /history?ticker=BNS` — historique paginé par cursor ; `?q=ACHAT` pour recherche cross-ticker (Sprint 73) ; `?tags=value,growth` filtre les analyses dont l'annotation porte TOUS les tags (`@>` sur `annotations.tags TEXT[]`, index GIN ; aussi sur `/history-paged`) (Sprint 126)
- `GET /metrics?days=30` — coûts cumulés, taux de cache, top tickers, `skills_cost` (coût USD réparti par skill) + `cache_by_workflow` (taux de cache par workflow) (Sprint 107) + `daily_cost` (coût USD total par jour, clé YYYY-MM-DD) (Sprint 112)
- `GET /metrics/skill-analyses?skill=&days=30` — drill-down : analyses ayant utilisé un skill donné sur la période (ticker / workflow / coût / date), filtre jsonb `skills_used @> [skill]`, 422 si `skill` absent (Sprint 112)
- `GET /telemetry/summary|costs|cache|latency` — métriques observabilité (Sprint 18)
- `GET /performance/{ticker}` — rendement rétrospectif par analyse (Sprint 39)
- `POST /auth/register` — inscription email/mot de passe, cookies JWT httpOnly + CSRF (Sprint Login)
- `POST /auth/login` — authentification cookie, rate limiting Redis 5/15 min (Sprint Login)
- `POST /auth/logout` — blacklist JWT jti + invalidation refresh token (Sprint Login)
- `POST /auth/refresh` — rotation refresh token avec détection de vol par famille (Sprint Login)
- `GET /auth/me` — profil utilisateur authentifié via cookie access_token (Sprint Login)
- `GET /alerts?limit=50` — historique des alertes Celery (ESG + composite + prix) (Sprint 99)
- `GET /semantic-search?q=&k=5` — recherche sémantique RAG dans `investment_knowledge` ; `rag_enabled=false` + `results=[]` si `OPENAI_API_KEY` absente (Sprint 106)
- `GET`/`PUT /preferences/screener` — préférences Screener (tri + filtres) liées au compte authentifié, table `user_preferences` (JSONB, PK `(user_id, key)`) ; 401 si non authentifié, fallback localStorage côté client (Sprint 124)
- `POST /auth/forgot-password` — token réinitialisation itsdangerous 1h (anti-énumération) (Sprint Login)
- `POST /auth/reset-password` — réinitialisation mot de passe avec token signé (Sprint Login)
- `POST /admin/keys` — créer une clé API (admin only) (Sprint 62)
- `GET /admin/keys` — lister toutes les clés (admin only) (Sprint 62)
- `DELETE /admin/keys/{id}` — révoquer une clé (admin only) (Sprint 62)
- `DELETE /history/{analysis_id}` — supprimer une analyse individuelle (admin only, 204/404/422) (Sprint 95)
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts
- **Sécurité auth durcie (Sprint 125)** — secret JWT fail-fast (`RuntimeError` au boot hors dev/test si `JWT_SECRET_KEY` absent), blacklist JTI fail-closed (panne Redis → token refusé), réponses 500 assainies (body générique + `correlation_id`, `str(exc)` jamais exposé — global handler + tous les endpoints + flux SSE), CORS durci (`CORS_ORIGINS` CSV via env, méthodes explicites)

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance (avec source + date de récupération affichées sous les ratios — Sprint 134, étendues aux ratios Qualité bénéfices auto-remplis — Sprint 138 ; ratio absent de la source = `None` honnête, jamais `0.0` trompeur — Sprint 135), streaming SSE skill par skill, badge « score depuis cache <24h » ; **source + date des ratios Graham aussi affichées sous la carte Graham de l'analyse rendue/rechargée** (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, threadées jusqu'à la réponse et reconstruites depuis l'historique — Sprint 139)
- **Screener** — batch 2-20 tickers, tri + filtres composite **persistés côté serveur** (continuité multi-appareils, fallback localStorage hors-ligne — Sprint 124) + colonne fraîcheur (badge frais/périmé >24h) + export CSV filtré
- **History** — historique par ticker, recherche full-text `q` cross-ticker (index GIN pg_trgm), filtre par plage de dates, suppression par analyse
- **Watchlist** — positions surveillées, analyses manuelles, seuils ESG + prix éditables inline, score composite historique, export Excel
- **Dashboard v2** — métriques live WebSocket + section détaillée (top tickers, coût par skill avec drill-down, cache par workflow, alertes/jour, tendance coût quotidien), grille responsive 12 colonnes, eval drift
- **Comparer** — 2-5 tickers multi-skills côte à côte (historique ou analyse live opt-in, streaming SSE)
- **ESG** `/esg` — scores ESG de la watchlist (tableau triable, badges ESG_FORT/MODERE/FAIBLE)
- **Alertes** `/alerts` — tableau des alertes Celery récentes
- **Recherche** `/recherche` — recherche sémantique RAG en langage naturel
- **Admin** — gestion des clés API (créer/lister/révoquer)
- **Auth** — pages register / forgot-password / reset-password, session restaurée au montage (authMe)
- **Rapports PDF** — par ticker (ou analyse précise `analysis_id`), screener, watchlist, mensuel (section ESG) ; **bloc d'avertissement réglementaire** (« recherche éducative — pas un conseil financier ») inséré dans chaque rapport (Sprint 129)
- **Avertissement de conformité** — composant `Disclaimer` (variantes `inline`/`footer`) affiché sous les résultats d'analyse, sous le tableau du Screener et sous la comparaison de tickers (Sprint 133), et en pied de page global ; texte centralisé (constante TS + constante Python) (Sprint 129)
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants React structurés et typés depuis les schemas Pydantic (plus aucun JSON brut ; `SkillSection` générique retiré) — Sprints 118-121 ; la carte Z-Score (Earnings Quality) affiche désormais ses termes auditables X1-X5 en grille, en parité avec les 8 indices du M-Score (Sprint 136)

#### Outillage & corpus
- `.claude/rules/` — 16 règles path-scoped (CLAUDE.md allégé) ; `docs/cheatsheet.md` — commandes opérationnelles ; `.gitignore` durci
- `.claude/skills/` — 16/16 skills tier2 documentés (SKILL.md + references) → corpus RAG `investment_knowledge` complet

### Skills opérationnels
18 skills en production (16 tier2 + 2 tier1). Catalogue détaillé (code API → chemin de code) : `.claude/rules/base-connaissances-skills.md` et `CLAUDE.md`.

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Sprint 140 — Exposition par ratio de la source de repli (`_resolve_ratio`) ✅

**Objectif :** `_resolve_ratio` (`yahoo_finance.py:87`) retournait déjà la `clé_retenue` (clé primaire ou clé de repli effective) mais les appelants la **jetaient** (`raw_de, _ = …`). Capitaliser sur cette provenance : exposer, pour chaque ratio Graham susceptible de repli (`pb`, `debt_equity`, `book_value`), **quelle clé yfinance a effectivement fourni la valeur** — provenance vérifiable plutôt que seulement loggée. Suite de la file revue expert FinTech. **Sprint backend seul** (frontend reporté au Sprint 141).

**Livrables :**
- `app/skills/tier1/yahoo_finance.py` — `extract()` capture la `clé_retenue` (au lieu de `_`) et passe ≥ 1 clé de repli par ratio (`debtToEquity`←`debtToEquityRatio`, `priceToBook`←`priceToBookRatio`, `bookValue`←`bookValuePerShare`) ; construit `ratios_provenance: dict[str, str] | None` (nom de ratio → clé yfinance effective, `None` si aucun ratio résolu). **Honnêteté documentée** : ces clés de repli sont des variantes de nommage rarement exposées par yfinance actuel ; la valeur livrée est le **mécanisme de provenance vérifiable** (qui confirme la clé primaire et diverge si un repli réel se produit), pas le repli lui-même
- `app/skills/tier2/graham_analysis/schemas.py` — `GrahamRatios` gagne `ratios_provenance: dict[str, str] | None = None` (optionnel → rétrocompatible avec les analyses persistées et la saisie manuelle)
- `app/services/analysis_cache.py` — `ratios_provenance` ajouté à l'`exclude` de `_cache_key` (comme `ratios_fetched_at`/`ratios_source` au Sprint 134) : la provenance ne change pas l'identité financière, sinon le cache ne hit jamais
- **Décision de périmètre** : limité aux 3 ratios Graham passant par `_resolve_ratio`. `pe` (repli calculé `price/eps`) et `eps_growth` (repli `_resolve_eps_growth`) hors périmètre. Propagation TS + tooltip UI reportées au Sprint 141 (le payload `/extract` transporte déjà le champ ; l'interface TS ignore la clé inconnue → aucune régression frontend)
- Tests : extracteur (provenance = clés primaires ; repli simulé → clés de repli effectives ; aucun ratio résolu → `None`), schema (`ratios_provenance` défaut `None` + accepte un dict), cache (deux `GrahamRatios` ne différant que par la provenance → même `_cache_key`)

**Version** : 10.26.0
**Tests** : `ruff All checks passed` ; `tests/skills/test_yahoo_finance.py` + `tests/services/test_analysis_cache.py` verts avec les edits (61 passés mesurés avant ajout des tests provenance). Compteur backend complet et suite Vitest/tsc/ESLint **à confirmer en local** (canal d'exécution de la session web dégradé — flush sporadique ; sprint backend seul, aucun changement frontend)

**Note d'environnement :** session web — extraction tier1 = données brutes, **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. Réconciliation carte↔code : prémisses du chemin critique vérifiées par `grep`/lecture avant implémentation (`_resolve_ratio` retourne `(valeur, clé)` `yahoo_finance.py:87` ; appelants jetaient la clé `:257/:261/:262` ; `GrahamRatios` `graham_analysis/schemas.py:14` ; exclusion cache `analysis_cache.py:72`). Stack Docker non démarrée → extraction yfinance sur mocks. Pas de test navigateur live. **Revue indépendante à contexte frais non exécutée** (canal dégradé) — à compléter en local avant merge.

### Sprint 139 — Affichage de la traçabilité sur l'analyse rendue (AnalysisResult) ✅

**Objectif :** La traçabilité source+date des ratios (Sprints 134/138) n'était visible que sur le **formulaire d'entrée** (`AnalyzeForm`, après auto-fill) et dans le PDF — pas sur le **dossier d'analyse rendu/rechargé** (`AnalysisResult`), car `AnalyzeResponse` ne portait pas les ratios d'entrée. Une fois l'analyse lancée (event SSE `complete`) ou rechargée depuis l'historique, la source+date disparaissait. Threader la traçabilité Graham jusqu'à `AnalyzeResponse` puis l'afficher sous la carte Graham. Suite de la file revue expert FinTech.

**Livrables :**
- `app/orchestrator/core.py` — `AnalyzeResponse` gagne `ratios_fetched_at: str | None = None` et `ratios_source: str | None = None` (optionnels → rétrocompatibles avec les analyses persistées). **Choix de type : `str` ISO** (cohérent avec `created_at: str` déjà présent) plutôt que `datetime` — élimine tout hazard de sérialisation `json.dumps`-sur-`datetime` sur les chemins SSE/cache/persistance. Helper `_graham_ratios_trace(ratios) -> (date ISO | None, source | None)` centralisant la conversion `.isoformat()`, câblé aux 4 sites de construction (2 builds principaux sync/stream + 2 courts-circuits cache composite)
- **Reconstruction depuis l'historique** : `app/api/endpoints/report.py` (la requête `get_report` sélectionne désormais `input_data` ; nouveau `_reconstruct_ratios_trace` parse `GrahamRatios` depuis le JSONB de façon défensive : None/vide/illisible → `(None, None)`) et `app/api/endpoints/ticker_report.py` (réutilise `_extract_ratios` existant + `_graham_ratios_trace`). Les hits cache Redis transportent le champ automatiquement (round-trip `model_dump_json`/`model_validate_json`)
- `frontend/src/types/index.ts` — `interface AnalyzeResponse` gagne `ratios_fetched_at?`/`ratios_source?` (`string | null`, zéro `any`)
- `frontend/src/components/AnalysisResult.tsx` — affiche « Source : … · récupéré le AAAA-MM-JJ » sous la carte Graham (`data-testid="result-ratios-source"`, `.slice(0,10)`), rien si `None` — clone du pattern `AnalyzeForm`
- **Décision de périmètre** : limité à la traçabilité **Graham** (cohérent avec l'affichage existant). Earnings/valuation hors périmètre de ce sprint (PDF : Sprint 142)
- Tests : schema (`AnalyzeResponse` accepte les champs + défaut `None`), helper `_graham_ratios_trace` (None/datetime/sans horodatage), reconstruction `report.py` et `ticker_report.py` (input_data avec/sans horodatage + `input_data` illisible → `None` sans crash), composant `AnalysisResult` (source+date affichées si présentes, rien sinon)

**Version** : 10.25.0
**Tests** : 1 646 backend collectés (1 642 passés, 3 skipped, 1 xfailed — +11) ; 425 Vitest verts (+2) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — sprint de threading/affichage, **aucun prompt de skill ni l'orchestrateur (logique de routing) modifié → evals non concernées**. `node_modules` frontend installé à l'amorçage (`npm install`). Réconciliation carte↔code : prémisses du chemin critique vérifiées par `grep`/lecture avant implémentation (`AnalyzeResponse` sans champ ratios `core.py:237`, `AnalyzeRequest.ratios` `core.py:213`, `GrahamRatios.ratios_fetched_at/source` `graham_analysis/schemas.py:34-41`, `interface AnalyzeResponse` `types/index.ts:449`, clé de cache excluant déjà les champs trace `analysis_cache.py:72`). **Revue indépendante à contexte frais (sous-agent `/code-review` high, distinct de la session auteur)** : aucun bug HIGH/MED ; 1 finding LOW (le `json.loads` non gardé de `_extract_ratios` dans `ticker_report.py`, pré-existant mais désormais sur un chemin de rechargement) **corrigé** (try/except symétrique au chemin report.py + test de régression `test_input_data_corrompu_ne_fait_pas_crasher`). Passe qualité : helper déjà DRY ; asymétrie report.py self-contained vs ticker_report réutilisant `_extract_ratios` **écartée** (intentionnelle — un import inter-endpoints serait pire). Stack Docker non démarrée. Pas de test navigateur live.

### Sprint 138 — Traçabilité source+date étendue (ValuationRatios + EarningsQualityRatios) ✅

**Objectif :** Le Sprint 134 n'avait posé la traçabilité source+date (`donnees-financieres.md` : « une donnée sans date est inutilisable ») que sur `GrahamRatios`. Les ratios de valorisation (`ValuationRatios`) et de qualité comptable (`EarningsQualityRatios`) extraits de Yahoo Finance restaient sans horodatage de récupération. Étendre le pattern à ces deux schemas + leurs extracteurs tier1, et l'exposer côté frontend (type + affichage earnings). Suite de la file revue expert FinTech.

**Livrables :**
- `app/skills/tier2/stock_valuation/schemas.py` + `app/skills/tier2/earnings_quality/schemas.py` — `ValuationRatios` et `EarningsQualityRatios` gagnent `ratios_fetched_at: datetime | None = None` et `ratios_source: str | None = None` (défaut `None` → rétrocompatible avec les analyses persistées avant ce champ ; miroir exact des champs posés sur `GrahamRatios` au Sprint 134)
- `app/skills/tier1/yahoo_finance.py` — `extract_valuation()` et `extract_earnings_quality()` posent `ratios_fetched_at=datetime.now(timezone.utc)` + `ratios_source=RATIOS_SOURCE` (constante module réutilisée, jamais un littéral dispersé)
- `frontend/src/types/index.ts` — `interface EarningsQualityRatios` gagne `ratios_fetched_at?`/`ratios_source?` (optionnels, miroir du payload `/extract`). `ValuationRatios` n'a pas d'interface TS (non exposé au frontend) → aucun changement TS de ce côté
- `frontend/src/components/AnalyzeForm.tsx` — le badge « ✓ chargé (Yahoo Finance) » des ratios earnings affiche désormais la date quand présente (« ✓ chargé (Yahoo Finance · AAAA-MM-JJ) ») via `earningsSourceLabel` ; reste « (Yahoo Finance) » sans horodatage (`data-testid="earnings-source"`)
- **Décision de sérialisation (confirmée par la revue)** : contrairement au Sprint 134, aucun risque de crash `json.dumps`-sur-`datetime` — ni `_persist`/`_cache_key` (qui ne touchent que `GrahamRatios`) ni les skills (`model_dump_json`, datetime-safe) ne sérialisent ces deux types via un `json.dumps(model_dump())` brut
- Tests : extracteurs (`extract_valuation`/`extract_earnings_quality` horodatent UTC + posent la source), schemas (champs `None` par défaut + ISO acceptée, rétrocompat), composant `AnalyzeForm` (source+date earnings affichées après auto-fill)

**Version** : 10.24.0
**Tests** : 1 635 backend collectés (1 631 passés, 3 skipped, 1 xfailed — +6) ; 425 Vitest verts (+1) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — extraction tier1 = données brutes, **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. `node_modules` frontend installé à l'amorçage (`npm install`). Réconciliation carte↔code : prémisses du chemin critique (`RATIOS_SOURCE` `yahoo_finance.py:164`, `extract_earnings_quality` `:303`, `extract_valuation` `:441`, champs Sprint 134 `graham_analysis/schemas.py:34-41`) vérifiées par `grep`/lecture avant implémentation. **Revue indépendante à contexte frais (sous-agent `/code-review` high, distinct de la session auteur) : 1 bug HIGH détecté et corrigé** — l'ajout des champs `ratios_fetched_at?`/`ratios_source?` à l'interface TS `EarningsQualityRatios` (`types/index.ts`) n'avait pas été persisté (édition perdue, masquée par Vitest qui transpile sans typecheck → `tsc` rouge en CI) ; champs ré-ajoutés. Même incident corrigé sur `docs/roadmap-archive.md` (bloc Sprint 133 réinséré). Sérialisation vérifiée : **aucun `json.dumps(model_dump())` brut** sur `ValuationRatios`/`EarningsQualityRatios` (`model_dump_json` datetime-safe dans les skills ; `_cache_key`/`_persist` ne touchent que `GrahamRatios` via `mode="json"`) → contrairement au Sprint 134, pas de hazard `datetime`. 2 limites connues : `extract_valuation` sans appelant câblé aujourd'hui ; earnings/valuation non encore propagés au PDF / à l'analyse persistée (reportés Sprints 139/142). Qualité : extraction d'un mixin partagé des 2 champs **écartée** — parité intentionnelle (comme Graham). Stack Docker non démarrée. Pas de test navigateur live.

### Sprint 136 — UI : sous-composantes auditables X1-X5 du Z-Score ✅

**Objectif :** Les termes X1-X5 du Z-Score d'Altman sont calculés en Python et persistés depuis le Sprint 131, mais l'UI ne les affichait pas — alors que la carte M-Score rendait déjà ses 8 indices Beneish en grille. Asymétrie d'auditabilité côté frontend. Combler l'écart : déclarer `x1`-`x5` dans le type TS `ZScoreDetail` puis les rendre dans `ZScoreCard` en clonant le pattern de grille de `MScoreCard`. Sprint frontend pur — aucun backend, aucune migration, aucun prompt de skill.

**Livrables :**
- `frontend/src/types/index.ts` — `interface ZScoreDetail` gagne `x1`-`x5: number | null` (snake_case, miroir du payload backend `earnings_quality/schemas.py:106-110` ; zéro `any`). Aucun autre littéral `ZScoreDetail` dans le frontend (seul la fixture de test construit l'objet) → l'élargissement en champs requis ne casse aucun typecheck
- `frontend/src/components/EarningsQualitySection.tsx` — `ZScoreCard` construit un tableau `{label, titre, value}[]` (X1 = fonds de roulement/actif total, …, X5 = ventes/actif total) filtré sur `value !== null` et le rend en grille `grid-cols-2` (`.toFixed(3)`), clone du pattern `MScoreCard`. `data-testid="zscore-termes"` + `title` par terme (libellé complet en survol) pour l'auditabilité. Si tous les termes sont `None` (banque/`is_financial`) → aucune grille, exactement comme `MScoreCard` ; score Z + variante + interprétation inchangés
- Zéro régression : `MScoreCard`, `FScoreCard`, `CScoreCard`, `SloanCard` non touchés
- Tests : composant (`EarningsQualitySection.test.tsx`) — X1-X5 renseignés → grille rendue avec les 5 labels + valeurs concrètes (`0.215`, `1.874`) ; X1-X5 tous `null` (banque) → aucune grille mais `zscore-value` (3.15) + interprétation toujours présents (cas dégradé)

**Version** : 10.23.0
**Tests** : 1 614 backend collectés (inchangé — sprint frontend pur, non-régression : 1 610 passés, 3 skipped, 1 xfailed) ; 422 Vitest verts (+2) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — sprint d'affichage pur, **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. `node_modules` frontend absent à l'amorçage → `npm install`. Réconciliation carte↔code : les 4 prémisses du chemin critique (backend `x1`-`x5` en `schemas.py:106-110`, type TS `ZScoreDetail` sans termes en `index.ts:114`, `ZScoreCard` sans grille en `EarningsQualitySection.tsx:139`, pattern `MScoreCard:106-134`) vérifiées par `grep`/lecture avant implémentation. Revue indépendante à contexte frais (correctness high + qualité, 2 sous-agents distincts de la session auteur) : **aucun bug de correctness** ; seul point qualité (extraire un helper `RatioGrid` partagé M-Score/Z-Score) **écarté** — l'extraction toucherait `MScoreCard` que la spec impose de laisser intact (zéro-régression), et c'est un clone intentionnel à 2 sites avec divergences (`title`/`testid`). Stack Docker non démarrée. Pas de test navigateur live.

---

## Sprints antérieurs (Sprint 121 → Sprint 0)

L'historique détaillé des sprints complétés est archivé dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) — il n'est **pas** lu à
l'amorçage d'un sprint, afin de réduire le coût en tokens. Seuls les ~4 derniers
sprints restent ici (section « Phases complétées » ci-dessus).

---

## Décisions d'architecture

Les décisions structurantes (choix d'embedding, Tool Use, multi-model routing,
streaming SSE, scoring composite, etc.) sont documentées au fil des sprints dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) et dans `.claude/rules/`
(`api-architecture.md`, `api-orchestrator.md`).

---

## Règles de mise à jour de ce fichier

1. **Après chaque sprint** : passer le sprint de 🔜 → ✅, mettre à jour le tableau
   « État courant » (Version, Sprint actif, Dernier sprint complété) et ajouter un
   bloc détaillé en tête de « Phases complétées ».
2. **Rotation vers l'archive** : ne garder ici que les **~4 derniers sprints** en
   détail. Déplacer les blocs plus anciens vers `docs/roadmap-archive.md`. Ce
   fichier doit rester court (cible < 200 lignes) — c'est lui qui est lu à chaque
   amorçage de session.
3. **Pas de doublon** : un sprint n'apparaît qu'une seule fois. Ne jamais recopier
   l'historique de mémoire — **déplacer**, pas réécrire.
4. **Chiffres de tests vérifiables** : les compteurs (« N CI verts », « N Vitest »)
   doivent provenir d'une commande réelle, pas d'une estimation
   (voir `.claude/rules/workflow-sprint.md`).
5. **Version** : semver — incrément mineur (`X.Y.0`) par sprint livré, patch
   (`X.Y.Z`) pour un correctif isolé.

---

*Roadmap mise à jour le 2026-05-28 — historique complet dans `docs/roadmap-archive.md`.*
