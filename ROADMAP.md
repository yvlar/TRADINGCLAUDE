# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-06 — Sprint 167 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.54.0 |
| **Phase active** | Transformation B2B/SaaS — P0→P1 (plan directeur FinTech) |
| **Sprint actif** | Sprint 168 — E4-S3 clés API rattachées au tenant (`api_keys.tenant_id` + résolution tenant sur le chemin Bearer) |
| **Dernier sprint complété** | Sprint 167 — E4-S2 quotas : table de référence `plan_limits` (bornes par plan) + `tenants.plan` (FK), `QuotaService` (compteur mensuel Redis, borne dure fail-open), `429` au dépassement sur `/analyze`+`/analyze-stream` (cache hit ne consomme pas) + borne `max_screener_tickers` par tenant sur `/screen`, bandeau quota frontend ✅ |

> **Pivot stratégique 2026-06-05** — la roadmap adopte la **transformation B2B/SaaS** : plan directeur `docs/plan-directeur-fintech-2026.md` (audit FinTech → 44 sprints `E#-S#`, phases P0→P3). Les sprints **154+ exécutent ce backlog** (154 = E1-S1, sécurité fail-closed). Le backlog analyse-tool antérieur (provenance PDF…) est parqué (historique git).

> **Sprint 137 exécuté (2026-05-31, evals Claude réelles)** — clé API temporaire fournie en session. `stock_valuation` (Sonnet, golden 5 cas) : **15 passed / 5 skipped / 0 failed** (8m50s) — la **substitution DCF déterministe (Sprint 132) survit à l'aller-retour tool-use réel** (valeur DCF + matrice = ossature Python), gate sectoriel financières/REIT correct. `earnings_quality` (Haiku, golden 20 cas) : **81 passed / 10 failed / 10 skipped** (33m45s) — **tous les scores déterministes M/Z/F/C/Sloan passent** (Sprints 128/131) et la concordance verdict globale ≥ 80 % tient ; les 10 échecs portent **uniquement sur des champs narratifs libres du LLM**, pas sur les calculs (voir « Drift earnings_quality » ci-dessous). Aucun lien avec le Sprint 140 (extraction tier1 uniquement).

> **Drift `earnings_quality` — état au Sprint 149** : la cause racine (contrat `drapeaux_rouges` sous-spécifié au Sprint 137) est désormais encadrée. Le prompt (`system.md` Cadre 6) porte une consigne de cardinalité **verrouillée par test** (Sprint 149) et **les 5 cadres d'interprétation sont déterministes** (M/Z Sprint 131, F/C Sprint 143, Sloan Sprint 148). Le **replay déterministe hors-ligne** (`tests/skills/test_earnings_deterministic_replay.py`, Sprint 149) confirme la cohérence golden des cadres substitués (Z 20/20, M 13/13, F 17/17 à ±1, Sloan 20/20). **Mesure live résiduelle différée** : la cardinalité `drapeaux_rouges` (champ libre du LLM) ne se mesure qu'avec `ANTHROPIC_API_KEY` (~100 appels Haiku, ~33 min — absente du conteneur web, exclue du CI) → `ANTHROPIC_API_KEY=… pytest tests/evals/test_earnings_evals.py -m evals`.

> **Re-priorisation 2026-05-29** — La revue expert FinTech (`docs/revue-expert-fintech.md`) a identifié des correctifs P0 de sécurité, livrés au **Sprint 125** (complété). La suite de la file issue de la revue (déterminisme LLM, calculs déterministes, disclaimers, données multi-sources) est dans les sprints suggérés de `prompt-mise-a-jour-roadmap.md`.

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB) ; **scores financiers déterministes** (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham) calculés en Python (`app/services/financial_calculations.py`) et substitués au bloc LLM — le modèle interprète, il ne produit plus les chiffres (Sprint 128) ; **sous-composantes auditables** (8 indices Beneish DSRI/GMI/… + termes X1-X5 Altman ; **+ critères détaillés F-Score (9 Piotroski) et signaux C-Score (6 Montier) — booléen `passe`/`present` par signal, Sprint 142** ; **+ libellés d'interprétation au niveau cadre F-Score / C-Score (`forte_qualite`/…/`value_trap` ; `propre`/`signaux_mineurs`/`signaux_multiples`) dérivés du score agrégé déterministe et substitués post-parse — parité avec M/Z déjà déterministes, Sprint 143 ; `sloan.interpretation` rejoint la parité (Sprint 148) — les 5 libellés de cadre sont déterministes**) également calculées en Python et persistées dans l'output — `sum(passe) == f_score` / `sum(present) == c_score` par construction, analyse entièrement rejouable (Sprint 131) ; **ossature DCF déterministe** (`stock_valuation`) — WACC (CMPC), valeur intrinsèque DCF par action et matrice de sensibilité WACC×g calculées en Python (`app/services/valuation_calculations.py`) et substituées au bloc LLM ; le modèle conserve comparables, sectoriel et verdict ; financières/REIT exclues du DCF (méthode sectorielle prime) (Sprint 132)
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
- `GET /admin/audit-log?limit=50` — journal d'audit append-only des mutations métier (watchlist, annotation, clé API), admin only (Sprint 160 — traçage best-effort côté service via `AuditLogService.record`, table `audit_log` posée par Alembic, `tenant_id` nullable en forward-compat E3)
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible) ; **bloc « Sources des ratios complémentaires »** rendu via `_fmt_ratios_source` quand les ratios earnings/valuation reconstruits (Sprint 144) portent une source+date, ligne omise sinon — parité Graham (Sprint 145)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts
- **Sécurité auth durcie (Sprint 125)** — secret JWT fail-fast (`RuntimeError` au boot hors dev/test si `JWT_SECRET_KEY` absent), blacklist JTI fail-closed (panne Redis → token refusé), réponses 500 assainies (body générique + `correlation_id`, `str(exc)` jamais exposé — global handler + tous les endpoints + flux SSE), CORS durci (`CORS_ORIGINS` CSV via env, méthodes explicites)
- **Isolation RLS multi-tenant (Sprints 163-165)** — Row-Level Security PostgreSQL active (`ENABLE` + `FORCE`) sur les 6 tables métier avec policy `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` (USING + WITH CHECK) ; GUC `app.tenant_id` posé par connexion au pool asyncpg (`app/db/tenant_context.py`), threadé depuis le claim JWT (Sprint 164). Fail-closed : sans contexte tenant, 0 ligne visible. **Isolation prouvée table par table en rouge→vert** (matrice paramétrée `tests/integration/test_rls_isolation.py`, rôle NOSUPERUSER, gate CI sur les 6 tables — Sprint 165) ; revue OWASP de la policy : `docs/revue-owasp-rls-2026-06.md` (2 risques résiduels suivis hors code : rôle runtime `NOSUPERUSER`/`NOBYPASSRLS`, scoping tenant de `/report`)
- **Metering `usage_events` (Sprint 166 — ouvre E4)** — table append-only `usage_events` (`alembic/versions/0006_usage_events.py`) horodatant **par skill exécuté** la consommation facturable d'un tenant (`tenant`, `skill`, `workflow`, `cost_usd NUMERIC(10,6)`, `tokens_input/output`, `created_at`) + index `(tenant_id, created_at DESC)` ; **pas de FK vers `analysis_history`** (survit à la purge d'une analyse). 7ᵉ table RLS (`ENABLE`+`FORCE` + policy tenant standard, matrice d'isolation étendue, gate CI). Émise best-effort depuis l'orchestrateur (`_emit_usage_events`, appariement positionnel `skills_applied`↔`all_usages`) à chaque skill consommé — **un cache hit (`cost_usd=0`) n'émet rien** ; un échec de metering n'avorte jamais l'analyse. Source de vérité unique de la facturation (agrégation E4-S2/E4-S5). Chemin worker non metré (analyses planifiées sous tenant legacy — déféré)
- **Quotas par plan (Sprint 167 — E4-S2)** — table de référence **globale** `plan_limits` (`alembic/versions/0007_plan_limits.py`, **sans** `tenant_id`/RLS) définissant par plan (`free`/`pro`) `max_analyses_per_month`, `max_screener_tickers`, `retention_days` ; rattachement `tenants.plan TEXT NOT NULL DEFAULT 'free'` (FK `→ plan_limits(plan)`). `QuotaService` (`app/services/quota_service.py`) résout le plan du tenant courant et applique une **borne dure** : compteur mensuel Redis `quota:{tenant}:{YYYY-MM}` (incr/expire calqué sur `RateLimitMiddleware`), `429` clair (`Retry-After`) au dépassement sur `POST /analyze` et `/analyze-stream` — un **cache hit (`cost_usd=0`) ne consomme pas** (cohérent avec le metering). `POST /screen` borné à `max_screener_tickers` du plan (en plus du plafond technique max 20) → `429`. **Fail-open documenté** : panne Redis → requête autorisée (la conso reste tracée dans `usage_events`). Bandeau quota frontend (`QuotaBanner`) sur Analyze + Screener

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance (avec source + date de récupération affichées sous les ratios — Sprint 134, étendues aux ratios Qualité bénéfices auto-remplis — Sprint 138 ; ratio absent de la source = `None` honnête, jamais `0.0` trompeur — Sprint 135), streaming SSE skill par skill, badge « score depuis cache <24h » ; **source + date des ratios Graham aussi affichées sous la carte Graham de l'analyse rendue/rechargée** (`AnalyzeResponse.ratios_fetched_at`/`ratios_source`, threadées jusqu'à la réponse et reconstruites depuis l'historique — Sprint 139 ; **étendues aux cartes Qualité bénéfices et Valorisation** via quatre champs miroir `earnings_ratios_*`/`valuation_ratios_*`, threadés aux 4 sites de construction de `AnalyzeResponse` + reconstruction historique, `data-testid` `earnings-ratios-source`/`valuation-ratios-source` — Sprint 146) ; **provenance par ratio en signal-only** sous la carte Graham après auto-fill — badge discret « P/B via `clé` (repli) » uniquement quand la clé yfinance effective diffère de la clé primaire attendue (`ratios_provenance`, Sprint 141) ; **étendue à l'analyse rendue/rechargée** (`AnalysisResult`) via le composant partagé `RatiosProvenanceNote` en threadant `ratios_provenance` jusqu'à `AnalyzeResponse` (Sprint 150)
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

### Sprint 167 — E4-S2 : quotas par plan + quota screener par tenant ✅

**Objectif :** Transformer la multi-tenance en **offre commerciale bornée** — un plan tarifaire limite la consommation d'un tenant, un compteur applique la borne, un `429` explicite signale le dépassement. Absorbe le **quota screener par tenant** reporté de l'E3-S4.

**Livrables :**
- `alembic/versions/0007_plan_limits.py` (nouveau, chaîné après `0006_usage_events`) — table de **référence globale** `plan_limits(plan TEXT PK, max_analyses_per_month, max_screener_tickers, retention_days, created_at)`, seed `free` (50/5/30) + `pro` (1000/20/365). **Décisions documentées** : (1) `plan_limits` **sans `tenant_id`/RLS** — un plan porte la même borne pour tous les tenants (clé = nom de plan), rien à isoler ; elle **n'entre pas** dans la matrice RLS (reste 7 tables). (2) Rattachement par **colonne `tenants.plan TEXT NOT NULL DEFAULT 'free'` (option a)** + FK `→ plan_limits(plan)` (un tenant = un plan, pas d'historique ce sprint ; FK = intégrité référentielle, DEFAULT = legacy/nouveaux tenants au plan gratuit sans backfill). (3) `retention_days` posé (socle purge par plan M4) mais pas encore appliqué.
- `app/services/quota_service.py` (nouveau) — `QuotaService` : `_resolve_limits` (join `tenants ⨝ plan_limits` sur le tenant courant), **compteur mensuel Redis** `quota:{tenant}:{YYYY-MM}` (incr/expire calqué sur `RateLimitMiddleware`), `check()` (lève `QuotaExceededError` à `used ≥ max`, lecture seule) / `increment()` (incr + `expire` posé **au seul premier incr** du mois) / `check_and_increment()` (raccourci non-cache) / `check_screener_size()`. **Choix Redis (et non agrégation `usage_events`)** : application rapide sur le chemin chaud + `usage_events` est par-skill (compter les analyses exigerait un COUNT DISTINCT) ; `usage_events` reste la source de vérité durable (E4-S5). **Borne DURE, pas best-effort** : politique de panne **fail-open documentée** (panne Redis → requête autorisée comme `RateLimitMiddleware` ; la conso reste tracée dans `usage_events`) — tranché explicitement, l'alternative fail-closed `503` rejetée (transformerait une panne Redis en interruption facturable).
- `app/utils/quota_http.py` (nouveau) — `quota_exceeded_http` : `QuotaExceededError` → `HTTPException(429)` + `Retry-After` (si borne temporelle), à la frontière endpoint (le service reste agnostique HTTP).
- **Application du quota** : `/analyze` + `/analyze-stream` appellent `check()` **avant** l'orchestrateur (429 clair ; pour le SSE, hissé **avant** l'ouverture du flux — impossible une fois le 200 commencé), puis `increment()` **seulement si `response.cost_usd > 0`** — un **cache hit (Redis ou composite, `cost_usd=0`) ne consomme pas** (cohérent metering). `/screen` borné à `max_screener_tickers` du plan (en plus du plafond technique max 20) → 429.
- **Frontend (léger)** — `QuotaBanner` (`isQuotaError` = détection structurelle `ApiError.status===429`, bandeau ambre distinct de l'erreur rouge générique) sur Analyze (état `quotaError`) + Screener (dérivation au rendu depuis l'erreur de mutation).

**Validation runtime (Postgres 16 local migré)** : `upgrade head` → `plan_limits` seedée (free/pro), `tenants.plan='free'` (legacy), FK `tenants_plan_fkey` présente et **rejetant un plan inexistant** ; `downgrade -1` retire colonne puis table, re-`upgrade` idempotent. **Quota prouvé end-to-end** (`QuotaService` sur le schéma réel + FakeRedis) : résolution plan→bornes free, **429 à la borne** (50/50) + **autorisation sous quota** (49/50), borne screener (5 OK, 6 → 429), `increment` pose le compteur + TTL.

**Version** : 10.54.0
**Tests** : 2 136 backend collectés (+39 : unitaires `QuotaService` [résolution plan→bornes, sous/à la borne, expire au 1er incr seulement, `check_and_increment`, screener over/under, fail-open plan absent + Redis read/incr, clé mensuelle, `_seconds_until_month_end` juin + bascule déc→jan], forme migration `plan_limits` [chaînage, colonnes, PK plan, **sans tenant/RLS**, seed free/pro, FK+DEFAULT, downgrade], endpoints [analyze 429/200/cache-hit-no-consume, analyze-stream 429 avant flux, screen 429/200], intégration PG migré [seed, bornes legacy, 429/sous-quota, screener, increment+TTL]) ; `ruff`/`mypy app/` verts ; **frontend 449 Vitest verts** (+4 `QuotaBanner` : rendu message, role=alert, `isQuotaError` 429 vs autres) + typecheck/ESLint verts ; **pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — application de quota au niveau endpoint uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (off-by-one : exactement `max` autorisé / `max+1` bloqué ; cache-hit-no-consume vérifié pour les 2 caches ; 429 SSE avant le 200 ; TTL posé au seul 1er incr + bascule déc→jan ; fail-open lecture+incr ne lève jamais ; `plan_limits`/`tenants` non-RLS lus par `id` dérivé du ContextVar serveur → pas de fuite cross-tenant ; ordre FK migration ; `QuotaExceededError`→429 non avalé par le 500) — 0 finding CRITICAL/MAJOR/MINOR, 3 NIT intentionnels/in-scope ; **qualité** (`/simplify` 4 axes) : altitude jugée correcte (per-endpoint requis car le cache-hit-no-consume a besoin de la réponse ; middleware ne peut pas voir le body ; `QuotaExceededError`→429 au bon niveau), 1 finding convergent traité (docstring `check_and_increment` durcie contre le sur-comptage), optimisation cache `_resolve_limits` écartée (join 2-PK index-only négligeable vs Redis+Claude ; cache = staleness inutile pour 2 lignes de référence), pipeline incr/expire écarté (idiome `RateLimitMiddleware`).

### Sprint 166 — E4-S1 : metering `usage_events` (ouvre E4) ✅

**Objectif :** Poser la fondation de facturation — une table **`usage_events` append-only** qui enregistre, **par skill exécuté** (pas seulement par analyse), la consommation facturable d'un tenant. Source de vérité unique de l'agrégation (E4-S2 quotas, E4-S5 export). Ouvre l'épic E4 (facturation/SaaS).

**Livrables :**
- `alembic/versions/0006_usage_events.py` (nouveau, chaîné après `0005_business_rls`) — table `usage_events(id UUID gen_random_uuid, tenant_id UUID NOT NULL REFERENCES tenants(id), skill TEXT, workflow TEXT, cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0, tokens_input/output INTEGER, created_at TIMESTAMPTZ)` + index `(tenant_id, created_at DESC)`. **Décisions documentées** : (1) **pas de FK vers `analysis_history`** — un événement de consommation survit à la purge de l'analyse (rétention facturation ≠ rétention analyse) ; (2) **`cost_usd NUMERIC`** — précision monétaire exacte, jamais float ; (3) **`id` UUID** (pas BIGSERIAL) — append-only aligné sur `audit_log`, aucune séquence à GRANT. **RLS 7ᵉ table** : `ENABLE`+`FORCE` + policy `usage_events_tenant_isolation` (USING + WITH CHECK sur le prédicat tenant fail-closed `NULLIF`). Downgrade idempotent (DROP POLICY → DISABLE → DROP TABLE).
- `app/services/usage_event_service.py` (nouveau) — `UsageEventService` **append-only** calqué sur `AuditLogService` : `record(...)` (INSERT pur, `tenant_id` défaut `resolve_tenant(...)`, `cost_usd` lié en `Decimal` — asyncpg exige un Decimal pour `NUMERIC`) + helper `record_usage_safe(...)` **best-effort** (un échec de metering n'avorte jamais l'analyse — log + continue).
- **Émission par-skill depuis l'orchestrateur** (`app/orchestrator/core.py`) — `_emit_usage_events(skills_applied, all_usages, workflow)` : appariement **positionnel** des deux listes remplies en lockstep, un `usage_events` best-effort par skill à `cost_usd>0` (**cache hit = 0 ligne**), appelé après `_persist` dans `run_company_analysis` **et** `stream_company_analysis`. Service injecté optionnellement au constructeur (rétrocompat : workers/tests sans service restent verts). **Chemin worker non metré** (analyses planifiées sous tenant legacy — déféré, commenté dans `app/workers/tasks.py`).
- **Lifespan** (`app/api/main.py`) — `UsageEventService` instancié, injecté à l'orchestrateur + exposé sur `app.state` (câblage `AuditLogService`).
- **Matrice RLS + CI** (`tests/integration/test_rls_isolation.py`, `.github/workflows/ci.yml`) — `usage_events` ajoutée comme 7ᵉ table de la matrice d'isolation ; GRANT du rôle `rls_tester` étendu.

**Validation runtime (Postgres 16 local + rôle NOSUPERUSER)** : `upgrade head` → `usage_events` avec RLS `ENABLE`+`FORCE`, policy USING==WITH CHECK, index, FK vers `tenants` uniquement ; matrice d'isolation 7 tables verte ; **émission prouvée via le vrai service** (1 ligne isolée par tenant, A voit sa ligne, B rien ; binding `Decimal` OK) ; downgrade/re-upgrade idempotents.

**Version** : 10.53.0
**Tests** : 2 097 backend collectés (2 075 passés, 21 skipped [+1 : matrice 7ᵉ table, skippée hors PG migré], 1 xfailed — +34 : forme migration usage_events [colonnes/index/RLS ENABLE+FORCE/policy USING+WITH CHECK/fail-closed NULLIF/pas de FK analysis_history/downgrade], unitaires service [record INSERT pur, défaut tenant legacy, tenant explicite, binding Decimal, append-only, `record_usage_safe` best-effort], émission orchestrateur [appariement par-skill, cache hit=0, sans service, best-effort, **bout-en-bout via `run_company_analysis`**]) ; `ruff`/`mypy app/` verts ; frontend inchangé ; **pas d'eval** (orchestrateur touché mais aucun prompt de skill modifié — émission de metering uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (appariement lockstep vérifié sur les 17 blocs des 2 chemins ; invariant `WITH CHECK` colonne==GUC garanti par émission `await` inline ; best-effort prouvé ; `cost_usd>0` skip cache hit ; migration fail-closed sans FK analysis_history) — 2 findings MINOR traités (worker non metré documenté ; test bout-en-bout ajouté), NIT cosmétiques traités (titre step CI « 7 tables ») ; **qualité** : `_emit_usage_events` au bon altitude, `UsageEventService` fidèle à `AuditLogService` sans divergence superflue, aucun refactor requis.

### Sprint 165 — E3-S5 : preuve d'isolation rouge→vert (clôt E3) ✅

**Objectif :** Transformer la preuve d'isolation minimale (1 table, E3-S3) en **matrice cross-tenant exhaustive sur les 6 tables métier**, en rouge→vert, + revue OWASP de la policy RLS. Clôt l'épic E3 (bloqueur n°1, isolation au niveau base).

**Livrables :**
- `tests/integration/test_rls_isolation.py` — la preuve 1-table devient une **matrice paramétrée** sur les 6 tables (`@pytest.mark.parametrize` sur `_TABLES`, parité verrouillée ↔ migration `0005_business_rls._TABLES`). Pour chaque table, sous rôle **NOSUPERUSER** : (a) **lecture isolée** — A ne voit que A (`USING`) ; (b) **`WITH CHECK`** — A ne peut pas écrire une ligne de B ; (c) **fail-closed** — GUC vide → `NULLIF`→`NULL::uuid` → 0 ligne. Fabrique de payload par table (`_PAYLOADS` + `_build_insert`) gérant les contraintes propres : `watchlist` (index unique **global** `(ticker, workflow)` → marqueurs distincts par tenant), `annotations` (`analysis_id` UNIQUE global → UUID neuf par insertion ; `note` NOT NULL), `analysis_history` (`input_data`/`result` JSONB NOT NULL). Le test E3-S4 (ContextVar→pool→GUC) est conservé.
- **Aspect rouge→vert prouvé empiriquement** : même requête de lecture → `{A}` sous GUC=A et `{B}` sous GUC=B (les deux lignes existent ; seule la policy masque celle de l'autre). Désactiver la RLS sur une table fait virer le cas au rouge ; la réactiver, au vert — vérifié en session.
- **Gate CI étendu** (`.github/workflows/ci.yml`) — le `GRANT` du rôle `rls_tester` couvre désormais les **6 tables + `tenants`** + `USAGE ON ALL SEQUENCES` (les BIGSERIAL `esg_score_history`/`alert_history` en dépendent) ; la matrice tourne en gate, pas seulement en local.
- **Revue OWASP** (`docs/revue-owasp-rls-2026-06.md`, nouveau) — policy passée au crible : injection GUC **non exploitable** (`set_config` en paramètres liés + `UUID(...)` fail-safe legacy), **aucune** fonction `SECURITY DEFINER`, `FORCE RLS` couvre le propriétaire (les 6 tables `ENABLE`+`FORCE` vérifiées runtime). **2 risques résiduels hors code, suivis** : (1) le rôle runtime doit être `NOSUPERUSER`/`NOBYPASSRLS`/non-propriétaire (sinon RLS inerte — `copilote` est superuser+BYPASSRLS) ; (2) `/report` auth-exempté → GUC legacy : **décision = documenter legacy-only**, scoping tenant du token de rapport reporté à un sprint dédié.

**Validation runtime (Postgres 16 local + rôle NOSUPERUSER)** : matrice 6 tables verte (7 tests intégration : 6 paramétrés + threading E3-S4) ; rouge→vert démontré (RLS off → rouge, on → vert) ; état RLS des 6 tables vérifié en base (`ENABLE`+`FORCE`+1 policy `ALL` USING==WITH CHECK).

**Version** : 10.52.0
**Tests** : 2 063 backend collectés (2 042 passés, 20 skipped [+5 : matrice 6 tables, skippée hors PG migré], 1 xfailed) ; `ruff`/`mypy app/` verts ; frontend inchangé ; **pas d'eval** (aucun prompt skill ni orchestrateur touché — tests d'intégration RLS uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (matrice prouve les 3 propriétés par table, rouge→vert causal et non vacuous, `WITH CHECK` ne peut pas passer à vide [payloads par ailleurs valides, zéro contrainte CHECK collatérale], grants CI suffisants tables+séquences, doc OWASP factuellement cohérente) — 1 finding cosmétique traité (docstring : privilèges requis SELECT/INSERT/UPDATE/DELETE) ; **qualité** : aucun changement justifié (paramétrage + `_build_insert` retirent déjà la duplication ; connexion par test préférée à un savepoint partagé).

### Sprint 164 — E3-S4 : threading tenant bout-en-bout ✅

**Objectif :** Faire circuler le tenant **authentifié** depuis l'entrée de requête jusqu'aux écritures DB et au cache Redis, pour que l'isolation RLS (Sprint 163) protège les **vrais** tenants — plus seulement le palier legacy. 4ᵉ marche de l'épic E3.

**Décision d'architecture — source unique `ContextVar` :** un seul `ContextVar` `current_tenant` (`app/db/tenant_context.py`) alimente **à la fois** le GUC RLS (couche DB) **et** la colonne applicative `tenant_id` (les 6 sites d'écriture défaultent à `tenant_id or get_current_tenant()`). La colonne écrite égale donc toujours le GUC → le `WITH CHECK` des policies est satisfait par construction, sans threading profond de la pile d'appels (≈15 niveaux) ni risque de divergence à deux sources sous RLS.

**Livrables :**
- `app/middleware/tenant.py` (nouveau) — `TenantContextMiddleware`, **ASGI pur** (pas `BaseHTTPMiddleware`) monté en couche la plus interne : lit `scope["state"]["tenant_id"]` (posé par `BearerTokenMiddleware`), `set`/`reset` du ContextVar dans la **même tâche** que l'endpoint → propagation fiable aux acquisitions de connexion, reset en `finally` (zéro fuite inter-requêtes sous concurrence). Défaut legacy : requêtes non authentifiées / clés API / chemins exemptés.
- `app/db/tenant_context.py` — `ContextVar` + `get/set/reset_current_tenant` ; `apply_tenant_context` (setup du pool, rejoué à chaque acquire) lit désormais `get_current_tenant()` au lieu de la constante figée. `set_current_tenant` fail-safe : claim absent/malformé → legacy.
- **Claim JWT `tenant_id`** : `auth_token_service.create_access_token` porte le tenant (optionnel — token sans claim → legacy en aval) ; threadé depuis `user.tenant_id` aux 3 sites (register/login/refresh). `BearerTokenMiddleware` expose `request.state.tenant_id`.
- **6 sites d'écriture** (`core.py::_persist` + `watchlist`/`annotation`/`esg_history`/`composite_history`/`alert_history`) : défaut `tenant_id or get_current_tenant()`.
- **Cache Redis préfixé tenant** : `analysis_cache._cache_key` → `analysis:{tenant}:{ticker}:{workflow}:{hash}` ; `invalidate()` ciblé sur le tenant courant — un tenant ne sert jamais l'analyse cachée d'un autre.
- **Quotas screener par tenant (M3)** : **différés à un sprint E4 dédié** (hors périmètre du threading — décision de cadrage).

**Validation runtime (Postgres 16 local + rôle NOSUPERUSER `rls_tester`)** : preuve d'isolation de **deux tenants réels** via le chemin réel du sprint (`set_current_tenant` → `apply_tenant_context` setup du pool → GUC → RLS), pas le GUC constant legacy — A n'écrit/ne lit que A, B que B. Non-régression du `ContextVar` sous concurrence (`asyncio.gather` de deux tenants) ; cache : deux tenants, même ticker/workflow/ratios → 2 clés, aucun hit croisé ; rétrocompat non-auth/worker → legacy.

**Version** : 10.51.0
**Tests** : 2 058 backend collectés (2 042 passés, 15 skipped [+1 : isolation threading runtime, skippée hors PG migré], 1 xfailed — +19 : ContextVar set/reset/concurrence + valeur invalide, `apply_tenant_context` tenant courant, middleware ASGI [résolution scope/legacy/reset-on-raise/passthrough], claim JWT présent/absent, threading write-site sans param, isolation cache cross-tenant + non-hit croisé, isolation runtime 2 tenants réels) ; `ruff`/`mypy app/` verts ; frontend inchangé ; pas d'eval (aucun prompt skill ni orchestrateur de skills touché — seul `_persist` côté écriture DB).

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
