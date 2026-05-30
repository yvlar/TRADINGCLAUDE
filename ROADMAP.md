# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-30 — Sprint 132 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.19.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 133 — Disclaimer : couverture des surfaces restantes (Screener, Comparer) |
| **Dernier sprint complété** | Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation) ✅ |

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
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance, streaming SSE skill par skill, badge « score depuis cache <24h »
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
- **Avertissement de conformité** — composant `Disclaimer` (variantes `inline`/`footer`) affiché sous les résultats d'analyse et en pied de page global ; texte centralisé (constante TS + constante Python) (Sprint 129)
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants React structurés et typés depuis les schemas Pydantic (plus aucun JSON brut ; `SkillSection` générique retiré) — Sprints 118-121

#### Outillage & corpus
- `.claude/rules/` — 16 règles path-scoped (CLAUDE.md allégé) ; `docs/cheatsheet.md` — commandes opérationnelles ; `.gitignore` durci
- `.claude/skills/` — 16/16 skills tier2 documentés (SKILL.md + references) → corpus RAG `investment_knowledge` complet

### Skills opérationnels
18 skills en production (16 tier2 + 2 tier1). Catalogue détaillé (code API → chemin de code) : `.claude/rules/base-connaissances-skills.md` et `CLAUDE.md`.

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation) ✅

**Objectif :** Dernier producteur de valeurs numériques critiques par le LLM, `stock_valuation_triangulation` générait entièrement l'ossature DCF (WACC, valeur actualisée, matrice de sensibilité) — même défaut de fiabilité numérique que les scores `earnings_quality` avant Sprint 128. Rapatrier cette ossature en Python et la substituer post-parse (les valeurs Python priment), en clonant le pattern `_injecter_scores` / fonctions pures. Le LLM conserve la **narrative** (comparables, sectoriel, pondération de la fourchette, verdict), pas l'arithmétique du DCF. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §1). Sprint backend pur.

**Livrables :**
- `app/services/valuation_calculations.py` (nouveau) — module distinct de `financial_calculations.py` (cohésion : valorisation ≠ scores de fraude/faillite). Fonctions pures, typées, `float | None`, **jamais d'exception** : `capm_cost_of_equity` (Re = Rf + β×ERP), `wacc_cmpc` (CMPC), `poids_capital` (E/V, D/V depuis D/E), `dcf_value_per_share` (Gordon à deux temps : FCF actualisés + valeur terminale − dette nette ÷ actions), `dcf_sensitivity_matrix` (grille 5×5 WACC×g, chaque cellule = valeur DCF/action). Hypothèses par défaut (ERP 4.23 %, Rf 3.75 %, T 26.5 %, g 2.5 %) RECOPIÉES de `references/dcf.md`
- `app/skills/tier2/stock_valuation/skill.py` — `_dcf_depuis_ratios` (WACC central via CMPC ou `ratios.wacc`, croissance phase 1 EPS/revenus plafonnée, dette nette proxy book) + `_injecter_dcf` : écrase la valeur de la méthode `dcf` + `matrice_sensibilite` du bloc LLM par les valeurs Python ; narrative préservée. Valeurs aussi exposées au LLM dans le message. Gate sectoriel `_secteur_exclut_dcf` (fragments EN+FR : `financ`/`banq`/`assur`/`immobil`/`reit`…) → financières/REIT non substituées (méthode sectorielle prime, `references/dcf.md`)
- `app/skills/tier2/stock_valuation/prompts/system.md` — note « valeur DCF + matrice calculées en amont, reprends-les » ; financière → applique le sectoriel
- Persistance : aucune migration — `matrice_sensibilite` + valeurs DCF sont des champs Pydantic existants, sérialisés via `valuation_output.model_dump()` (`core.py:1702`), rechargés via `model_validate` (`report.py`/`ticker_report.py`)
- Tests : unitaires `test_valuation_calculations.py` (CAPM/CMPC vecteurs connus ; DCF main 122.73 ; None/div0 : WACC≤g, FCF/actions manquants, fcf<0 ; matrice 5×5 monotone WACC↓/g↑ ; None si FCF absent) ; intégration `test_stock_valuation.py` (DCF Python prime sur bloc LLM aberrant 99999 + matrice ; narrative préservée ; gate sectoriel EN+FR prouvé **avec données complètes** — anti-tautologie)

**Limites connues :** la `fourchette` composite reste la pondération du LLM (mélange DCF + comparables + sectoriel) — seuls la valeur DCF et la matrice sont déterministes. Dette nette = proxy comptable (D/E × capitaux propres book), cash excédentaire ignoré faute de donnée. WACC central (CMPC) ne coïncide pas avec une cellule exacte de la grille fixe 7-11 % mais y est correctement encadré (vérifié par double revue indépendante).

**Version** : 10.19.0
**Tests** : 1 595 backend collectés (1 591 passés, 3 skipped, 1 xfailed — +51) ; Vitest inchangé (sprint backend pur) ; ruff `All checks passed`

**Note d'environnement :** session web — le prompt `stock_valuation` est modifié (note « calculées en amont ») → **evals `stock_valuation` concernées, mais aucune clé Anthropic dans le conteneur → non lançables** (la suite `pytest` reste verte avec Claude mocké sans rien prouver sur la qualité réelle du prompt). La substitution déterministe est validée sur payloads construits (le bloc LLM injecte une valeur DCF + matrice aberrantes, les valeurs Python les écrasent). Revue indépendante à contexte frais (2 passes correctness + 1 qualité) : bug HIGH du gate sectoriel franco-centré détecté et corrigé avant commit. Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

### Sprint 131 — Auditabilité : persistance des sous-composantes déterministes ✅

**Objectif :** Le Sprint 128 a rendu déterministes les *scores agrégés* d'`earnings_quality` (Altman Z, Beneish M, Piotroski F, Montier C, Sloan), mais leurs *sous-composantes* restaient produites par le LLM — auditabilité incomplète (cf. « Limites connues » du Sprint 128). Calculer EN PYTHON les 8 indices du M-Score (DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI) et les termes X1-X5 du Z-Score, puis les substituer post-parse (comme les scores agrégés) pour qu'une analyse soit entièrement rejouable et explicable. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §1). Sprint backend pur.

**Livrables :**
- `app/services/financial_calculations.py` — deux dataclasses `BeneishComponents` (8 indices + `m_score`) et `AltmanComponents` (X1-X5 + `variante` + `z_score`) ; nouvelles fonctions pures `beneish_m_score_detail()` et `altman_z_score_detail()` exposant chaque intermédiaire (un indice/terme calculable est exposé **même si le score agrégé est `None`** — auditabilité partielle). `beneish_m_score()`/`altman_z_score()` deviennent de minces délégateurs (`.m_score`/`.z_score`) — comportement agrégé strictement préservé. `is_financial=True` → tous les intermédiaires `None`. Variante service exclut X5 ; X4 = market value (original) ou book equity (private/service)
- `app/skills/tier2/earnings_quality/schemas.py` — `ZScoreDetail` gagne `x1`-`x5` (`FiniteFloatOrNone`, **défaut `None`** : rétrocompatible avec les analyses persistées avant ce sprint, rechargées via `report.py`). `MScoreDetail` portait déjà les 8 indices (peuplés par le LLM jusqu'ici)
- `app/skills/tier2/earnings_quality/skill.py` — `_ScoresDeterministes` porte désormais les dataclasses `m`/`z` ; `_injecter_scores` substitue les 8 indices + X1-X5 via `asdict().update()` (les noms de champs des dataclasses miroitent le schéma → substitution en bloc, `interpretation` LLM préservé). Gate sectoriel `is_financial` post-parse conservé
- `app/skills/tier2/earnings_quality/prompts/system.md` — note « scores calculés en amont » étendue aux sous-composantes ; X1-X5 ajoutés à l'exemple JSON
- Persistance : aucune migration — l'output JSON (`earnings_output.model_dump()` → `analysis_history.result`, `core.py:1696`) porte déjà les `*Detail` enrichis (confirmé par `grep`)
- Tests : unitaires `test_financial_calculations.py` (indices Beneish stable = 1.0/TATA=0 ; termes Altman X1-X5 connus ; cohérence agrégé↔détail ; indice/terme partiel exposé alors que le score est `None` ; banque → tout `None`) ; intégration `test_earnings_quality.py` (indices/termes Python priment sur un bloc LLM aberrant + persistés ; financière → indices/termes annulés)

**Limites connues :** les signaux détaillés du F-Score (`criteria[].passe`) et du C-Score (`signaux[].present`) restent interprétés par le LLM (seuls leurs scores agrégés sont déterministes depuis Sprint 128) — hors périmètre nommé du sprint (indices Beneish + termes Altman). L'UI (`EarningsQualitySection.tsx`) n'affiche pas encore X1-X5 (déjà rendus pour le M-Score) — affichage = sprint futur ; les valeurs sont néanmoins persistées et auditables dans le JSON.

**Version** : 10.18.0
**Tests** : 1 544 backend collectés (1 540 passés, 3 skipped, 1 xfailed — +11) ; 414 Vitest verts (inchangé, sprint backend pur) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — le prompt `earnings_quality` est modifié (note + exemple JSON) → **evals `earnings_quality` concernées, mais aucune clé Anthropic dans le conteneur → non lançables** (vérifié : la suite `pytest` reste verte avec Claude mocké sans rien prouver sur la qualité réelle du prompt). La substitution déterministe des intermédiaires est validée sur payloads construits (le bloc LLM injecte un indice/terme aberrant, la valeur Python l'écrase). Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

### Sprint 130 — Données : honnêteté du label + repli multi-sources ✅

**Objectif :** Le champ `eps_growth_10y` annonçait « 10 ans » mais `_compute_eps_growth` calcule en réalité la croissance sur l'horizon disponible (~4 ans) ; et `yfinance` est une source unique (SPOF). Corriger le label trompeur de bout en bout, exposer l'horizon réel, et ajouter un repli quand la source primaire ne renvoie rien. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §2, §5).

**Livrables :**
- `app/skills/tier1/yahoo_finance.py` — `_compute_eps_growth` retourne désormais `(croissance_totale, horizon_ans)` où l'horizon = `len(valeurs) - 1` (N exercices annuels couvrent N-1 années de croissance — pas N, pas 10). `extract()` câble `eps_growth_total` + `eps_growth_years`. **Repli de source** : si `income_stmt` absent/vide, repli explicite et tracé (`logger.info`) sur `info.earningsGrowth` (croissance YoY, horizon 1 an) au lieu de tomber muettement à `0.0`. `ValuationRatios` (chemin `extract_valuation`) inchangé
- `app/skills/tier2/graham_analysis/schemas.py` — `GrahamRatios.eps_growth_10y` → `eps_growth_total: float` (croissance totale honnête) + nouveau `eps_growth_years: int | None` (horizon réel, `None` si inconnu) ; validateur de plausibilité (> 500 %) renommé et message corrigé
- `app/skills/tier2/graham_analysis/prompts/system.md` — toutes les références `eps_growth_10y` → `eps_growth_total` ; **correction d'un bug d'annualisation** : la formule supposait exactement 10 ans (`g = (1+x)^0.1 - 1`) → utilise désormais l'horizon réel `g = (1 + eps_growth_total)^(1/eps_growth_years) - 1` (pas d'annualisation si horizon inconnu)
- `app/services/pdf_report_service.py` — libellé honnête « Croissance BPA sur N ans » (`eps_growth_years`) ou « (horizon n.d.) » si inconnu, au lieu de « 10 ans »
- `frontend/src/types/index.ts` + `AnalyzeForm.tsx` — `GrahamRatios.eps_growth_total` + `eps_growth_years?` ; libellé du champ « Croissance EPS (totale) » (au lieu de « 10a ») + indice « sur N ans » affiché après auto-fill (`data-testid="eps-growth-horizon"`)
- `.claude/rules/variables-financieres.md` — tableau standardisé mis à jour (`eps_growth_total`/`epsGrowthTotal` + `eps_growth_years`/`epsGrowthYears`) ; note de périmètre sur les champs `eps_growth_10y` distincts d'`EsgInput`/`ValuationRatios` (hors scope)
- Tests : unitaires `_compute_eps_growth` (tuple + horizon 2/4 points + base négative + repli `info`) ; intégration `extract()` (horizon exposé, repli déclenché, absence sans repli → `0.0`/`None`) ; schema (`eps_growth_years` optionnel + renseigné) ; PDF (`_build_ratios_rows` libellé « sur N ans »/« horizon n.d. ») ; composant `AnalyzeForm` (libellé honnête + indice « sur 4 ans » après auto-fill)

**Périmètre :** `EsgInput` (`esg_simplified`) et `ValuationRatios` (`stock_valuation`) conservent un champ `eps_growth_10y` distinct (sources différentes : saisie ESG / `info.earningsGrowth` / `None`, jamais le calcul tier1 corrigé) — hors scope, documenté.

**Version** : 10.17.0
**Tests** : 1 533 backend collectés (1 529 passés, 3 skipped, 1 xfailed — +7) ; 414 Vitest verts (+2) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — le prompt `graham_analysis` est modifié (renommage + correction d'annualisation) → **evals `graham_analysis` concernées, mais aucune clé Anthropic dans le conteneur → non lançables** (la suite `pytest` reste verte avec Claude mocké sans rien prouver sur la qualité réelle du prompt). Stack Docker non démarrée → extraction yfinance exercée sur mocks (pas d'appel réseau live). Pas de test navigateur live.

### Sprint 129 — Conformité : disclaimers & avertissement de risque ✅

**Objectif :** Le système émet des verdicts d'achat/vente explicites mais sans aucun disclaimer — exposition réglementaire (AMF/SEC/MiFID). Afficher un avertissement clair « recherche éducative — pas un conseil financier » à chaque endroit où un verdict actionnable est présenté : résultats d'analyse, pied de page global, et rapports PDF. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §6). Sprint d'affichage pur — aucun prompt de skill ni orchestrateur modifié.

**Livrables :**
- `app/services/disclaimer.py` (nouveau) — source de vérité unique du texte backend : `DISCLAIMER_TITLE`/`DISCLAIMER_TEXT` + helper `build_disclaimer_flowables()` (Spacer + HRFlowable + Paragraph discret) réutilisé tel quel par les 3 services PDF
- `app/services/pdf_report_service.py` + `screener_pdf_service.py` + `watchlist_pdf_service.py` — `story.extend(build_disclaimer_flowables())` inséré avant le pied de page. `monthly_report_service.py` **non modifié** : il compose les PDF watchlist + screener qui portent désormais le disclaimer (pas de duplication)
- `frontend/src/constants/disclaimer.ts` (nouveau) — source de vérité unique du texte frontend (`DISCLAIMER_HEADING`/`DISCLAIMER_TEXT`, aligné mot pour mot sur le backend)
- `frontend/src/components/Disclaimer.tsx` (nouveau) — composant réutilisable, variantes `inline` (bandeau encadré) et `footer` (ligne discrète), `data-testid="disclaimer"`, `role="note"` ; affiché dans `AnalysisResult.tsx` (bas du bloc résultats) et dans le pied de page global de `App.tsx`
- Tests : composant `frontend/src/__tests__/Disclaimer.test.tsx` (inline + footer + défaut + présence dans `AnalysisResult`) ; backend `tests/services/test_disclaimer.py` (helper ; story du rapport ticker / screener / watchlist contient le texte via capture de `SimpleDocTemplate.build`)

**Version** : 10.16.0
**Tests** : 1 526 backend collectés (1 522 passés, 3 skipped, 1 xfailed — +4) ; 412 Vitest verts (+4) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — sprint d'affichage pur, **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. Stack Docker non démarrée → les rapports PDF sont exercés sur mocks (capture du `story` ReportLab, pas de rendu navigateur). Le `node_modules` frontend était partiel à l'amorçage → `npm install` exécuté. Pas de test navigateur live.

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
