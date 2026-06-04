# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-04 — Sprint 146 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.32.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 147 — Interprétation déterministe Sloan (dernier cadre LLM) |
| **Dernier sprint complété** | Sprint 146 — Affichage earnings/valuation source+date sur l'analyse rendue (AnalysisResult) ✅ |

> **Sprint 137 exécuté (2026-05-31, evals Claude réelles)** — clé API temporaire fournie en session. `stock_valuation` (Sonnet, golden 5 cas) : **15 passed / 5 skipped / 0 failed** (8m50s) — la **substitution DCF déterministe (Sprint 132) survit à l'aller-retour tool-use réel** (valeur DCF + matrice = ossature Python), gate sectoriel financières/REIT correct. `earnings_quality` (Haiku, golden 20 cas) : **81 passed / 10 failed / 10 skipped** (33m45s) — **tous les scores déterministes M/Z/F/C/Sloan passent** (Sprints 128/131) et la concordance verdict globale ≥ 80 % tient ; les 10 échecs portent **uniquement sur des champs narratifs libres du LLM**, pas sur les calculs (voir « Drift earnings_quality » ci-dessous). Aucun lien avec le Sprint 140 (extraction tier1 uniquement).

> **Drift `earnings_quality` (à calibrer — sprint dédié)** — 8 échecs `drapeaux_rouges_cardinalite` (le modèle dépasse le `max` du golden : ex. MRO 7 vs max 2 ; cas 002/003/004/006/007/009/010/020) + 2 échecs `verdict_dans_valeurs_attendues` (005 KO, 020 MRO). Cause racine identifiée : **contrat sous-spécifié** — le prompt (`app/skills/tier2/earnings_quality/prompts/system.md`) n'impose **aucune borne de cardinalité** sur `drapeaux_rouges` (schéma = `list[str]` nu), alors que le golden encode une attente de sélectivité (`drapeaux_rouges_max` 1-4). Correctif = point de jugement métier (resserrer le prompt OU élargir les bornes du golden) → **Sprint de calibrage suggéré** dans `prompt-mise-a-jour-roadmap.md`. Non bloquant pour la PR Sprint 140.

> **Re-priorisation 2026-05-29** — La revue expert FinTech (`docs/revue-expert-fintech.md`) a identifié des correctifs P0 de sécurité, livrés au **Sprint 125** (complété). La suite de la file issue de la revue (déterminisme LLM, calculs déterministes, disclaimers, données multi-sources) est dans les sprints suggérés de `prompt-mise-a-jour-roadmap.md`.

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB) ; **scores financiers déterministes** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham) calculés en Python (`app/services/financial_calculations.py`) et substitués au bloc LLM — le modèle interprète, il ne produit plus les chiffres (Sprint 128) ; **sous-composantes auditables** (8 indices Beneish DSRI/GMI/… + termes X1-X5 Altman ; **+ critères détaillés F-Score (9 Piotroski) et signaux C-Score (6 Montier) — booléen `passe`/`present` par signal, Sprint 142** ; **+ libellés d'interprétation au niveau cadre F-Score / C-Score (`forte_qualite`/…/`value_trap` ; `propre`/`signaux_mineurs`/`signaux_multiples`) dérivés du score agrégé déterministe et substitués post-parse — parité avec M/Z déjà déterministes, Sprint 143**) également calculées en Python et persistées dans l'output — `sum(passe) == f_score` / `sum(present) == c_score` par construction, analyse entièrement rejouable (Sprint 131) ; **ossature DCF déterministe** (`stock_valuation`) — WACC (CMPC), valeur intrinsèque DCF par action et matrice de sensibilité WACC×g calculées en Python (`app/services/valuation_calculations.py`) et substituées au bloc LLM ; le modèle conserve comparables, sectoriel et verdict ; financières/REIT exclues du DCF (méthode sectorielle prime) (Sprint 132)
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
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible) ; **bloc « Sources des ratios complémentaires »** rendu via `_fmt_ratios_source` quand les ratios earnings/valuation reconstruits (Sprint 144) portent une source+date, ligne omise sinon — parité Graham (Sprint 145)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts
- **Sécurité auth durcie (Sprint 125)** — secret JWT fail-fast (`RuntimeError` au boot hors dev/test si `JWT_SECRET_KEY` absent), blacklist JTI fail-closed (panne Redis → token refusé), réponses 500 assainies (body générique + `correlation_id`, `str(exc)` jamais exposé — global handler + tous les endpoints + flux SSE), CORS durci (`CORS_ORIGINS` CSV via env, méthodes explicites)

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance (avec source + date de récupération affichées sous les ratios — Sprint 134, étendues aux ratios Qualité bénéfices auto-remplis — Sprint 138 ; ratio absent de la source = `None` honnête, jamais `0.0` trompeur — Sprint 135), streaming SSE skill par skill, badge « score depuis cache <24h » ; **source + date des ratios Graham aussi affichées sous la carte Graham de l'analyse rendue/rechargée** (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, threadées jusqu'à la réponse et reconstruites depuis l'historique — Sprint 139 ; **étendues aux cartes Qualité bénéfices et Valorisation** via quatre champs miroir `earnings_ratios_*`/`valuation_ratios_*`, threadés aux 4 sites de construction de `AnalyzeResponse` + reconstruction historique, `data-testid` `earnings-ratios-source`/`valuation-ratios-source` — Sprint 146) ; **provenance par ratio en signal-only** sous la carte Graham après auto-fill — badge discret « P/B via `clé` (repli) » uniquement quand la clé yfinance effective diffère de la clé primaire attendue (`ratios_provenance`, Sprint 141)
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

### Sprint 146 — Affichage earnings/valuation source+date sur l'analyse rendue (AnalysisResult) ✅

**Objectif :** Parité d'affichage avec Graham. La source+date des ratios Graham d'entrée est threadée jusqu'à `AnalyzeResponse` (`ratios_fetched_at`/`ratios_source`) et affichée sous la carte Graham de l'analyse rendue/rechargée (Sprint 139) ; earnings/valuation ne l'étaient pas. Threader la source+date earnings/valuation jusqu'à `AnalyzeResponse` (analyse live **et** reconstruction historique) et l'afficher sous leurs cartes respectives sur `AnalysisResult`. **Sprint backend (threading) + frontend (affichage)** — aucun prompt de skill, aucune migration.

**Livrables :**
- `app/orchestrator/core.py` — helpers `_earnings_ratios_trace`/`_valuation_ratios_trace` (`:308`/`:318`), clones exacts de `_graham_ratios_trace` (`(ratios.ratios_fetched_at.isoformat() if … else None, ratios.ratios_source)`, `(None, None)` si ratio `None`). Quatre champs `str | None` additifs sur `AnalyzeResponse` : `earnings_ratios_fetched_at`/`earnings_ratios_source`, `valuation_ratios_fetched_at`/`valuation_ratios_source` (défaut `None` → rétrocompat). Peuplés depuis `request.earnings_ratios`/`request.valuation_ratios` aux **4 sites** de construction de `AnalyzeResponse` (cache composite sync/stream + réponse complète sync/stream — la réconciliation a révélé 4 sites là où la carte n'en citait qu'un, tous threadés pour parité).
- `app/api/endpoints/ticker_report.py` — `_reconstruct_analyze_response` peuple les quatre champs depuis `_extract_earnings_ratios(row)`/`_extract_valuation_ratios(row)` (Sprint 144), parité avec le trace Graham. None-safety : ancien `input_data` plat sans sous-clés → quatre champs `None`, pas de crash.
- `frontend/src/types/index.ts` — quatre champs miroir (snake_case, `string | null`) sur `interface AnalyzeResponse`.
- `frontend/src/components/RatiosSourceNote.tsx` — composant présentationnel partagé (gate `if (!fetchedAt) return null` — honnêteté None ; classes calquées sur la note Graham, `border-t border-border pt-3`). Rendu **dans** le `CardContent` de `EarningsQualitySection` (`data-testid="earnings-ratios-source"`) et de `ValuationSection` (`data-testid="valuation-ratios-source"`) via props `ratiosFetchedAt`/`ratiosSource` — parité visuelle stricte avec Graham (la note vit dans la carte repliable, pas orpheline dessous ; correctif issu de la revue PR). Affichage Graham (Sprint 139) inchangé.
- **Décision de périmètre** : earnings/valuation source+date sur `AnalysisResult` uniquement. Affichage Graham, PDF (Sprint 145) et schémas de skill **inchangés**.
- Tests : unitaires `core.py` (`_earnings_ratios_trace`/`_valuation_ratios_trace` : horodatage → ISO+source, ratio `None`/sans horodatage → `None`) ; intégration `ticker_report` (reconstruction des quatre champs avec sous-clés horodatées ; ligne plate ancienne → quatre `None`) ; composant `AnalysisResult` (source+date earnings/valuation affichées quand présentes, omises sinon).

**Version** : 10.32.0
**Tests** : 1 702 backend collectés (1 698 passés, 3 skipped, 1 xfailed — +8) ; `ruff All checks passed` ; 431 Vitest verts (+5) ; `tsc --noEmit` 0 erreur ; ESLint 0/0.

**Note d'environnement :** session web — **aucun prompt de skill ni la logique de routing de l'orchestrateur modifié → evals non concernées** (champs additifs sur l'enveloppe + threading + affichage ; l'output de chaque skill est inchangé). `ANTHROPIC_API_KEY` absente du conteneur web. Stack Docker non démarrée ; pas de test navigateur live ; canal d'exécution vérifié. **Réconciliation carte↔code** : prémisses du chemin critique vérifiées avant implémentation (`_graham_ratios_trace` `core.py:284`, champs `AnalyzeResponse.ratios_fetched_at`/`ratios_source`, `request.earnings_ratios`/`valuation_ratios` `core.py:220/223`, reconstructeurs `_extract_earnings_ratios`/`_extract_valuation_ratios` `ticker_report.py:240/247`, champs source+date `earnings_quality/schemas.py:69/73` + `stock_valuation/schemas.py:32/36`, affichage Graham `AnalysisResult.tsx:211-216`). **Écart vs carte** : 4 sites de peuplement du trace Graham (pas 1) — tous threadés, pas un STOP (symboles existants, simple incomplétude de la carte). Revue indépendante à contexte frais (sous-agent correctness `/code-review` high, distinct de la session auteur, nourri des critères d'acceptation) : **APPROVE — aucun bug HIGH/MED** (4 sites cohérents, noms de variables alignés sans swap earnings/valuation, None-safety reconstruction vérifiée, gate frontend carte+champ, périmètre Graham/PDF/schémas respecté ; 2 observations LOW non bloquantes). Passe qualité `/simplify` (4 axes reuse/simplification/efficacité/altitude, sous-agent dédié) : **ship as-is** — les 3 helpers `_*_ratios_trace` quasi-identiques **conservés** (spec les nomme, tests les référencent, style projet clone-pas-généralise cf. Sprint 143, périmètre interdit de toucher Graham) ; champs plats vs objet imbriqué **plats conservés** (parité avec `ratios_fetched_at`/`ratios_source` existants) ; re-parse `input_data` négligeable à l'altitude d'une reconstruction PDF.

### Sprint 145 — Affichage PDF de la source+date earnings/valuation ✅

**Objectif :** Le rapport PDF par ticker ne rendait la ligne « Source des ratios » que pour Graham (`_build_ratios_rows(r: GrahamRatios)`). Le Sprint 144 ayant rendu les ratios `EarningsQualityRatios`/`ValuationRatios` horodatés **reconstructibles** depuis `input_data` (`_extract_earnings_ratios`/`_extract_valuation_ratios`), il restait à les **câbler dans le PDF** et rendre une ligne « Source des ratios (Qualité bénéfices) » / « Source des ratios (Valorisation) » via le helper `_fmt_ratios_source` **existant**. **Sprint backend pur** (aucun frontend, migration, ni prompt de skill).

**Livrables :**
- `app/services/pdf_report_service.py` — helper `_build_ratios_source_rows(earnings_ratios, valuation_ratios) -> list[tuple[str, str]]` (`:251`), miroir de `_build_ratios_rows` : une ligne par ratio **uniquement** si le ratio est présent ET porte une source ou une date (gate `r.ratios_fetched_at is not None or r.ratios_source is not None` — parité byte-for-byte avec le gate Graham `:246`), libellé via `_fmt_ratios_source` **réutilisé** (zéro duplication de format). `generate_ticker_report` gagne `earnings_ratios`/`valuation_ratios: … | None = None` (rétrocompat) ; bloc de rendu dédié « Sources des ratios complémentaires » inséré entre la section Graham « Ratios clés » et le bloc ESG, rendu seulement si au moins une ligne existe (`if ratios_source_rows:`).
- `app/api/endpoints/ticker_report.py` — `get_ticker_report` reconstruit `earnings_ratios = _extract_earnings_ratios(row)` / `valuation_ratios = _extract_valuation_ratios(row)` sous le **même gate** `if row is not None` que `ratios` Graham (initialisés `None` avant), et les passe à `generate_ticker_report`.
- **Décision de périmètre** : affichage PDF earnings/valuation **uniquement**. Affichage Graham (`_build_ratios_rows`), threading `AnalyzeResponse` (Sprints 139/143) et reconstructeurs (Sprint 144) **inchangés**. Honnêteté None : ratio absent ou sans source/date → ligne omise (parité Graham). Rétrocompat : params défaut `None` → PDF byte-for-byte identique quand earnings/valuation absents (ancien `input_data` à plat).
- Tests : unitaires `_build_ratios_source_rows` (earnings/valuation seul, les deux, source sans date, ratio sans traçabilité omis, None → liste vide) ; **acceptation `pypdf`** (le texte du PDF rendu contient les deux lignes + la date `2026-05-30`) + omission vérifiée quand traçabilité absente ; intégration `ticker_report` (sous-clés reconstruites passées au service PDF ; ancien `input_data` sans sous-clés → earnings/valuation `None`, pas de crash).

**Version** : 10.31.0
**Tests** : 1 694 backend collectés (1 690 passés, 3 skipped, 1 xfailed — +9) ; `ruff All checks passed` ; frontend inchangé (sprint backend pur).

**Note d'environnement :** session web — **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées** (rendu PDF Python pur depuis l'output persisté). `ANTHROPIC_API_KEY` absente du conteneur web. Stack Docker non démarrée ; pas de test navigateur live ; canal d'exécution vérifié (sortie des commandes rendue). **Réconciliation carte↔code** : les 5 prémisses du chemin critique vérifiées par grep/lecture avant implémentation (reconstructeurs `ticker_report.py:234/241` non câblés ; site `ratios=_extract_ratios(row)` `:111` passé `:124` ; `_fmt_ratios_source` `pdf_report_service.py:150` ; rendu Graham `_build_ratios_rows` source `:245`/section `:327`, signature `:250` ; champs source+date `earnings_quality/schemas.py:69/73`, `stock_valuation/schemas.py:32/36`) — carte exacte, aucun STOP. Revue indépendante à contexte frais (sous-agent correctness `/code-review` high, distinct de la session auteur, nourri des critères d'acceptation) : **APPROVE — aucun bug HIGH/MED/LOW** (gate honnête-None parité Graham vérifiée ; `GrahamRatios` sans `extra='forbid'` → sous-clés `input_data` ignorées, Graham intact ; params défaut None rétrocompat ; périmètre respecté). Passe qualité `/simplify` (4 axes reuse/simplification/efficacité/altitude, sous-agent dédié) : **propre — ship as-is** ; seule idée non bloquante (centraliser le gate honnête-None dupliqué `:246`/`:261` en prédicat partagé) **écartée** — toucher `_build_ratios_rows:246` (Graham) violerait le périmètre « ne pas retoucher l'affichage Graham », et un prédicat à usage unique serait de la sur-abstraction (à mutualiser dans un futur sprint de consolidation reuse).

### Sprint 144 — Persistance reconstructible des ratios earnings/valuation (input_data) ✅

**Objectif :** Le rapport PDF par ticker n'affichait la ligne « Source des ratios » que pour Graham. L'étendre aux ratios `EarningsQualityRatios`/`ValuationRatios` exigeait d'abord de **persister** leur source+date — or la réconciliation carte↔code a révélé que la prémisse « ratios earnings/valuation reconstructibles » était **fausse** : `analysis_history.input_data` ne stockait que `request.ratios` (Graham), et les sorties de skills (`result`) n'échoent pas les ratios d'entrée (`EarningsQualityOutput` `earnings_quality/schemas.py:161` et `StockValuationOutput` `stock_valuation/schemas.py:95` n'ont aucun champ `ratios`). Le périmètre a été **re-cadré (décision Yves) en sprint de persistance pure** : threader/persister les ratios earnings/valuation horodatés de façon reconstructible, **sans changement PDF visible** (l'affichage devient le Sprint 145). **Sprint backend pur** (aucun frontend, migration, ni prompt de skill).

**Livrables :**
- `app/orchestrator/core.py` — helper `_build_input_data(request) -> str` (`:292`) substitué au `json.dumps` inline du site de persistance `_persist` (`:1734`). Graham reste sérialisé **à plat** (les deux lecteurs valident `input_data` comme `GrahamRatios` ; `extra='ignore'` par défaut ignore les sous-clés → rétrocompat des lignes antérieures, **zéro changement des consommateurs**) ; `earnings_ratios`/`valuation_ratios` persistés sous **clés dédiées** (`model_dump(mode="json")` → datetime ISO), gardés par None.
- `app/api/endpoints/ticker_report.py` — parsing factorisé `_parse_input_data(row) -> dict | None` (réutilisé par `_extract_ratios`, comportement Graham inchangé) + reconstructeurs `_extract_earnings_ratios` (`:234`) / `_extract_valuation_ratios` (`:241`) via un cœur générique typé `_extract_sub_ratios(row, key, model_cls)` (`:220`, `TypeVar` borné `BaseModel`) — **seam** pour l'affichage PDF différé, non encore câblé (intentionnel). Honnêteté None : sous-clé absente / `input_data` illisible / sous-dict malformé → `None`, jamais d'exception.
- **Décision de périmètre** : persistance + reconstruction **uniquement**. Cache **non affecté** (`_cache_key` hashe l'objet `request.ratios`, jamais `input_data` — `analysis_cache.py`). Graham (affichage + reconstruction des deux consommateurs `ticker_report`/`report.py`) **byte-for-byte inchangé**. Source+date earnings/valuation portées seulement par les schémas d'entrée (`earnings_quality/schemas.py:69/73`, `stock_valuation/schemas.py:32/36`).
- Tests : unitaires `_build_input_data` (forme persistée, None-safety, **pin rétrocompat** : `GrahamRatios.model_validate` ignore les sous-clés) ; intégration orchestrateur (input_data persisté porte les sous-clés quand la requête les fournit) ; reconstruction `ticker_report` (avec/sans horodatage, `input_data` illisible → pas de crash, sous-clé malformée → None, Graham intact malgré les sous-clés).

**Version** : 10.30.0
**Tests** : 1 680 backend collectés (1 676 passés, 3 skipped, 1 xfailed — +12) ; `ruff All checks passed` ; frontend inchangé (sprint backend pur).

**Note d'environnement :** session web — **aucun prompt de skill ni l'orchestrateur (logique de routing) modifié → evals non concernées** (persistance pure ; l'output des skills est inchangé). `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutables ici de toute façon. Stack Docker non démarrée ; pas de test navigateur live. **Réconciliation carte↔code (STOP avant implémentation)** : la prémisse « earnings/valuation persistés/reconstructibles » s'est avérée fausse (`input_data` = `request.ratios` seul `core.py:1719` pré-sprint ; sorties de skills sans champ `ratios`) → re-cadrage en persistance pure validé par Yves avant tout code. Revue indépendante à contexte frais (sous-agent correctness high, distinct de la session auteur, nourri des critères d'acceptation) : **APPROVE — aucun bug HIGH/MED/LOW** (design `extra='ignore'` vérifié à l'exécution ; edge case graham None + earnings → `GrahamRatios.model_validate` échoue sur champs requis → None, parité avec le comportement antérieur ; cache non touché ; aucun autre lecteur d'`input_data`). Passe qualité `/simplify` (4 sous-agents reuse/simplification/efficacité/altitude) : efficacité/altitude **propres** (clés dédiées = bonne profondeur vs envelope qui forcerait à toucher les deux consommateurs + détection de version) ; **collapse** des deux reconstructeurs en cœur générique typé + wrappers (simplification) **appliqué** ; partage de `_parse_input_data` avec `report.py` (reuse) **écarté** — hors périmètre (report.py non touché ; à faire au Sprint 145 qui active les reconstructeurs).

### Sprint 143 — Interprétations déterministes F-Score / C-Score (parité M-Score / Z-Score) ✅

**Objectif :** Le Sprint 142 a rendu déterministes les *signaux* F/C (`criteria[].passe`, `signaux[].present`), mais les **libellés d'interprétation au niveau cadre** — `f_score.interpretation` et `c_score.interpretation` — restaient **produits par le LLM**, alors que les interprétations M/Z étaient déjà déterministes (Python, Sprint 131). Compléter la parité : dériver l'interprétation F/C du **score agrégé déjà déterministe** selon les seuils des références, et la substituer post-parse — même remède qui a éliminé la dérive de vocabulaire des golden M/Z. **Sprint backend pur** (frontend rend déjà le libellé verbatim, aucun changement requis).

**Livrables :**
- `app/services/financial_calculations.py` — fonctions pures `_piotroski_interpretation(f_score: int | None)` et `_montier_interpretation(c_score: int | None)`, calquées sur `_beneish_interpretation` (None → `"DONNEES_MANQUANTES"` ASCII, sinon libellé par seuil). Vocabulaire **réconcilié avec le prompt `system.md` et les références** : F-Score 8-9 `forte_qualite` · 7 `bonne_qualite` · 4-6 `qualite_moyenne` · 0-3 `value_trap` ; C-Score 0-1 `propre` · 2-3 `signaux_mineurs` · 4-6 `signaux_multiples`. Aucun gate sectoriel sur ces fonctions (le gate None est porté au niveau du score, comme pour les signaux Sprint 142).
- `app/skills/tier2/earnings_quality/skill.py` — `_ScoresDeterministes` gagne `f_interpretation`/`c_interpretation: str | None`. `_scores_depuis_ratios` dérive le score agrégé **une fois** en local (`# source unique`, déduplication des deux `sum(...)` auparavant inline) et en déduit l'interprétation (`None` quand le score l'est). `_injecter_scores` écrit `data["f_score"]["interpretation"]` / `data["c_score"]["interpretation"]` **sous le même gate** que `criteria`/`signaux` (`if scores.f_criteria is not None` / `if scores.c_signaux is not None`) → sous le gate, score non-None ⟹ interprétation non-None (le schéma exige `str`). **Asymétrie financière** : F conservé du LLM (gate None, Piotroski inapplicable), C substitué (parité Sprint 142).
- **Décision de périmètre** : interprétation F/C **uniquement**. Signaux/critères/scores (Sprint 142) et M/Z (Sprint 131) intacts. Prompt de skill et `_build_user_message` **inchangés** (le LLM produit toujours l'interprétation, écrasée post-parse comme M/Z).
- Tests : unitaires `financial_calculations` (`_piotroski_interpretation`/`_montier_interpretation` par seuil + `None → DONNEES_MANQUANTES`) ; intégration `skill.py` (poison LLM `interpretation` écrasé par le libellé dérivé du score ; financière → F LLM conservée via marqueur, C substituée). Refactor qualité : le helper de test `_earnings_tool_use_response` gagne un paramètre `data=` (injection de payload empoisonné sans repasser par un output valide) — les deux nouveaux tests le réutilisent.

**Version** : 10.29.0
**Tests** : 1 668 backend collectés (1 664 passés, 3 skipped, 1 xfailed — +4) ; `ruff All checks passed` ; frontend inchangé (sprint backend pur).

**Note d'environnement :** session web — **prompt de skill et orchestrateur NON modifiés** (substitution post-parse uniquement), mais l'output `earnings_quality` change (`f_score.interpretation`/`c_score.interpretation` déterministes) → **evals ciblées à relancer en local** : `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles **non exécutées ici**. Stack Docker non démarrée ; pas de test navigateur live. Réconciliation carte↔code : prémisses du chemin critique vérifiées avant implémentation (`FScoreDetail.interpretation` `schemas.py:141` / `CScoreDetail.interpretation` `:153` ; `_beneish_interpretation` `financial_calculations.py:91` ; gate `_injecter_scores` `skill.py:183-190` ; vocabulaire canonique `system.md:115-145` ; golden `earnings_golden.json` ne contraint **pas** l'interprétation F/C ; fixture `conftest.py:263/268` = `forte_qualite`/`propre`). Revue indépendante à contexte frais (sous-agent correctness, distinct de la session auteur, nourri des critères d'acceptation) : **APPROVE — aucun bug HIGH/MED/LOW** (seuils byte-for-byte corrects, None-safety sous gate vérifiée, asymétrie financière correcte, golden/fixture non cassés, frontend verbatim). Passe qualité `/simplify` (4 sous-agents reuse/simplification/efficacité/altitude) : efficacité et altitude **propres** (refactor « score en local » = déduplication nette ; champs plats `f/c_interpretation` = bonne altitude, le conteneur dédié serait un refactor cross-sprint inutile) ; reuse/simplification ont relevé la **duplication du bloc mock** dans les 2 nouveaux tests → **corrigé** (paramètre `data=` sur `_earnings_tool_use_response`, sans toucher les tests pré-existants hors périmètre).

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
