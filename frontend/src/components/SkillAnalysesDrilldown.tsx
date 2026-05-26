import { useQuery } from '@tanstack/react-query'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table'
import { fetchSkillAnalyses } from '../api/metrics'
import type { SkillAnalysisEntry } from '../types'

interface Props {
  skill: string
  days: number
  onClose?: () => void
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function DrilldownRow({ entry }: { entry: SkillAnalysisEntry }) {
  return (
    <TableRow data-testid={`skill-analysis-row-${entry.analysis_id}`}>
      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
        {formatDate(entry.created_at)}
      </TableCell>
      <TableCell className="font-mono font-semibold">{entry.ticker}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{entry.workflow_name}</TableCell>
      <TableCell className="text-right tabular-nums">${entry.cost_usd.toFixed(4)}</TableCell>
    </TableRow>
  )
}

export function SkillAnalysesDrilldown({ skill, days, onClose }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['skill-analyses', skill, days],
    queryFn: () => fetchSkillAnalyses(skill, days),
  })

  const entries = data?.entries ?? []

  return (
    <div className="rounded border border-border p-4 space-y-3" data-testid="skill-drilldown">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">
          Analyses utilisant <span className="font-mono">{skill}</span>
          {entries.length > 0 && (
            <span className="ml-2 text-xs text-muted-foreground">({entries.length})</span>
          )}
        </p>
        {onClose && (
          <button
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-foreground"
            data-testid="skill-drilldown-close"
          >
            Fermer ✕
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground py-2" data-testid="skill-drilldown-loading">
          Chargement...
        </p>
      ) : isError ? (
        <p className="text-xs text-destructive py-2" data-testid="skill-drilldown-error">
          Erreur de chargement
        </p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2" data-testid="skill-drilldown-empty">
          Aucune analyse pour ce skill sur la période.
        </p>
      ) : (
        <Table data-testid="skill-drilldown-table">
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Ticker</TableHead>
              <TableHead>Workflow</TableHead>
              <TableHead className="text-right">Coût (USD)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <DrilldownRow key={entry.analysis_id} entry={entry} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
