---
paths:
  - "app/**/*.py"
  - "frontend/src/**/*.{ts,tsx}"
  - "analyses/**"
---

# Variables financières — nommage standardisé

## Quand cette règle s'applique

Lors de l'édition de code Python dans `app/`, de TypeScript/TSX dans `frontend/src/`, ou de fichiers d'analyse dans `analyses/`. S'applique aux schemas Pydantic, aux types TypeScript, et aux formules dans les analyses.

## Règles

Utiliser **exactement** ces identifiants. Toute déviation introduit des incohérences entre le backend Python et le frontend TypeScript.

### Tableau des variables standardisées

| Variable Python (`snake_case`) | Variable TS (`camelCase`) | Type | Signification |
|---|---|---|---|
| `eps` / `eps_ttm` | `eps` / `epsTtm` | `float \| None` | Bénéfice par action (12 derniers mois) |
| `bvps` / `book_value` | `bvps` / `bookValue` | `float \| None` | Valeur comptable par action |
| `pe` | `pe` | `float \| None` | Price/Earnings ratio |
| `pb` | `pb` | `float \| None` | Price/Book ratio |
| `fcf` | `fcf` | `float \| None` | Free cash flow |
| `roic` | `roic` | `float \| None` | Return on invested capital |
| `roe` | `roe` | `float \| None` | Return on equity |
| `eps_growth_total` | `epsGrowthTotal` | `float \| None` | Croissance totale BPA sur l'horizon réellement disponible (fraction : `0.85` = 85 %). Pour `GrahamRatios` — calculé par le tier1 sur ~4 ans, pas 10 |
| `eps_growth_years` | `epsGrowthYears` | `int \| None` | Horizon réel (en années) couvert par `eps_growth_total`. `None` si inconnu (donnée absente ou repli de source) |
| `current_ratio` | `currentRatio` | `float \| None` | Actif circulant / Passif circulant — `null` normal pour banques |
| `debt_equity` | `debtEquity` | `float \| None` | Dette totale / Capitaux propres |
| `cost_usd` | `costUsd` | `float` | Coût API Claude de l'appel en USD — jamais `None` |
| `graham_number` | `grahamNumber` | `float \| None` | √(22.5 × EPS × BVPS) |
| `peg_ratio` | `pegRatio` | `float \| None` | P/E ÷ taux de croissance des bénéfices |
| `sharpe_ratio` | `sharpeRatio` | `float \| None` | Rendement excédentaire / volatilité |
| `max_drawdown` | `maxDrawdown` | `float \| None` | Perte maximale pic-à-creux (fraction négative, ex. `-0.32`) |

### Convention de casse
- Python backend : `snake_case` — schemas Pydantic, fonctions, variables
- TypeScript frontend : `camelCase` — types `index.ts`, props, variables
- Les schemas Pydantic utilisent `snake_case` ; le frontend convertit via `types/index.ts`

> **Note de périmètre** — `EsgInput` (`esg_simplified`) et `ValuationRatios` (`stock_valuation`)
> conservent un champ `eps_growth_10y` distinct, alimenté par d'autres sources (saisie ESG,
> `info.earningsGrowth`, ou `None`) et non par le calcul tier1 trompeur corrigé ici. Le standard
> ci-dessus s'applique au ratio Graham calculé ; ne pas confondre les deux.

### Exemples

```python
# ✅ Python — schema Pydantic
class GrahamRatios(BaseModel):
    eps_ttm: float | None = None
    book_value: float | None = None
    current_ratio: float | None = None  # null accepté pour banques
    cost_usd: float = 0.0
```

```typescript
// ✅ TypeScript — types/index.ts
interface GrahamRatios {
  epsTtm: number | null;
  bookValue: number | null;
  currentRatio: number | null;
  costUsd: number;
}
```
