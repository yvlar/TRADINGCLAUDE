import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HistoryPage from '../pages/HistoryPage'
import * as analyzeApi from '../api/analyze'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return { ...actual, getHistoryPaged: vi.fn(), downloadTickerPdf: vi.fn() }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const emptyPaged = {
  ticker: null,
  q: null,
  entries: [],
  page: 1,
  page_size: 10,
  total_count: 0,
  total_pages: 1,
}

describe('HistorySearch (Sprint 73 + Sprint 90)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('appelle getHistoryPaged avec q seul quand seul le champ recherche est rempli', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-search-input'), 'ACHAT')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(analyzeApi.getHistoryPaged).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'ACHAT' }),
        1,
        10,
      )
    })
  })

  it('appelle getHistoryPaged avec ticker et q quand les deux champs sont remplis', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.type(screen.getByTestId('history-search-input'), 'CANDIDAT')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(analyzeApi.getHistoryPaged).toHaveBeenCalledWith(
        expect.objectContaining({ ticker: 'BNS', q: 'CANDIDAT' }),
        1,
        10,
      )
    })
  })

  it('affiche le notice cross-ticker quand q seul est fourni et des résultats existent', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue({
      ...emptyPaged,
      entries: [
        {
          analysis_id: 'aaa',
          ticker: 'BNS',
          workflow: 'value_graham',
          skills_applied: ['graham_analysis'],
          cost_usd: 0.004,
          defensive_score: 7,
          graham_verdict: 'CANDIDAT_SOLIDE',
          earnings_verdict: null,
          tags: [],
          created_at: '2026-05-10T12:00:00+00:00',
        },
      ],
      total_count: 1,
    })
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-search-input'), 'CANDIDAT')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('search-cross-ticker-notice')).toBeInTheDocument()
    })
  })

  it('affiche le message "Aucun résultat" quand la recherche est vide', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-search-input'), 'INTROUVABLE')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('history-empty')).toBeInTheDocument()
    })
  })

  it('le bouton est activé dès que le champ recherche est non vide', async () => {
    const user = userEvent.setup()
    render(<HistoryPage />, { wrapper })

    const btn = screen.getByTestId('history-search-btn')
    expect(btn).toBeDisabled()

    await user.type(screen.getByTestId('history-search-input'), 'graham')
    expect(btn).not.toBeDisabled()
  })
})
