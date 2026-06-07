# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-07 — Sprint 170 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.57.0 |
| **Phase active** | Transformation B2B/SaaS — P0→P1 (plan directeur FinTech) |
| **Sprint actif** | Sprint 171 — E4-S6 purge de rétention par plan (`retention_days`) — tâche Celery purgeant analyses/événements au-delà de la rétention du plan de chaque tenant |
| **Dernier sprint complété** | Sprint 170 — E4-S5 endpoint d'agrégation de consommation `GET /usage` : `UsageEventService.aggregate(days)` agrège `usage_events` scopé tenant (RLS, sans `WHERE tenant_id`) → total coût/tokens + ventilation par skill + série quotidienne, exposé via `GET /usage?days=30` typé (`UsageResponse`) authentifié (cookie JWT) ✅ |

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
- `GET /usage?days=30` — **consommation agrégée du tenant courant** depuis `usage_events` (Sprint 170 — E4-S5) : total `cost_usd` + `tokens_input`/`output`, ventilation par skill (`by_skill: UsageBySkill[]` — coût/tokens/compte d'événements) et série quotidienne (`daily_cost`, clé YYYY-MM-DD) ; **authentifié** (cookie JWT), `days` borné 1-365 (`Query(ge=1,le=365)` → 422). Isolation **par la RLS** (contexte tenant serveur, ContextVar→GUC) — **aucun `tenant_id` en query, aucun `WHERE tenant_id` applicatif** ; `UsageEventService.aggregate(days)` reste lecture seule (metering toujours append-only)
- `GET /telemetry/summary|costs|cache|latency` — métriques observabilité (Sprint 18)
- `GET /performance/{ticker}` — rendement rétrospectif par analyse (Sprint 39)
- `POST /auth/register` — inscription email/mot de passe, cookies JWT httpOnly + CSRF (Sprint Login)
- `POST /auth/login` — authentification cookie, rate limiting Redis 5/15 min (Sprint Login)
- `POST /auth/logout` — blacklist JWT jti + invalidation refresh token (Sprint Login)
- `POST /auth/refresh` — rotation refresh token avec détection de vol par famille (Sprint Login)
- `GET /auth/me` — profil utilisateur authentifié via cookie access_token (Sprint Login) ; expose `tenant_id` + `tenant_name` (Sprint 169 — nom résolu par JOIN `tenants` dans `get_by_id`, parité login/register)
- `GET /alerts?limit=50` — historique des alertes Celery (ESG + composite + prix) (Sprint 99)
- `GET /semantic-search?q=&k=5` — recherche sémantique RAG dans `investment_knowledge` ; `rag_enabled=false` + `results=[]` si `OPENAI_API_KEY` absente (Sprint 106)
- `GET`/`PUT /preferences/screener` — préférences Screener (tri + filtres) liées au compte authentifié, table `user_preferences` (JSONB, PK `(user_id, key)`) ; 401 si non authentifié, fallback localStorage côté client (Sprint 124)
- `POST /auth/forgot-password` — token réinitialisation itsdangerous 1h (anti-énumération) (Sprint Login)
- `POST /auth/reset-password` — réinitialisation mot de passe avec token signé (Sprint Login)
- `POST /admin/keys` — créer une clé API (admin only) (Sprint 62) ; la clé est **rattachée au tenant courant** (`api_keys.tenant_id`, Sprint 168) — une requête authentifiée par cette clé s'exécute sous le tenant propriétaire (ContextVar/RLS/quota/metering), plus le tenant legacy
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
- **Auth** — pages register / forgot-password / reset-password, session restaurée au montage (authMe) ; **badge « Espace : <nom> »** (`TenantBadge`, réutilise le composant `Badge` du design system) affiché dans le header dès l'authentification, masqué si le nom de tenant est absent (rétrocompat réponse en cache) (Sprint 169)
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

### Sprint 170 — E4-S5 : endpoint d'agrégation de consommation `GET /usage` ✅

**Objectif :** Rendre le metering (S166) + quotas (S167) **actionnables côté produit** — exposer la consommation agrégée du tenant courant depuis `usage_events`, pour alimenter un futur tableau de bord de facturation et l'affichage « N analyses / coût ce mois ». 5ᵉ marche de l'épic E4. **Sans migration** (`usage_events` existe depuis S166) — sprint lecture + agrégation + endpoint.

**Livrables :**
- `app/services/usage_event_service.py` — nouvelle méthode **lecture seule** `aggregate(days=30)` sur `UsageEventService` (le metering reste append-only ; `aggregate` n'écrit pas) : trois agrégats sur `usage_events` **sous le contexte tenant courant** — total (`SUM cost_usd`/`tokens_input`/`tokens_output`), **ventilation par skill** (`GROUP BY skill` → coût/tokens/`COUNT(*)`), **série par jour** (`to_char(date_trunc('day', created_at), 'YYYY-MM-DD')` → coût, patron `daily_cost` de `core.py:1981`). **Aucun `WHERE tenant_id` applicatif** : l'isolation vient de la RLS (GUC `app.tenant_id` posé par connexion via `apply_tenant_context`) — chaque requête ne voit que les lignes du tenant courant. `cost_usd` (NUMERIC) arrondi à 6 décimales en `float`, cohérent avec `MetricsResponse` ; `COALESCE(SUM(...),0)` → jeu vide rend des zéros (jamais `None`). Fenêtre liée en str (`($1 || ' days')::interval`), même borne temporelle que `get_metrics`.
- `app/models/usage.py` (nouveau) — `UsageResponse` typé (`period_days`, `total_cost_usd`, `total_tokens_input/output`, `by_skill: list[UsageBySkill]`, `daily_cost: dict[str, float]`) + `UsageBySkill` (`skill`, `cost_usd`, `tokens_input`, `tokens_output`, `events`). Zéro `dict` non typé exposé ; modèle distinct de `MetricsResponse` (champs par-skill incompatibles avec `skills_cost: dict[str,float]`).
- `app/api/endpoints/usage.py` (nouveau, routeur dédié — convention « 1 router par domaine ») — `GET /usage?days=30` **authentifié** (`_get_current_user`, cookie JWT, 401 sinon) ; `days: int = Query(default=30, ge=1, le=365)` → **422 hors bornes** (patron idiomatique `telemetry.py`, plus propre que le garde manuel de `/metrics`). Lit le tenant depuis le contexte serveur (claim JWT → ContextVar → GUC) ; **pas de `tenant_id` en query**. Routeur monté dans `app/api/main.py`.
- **CI** (`.github/workflows/ci.yml`) — `test_usage_aggregate_rls.py` ajouté au gate NOSUPERUSER (`usage_events` déjà couverte par le `GRANT` du rôle `rls_tester` depuis S166).

**Validation runtime (Postgres 16 local migré + rôle NOSUPERUSER)** : **isolation RLS de l'agrégation prouvée bout-en-bout** (`test_usage_aggregate_rls.py`) — tenant A enregistre 2 événements (total 0.03) sous son contexte, B un (1.0) ; `aggregate` exécuté sous chaque tenant ne ramène **que** la consommation de ce tenant (A : skill_a/2 événements/0.03, jamais skill_b ; B : 1.0, jamais A), via le chemin réel ContextVar→pool setup→GUC→RLS. **Preuve d'acceptation observable** : `GET /usage` (test d'intégration) retourne la forme agrégée correcte (total + by_skill + daily_cost).

**Version** : 10.57.0
**Tests** : 2 170 backend collectés (2 141 passés, 28 skipped [+1 : isolation RLS agrégation, skippée hors PG migré], 1 xfailed — +12 : unitaires `aggregate` [total/par-skill/par-jour, fenêtre `days` liée en str aux 3 requêtes, jeu vide → zéros, aucun `WHERE tenant_id` applicatif], contrat append-only mis à jour `{record, aggregate}`, intégration `GET /usage` [401 sans session, forme `UsageResponse` agrégée, `days` transmis au service, 422 hors bornes `[0,366,-1]`, `tenant_id` en query ignoré], isolation RLS sous NOSUPERUSER) ; `ruff`/`mypy app/` (163 fichiers) verts ; **frontend non touché** — affichage versé au Sprint 174 (« page Facturation ») comme prévu par la carte ; **pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — agrégation lecture + endpoint uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (isolation par GUC et non filtre applicatif confirmée sur les 3 requêtes ; `days` lié en str comme `get_metrics` ; `COALESCE` sur jeu vide ; auth avant tout travail ; contrat append-only préservé ; test RLS non-vacuous rouge→vert avec garde superuser) — 0 finding CRITICAL/MAJOR, 1 MINOR traité (téardown de la fixture `usage_client` restaurant `app.state`) ; **qualité** (`/simplify` 4 axes) : 2 findings appliqués (validation `days` via `Query(ge/le)` idiomatique vs garde manuel dupliqué ; commentaire `window` allégé), 3 écartés avec justification (3 requêtes séquentielles + modèle distinct + duplication SQL `daily_cost` = délibérément cohérents avec `get_metrics`, l'efficacité jugée correcte pour un endpoint de reporting ; extraction de la fixture auth en `conftest` hors périmètre du diff ; default `30` dupliqué endpoint/service cohérent avec le précédent `/metrics`).

### Sprint 169 — E4-S4 : exposition du tenant dans `/auth/me` ✅

**Objectif :** Rendre le tenant **visible côté client** maintenant que le contexte tenant est threadé (E3-S4) et borné (E4-S2/S3). Exposer `tenant_id` **et le nom du tenant** dans `UserPublic` (préparation UI multi-tenant), en levant la restriction délibérée du Sprint 161 désormais cohérente. 4ᵉ marche de l'épic E4. **Sans migration** (`users.tenant_id` existe depuis le Sprint 161, `tenants.name` depuis le Sprint E3-S1) — lecture/enrichissement de réponse uniquement.

**Livrables :**
- `app/models/auth.py` — `UserPublic` porte désormais `tenant_id: UUID` + `tenant_name: str` (commentaire d'omission du Sprint 161 remplacé par la justification de la levée).
- `app/services/user_service.py` — **résolution du nom de tenant en un seul aller-retour** : `get_by_id` et `authenticate` font un `JOIN tenants t ON u.tenant_id = t.id` (`t.name AS tenant_name`) ; `create_user` utilise une **sous-requête corrélée** dans `INSERT … RETURNING` (`(SELECT name FROM tenants WHERE id = users.tenant_id)`) car `RETURNING` ne supporte pas de `JOIN`. `tenants` et `users` sont **hors RLS** (tables parentes) → le JOIN n'introduit aucune fuite d'isolation. La FK `users.tenant_id → tenants(id)` (Sprint E3-S1) garantit un `tenant_name` non-null.
- `app/api/endpoints/auth.py` — les **3 sites de construction** de `UserPublic` (`/me`, login, register) threadent `tenant_id` + `tenant_name` ; les dicts proviennent respectivement de `get_by_id`/`authenticate`/`create_user` qui retournent désormais tous le nom (aucun `KeyError`). `/refresh` et `/reset-password` lisent `get_by_id` mais n'utilisent que `email`/`role`/`tenant_id` — le nouveau champ est additif et inoffensif.
- **Frontend** — `User` (`frontend/src/types/index.ts`) gagne `tenant_id` + `tenant_name` (snake_case, miroir exact du JSON, zéro `any`) ; nouveau composant `TenantBadge` (réutilise le `Badge` `variant="outline"` du design system) rendu dans le header de `App.tsx` via `user?.tenant_name`, masqué (`return null`) si le nom est absent/vide (rétrocompat réponse `/auth/me` en cache d'avant le sprint).

**Validation runtime (Postgres 16 local migré)** : `UserService` exercé sur le schéma réel — `create_user` (tenant custom **et** legacy) ramène le bon `tenant_name` via la sous-requête corrélée ; `get_by_id` et `authenticate` via le JOIN ; `tenant_name` non-null prouvé (FK). **Preuve d'acceptation observable** : `GET /auth/me` (test d'intégration) retourne `tenant_id` + `tenant_name` corrects, tenant legacy → « Legacy ».

**Version** : 10.56.0
**Tests** : 2 158 backend collectés (2 130 passés, 27 skipped, 1 xfailed — +6 : unitaires `UserService` [`get_by_id` JOIN ramène `tenant_name` / absent → None, `authenticate` JOIN ramène `tenant_name`, `create_user` RETURNING inclut le nom], intégration [`GET /auth/me` expose `tenant_id`+`tenant_name`, tenant legacy → « Legacy »] + assertions tenant ajoutées à `test_register_success`/`test_login_success`) ; `ruff`/`mypy app/` verts ; **frontend 453 Vitest verts** (+4 : `TenantBadge` happy/undefined/empty, header App affiche le nom une fois authentifié) + typecheck/ESLint verts ; **pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — enrichissement de réponse d'authentification uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (3 sites threadés, aucun `KeyError`, JOIN sans fuite RLS, sous-requête corrélée valide + non-null garantie par la FK, tests non-vacuous prouvant le JOIN et la forme de `/auth/me`) — 0 finding CRITICAL/MAJOR/MINOR, 2 NIT traités (FK confirmée `0003_tenants.py:42` + preuve Postgres live ; assertions tenant ajoutées aux endpoints register/login) ; **qualité** (`/simplify` 4 axes) : 1 finding convergent appliqué (`TenantBadge` réutilise le composant `Badge` du design system au lieu d'un `<span>` brut), duplication des 3 constructions `UserPublic` et du JOIN `authenticate`/`get_by_id` conservée (pré-existante, les requêtes diffèrent — `authenticate` sélectionne `hashed_password` ; un fragment partagé serait plus fragile), efficacité jugée négligeable (lookups PK/index).

### Sprint 168 — E4-S3 : clés API rattachées au tenant ✅

**Objectif :** Fermer le dernier trou de la multi-tenance — une requête authentifiée par **clé API** (chemin Bearer) doit s'exécuter sous le tenant **propriétaire de la clé**, pas le tenant legacy. Prérequis pour facturer/quota-borner les appels programmatiques (M4). 3ᵉ marche de l'épic E4.

**Livrables :**
- `alembic/versions/0008_api_keys_tenant_id.py` (nouveau, chaîné après `0007_plan_limits`) — `api_keys.tenant_id UUID NOT NULL REFERENCES tenants(id)` (backfill-avant-NOT-NULL : ADD nullable → UPDATE legacy → SET NOT NULL, pattern Sprint 162/0004) + index `idx_api_keys_tenant`. **Décision documentée** : `api_keys` **reste hors RLS** — c'est la table d'authn lue par le middleware **avant** que le contexte tenant existe (c'est elle qui le pose) ; si elle était sous RLS, `validate_key` tournerait sous le GUC legacy par défaut et ne verrait jamais les clés des autres tenants → authn cassée. Sa colonne `tenant_id` sert à **résoudre** le tenant, pas à isoler la table. N'entre donc PAS dans la matrice RLS (reste 7 tables). Downgrade : index → colonne.
- `app/services/api_key_service.py` — `ApiKeyRecord.tenant_id` exposé ; le `SELECT` de `validate_key` et de `list_keys` le retourne ; `create_key(..., tenant_id=None)` rattache la clé au tenant courant via `resolve_tenant` (ContextVar, défaut legacy hors contexte) — même pattern param→ContextVar que `UsageEventService` (bind `str(tenant)` + cast `$5::uuid`).
- `app/middleware/auth.py` — `BearerTokenMiddleware` pose `request.state.tenant_id = str(record.tenant_id)` sur le chemin clé API (validation réussie), **symétrique au chemin JWT**. Le `TenantContextMiddleware` (E3-S4) pose alors le ContextVar → GUC RLS + quotas (E4-S2) + metering (E4-S1) + écritures défaultent au tenant de la clé. Fallbacks clé env (record `None`) → aucun `tenant_id` posé → legacy.
- **CI** (`.github/workflows/ci.yml`) — le `GRANT` du rôle NOSUPERUSER `rls_tester` couvre désormais `api_keys` ; le gate migré exécute `test_api_key_tenant_integration.py` en plus de la matrice RLS.

**Validation runtime (Postgres 16 local migré + rôle NOSUPERUSER)** : `upgrade head` → `api_keys.tenant_id NOT NULL` + FK + index, **hors RLS** (pas de policy) ; **threading prouvé bout-en-bout via le chemin réel** (`test_api_key_tenant_integration.py`) — une requête HTTP `Bearer <token>` d'une clé du tenant B écrit dans `watchlist` **sous B** (ligne visible sous B, masquée sous legacy par la RLS), pas le tenant legacy ; chemin middleware → ContextVar → setup du pool → GUC → RLS.

**Version** : 10.55.0
**Tests** : 2 152 backend collectés (2 124 passés, 27 skipped [+1 : intégration clé API tenant, skippée hors PG migré], 1 xfailed — +16 : forme migration `0008` [chaînage, colonne+FK+backfill+SET NOT NULL, index, **hors RLS**, downgrade ordre inverse, UUID legacy == constante], unitaires `api_key_service` [`validate_key` expose `tenant_id`, `create_key` rattache au tenant explicite / courant / défaut legacy], threading middleware [clé valide → `request.state.tenant_id` = tenant de la clé ; clé du tenant legacy → legacy ; fallback clé env → legacy], intégration PG migré [écriture sous B via le chemin réel]) ; `ruff`/`mypy app/` verts ; **frontend 449 Vitest verts** (inchangé) + typecheck/ESLint verts ; **pas d'eval** (aucun prompt de skill ni l'orchestrateur de skills touché — résolution de tenant au niveau middleware/service uniquement). Revue indépendante à contexte frais : **correctness CLEAN** (migration conforme [hors RLS confirmé, FK `tenants(id)`, backfill-avant-NOT-NULL, UUID legacy verrouillé], threading symétrique au chemin JWT prouvé, fallbacks clé env → legacy sans crash, `validate_key` lit toute clé car `api_keys` hors RLS, type `str(tenant_id)` cohérent avec `set_current_tenant`, intégration non-vacuous) — 0 finding CRITICAL/MAJOR/MINOR, 2 NIT traités (assertion de test épinglée en position ; clé créée via clé env admin = legacy, design documenté) ; **qualité** (`/simplify`) : diff idiomatique (réutilise les patterns `0004`/`0007`/`UsageEventService`/chemin JWT), 1 finding convergent appliqué (bind `str(tenant)` + cast `::uuid` pour symétrie cross-service), duplication `_execute_each` des migrations conservée (isolation délibérée des artefacts figés).

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
