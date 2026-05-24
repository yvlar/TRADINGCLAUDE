# Prompt — Sprint Indépendant Authentification (Login & Création de compte)

## CONTEXTE

Tu travailles sur un sprint indépendant dédié exclusivement au système
d'authentification de TradingClaude — copilote financier IA.

Ce sprint est développé EN PARALLÈLE du processus principal géré par
`prompt-mise-a-jour-roadmap.md`.

IMPORTANT :

- Lire `prompt-mise-a-jour-roadmap.md` avant toute modification.
- Lire `CLAUDE.md` et les règles dans `.claude/rules/` — elles sont
  contraignantes (conventions bilingues FR/EN, typage strict, async/await).
- Mettre à jour `ROADMAP.md` et `prompt-mise-a-jour-roadmap.md` en fin
  de sprint selon `workflow-sprint.md`.
- Ne pas créer de divergence d'architecture avec les sprints existants
  (api_keys, BearerTokenMiddleware, AuthContext).
- Toute nouvelle table PostgreSQL doit être documentée dans
  `architecture-copilote-financier.md`.

---

## OBJECTIF DU SPRINT

Créer un système complet de :

- création de compte utilisateur
- connexion email + mot de passe
- gestion de session avec refresh token rotation
- récupération de mot de passe
- sécurité des comptes

Le système doit être :

- professionnel, moderne, sécurisé, scalable, production-ready, UX-first
- **rétrocompatible** avec la table `api_keys` et `BearerTokenMiddleware`
  existants (accès programmatique par clé API non impacté)

---

## STACK TECHNIQUE IMPOSÉE

### Frontend

- React 18 + TypeScript strict (**zéro `any`**)
- Vite 8 — port 5173, proxy vers API `localhost:8000`
- Tailwind CSS 4 + shadcn/ui (`frontend/src/components/ui/`)
- React Hook Form + Zod (validation frontend uniquement)
- React Router v6 (`useNavigate`, `<Navigate>`)
- Tests : Vitest + `@testing-library/react`

### Backend

- Python 3.11, FastAPI ≥ 0.115, Pydantic v2
- asyncpg — requêtes SQL async directes (pas d'ORM)
- argon2-cffi — hachage des mots de passe
- python-jose — JWT HS256
- slowapi — rate limiting
- itsdangerous — tokens CSRF + reset password
- Redis 7 — blacklist JWT + cache sessions
- Logs structurés JSON via `app/logging_config.py`
- Tests : pytest + httpx AsyncClient

### Conventions obligatoires (`.claude/rules/`)

- Commentaires et docstrings en **français**, code (fonctions, classes) en
  **anglais**
- Type hints sur toutes les signatures Python, zéro `any` TypeScript
- Tout appel I/O : `async/await` (asyncpg, httpx.AsyncClient, Redis)
- Jamais `time.sleep()`, jamais de driver synchrone
- Logs via `logging` (jamais `print`)
- Commentaires WHY uniquement — pas de paraphrase du code

---

## EXIGENCES UX

### 1. Création de compte (`/register`)

Formulaire minimaliste avec composants shadcn/ui :

- Email (`Input` + validation temps réel Zod)
- Mot de passe (`Input` type password + toggle œil)
- Indicateur visuel de force du mot de passe (barre 4 niveaux, Tailwind)
- Support `autocomplete` HTML (`email`, `new-password`)
- Jamais bloquer le copier-coller
- Message de valeur : "Accédez à 18 frameworks d'analyse — Graham, Buffett,
  ESG et plus encore"
- Responsive mobile-first
- États loading / disabled pendant la requête
- Lien "Déjà un compte ? Se connecter"
- Dark mode via classe Tailwind (`class` strategy)
- Accessibilité WCAG — `aria-label`, rôles sémantiques

Architecture OAuth prévue (non implémentée ce sprint) :

- Google, GitHub — colonnes `oauth_provider` / `oauth_id` en DB

### 2. Connexion (`/login`)

- Email + mot de passe
- Compatible gestionnaires de mots de passe
  (`autocomplete="current-password"`)
- Jamais bloquer le copier-coller
- Message d'erreur générique sécurisé :
  **"Email ou mot de passe incorrect"** — ne jamais révéler si le compte
  existe
- Lien "Mot de passe oublié ?"
- Checkbox "Rester connecté" (refresh_token 90 jours vs 30 par défaut)
- État loading + bouton disabled pendant la requête
- Lien "Pas encore de compte ? S'inscrire"

### 3. Mot de passe oublié

- Saisie email → email avec lien token expirant 1h (itsdangerous)
- Page `/reset-password?token=...` : nouveau mot de passe + confirmation
- Invalider le token après usage (one-shot)
- Même délai de réponse si email inconnu (anti-enumération)

---

## SÉCURITÉ

### Mots de passe

- Minimum : 12 caractères, majuscule, minuscule, chiffre, caractère spécial
- Hachage : argon2-cffi (`time_cost=2, memory_cost=65536, parallelism=2`)
- Jamais logger un mot de passe, même partiel

### Tokens

- `access_token` : JWT HS256, TTL 15 min, claims : `sub` (user UUID),
  `exp`, `iat`, `jti`
- `refresh_token` : UUID v4 opaque, TTL 30 jours, stocké en DB
- Blacklist `jti` dans Redis sur logout (TTL = durée restante du token)
- **Jamais localStorage pour tokens sensibles** — cookies uniquement

### Cookies

- `access_token` : `httpOnly`, `Secure`, `SameSite=Strict`
- `refresh_token` : `httpOnly`, `Secure`, `SameSite=Strict`,
  `Path=/auth/refresh`

### Brute force

- Rate limiting : 5 tentatives / 15 min sur `POST /auth/login` via slowapi
- Réponse identique si email inconnu (timing-safe avec `hmac.compare_digest`)

### CSRF

- Token CSRF dans cookie non-httpOnly + header `X-CSRF-Token` sur mutations
- Validation dans un middleware FastAPI dédié

### Refresh token rotation

- Nouveau refresh_token émis à chaque usage, ancien invalidé en DB
- Détection de réutilisation → invalider toute la famille (vol détecté)

### MFA / 2FA — architecture prête, non implémentée

- Colonnes `mfa_secret`, `mfa_enabled` dans la table `users`
- Stubs : `POST /auth/mfa/setup`, `POST /auth/mfa/verify` (TOTP HMAC)

### Logs de sécurité

Logguer en JSON structuré via `app/logging_config.py` :

- login réussi / échoué, logout, reset demandé, email vérifié,
  token réutilisé (vol détecté)

---

## ARCHITECTURE ATTENDUE

### Backend — nouveaux fichiers
