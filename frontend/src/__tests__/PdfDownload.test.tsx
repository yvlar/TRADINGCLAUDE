import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HistoryPage from '../pages/HistoryPage'
import WatchlistPage from '../pages/WatchlistPage'
import * as analyzeApi from '../api/analyze'
import * as watchlistApi from '../api/watchlist'
import { ApiError } from '../api/client'
import type { WatchlistEntry } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    getHistory: vi.fn(),
    getHistoryPaged: vi.fn().mockResolvedValue({ entries: [], total_count: 0, total_pages: 1 }),
    downloadTickerPdf: vi.fn(),
  }
})

vi.mock('../api/watchlist')

beforeAll(() => {
  URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
  URL.revokeObjectURL = vi.fn()
})

const makeEntry = (overrides: Partial<WatchlistEntry> = {}): WatchlistEntry => ({
  id: 'entry-1',
  ticker: 'BNS',
  workflow: 'value_graham',
  last_analyzed_at: null,
  last_score: null,
  last_intrinsic_value: null,
  last_price_checked: null,
  price_alert_threshold_pct: 0.1,
  created_at: '2026-01-01T00:00:00Z',
  last_composite_score: null,
  composite_alert_threshold: 15.0,
  score_alerte_min: null,
  esg_alert_threshold: 5.0,
  last_esg_score: null,
  ...overrides,
})

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('PdfDownload — HistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(analyzeApi.getHistory).mockResolvedValue({
      ticker: 'BNS',
      entries: [],
      next_before: null,
    })
  })

  it('bouton "Télécharger PDF" visible après soumission du ticker', async () => {
    const user = userEvent.setup()
    wrap(<HistoryPage />)

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))

    await waitFor(() =>
      expect(screen.getByText('Télécharger PDF')).toBeInTheDocument(),
    )
  })

  it('clic "Télécharger PDF" appelle downloadTickerPdf avec le bon ticker', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadTickerPdf).mockResolvedValue(
      new Blob(['pdf'], { type: 'application/pdf' }),
    )
    wrap(<HistoryPage />)

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))
    await waitFor(() => expect(screen.getByText('Télécharger PDF')).toBeInTheDocument())

    await user.click(screen.getByText('Télécharger PDF'))

    await waitFor(() => {
      expect(analyzeApi.downloadTickerPdf).toHaveBeenCalledWith('BNS')
    })
  })

  it('affiche "Téléchargement..." et désactive le bouton pendant l\'appel', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadTickerPdf).mockImplementation(
      () => new Promise(() => {}),
    )
    wrap(<HistoryPage />)

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))
    await waitFor(() => expect(screen.getByText('Télécharger PDF')).toBeInTheDocument())

    await user.click(screen.getByText('Télécharger PDF'))

    await waitFor(() => {
      const btn = screen.getByText('Téléchargement...')
      expect(btn).toBeInTheDocument()
      expect(btn).toBeDisabled()
    })
  })

  it('affiche le message 404 si downloadTickerPdf rejette avec ApiError 404', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadTickerPdf).mockRejectedValue(
      new ApiError(404, 'Not Found'),
    )
    wrap(<HistoryPage />)

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByTestId('history-search-btn'))
    await waitFor(() => expect(screen.getByText('Télécharger PDF')).toBeInTheDocument())

    await user.click(screen.getByText('Télécharger PDF'))

    await waitFor(() => {
      expect(
        screen.getByText("Aucun rapport disponible pour BNS (pas d'historique)."),
      ).toBeInTheDocument()
    })
  })
})

describe('PdfDownload — WatchlistPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(watchlistApi.getWatchlist).mockResolvedValue([makeEntry()])
    vi.mocked(watchlistApi.addToWatchlist).mockResolvedValue(makeEntry())
    vi.mocked(watchlistApi.removeFromWatchlist).mockResolvedValue(undefined)
    vi.mocked(watchlistApi.triggerWatchlistAnalysis).mockResolvedValue({ job_id: 'job-1' })
  })

  it('bouton PDF présent pour chaque ticker avec data-testid correct', async () => {
    wrap(<WatchlistPage />)

    await waitFor(() => {
      expect(screen.getByTestId('pdf-btn-BNS')).toBeInTheDocument()
    })
  })

  it('clic PDF dans la watchlist appelle downloadTickerPdf avec le bon ticker', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadTickerPdf).mockResolvedValue(
      new Blob(['pdf'], { type: 'application/pdf' }),
    )
    wrap(<WatchlistPage />)

    const btn = await screen.findByTestId('pdf-btn-BNS')
    await user.click(btn)

    await waitFor(() => {
      expect(analyzeApi.downloadTickerPdf).toHaveBeenCalledWith('BNS')
    })
  })
})
