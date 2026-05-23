import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WatchlistTable } from '../components/WatchlistTable'
import type { WatchlistEntry } from '../types'

vi.mock('../components/CompositeSparkline', () => ({
  CompositeSparkline: () => null,
}))

const makeEntry = (overrides: Partial<WatchlistEntry> = {}): WatchlistEntry => ({
  id: 'esg-test-1',
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

describe('WatchlistTable — badge ESG', () => {
  it('affiche badge N/A (gris) si last_esg_score est null', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_esg_score: null })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const badge = screen.getByTestId('esg-badge-BNS')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('N/A')
  })

  it('affiche badge FORT (vert) si last_esg_score >= 10', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_esg_score: 11, ticker: 'TD' })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const badge = screen.getByTestId('esg-badge-TD')
    expect(badge).toHaveTextContent('FORT')
  })

  it('affiche badge MODERE (orange) si 5 <= last_esg_score < 10', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_esg_score: 7, ticker: 'RY' })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const badge = screen.getByTestId('esg-badge-RY')
    expect(badge).toHaveTextContent('MODERE')
  })

  it('affiche badge FAIBLE (rouge) si last_esg_score < 5', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_esg_score: 3, ticker: 'CM' })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const badge = screen.getByTestId('esg-badge-CM')
    expect(badge).toHaveTextContent('FAIBLE')
  })

  it('affiche badge FORT pour score exactement 10', () => {
    render(
      <WatchlistTable
        entries={[makeEntry({ last_esg_score: 10, ticker: 'NA' })]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    const badge = screen.getByTestId('esg-badge-NA')
    expect(badge).toHaveTextContent('FORT')
  })

  it('affiche colonne ESG dans les entêtes', () => {
    render(
      <WatchlistTable
        entries={[makeEntry()]}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />,
    )
    expect(screen.getByText('ESG')).toBeInTheDocument()
  })
})
