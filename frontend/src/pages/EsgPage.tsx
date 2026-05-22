import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchWatchlistEsgScores } from '../api/watchlist'
import { fetchEsgHistory } from '../api/esg'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { EsgHistoryChart } from '../components/EsgHistoryChart'
import type { WatchlistEsgEntry } from '../types'

type SortKey = 'last_esg_score' | 'ticker'
type SortDir = 'asc' | 'desc'

function esgBadgeProps(score: number | null): {
  label: string
  variant: 'success' | 'warning' | 'destructive' | 'secondary'
} {
  if (score === null) return { label: '--', variant: 'secondary' }
  if (score >= 10) return { label: 'ESG_FORT', variant: 'success' }
  if (score >= 5) return { label: 'ESG_MODERE', variant: 'warning' }
  return { label: 'ESG_FAIBLE', variant: 'destructive' }
}

function sortEntries(
  entries: WatchlistEsgEntry[],
  key: SortKey,
  dir: SortDir,
): WatchlistEsgEntry[] {
  return [...entries].sort((a, b) => {
    if (key === 'ticker') {
      const cmp = a.ticker.localeCompare(b.ticker)
      return dir === 'asc' ? cmp : -cmp
    }
    if (a.last_esg_score === null && b.last_esg_score === null) return 0
    if (a.last_esg_score === null) return 1
    if (b.last_esg_score === null) return -1
    const cmp = a.last_esg_score - b.last_esg_score
    return dir === 'asc' ? cmp : -cmp
  })
}

function SortIndicator({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-muted-foreground ml-1">↕</span>
  return <span className="ml-1">{dir === 'asc' ? '↑' : '↓'}</span>
}

export default function EsgPage() {
  const navigate = useNavigate()
  const [sortKey, setSortKey] = useState<SortKey>('last_esg_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['watchlist-esg'],
    queryFn: fetchWatchlistEsgScores,
  })

  // Sprint 89 — historique du ticker selectionne
  const {
    data: historyData,
    isLoading: historyLoading,
    isError: historyError,
  } = useQuery({
    queryKey: ['esg-history', selectedTicker],
    queryFn: () => fetchEsgHistory(selectedTicker!),
    enabled: selectedTicker !== null,
    retry: false,
  })

  const entries = data?.entries ?? []
  const sorted = sortEntries(entries, sortKey, sortDir)

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  if (isLoading) return <p className="text-muted-foreground">Chargement...</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Scores ESG</h1>

      {entries.length === 0 ? (
        <p data-testid="esg-empty" className="text-muted-foreground">
          Aucun ticker en surveillance.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <button
                  data-testid="sort-ticker"
                  className="flex items-center font-semibold hover:text-foreground"
                  onClick={() => toggleSort('ticker')}
                >
                  Ticker
                  <SortIndicator active={sortKey === 'ticker'} dir={sortDir} />
                </button>
              </TableHead>
              <TableHead>
                <button
                  data-testid="sort-esg-score"
                  className="flex items-center font-semibold hover:text-foreground"
                  onClick={() => toggleSort('last_esg_score')}
                >
                  Score ESG
                  <SortIndicator active={sortKey === 'last_esg_score'} dir={sortDir} />
                </button>
              </TableHead>
              <TableHead>Verdict</TableHead>
              <TableHead>Seuil alerte</TableHead>
              <TableHead>Dernière analyse</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((entry) => {
              const badge = esgBadgeProps(entry.last_esg_score)
              return (
                <TableRow
                  key={entry.ticker}
                  data-testid={`esg-row-${entry.ticker}`}
                  className={
                    selectedTicker === entry.ticker ? 'bg-muted/40' : undefined
                  }
                >
                  <TableCell className="font-mono font-semibold">
                    <button
                      data-testid={`esg-ticker-btn-${entry.ticker}`}
                      onClick={() => setSelectedTicker(entry.ticker)}
                      className="hover:underline"
                    >
                      {entry.ticker}
                    </button>
                  </TableCell>
                  <TableCell data-testid={`esg-score-cell-${entry.ticker}`}>
                    {entry.last_esg_score !== null
                      ? entry.last_esg_score.toFixed(1)
                      : '--'}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={badge.variant}
                      data-testid={`esg-verdict-badge-${entry.ticker}`}
                    >
                      {badge.label}
                    </Badge>
                  </TableCell>
                  <TableCell>{entry.esg_alert_threshold.toFixed(1)}</TableCell>
                  <TableCell>
                    {entry.last_analyzed_at ? (
                      new Date(entry.last_analyzed_at).toLocaleDateString('fr-CA')
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      data-testid={`analyser-btn-${entry.ticker}`}
                      onClick={() => navigate(`/?ticker=${entry.ticker}`)}
                    >
                      Analyser
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}

      {selectedTicker && (
        <div className="space-y-2" data-testid="esg-history-section">
          <h2 className="text-lg font-semibold">
            Évolution ESG — <span className="font-mono">{selectedTicker}</span>
          </h2>
          <EsgHistoryChart
            data={historyData?.points ?? []}
            isLoading={historyLoading}
            isError={historyError}
          />
        </div>
      )}
    </div>
  )
}
