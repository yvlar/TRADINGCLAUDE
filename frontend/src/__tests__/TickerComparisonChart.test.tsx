import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TickerComparisonChart } from '../components/TickerComparisonChart'
import type { CompositeHistoryPoint } from '../types'

vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-line-chart">{children}</div>
  ),
  Line: ({ dataKey }: { dataKey: string }) => <div data-testid={`recharts-line-${dataKey}`} />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-responsive-container">{children}</div>
  ),
}))

function makePoint(ticker: string, score: number, date: string): CompositeHistoryPoint {
  return {
    id: `uuid-${ticker}-${date}`,
    ticker,
    score,
    label: score >= 70 ? 'FORT' : score >= 45 ? 'MODERE' : 'FAIBLE',
    workflow: 'value_graham',
    recorded_at: `${date}T12:00:00Z`,
  }
}

describe('TickerComparisonChart', () => {
  it('affiche "Aucune donnée" avec une map vide', () => {
    render(<TickerComparisonChart tickers={[]} tickersData={new Map()} />)
    expect(screen.getByTestId('comparison-empty')).toBeInTheDocument()
    expect(screen.getByText('Aucune donnée')).toBeInTheDocument()
  })

  it('affiche l\'état de chargement', () => {
    render(
      <TickerComparisonChart
        tickers={['BNS', 'TD']}
        tickersData={new Map()}
        isLoading
      />,
    )
    expect(screen.getByTestId('comparison-loading')).toBeInTheDocument()
  })

  it('affiche l\'état d\'erreur', () => {
    render(
      <TickerComparisonChart
        tickers={['BNS', 'TD']}
        tickersData={new Map()}
        isError
      />,
    )
    expect(screen.getByTestId('comparison-error')).toBeInTheDocument()
    expect(screen.getByText('Erreur de chargement')).toBeInTheDocument()
  })

  it('rend le graphique recharts avec 2 tickers', () => {
    const data = new Map([
      ['BNS', [makePoint('BNS', 72.5, '2026-05-01'), makePoint('BNS', 68.0, '2026-05-10')]],
      ['TD', [makePoint('TD', 55.0, '2026-05-01'), makePoint('TD', 60.0, '2026-05-10')]],
    ])
    render(<TickerComparisonChart tickers={['BNS', 'TD']} tickersData={data} />)
    expect(screen.getByTestId('ticker-comparison-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-line-BNS')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-line-TD')).toBeInTheDocument()
  })

  it('rend le graphique recharts avec 5 tickers (max)', () => {
    const tickers = ['BNS', 'TD', 'RY', 'BMO', 'CM']
    const data = new Map(tickers.map((t) => [t, [makePoint(t, 65.0, '2026-05-01')]]))
    render(<TickerComparisonChart tickers={tickers} tickersData={data} />)
    expect(screen.getByTestId('ticker-comparison-chart')).toBeInTheDocument()
    for (const t of tickers) {
      expect(screen.getByTestId(`recharts-line-${t}`)).toBeInTheDocument()
    }
  })

  it('affiche "Aucune donnée" si tous les tickers ont une liste vide', () => {
    const data = new Map<string, CompositeHistoryPoint[]>([
      ['BNS', []],
      ['TD', []],
    ])
    render(<TickerComparisonChart tickers={['BNS', 'TD']} tickersData={data} />)
    expect(screen.getByTestId('comparison-empty')).toBeInTheDocument()
  })
})
