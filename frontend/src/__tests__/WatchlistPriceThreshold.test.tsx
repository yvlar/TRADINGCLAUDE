import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { WatchlistTable } from '../components/WatchlistTable'
import type { WatchlistEntry } from '../types'

vi.mock('../api/watchlist', () => ({
  patchEsgThreshold: vi.fn(),
  patchPriceThreshold: vi.fn(),
}))

vi.mock('../components/CompositeSparkline', () => ({
  CompositeSparkline: () => null,
}))

import * as watchlistApi from '../api/watchlist'

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
  esg_alert_threshold: 5.0,
  last_esg_score: null,
  ...overrides,
})

describe('WatchlistTable — Seuil Prix', () => {
  it('affiche le seuil de prix en pourcentage', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ price_alert_threshold_pct: 0.10 })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const display = screen.getByTestId('watchlist-price-threshold-abc-123-display')
    expect(display.textContent).toBe('10.0')
  })

  it('ouvre le champ input en cliquant sur le bouton crayon', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-edit-btn'))
    expect(screen.getByTestId('watchlist-price-threshold-abc-123-input')).toBeInTheDocument()
  })

  it('appelle patchPriceThreshold avec la valeur saisie lors de la sauvegarde', async () => {
    const mockPatch = vi.mocked(watchlistApi.patchPriceThreshold)
    mockPatch.mockResolvedValueOnce(makeEntry({ price_alert_threshold_pct: 0.05 }))
    const onRefresh = vi.fn()

    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
        onRefresh={onRefresh}
      />,
    )
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-edit-btn'))
    fireEvent.change(screen.getByTestId('watchlist-price-threshold-abc-123-input'), {
      target: { value: '5' },
    })
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-save-btn'))

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('abc-123', 5)
      expect(onRefresh).toHaveBeenCalled()
    })
  })

  it('ferme le champ sans appel API en cliquant Annuler', () => {
    const mockPatch = vi.mocked(watchlistApi.patchPriceThreshold)
    mockPatch.mockClear()

    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-edit-btn'))
    expect(screen.getByTestId('watchlist-price-threshold-abc-123-input')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-cancel-btn'))

    expect(screen.queryByTestId('watchlist-price-threshold-abc-123-input')).not.toBeInTheDocument()
    expect(mockPatch).not.toHaveBeenCalled()
  })

  it('affiche un message d\'erreur si patchPriceThreshold rejette', async () => {
    const mockPatch = vi.mocked(watchlistApi.patchPriceThreshold)
    mockPatch.mockRejectedValueOnce(new Error('Network error'))

    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-edit-btn'))
    fireEvent.click(screen.getByTestId('watchlist-price-threshold-abc-123-save-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('watchlist-price-threshold-abc-123-error')).toBeInTheDocument()
    })
  })
})
