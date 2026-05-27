import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CompositeScoreHistory } from '../components/CompositeScoreHistory'
import * as analyzeApi from '../api/analyze'
import type { CompositeHistoryPoint } from '../types'

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

describe('CompositeScoreHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('appelle getCompositeHistory et non getPerformance', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([makePoint()])
    render(<CompositeScoreHistory ticker="BNS" />, { wrapper })
    await waitFor(() => expect(analyzeApi.getCompositeHistory).toHaveBeenCalledWith('BNS'))
  })

  it('affiche un état de chargement', () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockReturnValue(new Promise(() => {}))
    render(<CompositeScoreHistory ticker="BNS" />, { wrapper })
    expect(screen.getByTestId('composite-history-loading')).toBeInTheDocument()
  })

  it('affiche les scores avec labels après chargement', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([
      makePoint({ score: 72.5, label: 'FORT' }),
      makePoint({ id: 'uuid-2', score: 45.0, label: 'MODÉRÉ', recorded_at: '2026-05-01T12:00:00Z' }),
    ])
    render(<CompositeScoreHistory ticker="BNS" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composite-score-history')).toBeInTheDocument()
    })
    const scores = screen.getAllByTestId('composite-score')
    expect(scores).toHaveLength(2)
    expect(scores[0]).toHaveTextContent('72.5/100')
    expect(scores[0]).toHaveTextContent('(FORT)')
    expect(scores[1]).toHaveTextContent('45.0/100')
    expect(scores[1]).toHaveTextContent('(MODÉRÉ)')
  })

  it('affiche FAIBLE pour un score avec label FAIBLE', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([
      makePoint({ ticker: 'TST', score: 32.0, label: 'FAIBLE' }),
    ])
    render(<CompositeScoreHistory ticker="TST" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composite-score')).toBeInTheDocument()
    })
    expect(screen.getByTestId('composite-score')).toHaveTextContent('32.0/100')
    expect(screen.getByTestId('composite-score')).toHaveTextContent('(FAIBLE)')
  })

  it('affiche un message si aucune entrée', async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue([])
    render(<CompositeScoreHistory ticker="TST" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Aucun historique disponible')).toBeInTheDocument()
    })
  })

  it("affiche un message d'erreur si la requête échoue", async () => {
    vi.mocked(analyzeApi.getCompositeHistory).mockRejectedValue(new Error('Erreur réseau'))
    render(<CompositeScoreHistory ticker="ERR" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Erreur de chargement')).toBeInTheDocument()
    })
  })

  it('limite à 5 entrées affichées', async () => {
    const points = Array.from({ length: 8 }, (_, i) => makePoint({ id: `uuid-${i}`, score: 50.0 + i, label: 'MODÉRÉ' }))
    vi.mocked(analyzeApi.getCompositeHistory).mockResolvedValue(points)
    render(<CompositeScoreHistory ticker="BNS" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composite-score-history')).toBeInTheDocument()
    })
    expect(screen.getAllByTestId('composite-score')).toHaveLength(5)
  })
})
