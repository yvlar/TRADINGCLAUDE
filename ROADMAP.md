# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-29 — Sprint 125 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.12.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 126 — Vue « Portefeuille » agrégée par pilier |
| **Dernier sprint complété** | Sprint 125 — Annotations enrichies : tags + filtres ✅ |

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB)
- `POST /screen` — screener multi-tickers (max 20, asyncio.gather + Semaphore) ; `ScreenEntry.analyzed_at` = date ISO de l'analyse sous-jacente (cache ou fraîche), None pour les échecs (Sprint 109)
- `DELETE /cache/{ticker}` — invalidation cache admin
- `GET /history?ticker=BNS` — historique paginé par cursor ; `?q=ACHAT` pour recherche cross-ticker (Sprint 73) ; `?tags=value,growth` filtre par tags d'annotation (containment JSONB `@>`, sémantique ET ; aussi sur `/history-paged`) — tags seuls autorisés, 422 si malformé (Sprint 125)
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

### Sprint 125 — Annotations enrichies : tags + filtres ✅

**Objectif :** Ajouter un champ `tags` (mots-clés libres) aux annotations (Sprint 78, jusqu'ici texte libre), filtrable via `GET /history?tags=value,growth`, avec chips affichées et éditables dans l'UI — pour un filtrage sémantique léger du portefeuille sans RAG.

**Livrables :**
- `infra/postgres/migration_sprint125.sql` + bootstrap lifespan (`app/api/main.py`) — colonne `tags JSONB NOT NULL DEFAULT '[]'::jsonb` + index GIN `jsonb_path_ops` sur `annotations.tags`. Choix JSONB (vs `TEXT[]`) pour cohérence avec le schéma existant (`user_preferences`, `analysis_history.result`) et réutilisation du décodage str→list ; opérateur `@>` (containment, sémantique **ET** : une annotation matche si elle contient **tous** les tags demandés)
- `app/models/annotation.py` — `normalize_tags()` (trim/minuscule/dédoublonnage, max 20 tags × 40 car.) ; `tags: list[str]` sur `Annotation` et `AnnotationCreate` (validator de normalisation)
- `app/services/annotation_service.py` — `upsert(analysis_id, note, tags)` persiste les tags (`json.dumps` → `::jsonb`) ; `get`/`get_all_with_ticker` les décodent (`_decode_tags` gère JSONB renvoyé en str par asyncpg)
- `app/orchestrator/core.py` — `HistoryEntry.tags` ; filtre `tags` dans `get_history` ET `get_history_paged` (LEFT JOIN `annotations` aliasé pour lever l'ambiguïté `created_at`, `a.tags @> $N::jsonb` sur requêtes rows + count) ; helper `_row_to_history_entry` partagé
- `app/api/main.py` — `?tags=` (CSV → liste normalisée) sur `/history` et `/history-paged` ; `_parse_tags_param` (422 si présent mais sans tag non vide) ; garde assouplie `ticker | q | tags` (tags seuls autorisés)
- Frontend — `AnnotationSection.tsx` : chips éditables (ajout normalisé via input/Entrée + bouton, suppression, persistance) ; `HistoryTable.tsx` : chips en lecture seule par entrée ; `HistoryPage.tsx` : champ filtre tags câblé vers `getHistoryPaged` ; types `Annotation.tags`/`HistoryEntry.tags` (`frontend/src/types/index.ts`)
- Tests : intégration `tests/api/test_history_filter_tags.py` (forward CSV/multi-tags, tags seuls 200, 422 malformé, `/history-paged`, sérialisation jsonb + décodage au niveau `get_history`, non-match → vide) ; unitaire `tests/services/test_annotation_service.py` (upsert/get tags) ; endpoint `tests/api/test_annotations_endpoint.py` (round-trip tags normalisés) ; composant `AnnotationSection.test.tsx` (ajout/retrait/erreur/lecture seule), `HistoryTableTags.test.tsx` (chips), `HistoryPage.test.tsx` (câblage filtre)

**Version** : 10.12.0
**Tests** : 1 460 backend collectés (1 456 passés, 3 skipped, 1 xfailed — +12 Sprint 125) ; 407 Vitest verts (+7 Sprint 125) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : migration SQL non exécutée live (syntaxe validée ; le filtrage `@>` lui-même s'exécute en SQL, vérifié au niveau construction de requête + décodage sur pool mocké). Pas de test navigateur live. Sprint sans changement de prompt de skill → evals non concernées.

### Sprint 124 — Persistance des préférences Screener côté serveur ✅

**Objectif :** Migrer le tri + les filtres du Screener du `localStorage` (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié, pour offrir une continuité multi-appareils. Le `localStorage` reste un fallback hors-ligne / anti-flash.

**Livrables :**
- `infra/postgres/migration_sprint124.sql` + bootstrap lifespan (`app/api/main.py`) + `init.sql` — table `user_preferences (user_id UUID, key TEXT, value JSONB, updated_at, PRIMARY KEY (user_id, key))` ; FK `REFERENCES users(id) ON DELETE CASCADE` posée par le lifespan + la migration (la table `users` n'existe pas dans le schéma Phase 0 `init.sql`)
- `app/services/user_preferences_service.py` — `get_preference` / `upsert_preference` (asyncpg, `INSERT ... ON CONFLICT (user_id, key) DO UPDATE`) ; `_decode_jsonb` gère JSONB renvoyé en `str` (aucun codec) ou déjà décodé
- `app/api/endpoints/preferences.py` — `GET`/`PUT /preferences/screener`, auth-scopés via `_get_current_user` (cookie JWT) plutôt que `request.state.user_id` (jamais posé en mode dev/test où l'auth est bypassée) ; GET tolère une préférence corrompue (→ `ScreenerPreferences()` au lieu d'un 500) ; schemas Pydantic v2 dédiés (`app/models/preferences.py`)
- `frontend/src/api/preferences.ts` — client typé `getScreenerPreferences`/`putScreenerPreferences` (CSRF/cookies, échec silencieux → `null`)
- `frontend/src/types/index.ts` — types `ScreenerSortKey`/`ScreenerSortState`/`ScreenerPreferences` (source canonique ; `screenerView.ts` réexporte `SortKey`/`SortState`, suppression du doublon)
- `frontend/src/components/ScreenerTable.tsx` — hydratation serveur au montage (fallback localStorage si 401 / réseau KO / champ null), persistance serveur + miroir localStorage à chaque changement de tri/filtre
- Tests : intégration `tests/api/test_preferences_endpoints.py` (401, round-trip, upsert idempotent, 422 clé invalide, JSONB str, valeur corrompue) ; unitaire `tests/services/test_user_preferences_service.py` ; composant `frontend/src/__tests__/ScreenerTablePreferences.test.tsx` (hydratation, filtre serveur, fallback localStorage, persistance)

**Version** : 10.11.0
**Tests** : 1 448 backend collectés (1 444 passés, 3 skipped, 1 xfailed — +6 Sprint 124) ; 400 Vitest verts (+4 Sprint 124) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : la migration SQL n'est pas exécutée live (syntaxe validée + tests d'intégration sur pool stateful mocké). Pas de test navigateur live. Sprint sans changement de prompt de skill → evals non concernées.

### Sprint 123 — Code-splitting des routes + lazy-load recharts ✅

**Objectif :** Accélérer le Time-To-Interactive de la première vue en isolant chaque page et la librairie recharts (lourde) du bundle d'entrée. Avant ce sprint, toutes les pages étaient importées statiquement dans le routeur — le navigateur téléchargeait tout le code (recharts compris) avant le premier rendu.

**Livrables :**
- `frontend/src/App.tsx` — conversion des 14 imports de pages statiques en `React.lazy(() => import('./pages/...'))` (Analyse, Screener, Historique, Dashboard, Watchlist, Comparer, ESG, Recherche, Alertes, Admin + 4 pages auth) ; `<Routes>` enveloppé dans un unique `<Suspense fallback={<RouteFallback />}>` placé sous le shell (header, palette, nav restent eager)
- `frontend/src/components/RouteFallback.tsx` — squelette de chargement de chunk réutilisant la primitive `ui/skeleton` ; respecte `max-w-shell` + tokens de design ; `role="status"` / `aria-busy` / texte `sr-only` pour l'accessibilité
- `frontend/src/__tests__/RouteFallback.test.tsx` — 2 tests Vitest (rend sans erreur + conteneur status `aria-busy` ; respect de `max-w-shell`)
- `frontend/src/__tests__/LazyRouting.test.tsx` — 1 test Vitest déterministe (promesse de chunk contrôlée) : le fallback skeleton apparaît, puis la page lazy le remplace après résolution
- **Découpage vérifié via `vite build`** : un chunk séparé par page (`AnalyzePage`, `DashboardPage`, `ScreenerPage`, … les 14) ; recharts isolé dans des chunks dédiés (`colors`, `YAxis`) chargés uniquement par les pages graphiques (Dashboard/ESG/Watchlist/Comparer) — le bundle d'entrée ne référence que le nom de fichier du chunk, aucun code recharts (0 marqueur interne)

**Version** : 10.10.0
**Tests** : 1 432 backend verts (3 skipped, 1 xfailed — inchangé, sprint frontend pur) ; 396 Vitest verts (+3 Sprint 123) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0), Vitest composant (+3), la vérification du `vite build` (chunks séparés + recharts hors entrée), et la suite backend complète (1 432 verts, ruff clean).

---

## Sprints antérieurs (Sprint 117 → Sprint 0)

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
