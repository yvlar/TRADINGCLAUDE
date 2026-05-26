import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SkillCostPieChart } from '../components/SkillCostPieChart'

interface MockSlice {
  skill: string
  cost: number
}
interface MockPieProps {
  children: React.ReactNode
  data?: MockSlice[]
  onClick?: (slice: { payload: MockSlice }) => void
}

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-pie-chart">{children}</div>
  ),
  // recharts passe le datum original sous `payload` au handler onClick
  Pie: ({ children, data, onClick }: MockPieProps) => (
    <div
      data-testid="recharts-pie"
      onClick={() => data?.[0] && onClick?.({ payload: data[0] })}
    >
      {children}
    </div>
  ),
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

describe('SkillCostPieChart', () => {
  it('rend le camembert quand des coûts sont présents', () => {
    render(<SkillCostPieChart skillsCost={{ graham_analysis: 0.01, buffett_quality: 0.02 }} />)
    expect(screen.getByTestId('skill-cost-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-pie-chart')).toBeInTheDocument()
  })

  it('affiche un état vide quand tous les coûts sont nuls', () => {
    render(<SkillCostPieChart skillsCost={{ graham_analysis: 0 }} />)
    expect(screen.getByTestId('skill-cost-empty')).toBeInTheDocument()
  })

  it('affiche un état vide quand aucun skill', () => {
    render(<SkillCostPieChart skillsCost={{}} />)
    expect(screen.getByTestId('skill-cost-empty')).toBeInTheDocument()
  })

  it('affiche un état de chargement', () => {
    render(<SkillCostPieChart skillsCost={{}} isLoading />)
    expect(screen.getByTestId('skill-cost-loading')).toBeInTheDocument()
  })

  it('affiche un état d’erreur', () => {
    render(<SkillCostPieChart skillsCost={{}} isError />)
    expect(screen.getByTestId('skill-cost-error')).toBeInTheDocument()
  })

  it('appelle onSkillClick avec le skill au clic sur une tranche', async () => {
    const onSkillClick = vi.fn()
    const user = userEvent.setup()
    render(
      <SkillCostPieChart
        skillsCost={{ buffett_quality: 0.02, graham_analysis: 0.01 }}
        onSkillClick={onSkillClick}
      />,
    )
    // data triée par coût DESC → première tranche = buffett_quality
    await user.click(screen.getByTestId('recharts-pie'))
    expect(onSkillClick).toHaveBeenCalledWith('buffett_quality')
  })
})
