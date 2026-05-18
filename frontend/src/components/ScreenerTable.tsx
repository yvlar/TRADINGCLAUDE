import { useMemo, useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import type { ScreenEntry } from '../types'

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

type SortKey = 'score' | 'ticker' | 'cost'

interface ScreenerTableProps {
  entries: ScreenEntry[]
  workflow: string
  durationMs: number
}

export function ScreenerTable({ entries, workflow, durationMs }: ScreenerTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [asc, setAsc] = useState(false)

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setAsc(!asc)
    } else {
      setSortKey(key)
      setAsc(key !== 'score')
    }
  }

  const sorted = useMemo(() => {
    return [...entries].sort((a, b) => {
      let diff = 0
      if (sortKey === 'score') {
        diff = (a.defensive_score ?? -1) - (b.defensive_score ?? -1)
      } else if (sortKey === 'ticker') {
        diff = a.ticker.localeCompare(b.ticker)
      } else if (sortKey === 'cost') {
        diff = a.cost_usd - b.cost_usd
      }
      return asc ? diff : -diff
    })
  }, [entries, sortKey, asc])

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="opacity-30 ml-1">↕</span>
    return <span className="ml-1">{asc ? '↑' : '↓'}</span>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Classement — {entries.length} tickers · workflow : {workflow} · {durationMs}ms
        </CardTitle>
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
              <TableHead>Composite</TableHead>
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
            {sorted.map((entry, i) => (
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
