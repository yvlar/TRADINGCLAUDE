# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-02 — Sprint 143 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.29.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 144 — Traçabilité source+date earnings/valuation dans le PDF |
| **Dernier sprint complété** | Sprint 143 — Interprétations déterministes F-Score / C-Score (parité M/Z) ✅ |

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
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts
- **Sécurité auth durcie (Sprint 125)** — secret JWT fail-fast (`RuntimeError` au boot hors dev/test si `JWT_SECRET_KEY` absent), blacklist JTI fail-closed (panne Redis → token refusé), réponses 500 assainies (body générique + `correlation_id`, `str(exc)` jamais exposé — global handler + tous les endpoints + flux SSE), CORS durci (`CORS_ORIGINS` CSV via env, méthodes explicites)

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance (avec source + date de récupération affichées sous les ratios — Sprint 134, étendues aux ratios Qualité bénéfices auto-remplis — Sprint 138 ; ratio absent de la source = `None` honnête, jamais `0.0` trompeur — Sprint 135), streaming SSE skill par skill, badge « score depuis cache <24h » ; **source + date des ratios Graham aussi affichées sous la carte Graham de l'analyse rendue/rechargée** (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, threadées jusqu'à la réponse et reconstruites depuis l'historique — Sprint 139) ; **provenance par ratio en signal-only** sous la carte Graham après auto-fill — badge discret « P/B via `clé` (repli) » uniquement quand la clé yfinance effective diffère de la clé primaire attendue (`ratios_provenance`, Sprint 141)
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

### Sprint 142 — Calculs déterministes : signaux détaillés F-Score / C-Score ✅

**Objectif :** Seuls les **scores agrégés** F-Score (0-9) et C-Score (0-6) étaient déterministes (Python, Sprints 128/131) ; les **signaux individuels** — `f_score.criteria[].passe` (9 critères Piotroski) et `c_score.signaux[].present` (6 signaux Montier) — restaient interprétés par le LLM, donc non rejouables et susceptibles de diverger du score agrégé qu'ils composent. Les calculer en Python et les substituer post-parse, en cohérence stricte avec le score agrégé. Suite de la file revue expert FinTech. **Sprint backend pur** (aucun frontend, migration ni prompt de skill).

**Livrables :**
- `app/services/financial_calculations.py` — dataclasses frozen `PiotroskiCriterion` (`nom`/`passe`/`detail`) et `MontierSignal` (`nom`/`present`/`detail`), miroir des schemas `FScoreCriterion`/`CScoreSignal` (substitution directe par `asdict()`, pattern Sprint 131). Fonctions pures `piotroski_f_criteria()` (9 critères) et `montier_c_signaux()` (6 signaux) portant booléen + libellé par signal ; `piotroski_f_score`/`montier_c_score` **réécrites pour déléguer** à ces builders et `sum()` les booléens → **source unique des seuils**, invariant `sum(passe) == f_score` / `sum(present) == c_score` garanti par construction (aucun seuil dupliqué). Helpers `_pct`/`_num` pour les libellés.
- `app/skills/tier2/earnings_quality/skill.py` — `_ScoresDeterministes` gagne `f_criteria`/`c_signaux` ; `_scores_depuis_ratios` calcule chaque liste **une fois** et en dérive le score agrégé. `_injecter_scores` étendu : écrase `data["f_score"]["criteria"]` et `data["c_score"]["signaux"]` par les listes Python. **Cohérence None/financière** : `f_criteria` est None dans les mêmes cas que `f_score` (financière, profitabilité de base manquante) → liste LLM conservée (gate identique à l'ancien `f_score is not None`, longueur 9 préservée pour le validateur). Montier sans gate sectoriel → signaux C toujours substitués (parité avec le score agrégé).
- **Décision de périmètre** : limité aux signaux F/C. M-Score (8 indices) / Z-Score (X1-X5) déjà déterministes (Sprint 131) — non touchés. Prompt de skill et `_build_user_message` **inchangés** : le LLM produit toujours criteria/signaux (requis par le schéma), écrasés post-parse comme M/Z (zéro changement du message utilisateur → pas de dérive d'eval sur l'entrée). `interpretation` F/C reste LLM (parité interprétation M/Z = sprint futur suggéré).
- Tests : unitaires `financial_calculations` (9 critères / 6 signaux, invariant `sum == score`, financière → None, donnée comparative manquante → 9 entrées dont critère non accordé) ; intégration `skill.py` (mock Claude : booléens Python écrasent le poison LLM, invariant post-substitution ; financière → critères F LLM conservés via marqueur sentinelle, signaux C substitués).

**Version** : 10.28.0
**Tests** : 1 664 backend collectés (1 660 passés, 3 skipped, 1 xfailed — +9) ; `ruff All checks passed` ; frontend inchangé (sprint backend pur).

**Note d'environnement :** session web — **prompt de skill et orchestrateur NON modifiés** (substitution post-parse uniquement), mais l'output `earnings_quality` change (criteria/signaux déterministes) → **evals ciblées à relancer en local** : `ANTHROPIC_API_KEY` absente du conteneur web → evals Claude réelles non exécutées ici. Stack Docker non démarrée ; pas de test navigateur live. Réconciliation carte↔code : prémisses du chemin critique vérifiées avant implémentation (`FScoreCriterion`/`CScoreSignal` `schemas.py:132/144` ; `_injecter_scores` `skill.py:154` ; agrégés `financial_calculations.py:398/470` ; validateur `valider_comptes_cadres` exige 9/6). Revue indépendante à contexte frais (sous-agent correctness high, distinct de la session auteur, nourri des critères d'acceptation) : **APPROVE — aucun bug HIGH/MED/LOW** (9+6 conditions vérifiées byte-for-byte équivalentes à l'ancienne logique ; invariant par construction ; None-safety OK ; asymétrie financière correcte ; M/Z intacts). Passe qualité `/simplify` (4 sous-agents reuse/simplification/efficacité/altitude) : **propre** — extension fidèle du pattern Sprint 131 ; seul point relevé (dédup du bloc mock « poison » partagé par 4 tests, dont 2 préexistants) **écarté** car hors périmètre du sprint.

### Sprint 141 — Propagation frontend de la provenance par ratio ✅

**Objectif :** Le Sprint 140 a exposé côté backend la provenance par ratio (`GrahamRatios.ratios_provenance: dict[str, str] | None`, nom de ratio → clé yfinance effective) ; le champ transite dans le payload `/extract` mais n'était **ni typé ni affiché** côté frontend. Rendre cette provenance visible et vérifiable — sans bruit : ne signaler qu'un **repli réel** (clé effective ≠ clé primaire attendue). Suite de la file revue expert FinTech. **Sprint frontend pur** (aucun backend, aucune migration, aucun prompt de skill).

**Livrables :**
- `frontend/src/types/index.ts` — `interface GrahamRatios` gagne `ratios_provenance?: Record<string, string> | null` (snake_case, miroir exact du payload `dict[str, str] | None` ; zéro `any`, cohérent avec `ratios_source`/`ratios_fetched_at` voisins)
- `frontend/src/components/AnalyzeForm.tsx` — affichage **signal-only** sous la carte Graham après auto-fill : helper pur `ratiosEnRepli(provenance)` qui ne retient que les ratios dont la clé effective diffère de la clé primaire attendue (`RATIO_PRIMARY_KEYS` : `pb`→`priceToBook`, `debt_equity`→`debtToEquity`, `book_value`→`bookValue`), badge discret « P/B via `clé` (repli) » avec `title` explicatif. Provenance `null`/absente ou clés toutes primaires → **rien affiché** (aucun bruit). `data-testid="ratios-provenance"`
- **Décision de périmètre** : limité aux 3 ratios Graham instrumentés au Sprint 140, affichage sur `AnalyzeForm` (qui consomme le payload `/extract` portant `ratios_provenance`). `AnalysisResult` reconstruit depuis l'analyse/historique **n'a pas** la provenance tant qu'elle n'est pas threadée dans `AnalyzeResponse` (backend) → reporté pour préserver le caractère « frontend pur » de ce sprint (extension possible comme au Sprint 139)
- Tests : composant `AnalyzeForm` — provenance avec une clé de repli (`pb`→`priceToBookRatio`) → badge affiché avec la clé effective, et un ratio resté sur sa clé primaire (`debt_equity`) **non** affiché (preuve du filtre par entrée) ; provenance toute-primaire → aucun badge ; provenance `null` → aucun badge

**Version** : 10.27.0
**Tests** : 1 655 backend collectés (1 651 passés, 3 skipped, 1 xfailed — inchangé, sprint frontend pur) ; 428 Vitest verts (+3) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — sprint d'affichage pur, **aucun prompt de skill ni l'orchestrateur modifié → evals non concernées**. `node_modules` frontend absent à l'amorçage → `npm install`. Canal d'exécution vérifié (la sortie des commandes rend bien — contrairement au flush sporadique du Sprint 140). Réconciliation carte↔code : les prémisses du chemin critique vérifiées par `grep`/lecture avant implémentation (`GrahamRatios.ratios_provenance` `graham_analysis/schemas.py:42` ; clés primaires `_resolve_ratio` `yahoo_finance.py:259-264` ; interface TS `GrahamRatios` `types/index.ts:50` ; `handleAutoFill` spread `result.graham` dans `ratios` `AnalyzeForm.tsx:60` ; patterns d'affichage à cloner `AnalyzeForm.tsx:172-177` / `AnalysisResult.tsx:211-216`). Phase A : `pytest`/`ruff` complets reconstatés verts (le Sprint 140 web n'avait pu confirmer que partiellement). Revue indépendante à contexte frais (sous-agent `/code-review` high, distinct de la session auteur, nourri des critères d'acceptation) : **aucun bug HIGH/MED** ; 3 findings LOW — (1) double appel `ratiosEnRepli` **corrigé** (hoisté en `const repliRatios`) ; (2) dépendance au contrat backend (provenance = clé yfinance réelle) **vérifiée** (`yahoo_finance.py:269-273` n'émet jamais d'entrée à clé `None`) ; (3) badge potentiellement périmé si un 2ᵉ auto-fill omettait le champ **écarté** (le backend émet toujours `ratios_provenance`, et le comportement est identique aux champs `ratios_source`/`ratios_fetched_at` voisins). Stack Docker non démarrée. Pas de test navigateur live.

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
