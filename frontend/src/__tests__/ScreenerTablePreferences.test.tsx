import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScreenerTable } from '../components/ScreenerTable'
import type { ScreenEntry } from '../types'
import { getScreenerPreferences, putScreenerPreferences } from '../api/preferences'

vi.mock('../api/preferences', () => ({
  getScreenerPreferences: vi.fn(),
  putScreenerPreferences: vi.fn().mockResolvedValue(null),
}))

const mockGet = vi.mocked(getScreenerPreferences)
const mockPut = vi.mocked(putScreenerPreferences)

const ENTRIES: ScreenEntry[] = [
  { ticker: 'BNS', defensive_score: 6, verdict: 'CANDIDAT_SOLIDE', composite_score: 72.5, composite_label: 'FORT', workflow_utilise: 'value_graham', cost_usd: 0.002, depuis_cache: false, analyzed_at: '2026-05-26T10:00:00+00:00', erreur: null },
  { ticker: 'TD', defensive_score: 7, verdict: 'EXEMPLAIRE', composite_score: 55.0, composite_label: 'MODÉRÉ', workflow_utilise: 'value_graham', cost_usd: 0.003, depuis_cache: true, analyzed_at: '2026-05-26T09:00:00+00:00', erreur: null },
  { ticker: 'BAC', defensive_score: 2, verdict: 'REJETER', composite_score: null, composite_label: null, workflow_utilise: 'value_graham', cost_usd: 0.001, depuis_cache: false, analyzed_at: null, erreur: null },
]

function tickerOrder(): (string | null)[] {
  const rows = screen.getAllByRole('row').slice(1) as HTMLTableRowElement[]
  return rows.map((r) => r.cells[1].textContent)
}

describe('ScreenerTable — persistance serveur', () => {
  beforeEach(() => {
    localStorage.clear()
    mockGet.mockReset()
    mockPut.mockReset().mockResolvedValue(null)
  })

  it('hydrate le tri depuis le serveur au montage (happy path)', async () => {
    mockGet.mockResolvedValue({ sort: { key: 'ticker', asc: true }, filter: null })
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)

    // Au montage : tri par défaut (score décroissant) avant résolution serveur
    expect(tickerOrder()[0]).toBe('TD')
    // Après hydratation serveur : tri par ticker ascendant
    await waitFor(() => expect(tickerOrder()).toEqual(['BAC', 'BNS', 'TD']))
  })

  it('applique le filtre de label provenant du serveur', async () => {
    mockGet.mockResolvedValue({ sort: null, filter: ['FORT'] })
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)

    await waitFor(() => {
      expect(screen.getByText('BNS')).toBeInTheDocument()
      expect(screen.queryByText('TD')).not.toBeInTheDocument()
      expect(screen.queryByText('BAC')).not.toBeInTheDocument()
    })
  })

  it('bascule sur localStorage si le serveur échoue (retourne null)', async () => {
    localStorage.setItem('copilote_screener_sort', JSON.stringify({ key: 'ticker', asc: true }))
    mockGet.mockResolvedValue(null)
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)

    // Le tri localStorage (ticker asc) reste appliqué — aucune régression hors-ligne
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(tickerOrder()).toEqual(['BAC', 'BNS', 'TD'])
  })

  it('persiste l\'état complet côté serveur au changement de tri', async () => {
    mockGet.mockResolvedValue(null)
    render(<ScreenerTable entries={ENTRIES} workflow="value_graham" durationMs={1200} />)
    await waitFor(() => expect(mockGet).toHaveBeenCalled())

    await userEvent.click(screen.getByText(/Ticker/))

    expect(mockPut).toHaveBeenCalledWith({ sort: { key: 'ticker', asc: true }, filter: [] })
  })
})
