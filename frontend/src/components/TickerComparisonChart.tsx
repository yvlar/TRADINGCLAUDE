import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { Skeleton } from './ui/skeleton'
import { CHART, SERIES } from '../lib/colors'
import type { CompositeHistoryPoint } from '../types'

interface Props {
  tickers: string[]
  tickersData: Map<string, CompositeHistoryPoint[]>
  isLoading?: boolean
  isError?: boolean
}

function buildChartData(
  tickers: string[],
  tickersData: Map<string, CompositeHistoryPoint[]>,
): Record<string, string | number | null>[] {
  const allDates = new Set<string>()
  for (const [, points] of tickersData) {
    points.forEach((p) => allDates.add(p.recorded_at.slice(0, 10)))
  }
  const sortedDates = Array.from(allDates).sort()

  return sortedDates.map((date) => {
    const point: Record<string, string | number | null> = { date }
    for (const ticker of tickers) {
      const points = tickersData.get(ticker) ?? []
      const match = points.find((p) => p.recorded_at.slice(0, 10) === date)
      point[ticker] = match !== undefined ? match.score : null
    }
    return point
  })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-border bg-card px-3 py-2 text-xs shadow-md">
      <p className="font-semibold mb-1">{label as string}</p>
      {(payload as Array<{ name: string; value: number | null; color: string }>).map((entry) =>
        entry.value !== null ? (
          <p key={entry.name}>
            <span style={{ color: entry.color }} className="font-medium">
              {entry.name}
            </span>
            {' : '}
            <span className="tabular-nums font-semibold" style={{ color: entry.color }}>
              {entry.value.toFixed(1)}/100
            </span>
          </p>
        ) : null,
      )}
    </div>
  )
}

export function TickerComparisonChart({ tickers, tickersData, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <div data-testid="comparison-loading">
        <Skeleton className="h-[260px] w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="comparison-error">
        Erreur de chargement
      </p>
    )
  }

  if (tickersData.size === 0 || tickers.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="comparison-empty">
        Aucune donnée
      </p>
    )
  }

  const chartData = buildChartData(tickers, tickersData)

  if (chartData.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="comparison-empty">
        Aucune donnée
      </p>
    )
  }

  return (
    <div data-testid="ticker-comparison-chart">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
            width={32}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '11px' }} />
          <ReferenceLine
            y={70}
            stroke={CHART.bull}
            strokeDasharray="4 2"
            label={{ value: 'FORT', position: 'insideTopRight', fontSize: 9, fill: CHART.bull }}
          />
          <ReferenceLine
            y={45}
            stroke={CHART.neutral}
            strokeDasharray="4 2"
            label={{ value: 'MODÉRÉ', position: 'insideTopRight', fontSize: 9, fill: CHART.neutral }}
          />
          {tickers.map((ticker, i) => (
            <Line
              key={ticker}
              type="monotone"
              dataKey={ticker}
              stroke={SERIES[i % SERIES.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5 }}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
