import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { WatchlistTable } from '../components/WatchlistTable'
import type { WatchlistEntry } from '../types'

vi.mock('../api/watchlist', () => ({
  patchEsgThreshold: vi.fn(),
}))

vi.mock('../components/CompositeSparkline', () => ({
  CompositeSparkline: () => null,
}))

import { patchEsgThreshold } from '../api/watchlist'

const makeEntry = (overrides: Partial<WatchlistEntry> = {}): WatchlistEntry => ({
  id: 'entry-test-1',
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

describe('WatchlistTable — seuil ESG édition inline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche la valeur actuelle du seuil ESG', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ esg_alert_threshold: 7.5 })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    expect(screen.getByTestId('esg-threshold-display')).toHaveTextContent('7.5')
  })

  it('click sur le bouton crayon ouvre l\'input d\'édition', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('esg-threshold-edit-btn'))
    expect(screen.getByTestId('esg-threshold-input')).toBeInTheDocument()
    expect(screen.getByTestId('esg-threshold-save-btn')).toBeInTheDocument()
    expect(screen.getByTestId('esg-threshold-cancel-btn')).toBeInTheDocument()
  })

  it('sauvegarde appelle patchEsgThreshold avec la bonne valeur', async () => {
    const mockPatch = vi.mocked(patchEsgThreshold)
    mockPatch.mockResolvedValue(makeEntry({ esg_alert_threshold: 8.5 }))
    const onRefresh = vi.fn()

    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
        onRefresh={onRefresh}
      />,
    )

    fireEvent.click(screen.getByTestId('esg-threshold-edit-btn'))
    fireEvent.change(screen.getByTestId('esg-threshold-input'), { target: { value: '8.5' } })
    fireEvent.click(screen.getByTestId('esg-threshold-save-btn'))

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('entry-test-1', 8.5)
    })
    expect(onRefresh).toHaveBeenCalled()
  })

  it('annuler ferme l\'input sans appel API', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByTestId('esg-threshold-edit-btn'))
    expect(screen.getByTestId('esg-threshold-input')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('esg-threshold-cancel-btn'))

    expect(screen.queryByTestId('esg-threshold-input')).not.toBeInTheDocument()
    expect(patchEsgThreshold).not.toHaveBeenCalled()
  })

  it('erreur API affiche un message d\'erreur', async () => {
    const mockPatch = vi.mocked(patchEsgThreshold)
    mockPatch.mockRejectedValue(new Error('Network error'))

    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByTestId('esg-threshold-edit-btn'))
    fireEvent.click(screen.getByTestId('esg-threshold-save-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('esg-threshold-error')).toBeInTheDocument()
    })
    expect(screen.getByTestId('esg-threshold-error')).toHaveTextContent('Erreur lors de la mise à jour')
  })
})
