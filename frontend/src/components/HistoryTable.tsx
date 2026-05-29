import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { AnnotationSection } from './AnnotationSection'
import { TagChip } from './TagChip'
import type { HistoryEntry } from '../types'

function verdictVariant(verdict: string | null): 'success' | 'warning' | 'danger' | 'outline' {
  if (!verdict) return 'outline'
  const v = verdict.toUpperCase()
  if (v.includes('ACHETER') || v.includes('EXEMPLAIRE') || v.includes('SOLIDE')) return 'success'
  if (v.includes('CONSERVER') || v.includes('WATCHLIST')) return 'warning'
  return 'danger'
}

interface HistoryTableProps {
  entries: HistoryEntry[]
  hasMore: boolean
  onLoadMore: () => void
  isLoading?: boolean
  onDownloadPdf?: (analysisId: string, ticker: string) => void
  onDeleteAnalysis?: (analysisId: string) => void
}

export function HistoryTable({
  entries,
  hasMore,
  onLoadMore,
  isLoading,
  onDownloadPdf,
  onDeleteAnalysis,
}: HistoryTableProps) {
  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Aucun historique trouvé.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      <Card>
        <CardHeader>
          <CardTitle>{entries.length} analyses</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Ticker</TableHead>
                <TableHead>Workflow</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Verdict</TableHead>
                <TableHead>Coût</TableHead>
                <TableHead>PDF</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>Supprimer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.analysis_id}>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(entry.created_at).toLocaleString('fr-CA')}
                  </TableCell>
                  <TableCell className="font-bold">{entry.ticker}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{entry.workflow}</TableCell>
                  <TableCell>
                    {entry.defensive_score != null ? (
                      <span
                        className={
                          entry.defensive_score >= 6
                            ? 'text-bull font-semibold'
                            : entry.defensive_score >= 4
                            ? 'text-neutral font-semibold'
                            : 'text-bear font-semibold'
                        }
                      >
                        {entry.defensive_score}/8
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {entry.graham_verdict ? (
                      <Badge variant={verdictVariant(entry.graham_verdict)}>
                        {entry.graham_verdict}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground tabular-nums">
                    ${entry.cost_usd.toFixed(4)}
                  </TableCell>
                  <TableCell>
                    {onDownloadPdf && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDownloadPdf(entry.analysis_id, entry.ticker)}
                        className="h-7 text-xs"
                      >
                        ⬇ PDF
                      </Button>
                    )}
                  </TableCell>
                  <TableCell className="min-w-[140px]">
                    {entry.tags.length > 0 && (
                      <div
                        className="mb-1 flex flex-wrap gap-1"
                        data-testid={`history-tags-${entry.analysis_id}`}
                      >
                        {entry.tags.map((tag) => (
                          <TagChip key={tag} tag={tag} />
                        ))}
                      </div>
                    )}
                    <AnnotationSection analysisId={entry.analysis_id} />
                  </TableCell>
                  <TableCell>
                    {onDeleteAnalysis && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDeleteAnalysis(entry.analysis_id)}
                        className="h-7 text-xs text-destructive hover:text-destructive"
                        data-testid={`delete-analysis-${entry.analysis_id}`}
                      >
                        🗑
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {hasMore && (
        <Button variant="outline" onClick={onLoadMore} disabled={isLoading} className="w-full">
          {isLoading ? 'Chargement...' : 'Charger plus'}
        </Button>
      )}
    </div>
  )
}
