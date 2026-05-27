import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DailyCostTrendChart } from '../components/DailyCostTrendChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

describe('DailyCostTrendChart', () => {
  it('rend la courbe quand des coûts quotidiens sont présents', () => {
    render(
      <DailyCostTrendChart
        dailyCost={{ '2026-05-24': 0.012, '2026-05-25': 0.018 }}
      />,
    )
    expect(screen.getByTestId('daily-cost-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-line-chart')).toBeInTheDocument()
  })

  it('affiche un état vide quand aucune donnée', () => {
    render(<DailyCostTrendChart dailyCost={{}} />)
    expect(screen.getByTestId('daily-cost-empty')).toBeInTheDocument()
  })

  it('affiche un état de chargement', () => {
    render(<DailyCostTrendChart dailyCost={{}} isLoading />)
    expect(screen.getByTestId('daily-cost-loading')).toBeInTheDocument()
  })

  it('affiche un état d’erreur', () => {
    render(<DailyCostTrendChart dailyCost={{}} isError />)
    expect(screen.getByTestId('daily-cost-error')).toBeInTheDocument()
  })
})
