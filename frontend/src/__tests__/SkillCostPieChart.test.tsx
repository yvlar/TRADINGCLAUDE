import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SkillCostPieChart } from '../components/SkillCostPieChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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
})
