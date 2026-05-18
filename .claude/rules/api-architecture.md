---
paths:
  - "app/**"
---

# API — Architecture et contraintes globales

## Quand cette règle s'applique

Lors de l'édition de tout fichier dans `app/` — endpoints, services, middleware, workers, rag, observabilité.

## Règles

### Avant de modifier l'infrastructure

Lire `architecture-copilote-financier.md` (sections **3.2, 7.3, 8.2, 9.1, 10, 11.2**) avant toute modification de :
- Configuration Langfuse, Qdrant, Redis ou Celery
- Middlewares auth (`BearerTokenMiddleware`) et rate-limit
- Schéma `analysis_history` PostgreSQL ou toute autre table
- Système de prompt caching

### Modèle Claude

- Modèle par défaut : **`claude-sonnet-4-6`** — lu depuis la variable d'environnement `CLAUDE_MODEL`
- Ne jamais hardcoder le nom du modèle — toujours `self._model` ou `os.getenv("CLAUDE_MODEL")`
- Modèle dans `.env` : `CLAUDE_MODEL=claude-sonnet-4-6`

### Contraintes API obligatoires

| Contrainte | Détail |
|---|---|
| **`cost_usd`** | Calculé depuis `response.usage` après chaque appel Claude, persisté dans `analysis_history` (section 10) |
| **Prompt caching** | Activé sur tous les system prompts de skills via `cache_control` dans `get_system_prompt()` (section 8.2) |
| **Retry exponentiel** | Utiliser `app/utils/retry.py` pour les erreurs 429/529 — pas de retry ad hoc dans les endpoints |
| **Validation tickers** | Utiliser `app/utils/ticker_sanitizer.py` pour normaliser les tickers en entrée |

### Stack infrastructure

| Composant | Version | Usage |
|---|---|---|
| PostgreSQL | 16 | `analysis_history`, `api_keys`, `composite_score_history` |
| Qdrant | v1.9 | Collection `investment_knowledge`, activé si `OPENAI_API_KEY` présente |
| Redis | 7 | Cache analyses + sessions Celery |
| Langfuse | latest | Observabilité LLM, activé si `LANGFUSE_SECRET_KEY` présente (optionnel) |

### Stack service

- Python 3.11, FastAPI ≥ 0.115, Anthropic SDK ≥ 0.40, asyncpg ≥ 0.29, Pydantic v2, Celery
- Tous les appels I/O doivent être async (`asyncpg`, `httpx.AsyncClient`)
- Lifespan FastAPI gère la connexion au pool PostgreSQL et à Qdrant
