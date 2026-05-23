import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WatchlistTable } from '../components/WatchlistTable'
import type { WatchlistEntry } from '../types'

vi.mock('../components/CompositeSparkline', () => ({
  CompositeSparkline: () => null,
}))

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

describe('WatchlistTable', () => {
  it('affiche le ticker dans le tableau', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    expect(screen.getByText('BNS')).toBeInTheDocument()
  })

  it('affiche la colonne Score composite', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    expect(screen.getByText('Score composite')).toBeInTheDocument()
  })

  it('affiche le composite_score si present', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_composite_score: 72.5 })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    expect(screen.getByText('72.5')).toBeInTheDocument()
  })

  it('affiche "—" si last_composite_score est null', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_composite_score: null })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const cell = screen.getByTestId('composite-score-cell')
    expect(cell.textContent?.trim()).toBe('—')
  })
})
