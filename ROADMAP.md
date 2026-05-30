# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-30 — Sprint 127 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.15.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 129 — Conformité : disclaimers & avertissement de risque |
| **Dernier sprint complété** | Sprint 128 — Calculs financiers déterministes en Python (le pivot) ✅ |

> **Re-priorisation 2026-05-29** — La revue expert FinTech (`docs/revue-expert-fintech.md`) a identifié des correctifs P0 de sécurité, livrés au **Sprint 125** (complété). La suite de la file issue de la revue (déterminisme LLM, calculs déterministes, disclaimers, données multi-sources) est dans les sprints suggérés de `prompt-mise-a-jour-roadmap.md`.

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB) ; **scores financiers déterministes** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham) calculés en Python (`app/services/financial_calculations.py`) et substitués au bloc LLM — le modèle interprète, il ne produit plus les chiffres (Sprint 128)
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
- **Rapports PDF** — par ticker (ou analyse précise `analysis_id`), screener, watchlist, mensuel (section ESG)
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

### Sprint 128 — Calculs financiers déterministes en Python (le pivot) ✅

**Objectif :** Rapatrier en Python les scores financiers jusqu'ici produits par le LLM (donc ni numériquement fiables ni auditables). Le LLM **interprète** désormais des chiffres calculés au lieu de les produire. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §1). Sprint backend + touche frontend mineure.

**Livrables :**
- `app/services/financial_calculations.py` (nouveau) — fonctions pures, typées, sans I/O : `altman_z_score` (variantes original/private/service ; `is_financial` → `None`), `beneish_m_score` (8 indices), `piotroski_f_score` (9 critères, 0-9), `montier_c_score` (6 signaux, 0-6), `sloan_accrual_ratio`, `graham_number` (√(22.5 × BPA × BVPS)). Coefficients RECOPIÉS depuis `.claude/skills/earnings-quality-fraud-detection/references/`. Retour `float | None` (ou `int | None`) — jamais d'exception sur donnée manquante / div0 (cf. `donnees-financieres.md`)
- `app/skills/tier2/earnings_quality/skill.py` — helper `_scores_depuis_ratios` (mappe `EarningsQualityRatios` → les 5 scores) + `_injecter_scores` : substitution **post-parse** des scores numériques (M/Z/F/C/Sloan) par les valeurs Python, qui priment sur le bloc LLM. Scores aussi injectés dans le message utilisateur pour interprétation. Gate sectoriel via `is_financial` (LLM) → M/Z/F `None` pour une financière. Garde-fous Sprint 127 (NaN/inf + bornes plausibilité) conservés en 2ᵉ ligne, mais **bornes élargies** (Z 50→200, M 20→30) : un Altman Z déterministe à composante market-value peut légitimement dépasser 50 pour une société peu endettée — borner trop serré supprimait silencieusement earnings_quality (skill optionnel) des sociétés les plus saines (corrigé suite revue indépendante)
- `app/skills/tier2/graham_analysis/{schemas,skill}.py` — nouveau champ `graham_number` (`FiniteFloatOrNone`, exclu du tool schema, calculé en Python), BPA reconstitué via `price/pe` si `eps_ttm` absent
- `app/skills/tier2/earnings_quality/schemas.py` + `app/skills/tier1/yahoo_finance.py` — champs `net_income_t1` / `cfo_t1` (exercice T-1) ajoutés pour fiabiliser F-Score (critère 3) et C-Score (signal 1)
- Prompts `earnings_quality` + `graham_analysis` — note « scores calculés en amont, interprète-les, ne les recalcule pas »
- `frontend/src/types/index.ts` + `AnalysisResult.tsx` — champ `graham_number` typé + affichage « Nombre de Graham »
- Tests : unitaire `tests/services/test_financial_calculations.py` (28 — vecteurs calculés à la main + None/div0 + banque) ; intégration `tests/skills/test_earnings_quality.py` (score Python prime sur bloc LLM, financière annule M/Z, message contient les scores) + `tests/skills/test_graham_tool_use.py` (graham_number calculé, None si BPA négatif, exclusion du tool schema) ; composant `AnalysisResultGrahamNumber.test.tsx`

**Limites connues :** les sous-composantes des `*Detail` (dsri, gmi… du M ; X1-X5 du Z) restent issues du LLM — seul le score agrégé est déterministe. Leur persistance est l'objet du Sprint 131 suggéré.

**Version** : 10.15.0
**Tests** : 1 522 backend collectés (1 518 passés, 3 skipped, 1 xfailed — +36) ; 408 Vitest verts (+2) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — **aucune clé Anthropic dans le conteneur → les `evals` ciblées (`earnings_quality` + `graham_analysis`, prompts modifiés) n'ont pas pu être lancées** (vérifié : `ANTHROPIC_API_KEY` absente). La substitution déterministe est validée sur payloads construits (le bloc LLM injecte un score aberrant, le score Python l'écrase). Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

### Sprint 127 — Déterminisme LLM + validation numérique des bornes ✅

**Objectif :** (1) rendre les analyses reproductibles en fixant `temperature=0` sur tous les appels Claude ; (2) ajouter des garde-fous Pydantic de plausibilité post-LLM sur les scores clés d'`earnings_quality`, pour qu'un chiffre aberrant produit par le modèle soit rejeté avant persistance. Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §3, §1). Sprint backend pur — aucune migration DB, aucun frontend.

**Livrables :**
- `app/utils/retry.py` — `kwargs.setdefault("temperature", 0)` ajouté dans `call_claude_with_retry` (point d'insertion central unique, couvre les 16 skills qui passent tous par ce helper — `grep` confirmant l'unique `messages.create` du backend). **Surchargeable** : un skill peut fournir explicitement `temperature` sans être écrasé
- `app/utils/numeric_validation.py` (nouveau) — type réutilisable `FiniteFloatOrNone = Annotated[float | None, AfterValidator(...)]` qui rejette NaN/inf (Pydantic par défaut accepte les floats non finis). Réflexe généralisable à tout score/ratio LLM exposé
- `app/skills/tier2/earnings_quality/schemas.py` — `FiniteFloatOrNone` appliqué aux 11 champs `float | None` de `MScoreDetail`/`ZScoreDetail`/`SloanDetail` (rejet NaN/inf uniforme) ; deux `@model_validator(mode="after")` (style `stock_valuation/schemas.py:98`) bornent la plausibilité : `z_score` hors `[-50, 50]` et `m_score` hors `[-20, 20]` rejetés (bornes larges documentées depuis les `references/` — Altman Z réel ~[-5, 15], Beneish M réel ~[-5, 2])
- Tests : unitaire `tests/services/test_retry.py` (temperature=0 par défaut + non-écrasement d'un temperature explicite, +2) ; unitaire `tests/skills/test_earnings_quality.py` (inf/nan → `ValidationError`, hors-bornes → `ValidationError`, scores plausibles acceptés, +6) — aucune régression des fixtures golden existantes

**Version** : 10.14.0
**Tests** : 1 486 backend collectés (1 482 passés, 3 skipped, 1 xfailed — +8) ; Vitest inchangé (sprint backend pur) ; ruff `All checks passed`

**Note d'environnement :** session web — `temperature=0` change le comportement de tous les skills ; la suite `pytest` (Claude mocké) reste verte sans rien prouver sur la qualité réelle. **Aucune clé Anthropic disponible dans le conteneur → les `evals` ciblées n'ont pas pu être lancées** (vérifié : `ANTHROPIC_API_KEY` absente). Le rejet NaN/inf et les bornes de plausibilité sont validés sur payloads construits (pas live). Pas de test navigateur live.

### Sprint 125 — Durcissement sécurité auth & fail-safe (P0) ✅

**Objectif :** Éliminer quatre faiblesses de sécurité de la couche auth/middleware relevées par la revue expert FinTech (`docs/revue-expert-fintech.md` §5), sans changer le comportement fonctionnel pour un déploiement correctement configuré. Sprint backend pur — aucune migration DB, aucun changement de prompt de skill (evals non concernées).

**Livrables :**
- `app/utils/jwt_secret.py` — `resolve_jwt_secret()` : **fail-fast** par défaut. Si `JWT_SECRET_KEY` absent, lève `RuntimeError` sauf si `APP_ENV ∈ {dev, development, test, testing}` (repli secret de dev toléré). `APP_ENV` absent = traité comme production (refus). Chaîne vide traitée comme absente. Câblé dans `auth_token_service.py` ET `password_reset_service.py` (qui partageaient le même secret de repli codé en dur — trou fermé partout)
- `app/services/auth_token_service.py` — `is_jti_blacklisted` **fail-closed** : appel Redis enveloppé dans `try/except` → panne Redis = token considéré révoqué (`True`). Les deux appelants (`middleware/auth.py:99`, `endpoints/auth.py:105`) rejettent en 401. Contraire au rate-limiting fail-open, par choix de sécurité
- `app/utils/error_sanitization.py` — `log_internal_error()` (log serveur-side + `correlation_id`) + `sanitized_http_500()` (HTTPException 500 au body générique). Appliqué au global exception handler (`main.py`), au `/analyze`, et à **tous les endpoints à chemin 500** (report, screen, screener_report, monthly_report, ticker_report, compare, extract, annotations, export) + au flux SSE `analyze_stream.py` — `str(exc)` ne sort plus jamais dans un body HTTP/SSE (anti-énumération d'utilisateurs)
- `app/api/main.py` — CORS durci : `allow_methods` explicite (`GET/POST/PUT/DELETE/OPTIONS`) ; origines lues depuis `CORS_ORIGINS` (CSV) avec repli localhost en dev
- `.env.example` — `APP_ENV=dev` + `CORS_ORIGINS` documentés
- `tests/conftest.py` — `os.environ.setdefault("APP_ENV", "test")` pour que le lifespan réel exercé en test tolère le repli secret
- Tests : unitaire `tests/services/test_jwt_secret.py` (8) + `test_auth_token_service.py` (fail-fast init + fail-closed blacklist, 5) ; intégration `tests/api/test_exception_sanitization.py` (global handler + `/analyze` + `/screen` n'exposent pas `str(exc)`, 3) — aucune régression des tests auth existants

**Version** : 10.13.0
**Tests** : 1 478 backend collectés (1 474 passés, 3 skipped, 1 xfailed — +16) ; 406 Vitest verts (inchangé, sprint backend pur) ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : le fail-closed Redis et le fail-fast au boot lifespan sont validés sur mocks (`AsyncMock` levant une exception, `monkeypatch` sur `APP_ENV`/`JWT_SECRET_KEY`), pas live. CORS vérifié observablement (parsing CSV + méthodes explicites via introspection du middleware). Pas de test navigateur live. Sprint sans changement de prompt → evals non concernées.

### Sprint 126 — Annotations enrichies : tags + filtres ✅

**Objectif :** Ajouter un champ `tags` (mots-clés libres) aux annotations, filtrable via `GET /history?tags=value,growth`, avec chips affichées/éditables dans `AnnotationSection` et en lecture seule dans `HistoryTable`. Les annotations (Sprint 78) étaient du texte libre sans structure ; les tags offrent un filtrage sémantique léger du portefeuille sans RAG. (Travail initialement cadré comme Sprint 125 ; renuméroté 126 après la re-priorisation sécurité P0.)

**Livrables :**
- `infra/postgres/migration_sprint126.sql` + bootstrap lifespan (`app/api/main.py`) — colonne `tags TEXT[] NOT NULL DEFAULT '{}'` + index GIN `idx_annotations_tags`. Type `TEXT[]` retenu (et non JSONB) : mapping natif asyncpg `list[str] ↔ text[]` + opérateur de confinement `@>` (match de TOUS les tags) sur index GIN `array_ops`
- `app/models/annotation.py` — `tags: list[str]` sur `Annotation` + `AnnotationCreate` ; `field_validator` autoritaire serveur (minuscules, sans espaces, sans doublons ni vides) — aligne la casse stockée sur le filtre `@>` sensible à la casse
- `app/services/annotation_service.py` — `upsert` persiste les tags (`$3::text[]`), `get`/`get_all_with_ticker` les renvoient
- `app/orchestrator/core.py` — `HistoryEntry.tags` ; `get_history` + `get_history_paged` (lignes ET comptage) joignent `annotations` (LEFT JOIN, `analysis_id` UNIQUE → pas de duplication) et filtrent `a.tags @> $N::text[]` ; helper `_row_to_history_entry` (dé-duplication du mapping, garde NULL → `[]`)
- `app/api/main.py` — `_parse_tags_param` (CSV → liste minuscule, 422 si vide/virgules seules) câblé sur `/history` et `/history-paged`
- `frontend/src/components/TagChip.tsx` — chip réutilisable (variante lecture seule + variante avec bouton ×)
- `frontend/src/components/AnnotationSection.tsx` — chips éditables (ajout via input/Entrée, suppression), persistés via le client annotations ; `HistoryTable.tsx` — chips lecture seule ; `HistoryPage.tsx` — champ filtre `tags` câblé sur `getHistoryPaged`
- `frontend/src/types/index.ts` — `Annotation.tags`, `AnnotationCreate.tags`, `HistoryEntry.tags` (`string[]`)
- Tests : intégration `tests/api/test_history_tags_filter.py` (CSV→liste, minuscules, 422, jointure + `@>` lié, comptage) ; unitaire `tests/services/test_annotation_service.py` (upsert/get tags) ; endpoint `tests/api/test_annotations_endpoint.py` (round-trip + normalisation) ; composant `AnnotationSection` (ajout/retrait/erreur) + `HistoryTable` (chips) + `HistoryPage` (filtre tags)

**Version** : 10.12.0
**Tests** : 1 462 backend collectés (1 458 passés, 3 skipped, 1 xfailed — +14) ; 406 Vitest verts (+6) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : la migration SQL et le filtre `@>` ne sont pas exercés live (syntaxe validée + jointure/binding `$N::text[]` vérifiés sur pool asyncpg mocké). Pas de test navigateur live. Sprint sans changement de prompt de skill → evals non concernées.

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
