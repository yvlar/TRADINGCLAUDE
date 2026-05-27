import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  dailyCost: Record<string, number>
  isLoading?: boolean
  isError?: boolean
}

/** Convertit le dict {YYYY-MM-DD: coût} en série triée par date croissante. */
function toSeries(dailyCost: Record<string, number>): { date: string; cost: number }[] {
  return Object.entries(dailyCost)
    .map(([date, cost]) => ({ date, cost }))
    .sort((a, b) => a.date.localeCompare(b.date))
}

export function DailyCostTrendChart({ dailyCost, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground py-4" data-testid="daily-cost-loading">
        Chargement...
      </p>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="daily-cost-error">
        Erreur de chargement
      </p>
    )
  }

  const data = toSeries(dailyCost)

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="daily-cost-empty">
        Aucun coût sur la période
      </p>
    )
  }

  return (
    <div data-testid="daily-cost-chart">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            width={48}
            tickFormatter={(value) => `$${Number(value).toFixed(3)}`}
          />
          <Tooltip
            cursor={{ stroke: '#1e293b' }}
            contentStyle={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`$${Number(value).toFixed(4)}`, 'Coût'] as [string, string]}
          />
          <Line
            type="monotone"
            dataKey="cost"
            stroke="#4ade80"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
