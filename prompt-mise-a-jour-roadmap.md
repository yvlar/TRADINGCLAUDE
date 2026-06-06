# Sprint 154 — Sécurité fail-closed : CSRF / CORS / comparaison timing-safe (E1-S1)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.39.0 — pivot stratégique 2026-06-05)

La roadmap **bascule** de la cadence « outil d'analyse » vers la **transformation B2B/SaaS** décrite dans le **plan directeur `docs/plan-directeur-fintech-2026.md`** (audit → 44 sprints `E#-S#`, phases P0→P3). **Sprint 154 = E1-S1**, premier des ~15 sprints **P0 (fondations)**. Le backlog analyse-tool antérieur (provenance PDF par ticker, etc.) est **parqué** — récupérable via l'historique git de ce fichier.

> **État courant complet** (version, fonctionnalités, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas.

> **Sprint backend/sécurité pur** — aucun prompt de skill ni l'orchestrateur modifié → **evals non concernées**. `ANTHROPIC_API_KEY` absente du conteneur web ; stack Docker non démarrée ; pas de test navigateur live. Frontend **non touché** (tsc/vitest/eslint restent verts sans modif).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (déjà injecté comme *project instructions* — ne pas le relire avec un outil)
2. `ROADMAP.md` — état courant v10.39.0
3. `docs/plan-directeur-fintech-2026.md` — **§3.3 (Sécurité OWASP)** + **§7 épic E1** (ce sprint = E1-S1, et la suite E1-S2→S4)
4. `.claude/rules/securite.md` — secrets via `.env`, pas de fuite dans logs/erreurs
5. `.claude/rules/api-architecture.md` — impose de lire `architecture-copilote-financier.md` (**sections 3.2, 7.3, 9.1, 11.2**) **avant toute modification des middlewares auth/rate-limit**

---

## TÂCHE — Sprint 154 (E1-S1) : rendre la sécurité *fail-closed*

**Objectif** : trois trous de configuration *fail-open* font qu'une mauvaise variable d'environnement en production **désactive silencieusement** des protections. Les fermer en répliquant le patron canonique déjà présent dans le repo (`resolve_jwt_secret`), où **`APP_ENV` absent = production = défaut sûr (refus)**.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **🔴 Bypass CSRF sur `API_KEY` vide** — `app/middleware/csrf.py:64-66` :
   ```python
   # Dev mode : API_KEY vide → bypass (cohérent avec BearerTokenMiddleware)
   if not os.environ.get("API_KEY", ""):
       return await call_next(request)
   ```
   En prod, si `API_KEY` n'est pas posée, **toute protection CSRF saute**. Doit dépendre de `APP_ENV`, pas de la présence d'`API_KEY`.
2. **🟠 Comparaison CSRF non timing-safe** — `app/middleware/csrf.py:77` : `if csrf_cookie != csrf_header:` → remplacer par `hmac.compare_digest`.
3. **🟠 Fallback CORS localhost si `CORS_ORIGINS` vide** — `app/api/main.py:599-609` : `_cors_origins_env = os.environ.get("CORS_ORIGINS", "")` puis repli sur `http://localhost:5173`… si vide. En prod, une variable oubliée ⇒ origines de dev acceptées avec `allow_credentials=True` (`:613`).
4. **✅ Patron fail-fast canonique à RÉUTILISER** — `app/utils/jwt_secret.py:9,12-36` : `_DEV_ENVS = {"dev","development","test","testing"}` ; `resolve_jwt_secret()` lit `APP_ENV` (`:25`), tolère le repli **uniquement** si `app_env in _DEV_ENVS`, sinon `raise RuntimeError` (`:33`). **`APP_ENV` absent → traité comme production** (le défaut sûr). C'est exactement la logique à généraliser.
5. **⚠️ Couplage `BearerTokenMiddleware`** — le commentaire `csrf.py:64` dit « cohérent avec BearerTokenMiddleware ». Ce middleware est monté en `app/api/main.py:597` (`BearerTokenMiddleware, api_key=_api_key_env`). **Le localiser** (probable `app/middleware/auth.py`) et vérifier s'il bypasse aussi sur `API_KEY` vide — si oui, **l'aligner sur le même garde** `APP_ENV` (sinon on ferme CSRF mais on laisse l'auth Bearer ouverte).

### Spécification

1. **Helper partagé `app/utils/env.py`** (nouveau) : `is_dev_environment() -> bool` — `APP_ENV.strip().lower() in _DEV_ENVS` (réutiliser/déplacer `_DEV_ENVS` depuis `jwt_secret.py` pour une **source unique**). Refactorer `resolve_jwt_secret()` pour consommer ce helper (pas de duplication de la liste).
2. **CSRF fail-closed** (`csrf.py:64-66`) : remplacer le test `not API_KEY` par `if is_dev_environment(): return await call_next(request)`. En prod, le CSRF s'applique **même si `API_KEY` est vide**.
3. **CSRF timing-safe** (`csrf.py:77`) : `import hmac` ; `if not hmac.compare_digest(csrf_cookie, csrf_header):` (garder le `403` + le `logger.warning`). La garde « manquant » `:71` reste inchangée.
4. **CORS fail-fast** (`main.py:599-609`) : si `not _cors_origins_env` **et** `not is_dev_environment()` → `raise RuntimeError("CORS_ORIGINS est obligatoire hors développement …")` (mêmes mots-clés que `jwt_secret.py:33-36`). Le repli localhost n'est conservé **que** en dev/test.
5. **Alignement `BearerTokenMiddleware`** (si le point 5 ci-dessus confirme le bypass) : même garde `is_dev_environment()`. Si l'aligner dépasse le périmètre raisonnable d'un sprint, **le documenter explicitement** et le sortir en E1-S1bis — ne pas le laisser silencieux.
6. **Périmètre** : middlewares + bootstrap CORS uniquement. Aucune migration, aucun skill, aucun frontend, aucun changement de contrat d'API.

### Tests obligatoires (pyramide — fixture `client`, cf. `.claude/rules/tests-pyramide.md`)
- **CSRF prod fail-closed** : `APP_ENV` non-dev (ou absent) + `API_KEY` vide + POST authentifié par cookie **sans** `X-CSRF-Token` → **403** (avant : 200). 
- **CSRF dev** : `APP_ENV=dev` → bypass conservé (rétrocompat dev). Requête `Authorization: Bearer …` → toujours exemptée (`:61-62`).
- **CSRF timing-safe** : cookie ≠ header → 403 ; cookie == header → passe ; vérifier l'usage de `hmac.compare_digest` (pas de `!=`).
- **CORS fail-fast** : construire l'app avec `APP_ENV=prod` + `CORS_ORIGINS` vide → `RuntimeError` ; `APP_ENV=dev` → repli localhost ; `CORS_ORIGINS="https://app.x"` → origines respectées.
- **`is_dev_environment`** unitaire : `dev/development/test/testing` → `True` ; `prod`/absent/`""` → `False`.
- **Non-régression** : `pytest` (hors e2e/evals) + `ruff` + `mypy app/ --ignore-missing-imports` verts.

### Note d'environnement (session web)
Tests middleware via le `TestClient` FastAPI (pas de Docker, pas de live). **Vérifier en début de session que le canal d'exécution rend bien la sortie des commandes.**

---

## SPRINTS SUGGÉRÉS (suite de l'épic E1 puis E2 — voir plan directeur §7)

### Sprint 155 — E1-S2 : durcir l'identité de requête + brute-force
**Objectif** : X-Forwarded-For lu seulement derrière un proxy de confiance (anti-spoof du rate-limit) ; rate-limit Redis sur la validation de clé API ; secret PostgreSQL généré obligatoire (≠ `copilote`).
**Complexité** : Faible/Moyenne.
**Référence** : EXISTANT (vérifié) — IP client dans `app/middleware/rate_limit.py` (`request.client.host`) ; `validate_key` dans `app/services/api_key_service.py` ; mot de passe PG par défaut dans `docker-compose.yml`. À CRÉER — liste d'IP de confiance + rate-limit clé.

### Sprint 156 — E1-S3 : confidentialité au repos & assainissement des logs
**Objectif** : assainisseur regex (tokens/clés/emails) avant tout log ; bannir `exc_info` complet en prod ; activer le chiffrement at-rest (volume/DB managée, Redis TLS).
**Complexité** : Moyenne.
**Référence** : EXISTANT (vérifié) — `app/utils/error_sanitization.py` (`log_internal_error`, `correlation_id`) ; `app/observability/`. À CRÉER — filtre de redaction + config infra.

### Sprint 157 — E1-S4 : dette crypto JWT (`python-jose` → `PyJWT`)
**Objectif** : remplacer `python-jose` (non maintenu) par `PyJWT` + pin `cryptography` ; ajouter `pip-audit`+`bandit` au CI.
**Complexité** : Moyenne.
**Référence** : EXISTANT (vérifié) — `python-jose[cryptography]>=3.3.0` dans `requirements.txt` ; signature/décodage dans `app/services/auth_token_service.py` (HS256). À VÉRIFIER — parité d'API JWT (claims, exp, jti) ; non-régression login/refresh/logout.

### Sprint 158 — E2-S1 : introduire Alembic (socle migrations)
**Objectif** : versionner le schéma (prérequis indispensable avant E3 multi-tenance) ; baseline = schéma actuel, env async asyncpg, `upgrade`/`downgrade` idempotents en CI.
**Complexité** : Moyenne.
**Référence** : EXISTANT (vérifié) — migrations actuellement **inline dans le lifespan** `app/api/main.py:159-313` (`CREATE TABLE IF NOT EXISTS …`) ; migrations ad hoc `infra/postgres/migration_sprint*.sql`. À CRÉER — `alembic/`, `alembic.ini`.

---

## Template de démarrage

```
Tu es un développeur Python senior sur le projet TradingClaude.
Lis d'abord CLAUDE.md, ROADMAP.md (v10.39.0), docs/plan-directeur-fintech-2026.md (§3.3 + §7 E1),
.claude/rules/securite.md, .claude/rules/api-architecture.md.
Sprint actif : 154 — Sécurité fail-closed (E1-S1, piste transformation B2B/SaaS).

CONTEXTE : 3 garde-fous sont fail-open. Patron canonique à réutiliser = app/utils/jwt_secret.py
(APP_ENV absent = production = refus). _DEV_ENVS = {dev,development,test,testing}.

TÂCHE :
1. app/utils/env.py (nouveau) : is_dev_environment() ; déplacer _DEV_ENVS depuis jwt_secret.py
   (source unique) et refactorer resolve_jwt_secret pour le consommer.
2. csrf.py:64-66 : bypass = is_dev_environment() (PAS « API_KEY vide »).
3. csrf.py:77 : hmac.compare_digest (import hmac), garder 403 + warning.
4. main.py:599-609 : si CORS_ORIGINS vide ET not is_dev_environment() → RuntimeError ;
   repli localhost conservé seulement en dev/test.
5. BearerTokenMiddleware (main.py:597, probable app/middleware/auth.py) : localiser ;
   si bypass sur API_KEY vide, aligner sur is_dev_environment() — sinon documenter en E1-S1bis.
PÉRIMÈTRE : middlewares + bootstrap CORS. Aucune migration, aucun skill, aucun frontend.

TESTS (fixture client) : CSRF prod sans API_KEY → 403 ; dev → bypass ; Bearer exempté ;
compare_digest ; CORS prod+vide → RuntimeError, dev → localhost, défini → respecté ;
is_dev_environment unitaire.
GATES vertes avant commit :
  .venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q
  .venv/bin/ruff check app/ tests/
  .venv/bin/mypy app/ --ignore-missing-imports
Compteurs MESURÉS pour le ROADMAP (pas d'estimation).
Branche dédiée (claude/sprint154-securite-fail-closed), PR base = dev. Confirmer avant git push / PR.
```
