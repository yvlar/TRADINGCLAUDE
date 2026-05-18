---
paths:
  - "frontend/**"
---

# Conventions frontend — React 18 + TypeScript

## Quand cette règle s'applique

Lors de l'édition de tout fichier dans `frontend/` — TypeScript, TSX, tests Vitest, config Vite/Tailwind.

## Règles

### Stack

- **React 18 + TypeScript strict** — `npm run dev` → port 5173, proxy vers API `localhost:8000`
- Design system : **Tailwind CSS 3** + composants **shadcn/ui** (`frontend/src/components/ui/`)
- Graphiques : **recharts** (ex. `TickerComparisonChart` — comparaison multi-tickers `composite_score`)
- Cache et mutations : **@tanstack/react-query**
- Auth : Bearer token dans `localStorage` via `AuthContext` (`frontend/src/contexts/AuthContext.tsx`)

### Structure (filesystem = source de vérité)

Ne jamais hardcoder le nombre de pages, composants ou tests dans le code ou les commentaires.

| Répertoire | Contenu |
|---|---|
| `frontend/src/pages/` | Pages de l'application |
| `frontend/src/components/` | Composants réutilisables |
| `frontend/src/components/ui/` | Composants shadcn/ui |
| `frontend/src/api/` | Couche HTTP (`client.ts`, `analyze.ts`, `watchlist.ts`, `ws.ts`) |
| `frontend/src/types/index.ts` | Types TypeScript centralisés (`AnalyzeResponse`, `CompositeScore`, etc.) |
| `frontend/src/__tests__/` | Tests Vitest |

### TypeScript strict

- **Zéro `any`** — typer explicitement ou créer un nouveau type dans `types/index.ts`
- Utiliser les types de domaine définis, ne pas recréer des types ad hoc inline

```tsx
// ✅ Correct
const calculateGrahamNumber = (eps: number, bvps: number): number =>
  Math.sqrt(22.5 * eps * bvps); // formule classique Graham

// ❌ Incorrect
const calc = (a: any, b: any) => Math.sqrt(22.5 * a * b);
```

### Tests composants

- Tout nouveau composant React → test composant obligatoire (happy path + cas d'erreur)
- Outils : **Vitest** + `@testing-library/react`
- Voir `tests-pyramide.md` pour la règle absolue sur le mock des appels API Claude

### Patterns React

- Composants fonctionnels uniquement — pas de class components
- Hooks personnalisés dans `frontend/src/hooks/` si la logique est réutilisable
- `data-testid` obligatoire sur les éléments interactifs testés (boutons, inputs, badges)
