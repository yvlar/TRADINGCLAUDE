import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const SLICE_COLORS = [
  '#60a5fa', '#4ade80', '#fb923c', '#c084fc', '#f87171',
  '#facc15', '#2dd4bf', '#f472b6', '#a3e635', '#38bdf8',
]

interface Props {
  skillsCost: Record<string, number>
  isLoading?: boolean
  isError?: boolean
}

export function SkillCostPieChart({ skillsCost, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground py-4" data-testid="skill-cost-loading">
        Chargement...
      </p>
    )
  }

  if (isError) {
    return (
      <p className="text-xs text-destructive py-4" data-testid="skill-cost-error">
        Erreur de chargement
      </p>
    )
  }

  const data = Object.entries(skillsCost)
    .map(([skill, cost]) => ({ skill, cost }))
    .filter((d) => d.cost > 0)
    .sort((a, b) => b.cost - a.cost)

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4" data-testid="skill-cost-empty">
        Aucun coût sur la période
      </p>
    )
  }

  return (
    <div data-testid="skill-cost-chart">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="cost"
            nameKey="skill"
            cx="50%"
            cy="50%"
            outerRadius={90}
            isAnimationActive={false}
          >
            {data.map((entry, i) => (
              <Cell key={entry.skill} fill={SLICE_COLORS[i % SLICE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value, name) => [`$${Number(value).toFixed(4)}`, name] as [string, string]}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
