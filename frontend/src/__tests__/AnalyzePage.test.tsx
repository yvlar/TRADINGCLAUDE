import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AnalyzePage from '../pages/AnalyzePage'
import * as analyzeApi from '../api/analyze'
import type { AnalyzeResponse } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    streamAnalyze: vi.fn(),
    getExtract: vi.fn().mockRejectedValue(new Error('not mocked')),
    postReport: vi.fn().mockResolvedValue(new Blob()),
    downloadTickerPdf: vi.fn().mockResolvedValue(new Blob()),
  }
})

const _MOCK_RESPONSE: AnalyzeResponse = {
  analysis_id: 'uuid-test-1',
  ticker: 'BNS',
  workflow: 'value_graham',
  skills_applied: ['graham_analysis'],
  graham: {
    ticker: 'BNS',
    profil_applique: 'DEFENSIF',
    defensive_score: 5,
    enterprising_score: 3,
    criteria_defensif: [],
    criteria_entreprenant: [],
    valeur_intrinseque_simple: 95.0,
    valeur_intrinseque_ajustee: 87.5,
    marge_securite: 0.09,
    drapeaux_rouges: [],
    verdict: 'CANDIDAT_SOLIDE',
    verdict_detail: 'BNS passe 5/8 critères.',
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.001,
  },
  earnings_quality: null,
  dorsey: null,
  buffett: null,
  valuation: null,
  thesis: null,
  munger: null,
  canadian_tax: null,
  lynch: null,
  fisher: null,
  klarman: null,
  greenblatt: null,
  damodaran: null,
  marks: null,
  pabrai: null,
  esg: null,
  cost_usd: 0.001,
  created_at: '2026-05-10T00:00:00+00:00',
  inter_skill_conflicts: [],
  composite_score: null,
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </MemoryRouter>
  )
}

describe('AnalyzePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
    window.URL.revokeObjectURL = vi.fn()
  })

  it('affiche le formulaire et le titre', () => {
    render(<AnalyzePage />, { wrapper })
    expect(screen.getByText('Analyse individuelle')).toBeInTheDocument()
    expect(screen.getByLabelText('Ticker')).toBeInTheDocument()
    expect(screen.getByText('Analyser')).toBeInTheDocument()
  })

  it('affiche StreamingProgress pendant le streaming', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'skill_start' as const, data: { skill_id: 'graham_analysis' } }
      // Pause suffisamment longue pour que waitFor (polling 50ms) détecte streaming-progress
      await new Promise((r) => setTimeout(r, 200))
      yield {
        type: 'skill_result' as const,
        data: { skill_id: 'graham_analysis', result: { verdict: 'CANDIDAT_SOLIDE' } },
      }
      yield { type: 'complete' as const, data: _MOCK_RESPONSE }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('streaming-progress')).toBeInTheDocument()
    })
  })

  it("affiche le résultat final après l'event complete", async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'skill_start' as const, data: { skill_id: 'graham_analysis' } }
      yield {
        type: 'skill_result' as const,
        data: { skill_id: 'graham_analysis', result: { verdict: 'CANDIDAT_SOLIDE' } },
      }
      yield { type: 'complete' as const, data: _MOCK_RESPONSE }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('result-ticker')).toBeInTheDocument()
    })
    expect(screen.getByTestId('result-ticker')).toHaveTextContent('BNS')
  })

  it("affiche un message d'erreur quand streamAnalyze rejette", async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* (): AsyncGenerator<never> {
      throw new Error('Connexion refusée')
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'ERR')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument()
    })
    expect(screen.getByTestId('error-message')).toHaveTextContent('Connexion refusée')
  })

  it('« Exporter cette analyse » appelle downloadTickerPdf avec analysis_id', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'complete' as const, data: _MOCK_RESPONSE }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('export-analysis-pdf')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('export-analysis-pdf'))

    await waitFor(() => {
      expect(analyzeApi.downloadTickerPdf).toHaveBeenCalledWith('BNS', 90, 'uuid-test-1')
    })
  })

  it('masque « Exporter cette analyse » pour un score depuis cache', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield {
        type: 'cached' as const,
        data: { ..._MOCK_RESPONSE, analysis_id: 'cached_composite' },
      }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('result-ticker')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('export-analysis-pdf')).not.toBeInTheDocument()
  })

  it('appelle streamAnalyze avec le ticker saisi', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'complete' as const, data: _MOCK_RESPONSE }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(analyzeApi.streamAnalyze).toHaveBeenCalledWith(
        expect.objectContaining({ ticker: 'BNS' }),
      )
    })
  })
})
