# Sprint Frontend — Rattrapage et correction de bugs
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# ROLE

Tu es un developpeur frontend senior specialiste **React 18 + TypeScript strict**.
Tu maitrises Vite 5, Tailwind CSS 3, shadcn/ui, @tanstack/react-query v5,
et les tests composants avec Vitest + @testing-library/react.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

1. `ROADMAP.md` -- version et sprint actif backend
2. `frontend/src/types/index.ts` -- types TS actuels
3. `frontend/src/api/analyze.ts` -- fonctions API actuelles
4. `app/api/endpoints/screen.py` -- ScreenEntry backend (source de verite)
5. `app/models/watchlist.py` -- WatchlistEntry backend (source de verite)
6. `app/services/composite_history_service.py` -- CompositeHistoryPoint (Sprint 57)

---

# ETAT DU PROJET A CE JOUR

| Champ | Valeur |
|-------|--------|
| Version backend | 5.0.0 |
| Sprint actif backend | Sprint 58 |
| Tests Vitest actuels | **1 failing, 67 passing** (68 total) |
| Frontend | `frontend/` -- `cd frontend && npm run dev` -- port 5173 |

## Endpoints backend disponibles (source de verite)
```
POST /analyze             -- analyse SSE streaming
POST /analyze-stream      -- SSE explicite
POST /screen              -- screener multi-tickers
GET  /composite-history/{ticker}?limit=90  -- NOUVEAU Sprint 57
GET  /history             -- historique analyses
GET  /performance/{ticker} -- rendement retrospectif
GET  /extract             -- ratios Yahoo Finance
GET  /report/{analysis_id} -- PDF analyse individuelle
GET  /watchlist           -- liste watchlist
POST /watchlist           -- ajout watchlist
DELETE /watchlist/{id}    -- suppression
POST /watchlist/{id}/analyze -- declencher analyse Celery
GET  /watchlist/{id}/price-status -- statut prix
POST /export/screen       -- export CSV ou Excel screener
GET  /telemetry/summary|costs|cache|latency|webhook
GET  /healthz
```

---

# BUGS CRITIQUES A CORRIGER (priorite 1)

## Bug 1 : Test Vitest failing — `streaming-progress` testid attendu

**Fichier** : `frontend/src/__tests__/AnalyzePage.test.tsx` ligne ~97
**Erreur** : `waitFor(() => expect(screen.getByTestId('streaming-progress'))`  
timeout — le composant `StreamingProgress` n'est pas affiche assez vite.

**Cause probable** : le mock de `streamAnalyze` ne respecte pas l'ordre
asynchrone exact attendu par React. Le `skill_start` event
n'a pas le temps de provoquer le re-render avant le `waitFor`.

**Fix** : Revoir le mock pour qu'il emette le `skill_start` apres un `await` minimal,
ou augmenter le delai entre les events dans le mock :
```typescript
vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
  yield { type: 'skill_start' as const, data: { skill_id: 'graham_analysis' } }
  await new Promise((r) => setTimeout(r, 50)) // delai suffisant
  yield { type: 'skill_result' as const, ... }
  yield { type: 'complete' as const, data: _MOCK_RESPONSE }
})
```

**Critere** : `npm test` -- 0 failing, 68 passing.

---

## Bug 2 : `CompositeScoreHistory.tsx` — mauvais endpoint (CRITIQUE)

**Fichier** : `frontend/src/components/CompositeScoreHistory.tsx`
**Probleme** : Le composant appelle `getPerformance(ticker)` → `GET /performance/{ticker}`.
Cet endpoint retourne des donnees de rendement financier (prix d'analyse, rendement %),
pas l'historique dedie du composite_score.

Depuis Sprint 57, il existe `GET /composite-history/{ticker}` qui retourne
`list[CompositeHistoryPoint]` — c'est le bon endpoint.

**Fix en 3 etapes** :

### Etape 2a — `frontend/src/types/index.ts` : ajouter le type
```typescript
// ---- Historique composite_score (Sprint 57) ----
export interface CompositeHistoryPoint {
  id: string
  ticker: string
  score: number
  label: string  // "FORT" | "MODERE" | "FAIBLE"
  workflow: string
  recorded_at: string  // ISO 8601
}
```

### Etape 2b — `frontend/src/api/analyze.ts` : ajouter la fonction
```typescript
export async function getCompositeHistory(
  ticker: string,
  limit = 90,
): Promise<CompositeHistoryPoint[]> {
  return apiClient.request<CompositeHistoryPoint[]>(
    `/composite-history/${encodeURIComponent(ticker)}?limit=${limit}`
  )
}
```

### Etape 2c — `CompositeScoreHistory.tsx` : utiliser le bon endpoint
Remplacer l'appel `getPerformance` par `getCompositeHistory`.
Adapter l'affichage : `CompositeHistoryPoint` a `score`, `label`, `workflow`, `recorded_at`
(pas de `rendement_pct` ni `price_current`).

---

## Bug 3 : Types TS desynchronises avec le backend

### Bug 3a — `ScreenEntry` manque `composite_score` et `composite_label`

**Fichier** : `frontend/src/types/index.ts`

Le backend (`app/api/endpoints/screen.py`) retourne :
```python
composite_score: float | None = None
composite_label: str | None = None
```
Mais le type TS `ScreenEntry` ne les inclut pas.

**Fix** :
```typescript
export interface ScreenEntry {
  ticker: string
  defensive_score: number | null
  verdict: string | null
  composite_score: number | null   // AJOUTER
  composite_label: string | null   // AJOUTER
  workflow_utilise: string
  cost_usd: number
  depuis_cache: boolean
  erreur: string | null
}
```

### Bug 3b — `WatchlistEntry` manque `last_composite_score`, `composite_alert_threshold`, `score_alerte_min`

**Fichier** : `frontend/src/types/index.ts`

Le backend (`app/models/watchlist.py`) retourne :
```python
last_composite_score: float | None = None
composite_alert_threshold: float = 15.0
score_alerte_min: int | None = None
```

**Fix** :
```typescript
export interface WatchlistEntry {
  id: string
  ticker: string
  workflow: string
  last_analyzed_at: string | null
  last_score: number | null
  last_intrinsic_value: number | null
  last_price_checked: number | null
  price_alert_threshold_pct: number
  created_at: string
  last_composite_score: number | null       // AJOUTER
  composite_alert_threshold: number         // AJOUTER (defaut 15.0)
  score_alerte_min: number | null           // AJOUTER
}
```

---

## Bug 4 : `HistoryPage.tsx` — ticker vide envoie 'ALL' au backend

**Fichier** : `frontend/src/pages/HistoryPage.tsx` lignes 19 et 38

```typescript
// PROBLEME : 'ALL' n'est pas un ticker valide cote backend
queryFn: async () => {
  const res = await getHistory(submittedTicker || 'ALL', 15) // ligne 19
},
function handleSubmit(e: React.FormEvent) {
  const t = ticker.trim().toUpperCase() || 'ALL'  // ligne 38
```

**Fix** : Interdire la soumission si le ticker est vide, ou supprimer le fallback 'ALL'.
```typescript
// handleSubmit : ne soumettre que si ticker non vide
if (!ticker.trim()) return
const t = ticker.trim().toUpperCase()
setSubmittedTicker(t)
```
Et retirer `|| 'ALL'` dans le queryFn.

---

# FEATURES MANQUANTES (priorite 2)

## Feature 1 : `ScreenerTable` — afficher composite_score et composite_label

**Fichier** : `frontend/src/components/ScreenerTable.tsx`

Apres correction du Bug 3a, ajouter une colonne "Score composite" entre
"Verdict" et "Cout". Afficher avec la meme logique de couleur que `CompositeBadge` :
- score >= 70 → `text-green-400` (FORT)
- score >= 45 → `text-yellow-400` (MODERE)
- score < 45 → `text-red-400` (FAIBLE)

Le tri existant reste sur `defensive_score` ; la nouvelle colonne est informative.

**Header** :
```tsx
<TableHead>Composite</TableHead>
```
**Cell** :
```tsx
<TableCell>
  {entry.composite_score != null ? (
    <span className={compositeColor(entry.composite_label ?? '')}>
      {entry.composite_score.toFixed(1)}
      <span className="ml-1 text-xs text-muted-foreground">({entry.composite_label})</span>
    </span>
  ) : <span className="text-muted-foreground">—</span>}
</TableCell>
```

---

## Feature 2 : `WatchlistTable` — afficher last_composite_score

**Fichier** : `frontend/src/components/WatchlistTable.tsx`

Apres correction du Bug 3b, ajouter une colonne "Score composite" avant "Actions".
Afficher avec badge FORT/MODERE/FAIBLE en couleur, ou "—" si null.

---

## Feature 3 : `AnalyzeForm` — activer les skills avancés via checkboxes

**Fichier** : `frontend/src/components/AnalyzeForm.tsx`

Actuellement seuls Graham + Earnings + Thesis + Munger sont activables.
Les 11 autres skills (dorsey, buffett, valuation, lynch, marks, fisher,
klarman, greenblatt, damodaran, pabrai, canadian_tax) ne sont pas accessibles
sans appel API direct.

**Approche recommandee** : section "Skills avances" avec checkboxes
pour les workflows qui ne requierent pas de ratios specifiques
(ex : le workflow selectionne determine quels skills s'executent).
Pour les skills qui ont des ratios specifiques (dorsey_ratios, buffett_ratios, etc.),
ne pas exposer les champs — l'auto-fill Yahoo Finance ne les fournit pas.

**Priorite pratique** : au minimum, ajouter des checkboxes pour :
- `Lynch` (necessite `lynch_ratios` -- peu de champs : pe_growth, peg, category_hint)
- `Marks` (necessite `marks_input` -- sentiment, vix_level, credit_spreads)
- `Damodaran` (necessite `damodaran_input` -- growth_rate, tam, market_share)

Ces 3 skills n'ont pas de ratios derivables de Yahoo Finance, donc les checkboxes
devraient afficher un mini-formulaire simplifie avec les champs cles.

---

## Feature 4 : Export screener — bouton CSV/Excel dans ScreenerPage

**Endpoint existant** : `POST /export/screen` (meme payload que `POST /screen`)  
**Parametre** : `format: "csv" | "xlsx"` (query param)

**Fichier a modifier** : `frontend/src/pages/ScreenerPage.tsx`

Apres affichage du resultat, ajouter deux boutons :
- "Exporter CSV" → `POST /export/screen?format=csv` → telechargement blob
- "Exporter Excel" → `POST /export/screen?format=xlsx` → telechargement blob

Fonction dans `api/analyze.ts` :
```typescript
export async function exportScreen(
  body: ScreenRequest,
  format: 'csv' | 'xlsx',
): Promise<Blob> {
  return apiClient.requestBlob(`/export/screen?format=${format}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
```

---

# TESTS VITEST OBLIGATOIRES (un test par bug + feature)

| Test | Fichier | Description |
|------|---------|-------------|
| Fix Bug 1 | `AnalyzePage.test.tsx` | `streaming-progress` visible apres `skill_start` |
| Bug 2 | `CompositeScoreHistory.test.tsx` | Appelle `getCompositeHistory` et non `getPerformance` |
| Bug 3a | `ScreenerTable.test.tsx` | Colonne "Composite" presente si composite_score != null |
| Bug 3b | `WatchlistTable.test.tsx` | Colonne "Score composite" presente si last_composite_score != null |
| Bug 4 | `HistoryPage.test.tsx` | Soumission vide ne declenche pas de requete |
| Feature 1 | `ScreenerTable.test.tsx` | Affiche "—" si composite_score null |
| Feature 4 | `ScreenerPage.test.tsx` | Boutons CSV/Excel appelles apres un resultat screener |

**Objectif** : 0 failing, >= 75 passing (actuel : 1 failing, 67 passing).

---

# DEFINITION OF DONE

- [x] Bug 1 : 0 test Vitest failing -- `npm test` 100% vert
- [x] Bug 2 : `CompositeScoreHistory` utilise `getCompositeHistory()` + type `CompositeHistoryPoint` dans `types/index.ts`
- [x] Bug 3a : `ScreenEntry` type TS avec `composite_score` et `composite_label`
- [x] Bug 3b : `WatchlistEntry` type TS avec `last_composite_score`, `composite_alert_threshold`, `score_alerte_min`
- [x] Bug 4 : Soumission vide interdite dans `HistoryPage`
- [x] Feature 1 : `ScreenerTable` affiche colonne composite_score
- [x] Feature 2 : `WatchlistTable` affiche colonne last_composite_score
- [x] Feature 4 : Boutons export CSV/Excel dans `ScreenerPage`
- [x] Total Vitest >= 75 passing, 0 failing — **83 passing, 0 failing**
- [x] `npm run build` sans erreur TypeScript
- [x] `ROADMAP.md` mis a jour — Sprint Frontend Catchup ✅

---

# CONTRAINTES ABSOLUES (frontend)

- **TypeScript strict** -- aucun `any`, toujours typer les retours d'API
- **Types TS synchronises** avec les schemas Pydantic backend -- lire les fichiers Python avant de modifier `types/index.ts`
- **Tests Vitest obligatoires** pour tout nouveau composant (happy path + cas erreur/null)
- **shadcn/ui** -- utiliser les composants existants dans `frontend/src/components/ui/`
- **@tanstack/react-query** -- toutes les requetes API via `useQuery` ou `useMutation`
- **Port 5173** -- `cd frontend && npm run dev`
- **Ne pas modifier** `frontend/vite.config.ts` ni `tailwind.config.js`
- **Pas de `console.log`** en production -- utiliser `data-testid` pour les tests

---

# INVENTAIRE COMPLET DES GAPS (pour reference future)

## Bugs corriges dans ce sprint
1. Test Vitest failing (AnalyzePage streaming-progress)
2. CompositeScoreHistory mauvais endpoint
3. ScreenEntry type TS incomplet
4. WatchlistEntry type TS incomplet
5. HistoryPage ticker 'ALL' invalide

## Features partiellement adressees dans ce sprint
6. ScreenerTable colonne composite_score
7. WatchlistTable colonne last_composite_score
8. Export screener CSV/Excel

## Features restantes pour sprints futurs
9. AnalyzeForm skills avances (dorsey, buffett, valuation, marks, damodaran, pabrai...)
10. Page Telemetry (GET /telemetry/summary|costs|cache|latency|webhook)
11. Dashboard trends graphique composite_score (Sprint 60 backend prevu)
12. Jobs Celery -- suivi des taches async depuis le frontend
13. Performance page dediee (GET /performance/{ticker}) avec graphique

---

*Audit realise le 2026-05-14 -- Yves / TradingClaude*
*Source : comparaison frontend/ vs app/api/endpoints/ + app/models/ -- 5 bugs identifies, 8 features manquantes*
