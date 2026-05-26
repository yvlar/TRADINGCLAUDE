import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TopTickersChart } from '../components/TopTickersChart'
import type { TickerMetrics } from '../types'

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

const tickers: TickerMetrics[] = [
  { ticker: 'BNS', analyses: 5, cost_usd: 0.02 },
  { ticker: 'TD', analyses: 9, cost_usd: 0.04 },
]

describe('TopTickersChart', () => {
  it('rend le graphique quand des tickers sont fournis', () => {
    render(<TopTickersChart tickers={tickers} />)
    expect(screen.getByTestId('top-tickers-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-bar-chart')).toBeInTheDocument()
  })

  it('affiche un état vide quand aucun ticker', () => {
    render(<TopTickersChart tickers={[]} />)
    expect(screen.getByTestId('top-tickers-empty')).toBeInTheDocument()
  })

  it('affiche un état de chargement', () => {
    render(<TopTickersChart tickers={[]} isLoading />)
    expect(screen.getByTestId('top-tickers-loading')).toBeInTheDocument()
  })

  it('affiche un état d’erreur', () => {
    render(<TopTickersChart tickers={[]} isError />)
    expect(screen.getByTestId('top-tickers-error')).toBeInTheDocument()
  })
})
