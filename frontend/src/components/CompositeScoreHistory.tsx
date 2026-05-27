import { useQuery } from '@tanstack/react-query'
import { getCompositeHistory } from '../api/analyze'
import { Skeleton } from './ui/skeleton'

function scoreLabelColor(label: string): string {
  if (label === 'FORT') return 'text-bull'
  if (label === 'MODÉRÉ' || label === 'MODERE') return 'text-neutral'
  return 'text-bear'
}

interface CompositeScoreHistoryProps {
  ticker: string
}

export function CompositeScoreHistory({ ticker }: CompositeScoreHistoryProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['composite-history', ticker],
    queryFn: () => getCompositeHistory(ticker),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="space-y-1" data-testid="composite-history-loading">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </div>
    )
  }

  if (isError) {
    return <p className="text-xs text-destructive">Erreur de chargement</p>
  }

  if (!data || data.length === 0) {
    return <p className="text-xs text-muted-foreground">Aucun historique disponible</p>
  }

  return (
    <div className="space-y-1" data-testid="composite-score-history">
      {data.slice(0, 5).map((point) => {
        const color = scoreLabelColor(point.label)
        return (
          <div key={point.id} className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground w-28 shrink-0">
              {new Date(point.recorded_at).toLocaleDateString('fr-CA')}
            </span>
            <span
              data-testid="composite-score"
              className={`font-semibold tabular-nums ${color}`}
            >
              {point.score.toFixed(1)}/100
              <span className="ml-1 text-muted-foreground">({point.label})</span>
            </span>
            <span className="text-muted-foreground truncate">{point.workflow}</span>
          </div>
        )
      })}
    </div>
  )
}
