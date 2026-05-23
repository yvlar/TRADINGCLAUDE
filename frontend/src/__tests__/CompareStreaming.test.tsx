import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ComparePage from '../pages/ComparePage'
import * as compareApi from '../api/compare'
import * as analyzeApi from '../api/analyze'
import type { AnalyzeResponse, CompareResponse } from '../types'

vi.mock('../api/compare', () => ({ postCompare: vi.fn() }))
vi.mock('../api/analyze', () => ({
  postAnalyze: vi.fn(),
  streamAnalyze: vi.fn(),
}))

function makeResponse(tickers: string[], scores: (number | null)[]): CompareResponse {
  return {
    tickers,
    comparisons: tickers.map((ticker, i) => ({
      ticker,
      analysis_id: scores[i] !== null ? 'uuid-' + i : null,
      graham_verdict: null,
      graham_score: null,
      buffett_verdict: null,
      dorsey_moat_type: null,
      composite_score: scores[i],
      composite_label: null,
      created_at: null,
    })),
  }
}

describe('ComparePage — Streaming SSE (Sprint 93)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('le toggle Streaming est présent et initialement désactivé', () => {
    render(<ComparePage />)
    const toggle = screen.getByTestId('streaming-toggle')
    expect(toggle).toBeInTheDocument()
    expect(toggle).not.toBeChecked()
  })

  it('avec toggle actif, handleAnalyze appelle streamAnalyze et non postAnalyze', async () => {
    const user = userEvent.setup()

    vi.mocked(compareApi.postCompare)
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [null, 70.0]))
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [70.0, 70.0]))

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'complete' as const, data: {} as AnalyzeResponse }
    })

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'FAKE.TO, BNS.TO')
    await user.click(screen.getByTestId('streaming-toggle'))
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())
    await user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(analyzeApi.streamAnalyze).toHaveBeenCalledWith({
        ticker: 'FAKE.TO',
        ratios: null,
        workflow: 'value_graham',
      })
    })
    expect(analyzeApi.postAnalyze).not.toHaveBeenCalled()
  })

  it('sans toggle, postAnalyze est appelé (rétrocompatibilité)', async () => {
    const user = userEvent.setup()

    vi.mocked(compareApi.postCompare)
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [null, 70.0]))
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [70.0, 70.0]))

    vi.mocked(analyzeApi.postAnalyze).mockResolvedValue({} as AnalyzeResponse)

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'FAKE.TO, BNS.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())
    await user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(analyzeApi.postAnalyze).toHaveBeenCalledWith({
        ticker: 'FAKE.TO',
        ratios: null,
        workflow: 'value_graham',
      })
    })
    expect(analyzeApi.streamAnalyze).not.toHaveBeenCalled()
  })

  it('les chunks skill_start sont affichés progressivement', async () => {
    const user = userEvent.setup()

    vi.mocked(compareApi.postCompare)
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [null, 70.0]))
      .mockResolvedValueOnce(makeResponse(['FAKE.TO', 'BNS.TO'], [70.0, 70.0]))

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'skill_start' as const, data: { skill_id: 'graham_analysis' } }
      // pause pour que waitFor détecte l'affichage du skill
      await new Promise((r) => setTimeout(r, 200))
      yield { type: 'complete' as const, data: {} as AnalyzeResponse }
    })

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'FAKE.TO, BNS.TO')
    await user.click(screen.getByTestId('streaming-toggle'))
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())
    // Lancer l'analyse sans attendre la fin
    void user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(screen.getByTestId('stream-skill-FAKE.TO')).toBeInTheDocument()
    })
    expect(screen.getByTestId('stream-skill-FAKE.TO').textContent).toContain('graham_analysis')
  })

  it("une erreur SSE est affichée inline sous le bouton Analyser", async () => {
    const user = userEvent.setup()

    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['FAKE.TO', 'BNS.TO'], [null, 70.0]),
    )

    vi.mocked(analyzeApi.streamAnalyze).mockImplementation(async function* () {
      yield { type: 'error' as const, data: { message: 'Erreur SSE serveur' } }
    })

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'FAKE.TO, BNS.TO')
    await user.click(screen.getByTestId('streaming-toggle'))
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())
    await user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(screen.getByTestId('analyze-error-FAKE.TO')).toBeInTheDocument()
    })
    expect(screen.getByTestId('analyze-error-FAKE.TO').textContent).toContain('Erreur SSE serveur')
  })
})
