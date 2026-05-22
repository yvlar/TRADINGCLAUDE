import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WatchlistPage from '../pages/WatchlistPage'
import * as analyzeApi from '../api/analyze'
import * as watchlistApi from '../api/watchlist'
import { ApiError } from '../api/client'
import type { WatchlistEntry } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    downloadTickerPdf: vi.fn(),
    downloadWatchlistPdf: vi.fn(),
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

describe('WatchlistPdfExport — bouton Exporter PDF global', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(watchlistApi.getWatchlist).mockResolvedValue([makeEntry()])
    vi.mocked(watchlistApi.addToWatchlist).mockResolvedValue(makeEntry())
    vi.mocked(watchlistApi.removeFromWatchlist).mockResolvedValue(undefined)
    vi.mocked(watchlistApi.triggerWatchlistAnalysis).mockResolvedValue({ job_id: 'job-1' })
  })

  it('bouton "Exporter PDF" présent avec data-testid correct', async () => {
    wrap(<WatchlistPage />)
    await waitFor(() => {
      expect(screen.getByTestId('export-pdf-watchlist')).toBeInTheDocument()
    })
  })

  it('clic "Exporter PDF" appelle downloadWatchlistPdf', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadWatchlistPdf).mockResolvedValue(
      new Blob(['pdf'], { type: 'application/pdf' }),
    )
    wrap(<WatchlistPage />)

    const btn = await screen.findByTestId('export-pdf-watchlist')
    await user.click(btn)

    await waitFor(() => {
      expect(analyzeApi.downloadWatchlistPdf).toHaveBeenCalledOnce()
    })
  })

  it('bouton désactivé pendant le téléchargement (état loading)', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadWatchlistPdf).mockImplementation(
      () => new Promise(() => {}),
    )
    wrap(<WatchlistPage />)

    const btn = await screen.findByTestId('export-pdf-watchlist')
    await user.click(btn)

    await waitFor(() => {
      expect(screen.getByTestId('export-pdf-watchlist')).toBeDisabled()
    })
  })

  it('affiche message "Watchlist vide" sur erreur 404', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadWatchlistPdf).mockRejectedValue(
      new ApiError(404, 'Watchlist vide'),
    )
    wrap(<WatchlistPage />)

    const btn = await screen.findByTestId('export-pdf-watchlist')
    await user.click(btn)

    await waitFor(() => {
      expect(
        screen.getByText('Watchlist vide — aucun rapport à générer.'),
      ).toBeInTheDocument()
    })
  })

  it('affiche message d\'erreur générique sur erreur non-404', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.downloadWatchlistPdf).mockRejectedValue(
      new ApiError(500, 'Erreur serveur'),
    )
    wrap(<WatchlistPage />)

    const btn = await screen.findByTestId('export-pdf-watchlist')
    await user.click(btn)

    await waitFor(() => {
      expect(
        screen.getByText('Erreur lors du téléchargement du rapport PDF global.'),
      ).toBeInTheDocument()
    })
  })
})
