import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CompositeSparkline } from '../components/CompositeSparkline'
import * as analyzeApi from '../api/analyze'
import type { CompositeHistoryPoint } from '../types'

vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-line-chart">{children}</div>
  ),
  Line: () => null,
}))

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return { ...actual, getCompositeHistory: vi.fn() }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const makePoint = (overrides: Partial<CompositeHistoryPoint> = {}): CompositeHistoryPoint => ({
  id: 'uuid-1',
  ticker: 'BNS',
  score: 72.5,
  label: 'FORT',
  workflow: 'value_graham',
  recorded_at: '2026-05-10T12:00:00Z',
  ...overrides,
})

describe('CompositeSparkline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('rend un indicateur de chargement quand la query est en cours', () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockReturnValue(new Promise(() => {}))
    render(<CompositeSparkline ticker="BNS" />, { wrapper })
    expect(screen.getByTestId('sparkline-loading')).toBeInTheDocument()
  })

  it('rend "--" quand la requête API échoue', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockRejectedValue(new Error('Erreur réseau'))
    render(<CompositeSparkline ticker="BNS" />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('—')).toBeInTheDocument()
    })
  })

  it('rend "--" quand 0 points retournés', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([])
    render(<CompositeSparkline ticker="BNS" />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('—')).toBeInTheDocument()
    })
  })

  it('rend un LineChart quand des données sont présentes', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([makePoint()])
    render(<CompositeSparkline ticker="BNS" />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('recharts-line-chart')).toBeInTheDocument()
    })
  })

  it('propage la prop height au conteneur', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([makePoint()])
    render(<CompositeSparkline ticker="BNS" height={60} />, { wrapper })
    await waitFor(() => {
      const container = screen.getByTestId('sparkline-container')
      expect(container).toHaveStyle({ height: '60px' })
    })
  })
})
