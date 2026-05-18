# Sécurité — clés API et secrets

<!-- Rule universelle : chargée à chaque session. -->

## Quand cette règle s'applique

Toujours — en particulier lors de l'ajout de nouveaux services, endpoints, ou variables de configuration.

## Règles

### Clés API et secrets

- **Aucune clé API dans le code** — toujours via variables d'environnement lues depuis `.env`
- **`.env` est dans `.gitignore`** — ne jamais le committer, même pour un test temporaire
- **`.env.example` est obligatoire** et doit contenir toutes les clés requises avec des valeurs exemples non-fonctionnelles

```bash
# .env.example — toutes les clés requises, valeurs clairement non-fonctionnelles
ANTHROPIC_API_KEY=sk-ant-VOTRE_CLE_ICI
OPENAI_API_KEY=sk-VOTRE_CLE_ICI
LANGFUSE_SECRET_KEY=sk-lf-VOTRE_CLE_ICI
LANGFUSE_PUBLIC_KEY=pk-lf-VOTRE_CLE_ICI
POSTGRES_URL=postgresql://copilote:password@localhost:5432/copilote
REDIS_URL=redis://localhost:6379
API_SECRET_KEY=votre-secret-api-ici
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_TIMEOUT_S=120
```

### Ajout d'une nouvelle variable d'environnement

1. Ajouter dans `.env` (local, non commité)
2. Ajouter dans `.env.example` avec valeur exemple clairement factice
3. Documenter dans `architecture-copilote-financier.md` si c'est une variable d'infrastructure

### Autres vecteurs à éviter

- Pas de logging de valeurs sensibles (tokens, clés, mots de passe) dans les logs JSON structurés
- Pas de secrets dans les noms de variables visibles dans les traces Langfuse ou les spans
- Pas de valeurs sensibles dans les messages d'erreur exposés via les endpoints
