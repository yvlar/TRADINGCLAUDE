# Stratégie de tests E2E — TradingClaude (React + FastAPI + PostgreSQL)

*Rôle : Architecte QA principal. Objectif : trouver les bogues avant les utilisateurs.*
*Framework retenu : **Python Playwright (sync) + pytest**, en extension du harnais existant `tests/e2e/` (décision Yves — réutilise les mocks Claude/asyncpg/Redis plutôt que de dupliquer l'infrastructure dans une suite Node séparée).*

---

## 1. Analyse de l'application

### 1.1 Frontend React (`frontend/src/`)

| Élément | Détail |
|---|---|
| **Pages (14)** | Analyze, Screener, History, Dashboard, Watchlist, Compare, Esg, Search, Alerts, Admin, Login, Register, ForgotPassword, ResetPassword |
| **Routes** | `react-router-dom` v6, lazy chunks par page (`React.lazy` + `Suspense`/`RouteFallback`). 10 routes protégées par `<ProtectedRoute>`, 4 routes publiques (auth) |
| **Composants critiques** | `AnalyzeForm`, `ScreenerTable`, `WorkflowSelector`, `CommandPalette` (Ctrl/⌘+K), `Disclaimer`, `ProtectedRoute` |
| **Context API** | `AuthContext` — restaure la session via `authMe()` au montage (cookie httpOnly), expose `login`/`logout`/`isAuthenticated`/`isLoading` |
| **State serveur** | `@tanstack/react-query` (mutations analyze/screen/watchlist, exports PDF/CSV/XLSX) |
| **Hooks perso** | `useAuth`, mutations React-Query, raccourci clavier global (palette) |
| **Gestion d'erreurs** | `data-testid="error-message"` par page ; parsing des erreurs de validation Pydantic (`detail[]`) dans `api/client.ts` |
| **Formulaires + validation** | Login/Register (email + password, force de mot de passe 4 niveaux), AnalyzeForm (ticker + ratios + autofill), Screener (tickers), Watchlist (ticker + workflow) |

### 1.2 Backend Python (`app/`)

| Élément | Détail |
|---|---|
| **Endpoints (~23 routers)** | `auth`, `admin`, `screen`, `analyze_stream`, `watchlist`, `compare`, `*_report`, `export`, `extract`, `performance`, `preferences`, `semantic_search`, `telemetry`, `evals`, `ws_metrics`, … |
| **Authentification** | JWT HS256 access token (15 min, cookie httpOnly) + refresh token UUID opaque (30/90 j, rotation + détection de vol par famille) + CSRF double-submit (cookie non-httpOnly `csrf_token` ↔ header `X-CSRF-Token`) |
| **Middleware** | `BearerTokenMiddleware` (clé API legacy), `CSRFMiddleware`, `RateLimitMiddleware` (Redis) |
| **Permissions** | Rôles `admin`/`reader` ; `_require_admin` sur `/admin/*` ; rate-limit login 5 / 15 min par IP |
| **Validation** | Pydantic v2 sur tous les corps de requête (422 structuré) |
| **Services métier** | `UserService` (argon2), `AuthTokenService`, `PasswordResetService`, `ScreenerService`, `WatchlistService`, PDF, alertes |
| **Tâches async** | Celery (screener planifié, alertes, rapports) |
| **Intégrations externes** | Anthropic (Claude), yfinance, SEDAR+, Qdrant (RAG), OpenAI (embeddings), Langfuse |

### 1.3 Base de données (PostgreSQL 16)

| Entité | Rôle | Contraintes notables |
|---|---|---|
| `users` | Comptes | UNIQUE `LOWER(email)`, `is_active`, `role` |
| `refresh_tokens` | Sessions | FK `user_id` ON DELETE CASCADE, `family`, `used`, `token_hash` UNIQUE |
| `user_preferences` | Prefs serveur | PK composite `(user_id, key)`, FK CASCADE |
| `analysis_history` | Historique analyses | Index GIN trigram (recherche), `cost_usd` |
| `watchlist` | Titres suivis | `price_alert_threshold_pct`, scores/verdict |
| `composite_score_history`, `esg_score_history`, `alert_history`, `api_keys` | Historiques + clés | Index par ticker/date |

---

## 2. Matrice de couverture (risque × priorité)

| Fonctionnalité | Risque | Couverture E2E ajoutée | Priorité |
|---|---|---|---|
| **Connexion (cookie JWT)** | 🔴 Critique | `auth/test_login.py` (7) | P0 |
| **Création de compte** | 🔴 Critique | `auth/test_register.py` (4) | P0 |
| **Session / déconnexion / routes protégées** | 🔴 Critique | `auth/test_session.py` (5) | P0 |
| **Mot de passe oublié / reset** | 🟠 Élevé | `auth/test_password_reset.py` (3) | P1 |
| **Protection des routes + RBAC + CSRF + anti-énumération** | 🔴 Critique | `security/test_security.py` (5+param) | P0 |
| **Analyse individuelle (multi-skills, stream)** | 🔴 Critique | `stock_analysis/test_analyze.py` (6) | P0 |
| **Screener multi-tickers** | 🟠 Élevé | `stock_analysis/test_screener.py` (3) | P1 |
| **Watchlist (CRUD, doublon, vide)** | 🟠 Élevé | `watchlist/test_watchlist.py` (4) | P1 |
| **Historique + recherche sémantique** | 🟡 Moyen | `settings/test_history_and_search.py` (4) | P2 |
| **Budgets de performance perçue** | 🟡 Moyen | `performance/test_performance.py` (3) | P2 |
| **Non-régression (bogues ancrés)** | 🔴 Critique | `regression/test_regressions.py` (5) | P0 |
| Dashboard métriques v2 | 🟡 Moyen | *à étendre* (graphes recharts) | P2 |
| Compare / ESG | 🟢 Faible | *smoke seulement* | P3 |
| Admin (clés API) | 🟠 Élevé | *RBAC couvert, CRUD clés à étendre* | P2 |

**Total ajouté : ~49 tests E2E** répartis sur 8 dossiers + 6 personas + monitoring auto.

---

## 3. Catalogue des scénarios

### Authentification (Happy / Edge / Erreur / Sécurité)
- ✅ Login valide → cookie posé, redirection `/`, header nav
- ⚠️ Mauvais mot de passe → 401, message **générique** (anti-énumération)
- ⚠️ Email inconnu → **même** message que mauvais mot de passe
- ⚠️ Compte suspendu (`is_active=False`) → refusé même avec bon mot de passe
- 🔲 Champs vides → validation client, **aucun** appel réseau
- ✅ « Rester connecté » → TTL refresh étendu
- 🔁 Register valide → redirection `/login` ; email existant → **409** lisible
- 🔑 Reset : token invalide → **400** ; forgot connu/inconnu → **réponse identique 204**

### API — codes HTTP par endpoint
Pour chaque endpoint critique (`/analyze`, `/screen`, `/watchlist`, `/auth/*`), un scénario par code pertinent simulé via interception (`helpers/network.py`) :
`200` (happy) · `400/422` (validation) · `401` (session) · `403` (RBAC admin) · `404` · `409` (doublon/email) · `429` (rate-limit login) · `500` (dégradation gracieuse).

### Analyse / Screener / Watchlist
- Happy path complet (autofill → verdict Graham rendu)
- Workflow alternatif (Lynch) routé correctement
- Backend 500 / API coupée / JSON corrompu → **message d'erreur, jamais d'écran blanc ni d'Error Boundary**
- Watchlist : ajout, doublon refusé, liste vide, erreur de chargement

### Sécurité
- Toutes les routes protégées redirigent sans session (paramétré ×10)
- Aucun secret (JWT/hash) en `localStorage`
- `access_token` httpOnly, `csrf_token` présent
- Session révoquée (401 `/auth/me`) → retour `/login`

### Performance
- TTI login < 6 s · chaque chunk lazy < 5 s · pas de spinner persistant au montage

---

## 4. Mécanismes anti-défaut silencieux

Chaque parcours « happy path » se termine par `assert_page_clean(monitor)`, qui **échoue automatiquement** si l'un de ces signaux est capté (`helpers/monitoring.py`) :

| Côté | Signal détecté | Détection |
|---|---|---|
| **React** | `console.error`, Unhandled Promise Rejection, Error Boundary, Hydration Error | `page.on("console")` + `page.on("pageerror")` + motifs `_REACT_FAULT` |
| **Backend** | `Traceback`, `Internal Server Error`, `ValidationError`, `DatabaseError`, `IntegrityError`, `TimeoutError` | inspection des corps de réponse ≥ 500 + console |
| **Réseau** | toute réponse ≥ 400 inattendue, `requestfailed` | `page.on("response")` / `page.on("requestfailed")`, avec liste blanche `allow_status` par test |

Les codes d'erreur **attendus** (un test qui provoque délibérément un 401/404/500) sont déclarés via `allow_status=[...]` pour ne pas masquer les vrais défauts.

---

## 5. Données de test — 6 personas

`fixtures/personas.py` seed un `InMemoryUserService` (argon2 réel) injecté dans `app.state.user_service` :

| Persona | Email | Rôle | Particularité |
|---|---|---|---|
| `empty` | vide@test.local | reader | Aucune donnée |
| `standard` | standard@test.local | reader | Usage nominal |
| `premium` | premium@test.local | reader | Usage intensif |
| `admin` | admin@test.local | **admin** | Accès `/admin` |
| `suspended` | suspendu@test.local | reader | `is_active=False` → login refusé |
| `massive` | massif@test.local | reader | Historique massif (simulé par interception réseau) |

> **Pourquoi un service en mémoire ?** Le harnais mocke `asyncpg.create_pool` génériquement : le vrai flux email/mot de passe ne pouvait pas authentifier (→ 401 systématique), ce qui rendait `authenticated_page` muet sur les régressions d'auth. `InMemoryUserService` rejoue le contrat de `UserService` pour que le cookie JWT traverse réellement le navigateur, sans PostgreSQL.

---

## 6. Régression automatique

Convention : `tests/e2e/regression/`, un test par bogue `test_BUGNNN_<desc>`, ancré de façon permanente.

```python
def test_BUG004_reponse_analyse_corrompue_ne_crashe_pas_react(authenticated_page):
    """BUG-004 — Un JSON d'analyse tronqué ne doit pas déclencher d'Error Boundary."""
    ...
```

---

## 7. Rapport final

### Couverture estimée
- **Parcours critiques (P0) : ~90 %** — auth, sessions, analyse, sécurité des routes, non-régression.
- **Parcours élevés (P1) : ~70 %** — screener, watchlist, reset password.
- **Parcours moyens (P2/P3) : ~30 %** — dashboard recharts, compare, ESG, CRUD clés admin (smoke + RBAC seulement).

### Zones à risque identifiées (défauts réels)
1. **🔴 BUG-001 — E2E d'auth obsolètes.** `tests/e2e/test_e2e_auth.py` (et `authenticated_page`) testent un écran « Clé API » **disparu**. L'app utilise email/mot de passe + cookie JWT depuis le sprint auth. Les anciens E2E donnaient une **fausse assurance**. → ancré dans `regression/test_regressions.py::test_BUG001`.
2. **🔴 BUG-002 — Restauration de session.** Si `/auth/me` renvoie 401 (token expiré/révoqué), l'app doit retomber sur `/login` et ne **jamais** laisser une route protégée visible. → `test_BUG002` + `security/test_security.py`.
3. **🟠 BUG-004 — Robustesse parsing.** Réponse JSON tronquée → vérifier l'absence d'Error Boundary (écran blanc). → `test_BUG004`.
4. **🟠 BUG-005 — Doublon watchlist.** Le contrôle de doublon n'existe que dans `InMemoryWatchlistService` (E2E), **pas** dans la vraie DB → risque de divergence prod/test à confirmer côté backend.

### Tests manquants (backlog priorisé)
- [ ] Dashboard : rendu des graphes recharts (coût quotidien, top tickers, drilldown skill) avec données vides / massives.
- [ ] Admin : cycle complet de gestion des clés API (création → 403 pour reader → suppression).
- [ ] Rate-limit login réel (429 après 5 tentatives) — actuellement le harnais lève la limite ; à tester avec un compteur fakeredis dédié.
- [ ] Refresh token rotation + détection de vol (parcours multi-onglets).
- [ ] Export PDF/CSV/XLSX : déclenchement du téléchargement (events `download`).
- [ ] WebSocket `/ws/metrics` : connexion, message, reconnexion.
- [ ] Compare & ESG : parcours fonctionnels au-delà du smoke.

### Recommandations
1. **Remplacer** les anciens `test_e2e_*.py` (racine `tests/e2e/`) par la nouvelle arborescence ; ils ciblent un flux d'auth mort et faussent la confiance.
2. **Intégrer les E2E au CI** dans un job dédié (`playwright install chromium` + `npm run dev &`), exécuté sur `dev` (pas bloquant master au début), avec upload des traces/vidéos en cas d'échec.
3. **Aligner le contrôle de doublon watchlist** entre la vraie `WatchlistService` (DB) et l'in-memory, sinon BUG-005 restera invisible en prod.
4. **Activer `expect` tracing** (`browser.new_context(record_video_dir=...)`, `tracing.start`) pour le débogage des échecs CI.
5. **Étendre les personas** vers des données réellement seedées (analysis_history) quand un Postgres éphémère sera disponible en CI, pour tester la pagination « massive » de bout en bout.

---

## 8. Comment exécuter

```bash
# 1. Dépendances + navigateur
pip install -r requirements-dev.txt
playwright install chromium

# 2. Frontend (doit tourner sur :5173)
cd frontend && npm run dev          # laisser ouvert

# 3. Tous les E2E
pytest tests/e2e/ -m e2e -v

# Sous-ensembles
pytest tests/e2e/auth -m e2e
pytest tests/e2e/ -m regression
pytest tests/e2e/ -m performance
pytest tests/e2e/security -m e2e --headed   # debug visuel
```

Le harnais démarre FastAPI (uvicorn thread, port 8000) avec Claude/DB/Redis mockés ; les tests **skip** proprement si le serveur Vite (`:5173`) n'est pas accessible.
```
Browser (Playwright) → Vite :5173 (proxy) → FastAPI :8000 (thread)
                                                  ↓ Claude stubbé · asyncpg mocké
                                                    fakeredis · InMemoryUserService
                                                    InMemoryWatchlistService
```
