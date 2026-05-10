import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScreenerTable } from '../components/ScreenerTable'
import type { ScreenEntry } from '../types'

const ENTRIES: ScreenEntry[] = [
  { ticker: 'BNS', defensive_score: 6, verdict: 'CANDIDAT_SOLIDE', workflow_utilise: 'value_graham', cost_usd: 0.002, depuis_cache: false, erreur: null },
  { ticker: 'TD', defensive_score: 7, verdict: 'EXEMPLAIRE', workflow_utilise: 'value_graham', cost_usd: 0.003, depuis_cache: true, erreur: null },
  { ticker: 'BAC', defensive_score: 2, verdict: 'REJETER', workflow_utilise: 'value_graham', cost_usd: 0.001, depuis_cache: false, erreur: null },
]

describe('ScreenerTable', () => {
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
})
