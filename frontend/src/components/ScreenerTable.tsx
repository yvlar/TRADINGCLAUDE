import { useEffect, useMemo, useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import type { ScreenEntry } from '../types'
import { getScreenerPreferences, putScreenerPreferences } from '../api/preferences'
import {
  availableLabels,
  buildScreenerCsv,
  formatFreshness,
  loadLabelFilter,
  loadSortState,
  saveLabelFilter,
  saveSortState,
  type SortKey,
  type SortState,
} from '../lib/screenerView'

function compositeColor(label: string | null): string {
  if (label === 'FORT') return 'text-bull'
  if (label === 'MODÉRÉ' || label === 'MODERE') return 'text-neutral'
  return 'text-bear'
}

function verdictVariant(verdict: string | null): 'success' | 'warning' | 'danger' | 'outline' {
  if (!verdict) return 'outline'
  const v = verdict.toUpperCase()
  if (v.includes('ACHETER') || v.includes('EXEMPLAIRE') || v.includes('SOLIDE')) return 'success'
  if (v.includes('CONSERVER') || v.includes('WATCHLIST')) return 'warning'
  return 'danger'
}

function ScoreCell({ score }: { score: number | null }) {
  if (score == null) return <span className="text-muted-foreground">—</span>
  const color = score >= 6 ? 'text-bull' : score >= 4 ? 'text-neutral' : 'text-bear'
  return <span className={`font-semibold tabular-nums ${color}`}>{score}/8</span>
}

function FreshnessCell({ analyzedAt }: { analyzedAt: string | null }) {
  const { label, stale } = formatFreshness(analyzedAt)
  const color = analyzedAt == null ? 'text-muted-foreground' : stale ? 'text-neutral' : 'text-bull'
  return (
    <span className={`text-xs tabular-nums ${color}`} title={analyzedAt ?? ''} data-testid="freshness-cell">
      {label}
    </span>
  )
}

/** Direction par défaut au changement de colonne : alpha/coût ascendant, scores/date descendants. */
function defaultAsc(key: SortKey): boolean {
  return key === 'ticker' || key === 'cost'
}

interface ScreenerTableProps {
  entries: ScreenEntry[]
  workflow: string
  durationMs: number
}

export function ScreenerTable({ entries, workflow, durationMs }: ScreenerTableProps) {
  // localStorage en état initial (anti-flash) ; le serveur prend le relais au montage
  const [sort, setSort] = useState<SortState>(() => loadSortState())
  const [activeLabels, setActiveLabels] = useState<string[]>(() => loadLabelFilter())
  const { key: sortKey, asc } = sort

  // Au montage : hydrater depuis le serveur ; si 401 / réseau KO / champ null, garder le localStorage
  useEffect(() => {
    let cancelled = false
    void getScreenerPreferences().then((prefs) => {
      if (cancelled || !prefs) return
      if (prefs.sort) {
        setSort(prefs.sort)
        saveSortState(prefs.sort)
      }
      if (prefs.filter) {
        setActiveLabels(prefs.filter)
        saveLabelFilter(prefs.filter)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  // Miroir localStorage (anti-flash) + persistance serveur best-effort de l'état complet
  function persist(nextSort: SortState, nextLabels: string[]) {
    saveSortState(nextSort)
    saveLabelFilter(nextLabels)
    void putScreenerPreferences({ sort: nextSort, filter: nextLabels })
  }

  function toggleSort(key: SortKey) {
    const next = sortKey === key ? { key, asc: !asc } : { key, asc: defaultAsc(key) }
    setSort(next)
    persist(next, activeLabels)
  }

  function toggleLabel(label: string) {
    const next = activeLabels.includes(label)
      ? activeLabels.filter((l) => l !== label)
      : [...activeLabels, label]
    setActiveLabels(next)
    persist(sort, next)
  }

  function clearLabels() {
    setActiveLabels([])
    persist(sort, [])
  }

  const labels = useMemo(() => availableLabels(entries), [entries])

  const visible = useMemo(() => {
    const filtered =
      activeLabels.length === 0
        ? entries
        : entries.filter((e) => e.composite_label != null && activeLabels.includes(e.composite_label))

    return [...filtered].sort((a, b) => {
      let diff = 0
      if (sortKey === 'score') {
        diff = (a.defensive_score ?? -1) - (b.defensive_score ?? -1)
      } else if (sortKey === 'ticker') {
        diff = a.ticker.localeCompare(b.ticker)
      } else if (sortKey === 'cost') {
        diff = a.cost_usd - b.cost_usd
      } else if (sortKey === 'composite') {
        diff = (a.composite_score ?? -1) - (b.composite_score ?? -1)
      } else if (sortKey === 'freshness') {
        diff = (a.analyzed_at ?? '').localeCompare(b.analyzed_at ?? '')
      }
      return asc ? diff : -diff
    })
  }, [entries, activeLabels, sortKey, asc])

  function handleExportFiltered() {
    const csv = '﻿' + buildScreenerCsv(visible)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `screener-${workflow}-filtre.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="opacity-30 ml-1" aria-hidden="true">↕</span>
    return <span className="ml-1" aria-hidden="true">{asc ? '↑' : '↓'}</span>
  }

  /** En-tête triable accessible au clavier (bouton + aria-sort sur le th). */
  function SortableHead({ k, label }: { k: SortKey; label: string }) {
    const ariaSort: 'ascending' | 'descending' | 'none' =
      sortKey === k ? (asc ? 'ascending' : 'descending') : 'none'
    return (
      <TableHead aria-sort={ariaSort} className="p-0 select-none">
        <button
          type="button"
          onClick={() => toggleSort(k)}
          className="flex h-10 w-full items-center px-3 text-left transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          {label}
          <SortIcon k={k} />
        </button>
      </TableHead>
    )
  }

  const isFiltered = activeLabels.length > 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Classement — {visible.length}
          {isFiltered ? ` / ${entries.length}` : ''} tickers · workflow : {workflow} · {durationMs}ms
        </CardTitle>
        {(labels.length > 0 || isFiltered) && (
          <div
            className="flex flex-wrap items-center gap-2 pt-2"
            data-testid="screener-filter-bar"
          >
            <span className="text-xs text-muted-foreground uppercase tracking-wide">Filtrer par label</span>
            {labels.map((label) => (
              <Button
                key={label}
                type="button"
                size="sm"
                variant={activeLabels.includes(label) ? 'default' : 'outline'}
                data-testid={`label-filter-${label}`}
                onClick={() => toggleLabel(label)}
              >
                {label}
              </Button>
            ))}
            {isFiltered && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                data-testid="label-filter-clear"
                onClick={clearLabels}
              >
                Réinitialiser
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="ml-auto"
              data-testid="export-filtered-csv"
              onClick={handleExportFiltered}
            >
              Exporter résultats filtrés (CSV)
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <SortableHead k="ticker" label="Ticker" />
              <SortableHead k="score" label="Score défensif" />
              <TableHead>Verdict</TableHead>
              <SortableHead k="composite" label="Composite" />
              <SortableHead k="freshness" label="Fraîcheur" />
              <SortableHead k="cost" label="Coût" />
              <TableHead>Cache</TableHead>
              <TableHead>Erreur</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((entry, i) => (
              <TableRow key={entry.ticker} data-testid="screener-row">
                <TableCell className="text-muted-foreground text-xs">{i + 1}</TableCell>
                <TableCell className="font-bold" data-testid="screener-ticker">{entry.ticker}</TableCell>
                <TableCell>
                  <ScoreCell score={entry.defensive_score} />
                </TableCell>
                <TableCell>
                  {entry.verdict ? (
                    <Badge data-testid="verdict-badge" variant={verdictVariant(entry.verdict)}>{entry.verdict}</Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell data-testid="composite-cell">
                  {entry.composite_score != null ? (
                    <span className={compositeColor(entry.composite_label ?? '')}>
                      {entry.composite_score.toFixed(1)}
                      <span className="ml-1 text-xs text-muted-foreground">({entry.composite_label})</span>
                    </span>
                  ) : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell>
                  <FreshnessCell analyzedAt={entry.analyzed_at} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground tabular-nums">
                  ${entry.cost_usd.toFixed(4)}
                </TableCell>
                <TableCell>
                  {entry.depuis_cache && (
                    <Badge variant="secondary" className="text-xs">cache</Badge>
                  )}
                </TableCell>
                <TableCell className="text-xs text-bear max-w-48 truncate">
                  {entry.erreur ?? ''}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
