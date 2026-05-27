import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CacheByWorkflowChart } from '../components/CacheByWorkflowChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

describe('CacheByWorkflowChart', () => {
  it('rend le graphique quand des workflows sont présents', () => {
    render(
      <CacheByWorkflowChart cacheByWorkflow={{ value_graham: 0.72, compounder_buffett: 0.55 }} />,
    )
    expect(screen.getByTestId('cache-workflow-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-bar-chart')).toBeInTheDocument()
  })

  it('affiche un état vide quand aucun workflow', () => {
    render(<CacheByWorkflowChart cacheByWorkflow={{}} />)
    expect(screen.getByTestId('cache-workflow-empty')).toBeInTheDocument()
  })

  it('affiche un état de chargement', () => {
    render(<CacheByWorkflowChart cacheByWorkflow={{}} isLoading />)
    expect(screen.getByTestId('cache-workflow-loading')).toBeInTheDocument()
  })

  it('affiche un état d’erreur', () => {
    render(<CacheByWorkflowChart cacheByWorkflow={{}} isError />)
    expect(screen.getByTestId('cache-workflow-error')).toBeInTheDocument()
  })
})
