import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EsgHistoryChart } from '../components/EsgHistoryChart'
import type { EsgHistoryPoint } from '../types'

// Recharts utilise SVG/canvas non disponibles en jsdom — on mocke le module entier
vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: ({ content }: { content: React.ReactNode }) => (
    <div data-testid="recharts-tooltip">{content as React.ReactNode}</div>
  ),
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-responsive-container">{children}</div>
  ),
}))

function makePoint(overrides: Partial<EsgHistoryPoint> = {}): EsgHistoryPoint {
  return {
    id: '1',
    ticker: 'BNS',
    score: 7.5,
    verdict: 'ESG_MODERE',
    recorded_at: '2026-05-10T12:00:00Z',
    ...overrides,
  }
}

describe('EsgHistoryChart', () => {
  it('rend "Aucun historique ESG" quand la liste est vide', () => {
    render(<EsgHistoryChart data={[]} />)
    expect(screen.getByTestId('esg-chart-empty')).toBeInTheDocument()
    expect(screen.getByText('Aucun historique ESG')).toBeInTheDocument()
  })

  it('rend le graphique recharts avec plusieurs points', () => {
    const data = [
      makePoint({ id: '1', score: 11, verdict: 'ESG_FORT', recorded_at: '2026-03-01T00:00:00Z' }),
      makePoint({ id: '2', score: 7, verdict: 'ESG_MODERE', recorded_at: '2026-04-01T00:00:00Z' }),
      makePoint({ id: '3', score: 3, verdict: 'ESG_FAIBLE', recorded_at: '2026-05-01T00:00:00Z' }),
    ]
    render(<EsgHistoryChart data={data} />)
    expect(screen.getByTestId('esg-history-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-line-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-responsive-container')).toBeInTheDocument()
  })

  it('affiche l\'etat de chargement et masque le graphique', () => {
    render(<EsgHistoryChart data={[makePoint()]} isLoading />)
    expect(screen.getByTestId('esg-chart-loading')).toBeInTheDocument()
    expect(screen.queryByTestId('esg-history-chart')).not.toBeInTheDocument()
  })

  it('affiche un message d\'erreur si isError=true', () => {
    render(<EsgHistoryChart data={[]} isError />)
    expect(screen.getByTestId('esg-chart-error')).toBeInTheDocument()
    expect(screen.getByText('Erreur de chargement')).toBeInTheDocument()
  })
})
