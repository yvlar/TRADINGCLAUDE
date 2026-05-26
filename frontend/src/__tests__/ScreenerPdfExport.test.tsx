import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ScreenerPage from '../pages/ScreenerPage'
import * as analyzeApi from '../api/analyze'
import type { ScreenResult } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    postScreen: vi.fn(),
    exportScreen: vi.fn(),
    downloadScreenerPdf: vi.fn(),
  }
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
      composite_score: 75.0,
      composite_label: 'FORT',
      workflow_utilise: 'value_graham',
      cost_usd: 0.002,
      depuis_cache: false,
      analyzed_at: '2026-05-26T10:00:00+00:00',
      erreur: null,
    },
  ],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('ScreenerPage — Exporter PDF', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Simuler URL.createObjectURL et revokeObjectURL (non dispo dans jsdom)
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
  })

  it("le bouton Exporter PDF n'apparaît pas avant un résultat", () => {
    render(<ScreenerPage />, { wrapper })
    expect(screen.queryByTestId('export-pdf')).not.toBeInTheDocument()
  })

  it('le bouton Exporter PDF apparaît après un résultat', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))

    await waitFor(() => {
      expect(screen.getByTestId('export-pdf')).toBeInTheDocument()
    })
  })

  it('le bouton Exporter PDF appelle downloadScreenerPdf', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)
    vi.mocked(analyzeApi.downloadScreenerPdf).mockResolvedValue(
      new Blob(['%PDF-1.4'], { type: 'application/pdf' }),
    )

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))
    await waitFor(() => expect(screen.getByTestId('export-pdf')).toBeInTheDocument())

    await user.click(screen.getByTestId('export-pdf'))

    await waitFor(() => {
      expect(analyzeApi.downloadScreenerPdf).toHaveBeenCalledWith(
        expect.objectContaining({ workflow: 'value_graham' }),
      )
    })
  })

  it('le bouton Exporter PDF est désactivé pendant le chargement', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)

    let resolveBlob: (b: Blob) => void
    vi.mocked(analyzeApi.downloadScreenerPdf).mockImplementation(
      () => new Promise<Blob>((res) => { resolveBlob = res }),
    )

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))
    await waitFor(() => expect(screen.getByTestId('export-pdf')).toBeInTheDocument())

    await user.click(screen.getByTestId('export-pdf'))

    await waitFor(() => {
      expect(screen.getByTestId('export-pdf')).toBeDisabled()
    })

    await act(async () => {
      resolveBlob!(new Blob(['%PDF'], { type: 'application/pdf' }))
    })
  })

  it("affiche une alerte en cas d'erreur de téléchargement PDF", async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)
    vi.mocked(analyzeApi.downloadScreenerPdf).mockRejectedValue(new Error('Serveur indisponible'))

    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))
    await waitFor(() => expect(screen.getByTestId('export-pdf')).toBeInTheDocument())

    await user.click(screen.getByTestId('export-pdf'))

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Serveur indisponible'))
    })

    alertSpy.mockRestore()
  })

  it('le bouton Exporter PDF affiche le texte correct par défaut', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postScreen).mockResolvedValue(MOCK_RESULT)

    render(<ScreenerPage />, { wrapper })
    await user.click(screen.getByText('Lancer le screener'))

    await waitFor(() => {
      expect(screen.getByTestId('export-pdf')).toHaveTextContent('Exporter PDF')
    })
  })
})
