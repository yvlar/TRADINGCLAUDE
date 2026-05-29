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

const _entry = (id: string) => ({
  analysis_id: id,
  ticker: 'BNS',
  workflow: 'value_graham',
  skills_applied: ['graham_analysis'],
  cost_usd: 0.004,
  defensive_score: 7,
  graham_verdict: 'CANDIDAT_SOLIDE',
  earnings_verdict: null,
  created_at: '2026-05-10T12:00:00+00:00',
  tags: [],
})

const pagedResp = (page: number, totalPages = 3, totalCount = 25) => ({
  ticker: 'BNS',
  q: null,
  entries: [_entry(`id-${page}-1`), _entry(`id-${page}-2`)],
  page,
  page_size: 10,
  total_count: totalCount,
  total_pages: totalPages,
})

describe('HistoryPagination (Sprint 90)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche les boutons Précédent/Suivant et le label de page après recherche', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(1))
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('history-pagination-prev')).toBeInTheDocument()
      expect(screen.getByTestId('history-pagination-next')).toBeInTheDocument()
      expect(screen.getByTestId('history-page-label')).toHaveTextContent('Page 1 sur 3')
    })
  })

  it('clic Suivant déclenche un appel getHistoryPaged avec page=2', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(1))
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('history-pagination-next')).toBeInTheDocument()
    })

    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(2))
    await user.click(screen.getByTestId('history-pagination-next'))

    await waitFor(() => {
      const calls = vi.mocked(analyzeApi.getHistoryPaged).mock.calls
      const page2Call = calls.find(([, page]) => page === 2)
      expect(page2Call).toBeDefined()
    })
  })

  it('clic Précédent décrémente la page', async () => {
    const user = userEvent.setup()
    // Démarrage en page 1, clic Suivant → page 2
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(1))
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('history-pagination-next')).toBeInTheDocument()
    })

    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(2))
    await user.click(screen.getByTestId('history-pagination-next'))

    await waitFor(() => {
      expect(screen.getByTestId('history-page-label')).toHaveTextContent('Page 2 sur 3')
    })

    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(1))
    await user.click(screen.getByTestId('history-pagination-prev'))

    await waitFor(() => {
      expect(screen.getByTestId('history-page-label')).toHaveTextContent('Page 1 sur 3')
    })
  })

  it('modification du filtre ticker remet currentPage à 1', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(1))
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByTestId('history-ticker-input'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('history-pagination-next')).toBeInTheDocument()
    })

    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedResp(2))
    await user.click(screen.getByTestId('history-pagination-next'))

    await waitFor(() => {
      expect(screen.getByTestId('history-page-label')).toHaveTextContent('Page 2 sur 3')
    })

    // Nouveau filtre : changer le ticker et re-soumettre
    vi.mocked(analyzeApi.getHistoryPaged).mockClear()
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue({ ...pagedResp(1), ticker: 'TD' })

    await user.clear(screen.getByTestId('history-ticker-input'))
    await user.type(screen.getByTestId('history-ticker-input'), 'TD')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      const calls = vi.mocked(analyzeApi.getHistoryPaged).mock.calls
      // Le dernier appel doit être page=1
      const last = calls[calls.length - 1]
      expect(last[1]).toBe(1)
    })
  })
})
