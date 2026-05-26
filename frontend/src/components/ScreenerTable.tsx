import { useMemo, useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import type { ScreenEntry } from '../types'
import {
  availableLabels,
  buildScreenerCsv,
  formatFreshness,
  loadLabelFilter,
  loadSortState,
  saveLabelFilter,
  saveSortState,
  type SortKey,
} from '../lib/screenerView'

function compositeColor(label: string | null): string {
  if (label === 'FORT') return 'text-green-400'
  if (label === 'MODÉRÉ' || label === 'MODERE') return 'text-yellow-400'
  return 'text-red-400'
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
  const color = score >= 6 ? 'text-green-400' : score >= 4 ? 'text-yellow-400' : 'text-red-400'
  return <span className={`font-semibold tabular-nums ${color}`}>{score}/8</span>
}

function FreshnessCell({ analyzedAt }: { analyzedAt: string | null }) {
  const { label, stale } = formatFreshness(analyzedAt)
  const color = analyzedAt == null ? 'text-muted-foreground' : stale ? 'text-yellow-400' : 'text-green-400'
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
  const [sort, setSort] = useState(() => loadSortState())
  const [activeLabels, setActiveLabels] = useState<string[]>(() => loadLabelFilter())
  const { key: sortKey, asc } = sort

  function toggleSort(key: SortKey) {
    const next = sortKey === key ? { key, asc: !asc } : { key, asc: defaultAsc(key) }
    setSort(next)
    saveSortState(next)
  }

  function toggleLabel(label: string) {
    const next = activeLabels.includes(label)
      ? activeLabels.filter((l) => l !== label)
      : [...activeLabels, label]
    setActiveLabels(next)
    saveLabelFilter(next)
  }

  function clearLabels() {
    setActiveLabels([])
    saveLabelFilter([])
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
    if (sortKey !== k) return <span className="opacity-30 ml-1">↕</span>
    return <span className="ml-1">{asc ? '↑' : '↓'}</span>
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
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort('ticker')}
              >
                Ticker <SortIcon k="ticker" />
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort('score')}
              >
                Score défensif <SortIcon k="score" />
              </TableHead>
              <TableHead>Verdict</TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort('composite')}
              >
                Composite <SortIcon k="composite" />
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort('freshness')}
              >
                Fraîcheur <SortIcon k="freshness" />
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort('cost')}
              >
                Coût <SortIcon k="cost" />
              </TableHead>
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
                <TableCell className="text-xs text-red-400 max-w-48 truncate">
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
