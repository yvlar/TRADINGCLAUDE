import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EsgPage from '../pages/EsgPage'
import * as watchlistApi from '../api/watchlist'
import type { WatchlistEsgResponse } from '../types'

vi.mock('../api/watchlist', () => ({
  fetchWatchlistEsgScores: vi.fn(),
  getWatchlist: vi.fn(),
  addToWatchlist: vi.fn(),
  removeFromWatchlist: vi.fn(),
  triggerWatchlistAnalysis: vi.fn(),
  getWatchlistPriceStatus: vi.fn(),
}))

const makeResponse = (entries: WatchlistEsgResponse['entries']): WatchlistEsgResponse => ({
  entries,
})

function renderEsgPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <EsgPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EsgPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche badge ESG_FORT pour score >= 10', async () => {
    vi.mocked(watchlistApi.fetchWatchlistEsgScores).mockResolvedValue(
      makeResponse([{ ticker: 'RY', last_esg_score: 12, esg_alert_threshold: 5.0, last_analyzed_at: null }]),
    )

    renderEsgPage()
    const badge = await screen.findByTestId('esg-verdict-badge-RY')
    expect(badge).toHaveTextContent('ESG_FORT')
  })

  it('affiche badge ESG_MODERE pour score >= 5 et < 10', async () => {
    vi.mocked(watchlistApi.fetchWatchlistEsgScores).mockResolvedValue(
      makeResponse([{ ticker: 'BNS', last_esg_score: 7, esg_alert_threshold: 5.0, last_analyzed_at: null }]),
    )

    renderEsgPage()
    const badge = await screen.findByTestId('esg-verdict-badge-BNS')
    expect(badge).toHaveTextContent('ESG_MODERE')
  })

  it('affiche badge ESG_FAIBLE pour score < 5', async () => {
    vi.mocked(watchlistApi.fetchWatchlistEsgScores).mockResolvedValue(
      makeResponse([{ ticker: 'TD', last_esg_score: 3, esg_alert_threshold: 5.0, last_analyzed_at: null }]),
    )

    renderEsgPage()
    const badge = await screen.findByTestId('esg-verdict-badge-TD')
    expect(badge).toHaveTextContent('ESG_FAIBLE')
  })

  it('affiche "--" pour score null dans la cellule Score ESG', async () => {
    vi.mocked(watchlistApi.fetchWatchlistEsgScores).mockResolvedValue(
      makeResponse([{ ticker: 'CM', last_esg_score: null, esg_alert_threshold: 5.0, last_analyzed_at: null }]),
    )

    renderEsgPage()
    const cell = await screen.findByTestId('esg-score-cell-CM')
    expect(cell).toHaveTextContent('--')
  })

  it('permute le sens de tri au second clic sur la colonne Score ESG', async () => {
    vi.mocked(watchlistApi.fetchWatchlistEsgScores).mockResolvedValue(
      makeResponse([
        { ticker: 'RY', last_esg_score: 11, esg_alert_threshold: 5.0, last_analyzed_at: null },
        { ticker: 'BNS', last_esg_score: 4, esg_alert_threshold: 5.0, last_analyzed_at: null },
      ]),
    )

    renderEsgPage()
    // Attendre que la page se charge
    await screen.findByTestId('sort-esg-score')

    const sortBtn = screen.getByTestId('sort-esg-score')
    // Premier clic : desc → asc
    fireEvent.click(sortBtn)
    const rowsAsc = screen.getAllByTestId(/^esg-row-/)
    expect(rowsAsc[0]).toHaveAttribute('data-testid', 'esg-row-BNS')

    // Deuxième clic : asc → desc
    fireEvent.click(sortBtn)
    const rowsDesc = screen.getAllByTestId(/^esg-row-/)
    expect(rowsDesc[0]).toHaveAttribute('data-testid', 'esg-row-RY')
  })
})
