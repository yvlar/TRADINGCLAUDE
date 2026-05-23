import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ComparePage from '../pages/ComparePage'
import * as compareApi from '../api/compare'
import * as analyzeApi from '../api/analyze'
import type { CompareResponse } from '../types'
import { ApiError } from '../api/client'

vi.mock('../api/compare', () => ({
  postCompare: vi.fn(),
}))

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
      graham_verdict: scores[i] !== null ? 'ACHETER' : null,
      graham_score: scores[i] !== null ? 6 : null,
      buffett_verdict: scores[i] !== null ? 'COMPOUNDER' : null,
      dorsey_moat_type: scores[i] !== null ? 'NARROW' : null,
      composite_score: scores[i],
      composite_label: scores[i] !== null ? 'FORT' : null,
      created_at: scores[i] !== null ? '2026-05-10T12:00:00+00:00' : null,
    })),
  }
}

describe('ComparePage (Sprint 80)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le champ de saisie et le bouton', () => {
    render(<ComparePage />)
    expect(screen.getByTestId('compare-ticker-input')).toBeInTheDocument()
    expect(screen.getByTestId('compare-submit-btn')).toBeInTheDocument()
  })

  it('soumet 2 tickers et affiche le tableau', async () => {
    const user = userEvent.setup()
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'TD.TO'], [72.5, 65.0]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, TD.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('compare-table')).toBeInTheDocument()
    })
    expect(compareApi.postCompare).toHaveBeenCalledWith(['BNS.TO', 'TD.TO'])
  })

  it('highlight la cellule composite_score du meilleur ticker', async () => {
    const user = userEvent.setup()
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'TD.TO'], [72.5, 65.0]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, TD.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('compare-cell-composite_score-BNS.TO')).toBeInTheDocument()
    })
    const bestCell = screen.getByTestId('compare-cell-composite_score-BNS.TO')
    expect(bestCell.className).toContain('bg-yellow')
  })

  it('affiche "--" pour un ticker sans analyse en DB', async () => {
    const user = userEvent.setup()
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, null]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, FAKE.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('compare-table')).toBeInTheDocument()
    })
    const cell = screen.getByTestId('compare-cell-composite_score-FAKE.TO')
    expect(cell.textContent).toBe('--')
  })

  it('affiche une erreur si moins de 2 tickers saisis', async () => {
    const user = userEvent.setup()
    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    expect(screen.getByTestId('compare-error')).toBeInTheDocument()
    expect(compareApi.postCompare).not.toHaveBeenCalled()
  })
})

describe('ComparePage — bouton Analyser (Sprint 87)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le bouton Analyser uniquement si analysis_id est null', async () => {
    const user = userEvent.setup()
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, null]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, FAKE.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('compare-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument()
    expect(screen.queryByTestId('analyze-btn-BNS.TO')).not.toBeInTheDocument()
  })

  it("n'affiche pas le bouton Analyser si tous les analysis_id sont définis", async () => {
    const user = userEvent.setup()
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'TD.TO'], [70.0, 65.0]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, TD.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('compare-table')).toBeInTheDocument()
    })

    expect(screen.queryByTestId('analyze-btn-BNS.TO')).not.toBeInTheDocument()
    expect(screen.queryByTestId('analyze-btn-TD.TO')).not.toBeInTheDocument()
  })

  it('le clic sur Analyser appelle postAnalyze avec le bon ticker', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postAnalyze).mockResolvedValue({} as never)
    vi.mocked(compareApi.postCompare)
      .mockResolvedValueOnce(makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, null]))
      .mockResolvedValueOnce(makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, 60.0]))

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, FAKE.TO')
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
  })

  it('après succès, postCompare est rappelé et le bouton disparaît', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postAnalyze).mockResolvedValue({} as never)
    vi.mocked(compareApi.postCompare)
      .mockResolvedValueOnce(makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, null]))
      .mockResolvedValueOnce(makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, 60.0]))

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, FAKE.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))
    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())

    await user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(compareApi.postCompare).toHaveBeenCalledTimes(2)
    })
    await waitFor(() => {
      expect(screen.queryByTestId('analyze-btn-FAKE.TO')).not.toBeInTheDocument()
    })
  })

  it('une erreur API affiche un message inline sous le bouton Analyser', async () => {
    const user = userEvent.setup()
    vi.mocked(analyzeApi.postAnalyze).mockRejectedValue(new ApiError(500, 'Erreur serveur'))
    vi.mocked(compareApi.postCompare).mockResolvedValue(
      makeResponse(['BNS.TO', 'FAKE.TO'], [70.0, null]),
    )

    render(<ComparePage />)
    await user.type(screen.getByTestId('compare-ticker-input'), 'BNS.TO, FAKE.TO')
    await user.click(screen.getByTestId('compare-submit-btn'))
    await waitFor(() => expect(screen.getByTestId('analyze-btn-FAKE.TO')).toBeInTheDocument())

    await user.click(screen.getByTestId('analyze-btn-FAKE.TO'))

    await waitFor(() => {
      expect(screen.getByTestId('analyze-error-FAKE.TO')).toBeInTheDocument()
    })
    expect(screen.getByTestId('analyze-error-FAKE.TO').textContent).toBe('Erreur serveur')
  })
})
