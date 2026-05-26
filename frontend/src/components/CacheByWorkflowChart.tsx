import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  cacheByWorkflow: Record<string, number>
  isLoading?: boolean
  isError?: boolean
}

export function CacheByWorkflowChart({ cacheByWorkflow, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground py-4" data-testid="cache-workflow-loading">
        Chargement...
      </p>
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
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="workflow"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            width={130}
          />
          <Tooltip
            cursor={{ fill: '#1e293b' }}
            contentStyle={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}%`, 'Taux de cache'] as [string, string]}
          />
          <Bar dataKey="pct" fill="#4ade80" radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
