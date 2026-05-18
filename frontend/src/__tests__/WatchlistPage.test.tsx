import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WatchlistPage from '../pages/WatchlistPage'
import * as watchlistApi from '../api/watchlist'
import type { WatchlistEntry } from '../types'

vi.mock('../api/watchlist')

const makeEntry = (overrides: Partial<WatchlistEntry> = {}): WatchlistEntry => ({
  id: 'abc-123',
  ticker: 'BNS',
  workflow: 'value_graham',
  last_analyzed_at: null,
  last_score: null,
  last_intrinsic_value: null,
  last_price_checked: null,
  price_alert_threshold_pct: 0.10,
  created_at: '2026-01-01T00:00:00Z',
  last_composite_score: null,
  composite_alert_threshold: 15.0,
  score_alerte_min: null,
  ...overrides,
})

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('WatchlistPage', () => {
  beforeEach(() => {
    vi.mocked(watchlistApi.getWatchlist).mockResolvedValue([makeEntry()])
    vi.mocked(watchlistApi.addToWatchlist).mockResolvedValue(makeEntry({ ticker: 'TD' }))
    vi.mocked(watchlistApi.removeFromWatchlist).mockResolvedValue(undefined)
    vi.mocked(watchlistApi.triggerWatchlistAnalysis).mockResolvedValue({ job_id: 'job-abc' })
  })

  it('affiche les tickers dans le tableau', async () => {
    wrap(<WatchlistPage />)
    await waitFor(() => expect(screen.getByText('BNS')).toBeInTheDocument())
  })

  it('ajouter un ticker appelle addToWatchlist avec le ticker', async () => {
    wrap(<WatchlistPage />)
    const input = await screen.findByLabelText('Ticker')
    await userEvent.clear(input)
    await userEvent.type(input, 'td')
    await userEvent.click(screen.getByText('Ajouter'))
    await waitFor(() => {
      expect(watchlistApi.addToWatchlist).toHaveBeenCalledWith(
        expect.objectContaining({ ticker: 'TD' }),
      )
    })
  })

  it('clic Supprimer appelle removeFromWatchlist avec l\'id', async () => {
    wrap(<WatchlistPage />)
    const btn = await screen.findByText('Supprimer')
    await userEvent.click(btn)
    await waitFor(() => {
      expect(watchlistApi.removeFromWatchlist).toHaveBeenCalledWith('abc-123')
    })
  })

  it('clic Analyser appelle triggerWatchlistAnalysis avec l\'id', async () => {
    wrap(<WatchlistPage />)
    const btn = await screen.findByText('Analyser')
    await userEvent.click(btn)
    await waitFor(() => {
      expect(watchlistApi.triggerWatchlistAnalysis).toHaveBeenCalledWith('abc-123')
    })
  })

  it('affiche le message vide quand la watchlist est vide', async () => {
    vi.mocked(watchlistApi.getWatchlist).mockResolvedValue([])
    wrap(<WatchlistPage />)
    await waitFor(() => {
      expect(screen.getByText('Aucun ticker en surveillance.')).toBeInTheDocument()
    })
  })

  it('affiche le badge Alerte quand le prix dépasse le seuil', async () => {
    vi.mocked(watchlistApi.getWatchlist).mockResolvedValue([
      makeEntry({
        last_intrinsic_value: 80,
        last_price_checked: 60, // écart 25% > seuil 10% → alerte
      }),
    ])
    wrap(<WatchlistPage />)
    await waitFor(() => {
      // Badge est un <div> — on cible le badge, pas le <th> "Alerte"
      expect(screen.getByText('Alerte', { selector: 'div' })).toBeInTheDocument()
    })
  })
})
