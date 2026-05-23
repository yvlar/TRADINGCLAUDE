import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
  }
})

const BASE_RESPONSE: AnalyzeResponse = {
  analysis_id: 'uuid-cache-test',
  ticker: 'BNS',
  workflow: 'value_graham',
  skills_applied: ['graham_analysis'],
  graham: null,
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
  created_at: '2026-05-16T00:00:00+00:00',
  inter_skill_conflicts: [],
  composite_score: null,
  depuis_cache_composite: false,
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('CacheIndicator — badge "Score depuis cache"', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('badge absent au chargement initial (avant toute analyse)', () => {
    render(<AnalyzePage />, { wrapper })
    expect(screen.queryByTestId('cache-badge')).not.toBeInTheDocument()
  })

  it('badge visible quand depuis_cache_composite=true dans la réponse SSE', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield {
        type: 'complete' as const,
        data: { ...BASE_RESPONSE, depuis_cache_composite: true },
      }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('cache-badge')).toBeInTheDocument()
    })
    expect(screen.getByTestId('cache-badge')).toHaveTextContent('Score depuis cache')
  })

  it('badge absent quand depuis_cache_composite=false dans la réponse SSE', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield {
        type: 'complete' as const,
        data: { ...BASE_RESPONSE, depuis_cache_composite: false },
      }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      // On attend que le résultat soit traité (streaming terminé)
      expect(analyzeApi.streamAnalyze).toHaveBeenCalled()
    })
    // Le badge ne doit pas apparaître
    expect(screen.queryByTestId('cache-badge')).not.toBeInTheDocument()
  })

  it('badge disparaît quand une nouvelle analyse est lancée', async () => {
    const user = userEvent.setup()

    // Première analyse : depuis_cache_composite=true
    vi.mocked(analyzeApi.streamAnalyze).mockImplementationOnce(async function* () {
      yield {
        type: 'complete' as const,
        data: { ...BASE_RESPONSE, depuis_cache_composite: true },
      }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('cache-badge')).toBeInTheDocument()
    })

    // Deuxième analyse : le badge doit disparaître dès le lancement
    vi.mocked(analyzeApi.streamAnalyze).mockImplementationOnce(async function* (): AsyncGenerator<never> {
      // Ne yield rien — l'analyse ne se termine pas
      await new Promise(() => {})
    })

    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.queryByTestId('cache-badge')).not.toBeInTheDocument()
    })
  })

  it('badge visible aussi quand le type SSE est "cached"', async () => {
    const user = userEvent.setup()

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield {
        type: 'cached' as const,
        data: { ...BASE_RESPONSE, depuis_cache_composite: true },
      }
    })

    render(<AnalyzePage />, { wrapper })

    await user.type(screen.getByLabelText('Ticker'), 'BNS')
    await user.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(screen.getByTestId('cache-badge')).toBeInTheDocument()
    })
  })
})
