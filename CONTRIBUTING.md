# Contribuer à TradingClaude / Contributing to TradingClaude

Merci de l'intérêt porté à ce projet. Ce guide explique comment configurer l'environnement local,
les conventions à respecter et le workflow pour soumettre des contributions.

---

## Prérequis / Prerequisites

- Docker Desktop ≥ 4.x
- Python 3.11
- Node.js 20 + npm
- Git

---

## Installation locale / Local setup

### 1. Infrastructure (Docker Compose)

```bash
git clone https://github.com/YOUR_USERNAME/tradingClaude.git
cd tradingClaude

cp .env.example .env
# Remplir les clés API dans .env (ANTHROPIC_API_KEY, etc.)

docker-compose up -d
curl localhost:8000/healthz
```

### 2. Backend FastAPI

```bash
pip install -r requirements.txt
# Le serveur FastAPI tourne dans Docker ; pour développement local :
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend React

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173 (proxy vers :8000)
```

---

## Conventions bilingues FR/EN

| Couche | Langue |
|---|---|
| Commentaires, docstrings, variables métier | **Français** |
| Fonctions, classes, modules, paramètres techniques | **Anglais** |

```python
# ✅ Correct
async def get_analysis(ticker: str) -> AnalysisResult | None:
    """Retourne la dernière analyse ou None si absente du cache."""
    ...

# ❌ Incorrect
def get_analysis(ticker: any) -> dict:
    result = db.query(ticker)  # requête la base de données
    return result
```

- **TypeScript** : zéro `any` — typer explicitement ou créer un type dans `frontend/src/types/index.ts`
- **Python** : type hints obligatoires sur toutes les signatures, Pydantic v2 pour les modèles
- **Async/await** : tout appel I/O (DB, API, Redis) doit être `async/await`

---

## Pyramide de tests (5 niveaux)

| Niveau | Outil | Portée |
|---|---|---|
| Unitaire backend | `pytest` | Fonctions isolées, mocks DB |
| Intégration backend | `pytest` + `TestClient` | Endpoints FastAPI, services |
| Unitaire frontend | `vitest` | Composants React isolés |
| Evals IA | `pytest tests/evals/` | Qualité des réponses Claude |
| E2E | `pytest tests/e2e/` | Flux complets (requiert infra) |

```bash
# Tests CI standard (aucune clé Claude requise)
python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q

# Tests frontend
cd frontend && npm test
```

Tout nouveau composant React → test Vitest obligatoire (happy path + cas d'erreur).

---

## Workflow sprint

Chaque PR doit s'inscrire dans un sprint numéroté :

1. Créer une branche `feat/sprint-NNN-description` ou `fix/description`
2. Implémenter les livrables en respectant les contraintes du sprint
3. Vérifier que tous les tests passent (CI vert)
4. Ouvrir une Pull Request via le template fourni

---

## Commandes essentielles

```bash
docker-compose up -d                        # démarrer l'infrastructure
curl localhost:8000/healthz                 # vérifier le service
python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals
cd frontend && npm run dev
cd frontend && npm run typecheck
ruff check app/ tests/
```

---

## Questions ?

Ouvrir une [issue](https://github.com/YOUR_USERNAME/tradingClaude/issues) avec le template approprié.
