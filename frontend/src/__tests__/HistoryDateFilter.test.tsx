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
  ticker: 'BNS',
  q: null,
  entries: [],
  page: 1,
  page_size: 10,
  total_count: 0,
  total_pages: 1,
}

describe('HistoryDateFilter (Sprint 79 + Sprint 90)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le champ date "Du"', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByTestId('history-from-date')).toBeInTheDocument()
  })

  it('affiche le champ date "Au"', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByTestId('history-to-date')).toBeInTheDocument()
  })

  it('appelle getHistoryPaged avec fromDt et toDt quand les deux dates sont renseignées', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.type(screen.getByTestId('history-from-date'), '2026-01-01')
    await user.type(screen.getByTestId('history-to-date'), '2026-05-18')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(analyzeApi.getHistoryPaged).toHaveBeenCalledWith(
        expect.objectContaining({
          ticker: 'BNS',
          fromDt: '2026-01-01',
          toDt: '2026-05-18',
        }),
        1,
        10,
      )
    })
  })

  it('affiche une erreur et ne soumet pas quand from > to', async () => {
    const user = userEvent.setup()
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.type(screen.getByTestId('history-from-date'), '2026-05-18')
    await user.type(screen.getByTestId('history-to-date'), '2026-01-01')
    await user.click(screen.getByTestId('history-search-btn'))

    expect(screen.getByTestId('history-date-error')).toBeInTheDocument()
    expect(analyzeApi.getHistoryPaged).not.toHaveBeenCalled()
  })

  it('appelle getHistoryPaged avec fromDt seul quand seule la date de début est renseignée', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(emptyPaged)
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.type(screen.getByTestId('history-from-date'), '2026-03-01')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(analyzeApi.getHistoryPaged).toHaveBeenCalledWith(
        expect.objectContaining({
          ticker: 'BNS',
          fromDt: '2026-03-01',
        }),
        1,
        10,
      )
    })
  })
})
