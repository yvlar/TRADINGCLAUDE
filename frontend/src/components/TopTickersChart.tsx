import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Skeleton } from './ui/skeleton'
import { CHART, SERIES } from '../lib/colors'
import type { TickerMetrics } from '../types'

interface Props {
  tickers: TickerMetrics[]
  isLoading?: boolean
  isError?: boolean
  limit?: number
}

export function TopTickersChart({ tickers, isLoading, isError, limit = 10 }: Props) {
  if (isLoading) {
    return (
      <div data-testid="top-tickers-loading">
        <Skeleton className="h-[220px] w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="top-tickers-error">
        Erreur de chargement
      </p>
    )
  }

  if (tickers.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="top-tickers-empty">
        Aucune analyse sur la période
      </p>
    )
  }

  const data = [...tickers]
    .sort((a, b) => b.analyses - a.analyses)
    .slice(0, limit)
    .map((t) => ({ ticker: t.ticker, analyses: t.analyses }))

  return (
    <div data-testid="top-tickers-chart">
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 28)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="ticker"
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
            width={64}
          />
          <Tooltip
            cursor={{ fill: CHART.cursor }}
            contentStyle={{
              background: CHART.tooltipBg,
              border: `1px solid ${CHART.tooltipBorder}`,
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}`, 'Analyses'] as [string, string]}
          />
          <Bar dataKey="analyses" fill={SERIES[0]} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
