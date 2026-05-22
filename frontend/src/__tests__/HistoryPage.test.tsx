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

describe('HistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le formulaire de recherche avec champ ticker et q', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByLabelText('Ticker')).toBeInTheDocument()
    expect(screen.getByLabelText('Recherche')).toBeInTheDocument()
    expect(screen.getByTestId('history-search-btn')).toBeInTheDocument()
  })

  it('le bouton est désactivé si ticker et q sont vides', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByTestId('history-search-btn')).toBeDisabled()
  })

  it('déclenche une requête avec le bon ticker si non vide', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue({
      ...emptyPaged,
      ticker: 'BNS',
    })
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(analyzeApi.getHistoryPaged).toHaveBeenCalledWith(
        expect.objectContaining({ ticker: 'BNS' }),
        1,
        10,
      )
    })
  })

  it("n'envoie jamais 'ALL' au backend", async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByLabelText('Recherche'), 'ACHAT')
    await user.click(screen.getByTestId('history-search-btn'))

    const calls = vi.mocked(analyzeApi.getHistoryPaged).mock.calls
    const allCalls = calls.some(([filters]) => filters.ticker === 'ALL')
    expect(allCalls).toBe(false)
  })
})
