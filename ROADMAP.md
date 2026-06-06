# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-06-06 — Sprint 165 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.52.0 |
| **Phase active** | Transformation B2B/SaaS — P0 Fondations (plan directeur FinTech) |
| **Sprint actif** | Sprint 166 — E4-S1 metering (`usage_events` append-only par skill, source de vérité facturation) |
| **Dernier sprint complété** | Sprint 165 — E3-S5 preuve d'isolation rouge→vert (matrice cross-tenant paramétrée sur les 6 tables : lecture isolée + `WITH CHECK` + fail-closed, NOSUPERUSER ; gate CI étendu aux 6 tables ; revue OWASP de la policy RLS) ✅ — **clôt l'épic E3** |

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

### Sprint 163 — E3-S3 : Row-Level Security PostgreSQL sur les 6 tables métier ✅

**Objectif :** Poser l'**isolation au niveau base** — `ENABLE ROW LEVEL SECURITY` + policy `tenant_id = current_setting('app.tenant_id')` sur les 6 tables métier, et injecter le GUC `app.tenant_id` par connexion au pool. Le mécanisme RLS + son câblage de contexte ; la matrice d'isolation exhaustive 6 tables relève d'E3-S5. 3ᵉ marche de l'épic E3.

**Livrables :**
- `alembic/versions/0005_business_rls.py` (nouveau) — révision chaînée après `0004_business_tenant_id`. Pour les 6 tables : `ENABLE` + `FORCE ROW LEVEL SECURITY` + `CREATE POLICY <table>_tenant_isolation` (USING + WITH CHECK sur `NULLIF(current_setting('app.tenant_id', true), '')::uuid`). DDL bâti par template sur le tuple `_TABLES` (réutilise le pattern Sprint 162). Downgrade : `DROP POLICY` + `NO FORCE` + `DISABLE`, idempotent.
- **Décisions documentées** : (1) **fail-closed** — GUC absent/vide → `NULL::uuid` → 0 ligne visible (le `NULLIF` neutralise aussi la chaîne vide qui sinon lèverait `22P02`) ; (2) **WITH CHECK** — un tenant ne peut pas écrire la ligne d'un autre ; (3) **FORCE RLS** — le propriétaire de table est lui aussi soumis (défense en profondeur + isolation prouvable en local via rôle NOSUPERUSER).
- `app/db/tenant_context.py` (nouveau) — `apply_tenant_context(conn)` posé comme `setup=` du pool asyncpg : `set_config('app.tenant_id', LEGACY_TENANT_ID, false)` (portée session) à chaque acquisition. Câblé au pool API (`app/api/main.py`) **et aux 7 pools workers** (`app/workers/tasks.py`) — sous `FORCE` RLS, un pool sans GUC verrait 0 ligne et ses INSERT échoueraient au `WITH CHECK`. Palier E3-S3 : tout le monde est « legacy » jusqu'au threading (E3-S4).
- **Périmètre** : RLS + policy + câblage GUC + tests. PAS de threading `current_user`/tenant (E3-S4), PAS de clé cache préfixée tenant (E3-S4), PAS de quotas (E4).

**Validation runtime (Postgres 16 local + gate CI)** : `upgrade head` → `rowsecurity = true` + `forcerowsecurity = true` + une policy ALL (USING+WITH CHECK) par table ; `downgrade` → policies retirées + RLS désactivée ; re-`upgrade` idempotent ; cycle `downgrade base → upgrade head` vert. **Isolation cross-tenant prouvée** (rôle **NOSUPERUSER**) : `SET app.tenant_id = A` ne voit que A, bascule B → seulement B, GUC vide → 0 ligne, INSERT cross-tenant refusé par `WITH CHECK`. Le job CI `migrations` crée un rôle NOSUPERUSER et exécute ce test d'isolation — l'isolation est un gate, pas seulement une preuve locale.

**Version** : 10.50.0
**Tests** : 2 039 backend collectés (2 024 passés, 14 skipped [+1 : isolation runtime, skippée hors PG migré], 1 xfailed — +37 : forme de migration RLS paramétrée sur 6 tables [ENABLE/FORCE/policy USING+WITH CHECK/prédicat fail-closed NULLIF/downgrade], unitaires du câblage GUC, isolation cross-tenant runtime) ; `ruff`/`mypy app/` verts ; frontend inchangé ; pas d'eval (aucun prompt skill ni orchestrateur de skills touché). Revue indépendante à contexte frais : **correctness CLEAN** (fail-closed sain — absent/vide → NULL, pas d'erreur de cast ; policy ALL couvre SELECT/INSERT/UPDATE/DELETE sans échappatoire DELETE ; les 8 pools routent par `apply_tenant_context`, aucun site DB des 6 tables ne le contourne ; `setup` correct pour le reset par-acquisition qu'exigera E3-S4 ; CI prouve l'isolation) — 2 findings traités (isolation câblée en gate CI via rôle NOSUPERUSER ; test de forme verrouille le prédicat dans USING **et** WITH CHECK) ; **qualité** : factory de pool partagée délibérément différée à E3-S4 (où `setup` portera une vraie logique per-requête ; fail-closed backstoppe un pool oublié), `app/db/` retenu comme home (callback connexion, pas middleware ASGI), 2 tests redondants retirés.

### Sprint 162 — E3-S2 : rattacher les 6 tables métier au tenant ✅

**Objectif :** Propager la dimension tenant aux **données** — `tenant_id UUID NOT NULL` (FK → `tenants`) + index sur chacune des 6 tables métier, avec backfill vers le tenant « legacy » (constante `LEGACY_TENANT_ID` posée au Sprint 161). Aucune RLS ni middleware de contexte ici (E3-S3/S4) ; le tenant legacy reste le défaut des écritures tant que le threading n'est pas câblé. 2ᵉ marche de l'épic E3.

**Livrables :**
- `alembic/versions/0004_business_tenant_id.py` (nouveau) — révision chaînée après `0003_tenants`. Pour les 6 tables (`analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`) : `ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)` (nullable) → backfill legacy (`WHERE tenant_id IS NULL`) → `SET NOT NULL` → index `idx_<table>_tenant`. DDL bâti par template sur un tuple `_TABLES` (uniformité prouvable, zéro copier-coller). Downgrade en ordre FK inverse (index → colonne) par table, idempotent. Littéral UUID legacy figé (parité ↔ `LEGACY_TENANT_ID` verrouillée par test).
- **Politique `ON DELETE` documentée** : `NO ACTION` (restrict, défaut PostgreSQL — comme `users.tenant_id` au Sprint 161). Supprimer un tenant **échoue** tant qu'il porte des données métier ; le hard-delete relève d'un sprint dédié, jamais d'un `CASCADE` silencieux.
- **Écritures applicatives** (6 sites d'INSERT) : `core.py::_persist` (analysis_history), `watchlist_service`, `annotation_service`, `esg_history_service`, `composite_history_service`, `alert_history_service` — chacun accepte un `tenant_id: UUID | None = None` (défaut legacy via `tenant_id or LEGACY_TENANT_ID`, idiome partagé avec `user_service`), `tenant_id` ajouté en dernier binding de l'INSERT. `annotation.upsert` : tenant posé à l'INSERT seulement, **non** réécrit en `ON CONFLICT` (ré-annoter ne déplace pas le tenant). Décision d'altitude : **service-level explicit sans DB `DEFAULT`** → tout futur INSERT oubliant le tenant échoue franchement (NOT NULL) au lieu de mal-rattacher silencieusement (prépare le threading E3-S4).

**Validation runtime (Postgres 16 local)** : `upgrade head` → les 6 tables portent `tenant_id NOT NULL` + index `idx_<table>_tenant` + FK `confdeltype=NO ACTION` ; une ligne insérée **avant** la migration dans chaque table est backfillée au legacy ; `DELETE` du tenant legacy **refusé** (données référencées) ; `downgrade 0003` → colonnes/index retirés (0 colonne) ; re-`upgrade head` idempotent ; cycle CI `downgrade base → upgrade head` vert.

**Version** : 10.49.0
**Tests** : 2 002 backend collectés (1 988 passés, 13 skipped, 1 xfailed — +14 : forme de migration paramétrée sur 6 tables [colonne/FK/backfill/ordre backfill-avant-NOT-NULL/index/parité littéral↔constante], écritures défaut-legacy/tenant-explicite des 5 services, défaut legacy de `_persist`) ; `ruff`/`mypy app/` verts ; frontend inchangé ; pas d'eval (aucun prompt skill ni orchestrateur de skills touché). Revue indépendante à contexte frais : **correctness CLEAN** (split DDL sûr, placeholders `$n` alignés aux args aux 6 sites, ON CONFLICT préserve le tenant, binding asyncpg `uuid.UUID`, aucun appelant cassé — défauts présents) ; **qualité** : 1 finding traité (tests d'écriture paramétrés legacy/explicite, 10→5 fonctions), 1 écarté (helper `_load` triplé dans les tests de migration = convention pré-existante, refactor hors périmètre de ce sprint).

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
