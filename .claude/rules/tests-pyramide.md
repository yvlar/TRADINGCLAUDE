---
paths:
  - "tests/**"
  - "frontend/src/__tests__/**"
---

# Stratégie de test — pyramide obligatoire

## Quand cette règle s'applique

Lors de l'écriture ou la modification de tests Python (`tests/`) ou TypeScript (`frontend/src/__tests__/`).

## Règles

### Pyramide 5 niveaux

| Niveau | Portée | Outils | Exemples dans ce projet |
|---|---|---|---|
| **Unitaire** | Fonctions / classes isolées, logique pure | `pytest`, `vitest` | Calculs Graham, schemas Pydantic, formules financières |
| **Composant** | Composant React isolé (mocks des dépendances) | `vitest` + `@testing-library/react` | `AnalyzeForm`, `ScreenerTable`, `LoginPage` |
| **Intégration** | Plusieurs modules — endpoints FastAPI, orchestrateur + skills | `pytest` + `httpx.AsyncClient` | `test_integration_sync.py`, `test_workflow_router.py` |
| **Système** | Application complète (sans UI) — API exercée de bout en bout | `pytest` + `httpx` contre uvicorn thread | `test_healthz_prod.py`, smoke tests |
| **Acceptation** | Scénarios navigateur complets | `playwright` | `tests/e2e/test_e2e_*.py` |

### Règle absolue — patch de `call_claude_with_retry()`

**Les appels à l'API Claude ne doivent jamais être réels dans les tests.**  
`call_claude_with_retry()` doit être patché à **chaque niveau** de la pyramide — unitaire, intégration, système, acceptation.

```python
# Backend — unittest.mock.patch
from unittest.mock import patch, AsyncMock

@patch(
    "app.skills.tier2.graham_analysis.skill.call_claude_with_retry",
    new_callable=AsyncMock,
)
async def test_graham_execute(mock_claude):
    mock_claude.return_value = fake_claude_response
    result = await skill.execute(input_data)
    assert result.defensive_score >= 0
```

```typescript
// Frontend — vi.mock
vi.mock("../../api/analyze", () => ({
  postAnalyze: vi.fn().mockResolvedValue(fakeAnalyzeResponse),
}));
```

### Marqueurs pytest

```python
@pytest.mark.e2e          # tests Playwright — exclus du CI standard
@pytest.mark.integration  # tests nécessitant une vraie DB ou un vrai Redis
```

Commande CI standard : `python -m pytest tests/ --ignore=tests/e2e`  
Tests intégration seuls : `python -m pytest tests/ -m integration --ignore=tests/e2e`

### Fixture pytest — `client` uniquement

```python
# tests/conftest.py définit client (TestClient synchrone)

# ✅ Correct
def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200

# ❌ Incorrect — async_client n'existe pas dans conftest.py
async def test_healthz(async_client):
    ...
```

### Couverture minimale par livrable

| Livrable | Tests obligatoires |
|---|---|
| Nouveau skill tier2 | Unitaires sur schemas + test d'intégration sur l'endpoint `/analyze` |
| Nouveau endpoint FastAPI | Test d'intégration obligatoire |
| Nouveau composant React | Test composant : happy path + cas d'erreur au minimum |
| Nouveau workflow orchestrateur | Test système via `tests/test_workflow_router.py` |
