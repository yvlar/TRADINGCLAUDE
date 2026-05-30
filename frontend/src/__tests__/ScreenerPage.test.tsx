import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ScreenerPage from '../pages/ScreenerPage'
import * as analyzeApi from '../api/analyze'
import type { ScreenResult } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return { ...actual, postScreen: vi.fn(), exportScreen: vi.fn(), downloadScreenerPdf: vi.fn() }
})

const MOCK_RESULT: ScreenResult = {
  tickers_analyses: 2,
  tickers_echec: 0,
  tickers_depuis_cache: 0,
  cout_total_usd: 0.005,
  duration_ms: 1200,
  workflow: 'value_graham',
  resultats: [
    {
      ticker: 'BNS',
      defensive_score: 6,
      verdict: 'CANDIDAT_SOLIDE',
      composite_score: 72.5,
      composite_label: 'FORT',
      workflow_utilise: 'value_graham',
      cost_usd: 0.002,
      depuis_cache: false,
      analyzed_at: '2026-05-26T10:00:00+00:00',
      erreur: null,
    },
    {
      ticker: 'TD',
      defensive_score: 7,
      verdict: 'EXEMPLAIRE',
      composite_score: 55.0,
      composite_label: 'MODÉRÉ',
      workflow_utilise: 'value_graham',
      cost_usd: 0.003,
      depuis_cache: false,
      analyzed_at: '2026-05-26T09:00:00+00:00',
      erreur: null,
    },
  ],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('ScreenerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le formulaire de screener', () => {
    render(<ScreenerPage />, { wrapper })
    expect(screen.getByText('Lancer le screener')).toBeInTheDocument()
    expect(screen.getByLabelText('Tickers')).toBeInTheDocument()
  })

  it('affiche les boutons export CSV et Excel après un résultat', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)

    render(<ScreenerPage />, { wrapper })

    await user.click(screen.getByText('Lancer le screener'))

    await waitFor(() => {
      expect(screen.getByTestId('export-csv')).toBeInTheDocument()
      expect(screen.getByTestId('export-xlsx')).toBeInTheDocument()
    })
  })

  it('bouton CSV appelle exportScreen avec format=csv', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)
    vi.mocked(analyzeApi.exportScreen).mockResolvedValue(new Blob(['csv'], { type: 'text/csv' }))

    render(<ScreenerPage />, { wrapper })

    await user.click(screen.getByText('Lancer le screener'))
    await waitFor(() => expect(screen.getByTestId('export-csv')).toBeInTheDocument())

    await user.click(screen.getByTestId('export-csv'))
    await waitFor(() => {
      expect(analyzeApi.exportScreen).toHaveBeenCalledWith(
        expect.objectContaining({ workflow: 'value_graham' }),
        'csv',
      )
    })
  })

  it('bouton Excel appelle exportScreen avec format=xlsx', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)
    vi.mocked(analyzeApi.exportScreen).mockResolvedValue(new Blob(['xlsx'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))

    render(<ScreenerPage />, { wrapper })

    await user.click(screen.getByText('Lancer le screener'))
    await waitFor(() => expect(screen.getByTestId('export-xlsx')).toBeInTheDocument())

    await user.click(screen.getByTestId('export-xlsx'))
    await waitFor(() => {
      expect(analyzeApi.exportScreen).toHaveBeenCalledWith(
        expect.objectContaining({ workflow: 'value_graham' }),
        'xlsx',
      )
    })
  })

  it("les boutons export ne s'affichent pas avant un résultat", () => {
    render(<ScreenerPage />, { wrapper })
    expect(screen.queryByTestId('export-csv')).not.toBeInTheDocument()
    expect(screen.queryByTestId('export-xlsx')).not.toBeInTheDocument()
  })

  it('affiche le disclaimer de conformité une fois les résultats présents', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))

    await waitFor(() => {
      expect(screen.getByTestId('disclaimer')).toBeInTheDocument()
    })
  })

  it("n'affiche pas le disclaimer sur la page vide (avant tout screener)", () => {
    render(<ScreenerPage />, { wrapper })
    expect(screen.queryByTestId('disclaimer')).not.toBeInTheDocument()
  })
})
