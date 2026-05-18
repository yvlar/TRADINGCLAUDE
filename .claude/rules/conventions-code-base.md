# Conventions de code — base universelle

<!-- Rule universelle : chargée à chaque session, tous fichiers confondus. -->

## Quand cette règle s'applique

Toujours — pour tout fichier du projet, toute technologie.

## Règles

### Langue
- **Commentaires, docstrings, noms de variables métier** : français
- **Code** (fonctions, classes, modules, paramètres techniques) : anglais
- Exemples :
  - `async def calculate_graham_number(eps, bvps)` + docstring en français
  - Variable métier : `cout_total` → en code : `cost_usd`
  - Commentaire : `# évite la division par zéro si EPS nul` — pas `# avoid division by zero`

### Typage strict
- TypeScript : **zéro `any`** — utiliser les types de `frontend/src/types/index.ts` ou en créer de nouveaux
- Python : type hints sur toutes les signatures de fonctions, Pydantic v2 pour les structures de données
- Jamais de `cast()` ou `# type: ignore` sans justification commentée

### Async/await
- Tout appel I/O (PostgreSQL via asyncpg, Redis, API Claude, yfinance, httpx) doit être `async/await`
- Jamais de `time.sleep()` ou appel bloquant dans un contexte async — utiliser `asyncio.sleep()`
- Jamais de driver synchrone (psycopg2, requests) dans le service copilote

### Commentaires
- Écrire un commentaire **uniquement si le WHY n'est pas évident** : contrainte cachée, invariant subtil, contournement d'un bug externe
- **Ne pas paraphraser** ce que le code fait déjà — un lecteur peut lire le code
- Ne pas référencer la tâche en cours, le ticket, ou l'auteur dans le code
- Un commentaire sur une seule ligne suffit dans 99 % des cas
- Pas de blocs de commentaires multi-lignes, pas de docstrings décoratifs

## Exemples

```python
# ✅ Correct
async def get_analysis(ticker: str) -> AnalysisResult | None:
    """Retourne la dernière analyse ou None si absente du cache."""
    ...

# ❌ Incorrect — any, synchrone, commentaire paraphrase
def get_analysis(ticker: any) -> dict:
    result = db.query(ticker)  # requête la base de données
    return result
```

```typescript
// ✅ Correct
const calculateGrahamNumber = (eps: number, bvps: number): number =>
  Math.sqrt(22.5 * eps * bvps);

// ❌ Incorrect
const calc = (a: any, b: any) => Math.sqrt(22.5 * a * b);
```
