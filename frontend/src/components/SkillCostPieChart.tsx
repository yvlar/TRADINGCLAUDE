import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type PieSectorDataItem,
} from 'recharts'
import { Skeleton } from './ui/skeleton'
import { CHART, SERIES } from '../lib/colors'

interface Props {
  skillsCost: Record<string, number>
  isLoading?: boolean
  isError?: boolean
  onSkillClick?: (skill: string) => void
}

export function SkillCostPieChart({ skillsCost, isLoading, isError, onSkillClick }: Props) {
  if (isLoading) {
    return (
      <div data-testid="skill-cost-loading">
        <Skeleton className="h-[260px] w-full" />
      </div>
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
            onClick={(slice: PieSectorDataItem) => {
              // recharts expose le datum original (`{skill, cost}`) sous `payload`
              const skill = slice?.payload?.skill
              if (onSkillClick && typeof skill === 'string') onSkillClick(skill)
            }}
            cursor={onSkillClick ? 'pointer' : undefined}
          >
            {data.map((entry, i) => (
              <Cell key={entry.skill} fill={SERIES[i % SERIES.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: CHART.tooltipBg,
              border: `1px solid ${CHART.tooltipBorder}`,
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
