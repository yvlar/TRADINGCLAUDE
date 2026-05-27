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
import { CHART } from '../lib/colors'

interface Props {
  cacheByWorkflow: Record<string, number>
  isLoading?: boolean
  isError?: boolean
}

export function CacheByWorkflowChart({ cacheByWorkflow, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <div data-testid="cache-workflow-loading">
        <Skeleton className="h-[140px] w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="cache-workflow-error">
        Erreur de chargement
      </p>
    )
  }

  const data = Object.entries(cacheByWorkflow)
    .map(([workflow, ratio]) => ({ workflow, pct: Math.round(ratio * 1000) / 10 }))
    .sort((a, b) => b.pct - a.pct)

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="cache-workflow-empty">
        Aucun workflow sur la période
      </p>
    )
  }

  return (
    <div data-testid="cache-workflow-chart">
      <ResponsiveContainer width="100%" height={Math.max(140, data.length * 36)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="workflow"
            tick={{ fontSize: 10, fill: CHART.axis }}
            tickLine={false}
            width={130}
          />
          <Tooltip
            cursor={{ fill: CHART.cursor }}
            contentStyle={{
              background: CHART.tooltipBg,
              border: `1px solid ${CHART.tooltipBorder}`,
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}%`, 'Taux de cache'] as [string, string]}
          />
          <Bar dataKey="pct" fill={CHART.bull} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
