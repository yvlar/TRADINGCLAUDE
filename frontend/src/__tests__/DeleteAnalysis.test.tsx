import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HistoryPage from '../pages/HistoryPage'
import * as analyzeApi from '../api/analyze'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    getHistoryPaged: vi.fn(),
    downloadTickerPdf: vi.fn(),
    deleteAnalysis: vi.fn(),
  }
})

vi.mock('../api/annotations', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/annotations')>()
  return {
    ...actual,
    downloadAnnotationsCsv: vi.fn(),
    downloadAnnotationsXlsx: vi.fn(),
  }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const ANALYSIS_ID = '550e8400-e29b-41d4-a716-446655440000'

const pagedWithEntry = {
  ticker: 'BNS',
  q: null,
  entries: [
    {
      analysis_id: ANALYSIS_ID,
      ticker: 'BNS',
      workflow: 'value_graham',
      skills_applied: ['graham_analysis'],
      cost_usd: 0.001,
      defensive_score: 5,
      graham_verdict: 'CONSERVER',
      earnings_verdict: null,
      tags: [],
      created_at: '2026-05-20T12:00:00+00:00',
    },
  ],
  page: 1,
  page_size: 10,
  total_count: 1,
  total_pages: 1,
}

describe('DeleteAnalysis — bouton Supprimer dans HistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le bouton Supprimer pour chaque entree', async () => {
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedWithEntry)
    const user = userEvent.setup()
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(
        screen.getByTestId(`delete-analysis-${ANALYSIS_ID}`),
      ).toBeInTheDocument()
    })
  })

  it('clic + confirmation appelle deleteAnalysis avec le bon analysis_id', async () => {
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedWithEntry)
    vi.mocked(analyzeApi.deleteAnalysis).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const user = userEvent.setup()
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId(`delete-analysis-${ANALYSIS_ID}`)).toBeInTheDocument()
    })

    await user.click(screen.getByTestId(`delete-analysis-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(analyzeApi.deleteAnalysis).toHaveBeenCalledWith(ANALYSIS_ID)
    })
  })

  it('apres suppression, l\'entree est retiree du tableau', async () => {
    vi.mocked(analyzeApi.getHistoryPaged).mockResolvedValue(pagedWithEntry)
    vi.mocked(analyzeApi.deleteAnalysis).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const user = userEvent.setup()
    render(<HistoryPage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() => {
      expect(screen.getByTestId(`delete-analysis-${ANALYSIS_ID}`)).toBeInTheDocument()
    })

    await user.click(screen.getByTestId(`delete-analysis-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(
        screen.queryByTestId(`delete-analysis-${ANALYSIS_ID}`),
      ).not.toBeInTheDocument()
    })
  })
})
