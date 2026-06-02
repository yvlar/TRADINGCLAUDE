# Tests E2E — Sprint 30 (étendu : stratégie QA E2E)

Tests end-to-end traversant le vrai frontend React → vrai backend FastAPI.
**Aucun token Anthropic consommé** : `call_claude_with_retry` est mocké dans chaque module skill.

> 📋 **Stratégie complète** : voir [`STRATEGIE-QA-E2E.md`](STRATEGIE-QA-E2E.md) — analyse front/back/DB,
> matrice de couverture, catalogue de scénarios, personas, monitoring anti-défaut, rapport final.

## Arborescence (stratégie QA)

```
tests/e2e/
├── STRATEGIE-QA-E2E.md      # stratégie + matrice + rapport
├── conftest.py              # harnais : uvicorn + mocks + personas + fixtures monitoring
├── fixtures/
│   ├── claude_stubs.py      # réponses Claude stubbées
│   └── personas.py          # 6 personas + InMemoryUserService (auth cookie JWT réelle)
├── pages/                   # Page Objects (base, auth_pages, app_pages)
├── helpers/                 # monitoring (console/réseau/React), assertions, network mocks
├── auth/                    # login, register, session, password reset
├── watchlist/               # CRUD watchlist (« portefeuille » suivi)
├── stock_analysis/          # analyse individuelle + screener
├── settings/                # historique + recherche
├── regression/              # test_BUGNNN_* — non-régression ancrée
├── performance/             # budgets de performance perçue
└── security/                # routes protégées, RBAC, CSRF, anti-énumération
```

> ⚠️ **Legacy à retirer** : `test_e2e_auth.py` (et le flux « Clé API ») ciblent un écran
> de connexion **disparu** — l'app utilise email/mot de passe + cookie JWT. Conservés
> temporairement ; remplacés par `auth/`. Voir BUG-001 dans `regression/`.

## Architecture

```
Browser (Playwright) → Vite :5173 (proxy) → FastAPI :8000 (uvicorn thread)
                                                    ↓
                                        Claude mocké (stubs JSON)
                                        PostgreSQL mocké (asyncpg mock)
                                        Redis (fakeredis)
                                        Watchlist (InMemoryWatchlistService)
```

## Prérequis

```bash
# 1. Installer les dépendances Python de développement
pip install -r requirements-dev.txt

# 2. Installer les navigateurs Playwright
playwright install chromium

# 3. Démarrer le Vite dev server (doit rester ouvert)
cd frontend && npm run dev
```

## Lancer les tests

```bash
# Tous les tests E2E
pytest tests/e2e/ -v -m e2e

# Un fichier spécifique
pytest tests/e2e/test_e2e_analyze.py -v

# Avec sortie visible (pas headless)
pytest tests/e2e/ -v --headed
```

## Structure

```
tests/e2e/
├── conftest.py              # Fixtures de session : uvicorn + mocks
├── fixtures/
│   └── claude_stubs.py      # Réponses Claude stubbées (15 skills)
├── test_e2e_auth.py         # 4 tests : login, déconnexion, redirections
├── test_e2e_analyze.py      # 5 tests : analyse BNS, workflow Lynch, erreurs
├── test_e2e_screener.py     # 3 tests : tableau, badges, majuscules
└── test_e2e_watchlist.py    # 4 tests : CRUD watchlist, doublon, liste vide
```

## Isolation des mocks

Les 15 skills importent `call_claude_with_retry` localement :
```python
from app.utils.retry import call_claude_with_retry
```

Le patch doit cibler **chaque module** (ex: `app.skills.tier2.graham_analysis.skill.call_claude_with_retry`),
et non `app.utils.retry.call_claude_with_retry` (qui serait ignoré).

## Watchlist en mémoire

`InMemoryWatchlistService` remplace `WatchlistService` en mémoire pour les tests E2E.
Il ajoute un contrôle de doublon (ticker + workflow) absent de la vraie DB.
