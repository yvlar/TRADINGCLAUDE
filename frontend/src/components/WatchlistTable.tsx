import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import type { WatchlistEntry } from '../types'

interface WatchlistTableProps {
  entries: WatchlistEntry[]
  onDelete: (id: string) => void
  onAnalyze: (id: string) => void
  deletingId?: string | null
  analyzingId?: string | null
  onDownloadPdf?: (ticker: string, id: string) => void
  pdfLoadingId?: string | null
}

function computeAlerte(entry: WatchlistEntry): boolean | null {
  if (
    entry.last_price_checked == null ||
    entry.last_intrinsic_value == null ||
    entry.last_intrinsic_value === 0
  ) {
    return null
  }
  const ecart =
    Math.abs((entry.last_price_checked - entry.last_intrinsic_value) / entry.last_intrinsic_value)
  return ecart >= entry.price_alert_threshold_pct
}

export function WatchlistTable({
  entries,
  onDelete,
  onAnalyze,
  deletingId,
  analyzingId,
  onDownloadPdf,
  pdfLoadingId,
}: WatchlistTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Workflow</TableHead>
          <TableHead>Dernier score</TableHead>
          <TableHead>Valeur intrinsèque</TableHead>
          <TableHead>Prix vérifié</TableHead>
          <TableHead>Alerte</TableHead>
          <TableHead>Score composite</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => {
          const alerte = computeAlerte(entry)
          return (
            <TableRow key={entry.id} data-testid="watchlist-row">
              <TableCell className="font-mono font-semibold">{entry.ticker}</TableCell>
              <TableCell>{entry.workflow}</TableCell>
              <TableCell>
                {entry.last_score != null ? (
                  <span className="tabular-nums">{entry.last_score}/8</span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {entry.last_intrinsic_value != null
                  ? `$${entry.last_intrinsic_value.toFixed(2)}`
                  : <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell>
                {entry.last_price_checked != null
                  ? `$${entry.last_price_checked.toFixed(2)}`
                  : <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell>
                {alerte === null ? (
                  <span className="text-muted-foreground">—</span>
                ) : alerte ? (
                  <Badge variant="destructive">Alerte</Badge>
                ) : (
                  <Badge variant="success">OK</Badge>
                )}
              </TableCell>
              <TableCell data-testid="composite-score-cell">
                {entry.last_composite_score != null ? (
                  <span className={
                    entry.last_composite_score >= 70 ? 'text-green-400 font-semibold' :
                    entry.last_composite_score >= 45 ? 'text-yellow-400 font-semibold' :
                    'text-red-400 font-semibold'
                  }>
                    {entry.last_composite_score.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={analyzingId === entry.id}
                    onClick={() => onAnalyze(entry.id)}
                  >
                    {analyzingId === entry.id ? '...' : 'Analyser'}
                  </Button>
                  {onDownloadPdf && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pdfLoadingId === entry.id}
                      onClick={() => onDownloadPdf(entry.ticker, entry.id)}
                      data-testid={`pdf-btn-${entry.ticker}`}
                    >
                      {pdfLoadingId === entry.id ? '...' : 'PDF'}
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="sm"
                    aria-label="Supprimer"
                    disabled={deletingId === entry.id}
                    onClick={() => onDelete(entry.id)}
                  >
                    {deletingId === entry.id ? '...' : 'Supprimer'}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
