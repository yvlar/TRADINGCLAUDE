import type { ScreenEntry, ScreenerSortKey, ScreenerSortState } from '../types'

// Définition canonique dans types/index.ts — réexport pour les consommateurs existants
export type SortKey = ScreenerSortKey
export type SortState = ScreenerSortState

export const SORT_STORAGE_KEY = 'copilote_screener_sort'
export const FILTER_STORAGE_KEY = 'copilote_screener_label_filter'

const DEFAULT_SORT: SortState = { key: 'score', asc: false }
const VALID_KEYS: readonly SortKey[] = ['score', 'ticker', 'cost', 'composite', 'freshness']

export function loadSortState(): SortState {
  try {
    const raw = localStorage.getItem(SORT_STORAGE_KEY)
    if (!raw) return { ...DEFAULT_SORT }
    const parsed = JSON.parse(raw) as Partial<SortState>
    if (parsed.key && VALID_KEYS.includes(parsed.key) && typeof parsed.asc === 'boolean') {
      return { key: parsed.key, asc: parsed.asc }
    }
  } catch {
    // localStorage indisponible (navigation privée, quota) — défaut silencieux
  }
  return { ...DEFAULT_SORT }
}

export function saveSortState(state: SortState): void {
  try {
    localStorage.setItem(SORT_STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore
  }
}

export function loadLabelFilter(): string[] {
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed.filter((v): v is string => typeof v === 'string')
  } catch {
    // ignore
  }
  return []
}

export function saveLabelFilter(labels: string[]): void {
  try {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(labels))
  } catch {
    // ignore
  }
}

/** Labels composite distincts présents dans les résultats, ordre stable d'apparition. */
export function availableLabels(entries: ScreenEntry[]): string[] {
  const seen: string[] = []
  for (const e of entries) {
    if (e.composite_label && !seen.includes(e.composite_label)) seen.push(e.composite_label)
  }
  return seen
}

/**
 * Indicateur de fraîcheur d'une analyse. `stale` est vrai au-delà de 24h —
 * seuil aligné sur le cache composite_score (< 24h) du backend.
 */
export function formatFreshness(
  analyzedAt: string | null,
  now: Date = new Date(),
): { label: string; stale: boolean } {
  if (!analyzedAt) return { label: '—', stale: false }
  const then = new Date(analyzedAt)
  const ms = now.getTime() - then.getTime()
  if (Number.isNaN(ms)) return { label: '—', stale: false }

  const minutes = Math.floor(ms / 60_000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (minutes < 60) return { label: "à l'instant", stale: false }
  if (hours < 24) return { label: `il y a ${hours} h`, stale: false }
  if (days === 1) return { label: 'hier', stale: true }
  return { label: `il y a ${days} j`, stale: true }
}

function csvCell(value: string | number | null): string {
  const s = value == null ? '' : String(value)
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

const CSV_HEADERS = [
  'Ticker',
  'Score défensif',
  'Verdict',
  'Composite',
  'Label composite',
  'Coût USD',
  'Cache',
  'Analysé le',
  'Erreur',
]

/** Sérialise les entrées (déjà filtrées/triées) en CSV, BOM exclu. */
export function buildScreenerCsv(entries: ScreenEntry[]): string {
  const rows = entries.map((e) =>
    [
      e.ticker,
      e.defensive_score,
      e.verdict,
      e.composite_score,
      e.composite_label,
      e.cost_usd,
      e.depuis_cache ? 'oui' : 'non',
      e.analyzed_at,
      e.erreur,
    ]
      .map(csvCell)
      .join(','),
  )
  return [CSV_HEADERS.join(','), ...rows].join('\n')
}
