import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScreenerTable } from '../components/ScreenerTable'
import type { ScreenEntry } from '../types'

const ENTRIES: ScreenEntry[] = [
  { ticker: 'BNS', defensive_score: 6, verdict: 'CANDIDAT_SOLIDE', composite_score: 72.5, composite_label: 'FORT', workflow_utilise: 'value_graham', cost_usd: 0.002, depuis_cache: false, analyzed_at: '2026-05-26T10:00:00+00:00', erreur: null },
  { ticker: 'TD', defensive_score: 7, verdict: 'EXEMPLAIRE', composite_score: 55.0, composite_label: 'MODÉRÉ', workflow_utilise: 'value_graham', cost_usd: 0.003, depuis_cache: true, analyzed_at: '2026-05-26T09:00:00+00:00', erreur: null },
  { ticker: 'BAC', defensive_score: 2, verdict: 'REJETER', composite_score: null, composite_label: null, workflow_utilise: 'value_graham', cost_usd: 0.001, depuis_cache: false, analyzed_at: null, erreur: null },
]

describe('ScreenerTable', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('rend le tableau avec tous les tickers', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('BNS')).toBeInTheDocument()
    expect(screen.getByText('TD')).toBeInTheDocument()
    expect(screen.getByText('BAC')).toBeInTheDocument()
  })

  it('trie par score décroissant par défaut', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    const rows = screen.getAllByRole('row').slice(1) as HTMLTableRowElement[]
    const tickers = rows.map((r) => r.cells[1].textContent)
    expect(tickers[0]).toBe('TD')    // score 7
    expect(tickers[1]).toBe('BNS')   // score 6
    expect(tickers[2]).toBe('BAC')   // score 2
  })

  it('affiche le verdict EXEMPLAIRE', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('EXEMPLAIRE')).toBeInTheDocument()
  })

  it('affiche un badge rouge pour REJETER', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('REJETER')).toBeInTheDocument()
  })

  it('affiche le badge cache pour les entrées en cache', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('cache')).toBeInTheDocument()
  })

  it('trie par ticker en cliquant sur l\'en-tête', async () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    await userEvent.click(screen.getByText(/Ticker/))
    const rows = screen.getAllByRole('row').slice(1) as HTMLTableRowElement[]
    const tickers = rows.map((r) => r.cells[1].textContent)
    expect(tickers).toEqual(['BAC', 'BNS', 'TD'])
  })

  it('affiche la colonne Composite avec score et label si non null', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('Composite')).toBeInTheDocument()
    expect(screen.getByText(/72\.5/)).toBeInTheDocument()
    const compositeCells = screen.getAllByTestId('composite-cell')
    expect(compositeCells.some((c) => /FORT/.test(c.textContent ?? ''))).toBe(true)
  })

  it('affiche "—" si composite_score est null', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    const cells = screen.getAllByTestId('composite-cell')
    const nullCell = cells.find((c) => c.textContent?.trim() === '—')
    expect(nullCell).toBeInTheDocument()
  })

  it('affiche une colonne Fraîcheur', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByText('Fraîcheur')).toBeInTheDocument()
    expect(screen.getAllByTestId('freshness-cell').length).toBe(3)
  })

  it('affiche des chips de filtre par label composite', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByTestId('label-filter-FORT')).toBeInTheDocument()
    expect(screen.getByTestId('label-filter-MODÉRÉ')).toBeInTheDocument()
  })

  it('filtre les lignes au clic sur un label composite', async () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    await userEvent.click(screen.getByTestId('label-filter-FORT'))
    expect(screen.getByText('BNS')).toBeInTheDocument()
    expect(screen.queryByText('TD')).not.toBeInTheDocument()
    expect(screen.queryByText('BAC')).not.toBeInTheDocument()
  })

  it('réinitialise le filtre via le bouton dédié', async () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    await userEvent.click(screen.getByTestId('label-filter-FORT'))
    expect(screen.queryByText('TD')).not.toBeInTheDocument()
    await userEvent.click(screen.getByTestId('label-filter-clear'))
    expect(screen.getByText('TD')).toBeInTheDocument()
  })

  it('persiste le tri sélectionné dans localStorage', async () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    await userEvent.click(screen.getByText(/Ticker/))
    const raw = localStorage.getItem('copilote_screener_sort')
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw as string)).toEqual({ key: 'ticker', asc: true })
  })

  it('restaure le tri persisté au montage', () => {
    localStorage.setItem('copilote_screener_sort', JSON.stringify({ key: 'ticker', asc: true }))
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    const rows = screen.getAllByRole('row').slice(1) as HTMLTableRowElement[]
    const tickers = rows.map((r) => r.cells[1].textContent)
    expect(tickers).toEqual(['BAC', 'BNS', 'TD'])
  })

  it('expose un bouton d\'export des résultats filtrés', () => {
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    expect(screen.getByTestId('export-filtered-csv')).toBeInTheDocument()
  })
})
