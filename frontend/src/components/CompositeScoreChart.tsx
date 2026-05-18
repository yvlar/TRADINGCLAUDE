import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { CompositeHistoryPoint } from '../types'

interface Props {
  data: CompositeHistoryPoint[]
  isLoading?: boolean
  isError?: boolean
}

function labelColor(label: string): string {
  if (label === 'FORT') return '#4ade80'       // vert
  if (label === 'MODERE' || label === 'MODÉRÉ') return '#fb923c'  // orange
  return '#f87171'                              // rouge (FAIBLE)
}

function formatDate(iso: string): string {
  return iso.slice(0, 10)
}

interface ChartPoint {
  date: string
  score: number
  label: string
  workflow: string
  color: string
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomDot(props: any) {
  const { cx, cy, payload } = props as { cx: number; cy: number; payload: ChartPoint }
  return <circle cx={cx} cy={cy} r={4} fill={payload.color} stroke={payload.color} />
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const pt = payload[0].payload as ChartPoint
  return (
    <div className="rounded border border-border bg-card px-3 py-2 text-xs shadow-md">
      <p className="font-semibold">{pt.date}</p>
      <p>
        Score :{' '}
        <span className="font-semibold tabular-nums" style={{ color: pt.color }}>
          {pt.score.toFixed(1)}/100
        </span>
      </p>
      <p>Label : <span style={{ color: pt.color }}>{pt.label}</span></p>
      <p className="text-muted-foreground">{pt.workflow}</p>
    </div>
  )
}

export function CompositeScoreChart({ data, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground py-4" data-testid="chart-loading">
        Chargement...
      </p>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="chart-error">
        Erreur de chargement
      </p>
    )
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="chart-empty">
        Aucune donnée
      </p>
    )
  }

  const chartData: ChartPoint[] = data.map((pt) => ({
    date: formatDate(pt.recorded_at),
    score: pt.score,
    label: pt.label,
    workflow: pt.workflow,
    color: labelColor(pt.label),
  }))

  return (
    <div data-testid="composite-score-chart">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            width={32}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Seuil FORT */}
          <ReferenceLine y={70} stroke="#4ade80" strokeDasharray="4 2" label={{ value: 'FORT', position: 'insideTopRight', fontSize: 9, fill: '#4ade80' }} />
          {/* Seuil MODÉRÉ */}
          <ReferenceLine y={45} stroke="#fb923c" strokeDasharray="4 2" label={{ value: 'MODÉRÉ', position: 'insideTopRight', fontSize: 9, fill: '#fb923c' }} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#94a3b8"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 6 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
