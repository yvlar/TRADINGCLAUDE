import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CompositeScoreChart } from '../components/CompositeScoreChart'
import type { CompositeHistoryPoint } from '../types'

// Recharts utilise SVG/canvas non disponibles en jsdom — on mocke le module entier
vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-responsive-container">{children}</div>
  ),
}))

function makePoint(overrides: Partial<CompositeHistoryPoint> = {}): CompositeHistoryPoint {
  return {
    id: 'uuid-1',
    ticker: 'BNS',
    score: 72.5,
    label: 'FORT',
    workflow: 'value_graham',
    recorded_at: '2026-05-10T12:00:00Z',
    ...overrides,
  }
}

describe('CompositeScoreChart', () => {
  it('rend sans crash avec un historique vide', () => {
    render(<CompositeScoreChart data={[]} />)
    expect(screen.getByTestId('chart-empty')).toBeInTheDocument()
  })

  it('affiche "Aucune donnée" quand la liste est vide', () => {
    render(<CompositeScoreChart data={[]} />)
    expect(screen.getByText('Aucune donnée')).toBeInTheDocument()
  })

  it('rend sans crash avec 3 points d\'historique', () => {
    const data = [
      makePoint({ id: '1', score: 72.5, label: 'FORT', recorded_at: '2026-03-01T00:00:00Z' }),
      makePoint({ id: '2', score: 50.0, label: 'MODERE', recorded_at: '2026-04-01T00:00:00Z' }),
      makePoint({ id: '3', score: 38.0, label: 'FAIBLE', recorded_at: '2026-05-01T00:00:00Z' }),
    ]
    render(<CompositeScoreChart data={data} />)
    expect(screen.getByTestId('composite-score-chart')).toBeInTheDocument()
  })

  it('affiche le graphique recharts quand la liste n\'est pas vide', () => {
    const data = [makePoint()]
    render(<CompositeScoreChart data={data} />)
    expect(screen.getByTestId('recharts-responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-line-chart')).toBeInTheDocument()
  })

  it('affiche l\'état de chargement', () => {
    render(<CompositeScoreChart data={[]} isLoading />)
    expect(screen.getByTestId('chart-loading')).toBeInTheDocument()
    expect(screen.getByText('Chargement...')).toBeInTheDocument()
  })

  it('affiche un message d\'erreur', () => {
    render(<CompositeScoreChart data={[]} isError />)
    expect(screen.getByTestId('chart-error')).toBeInTheDocument()
    expect(screen.getByText('Erreur de chargement')).toBeInTheDocument()
  })

  it('n\'affiche pas le graphique si isLoading est vrai même avec données', () => {
    render(<CompositeScoreChart data={[makePoint()]} isLoading />)
    expect(screen.queryByTestId('composite-score-chart')).not.toBeInTheDocument()
    expect(screen.getByTestId('chart-loading')).toBeInTheDocument()
  })
})
