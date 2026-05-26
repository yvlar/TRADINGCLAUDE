import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { AlertEntry } from '../types'

interface Props {
  alerts: AlertEntry[]
  isLoading?: boolean
  isError?: boolean
}

/** Regroupe les alertes par jour (YYYY-MM-DD) et compte les occurrences. */
function bucketByDay(alerts: AlertEntry[]): { date: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const a of alerts) {
    const day = a.created_at.slice(0, 10)
    counts.set(day, (counts.get(day) ?? 0) + 1)
  }
  return Array.from(counts.entries())
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date))
}

export function AlertsTimelineChart({ alerts, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground py-4" data-testid="alerts-timeline-loading">
        Chargement...
      </p>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="alerts-timeline-error">
        Erreur de chargement
      </p>
    )
  }

  const data = bucketByDay(alerts)

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="alerts-timeline-empty">
        Aucune alerte sur la période
      </p>
    )
  }

  return (
    <div data-testid="alerts-timeline-chart">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            width={28}
          />
          <Tooltip
            cursor={{ fill: '#1e293b' }}
            contentStyle={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}`, 'Alertes'] as [string, string]}
          />
          <Bar dataKey="count" fill="#fb923c" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
