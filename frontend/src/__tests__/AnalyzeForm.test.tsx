import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnalyzeForm } from '../components/AnalyzeForm'
import { getExtract } from '../api/analyze'
import { ApiError } from '../api/client'
import type { ExtractResponse } from '../types'

vi.mock('../api/analyze', () => ({
  postAnalyze: vi.fn(),
  postReport: vi.fn(),
  postScreen: vi.fn(),
  getHistory: vi.fn(),
  getHealthz: vi.fn(),
  getExtract: vi.fn(),
}))

const MOCK_GRAHAM_RATIOS = {
  pe: 11.0,
  pb: 1.3,
  price: 80.0,
  book_value: 61.5,
  eps_ttm: 7.25,
  revenue_bn: 38,
  debt_equity: 0.45,
  eps_growth_total: 0.27,
  eps_growth_years: 4,
  dividend_years: 190,
  current_ratio: null,
}

const MOCK_EARNINGS_QUALITY = {
  sales_t: 38_000_000_000,
  sales_t1: 36_000_000_000,
  cogs_t: 15_000_000_000,
  cogs_t1: 14_500_000_000,
  net_income_t: 10_000_000_000,
  cfo_t: 12_000_000_000,
  receivables_t: 50_000_000_000,
  receivables_t1: 48_000_000_000,
  current_assets_t: 100_000_000_000,
  current_liabilities_t: 80_000_000_000,
  total_assets_t: 1_000_000_000_000,
  total_assets_t1: 950_000_000_000,
}

const MOCK_EXTRACT_RESPONSE: ExtractResponse = {
  graham: MOCK_GRAHAM_RATIOS,
  earnings_quality: null,
}

const MOCK_EXTRACT_WITH_EARNINGS: ExtractResponse = {
  graham: MOCK_GRAHAM_RATIOS,
  earnings_quality: MOCK_EARNINGS_QUALITY,
}

describe('AnalyzeForm', () => {
  it('rend le formulaire avec les champs requis', () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    expect(screen.getByRole('form')).toBeInTheDocument()
    expect(screen.getByLabelText('Ticker')).toBeInTheDocument()
    expect(screen.getByText('Analyser')).toBeInTheDocument()
  })

  it('appelle onSubmit avec le ticker en majuscules', async () => {
    const onSubmit = vi.fn()
    render(<AnalyzeForm onSubmit={onSubmit} />)

    const tickerInput = screen.getByLabelText('Ticker')
    await userEvent.clear(tickerInput)
    await userEvent.type(tickerInput, 'bns')

    await userEvent.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce()
      const req = onSubmit.mock.calls[0][0]
      expect(req.ticker).toBe('BNS')
    })
  })

  it('le payload POST /analyze contient les ratios Graham', async () => {
    const onSubmit = vi.fn()
    render(<AnalyzeForm onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText('Ticker'), 'BNS')
    await userEvent.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce()
      const req = onSubmit.mock.calls[0][0]
      expect(req.ratios).toBeDefined()
      expect(typeof req.ratios.pe).toBe('number')
      expect(req.workflow).toBe('value_graham')
    })
  })

  it('le bouton est désactivé quand isLoading=true', () => {
    render(<AnalyzeForm onSubmit={vi.fn()} isLoading={true} />)
    expect(screen.getByText('Analyse en cours...')).toBeDisabled()
  })

  it('Munger est désactivé sans Thèse cochée', () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    const munger = screen.getByRole('checkbox', { name: /munger/i })
    expect(munger).toBeDisabled()
  })

  it('Munger devient actif quand Thèse est cochée', async () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    const thesis = screen.getByRole('checkbox', { name: /investissement/i })
    await userEvent.click(thesis)
    const munger = screen.getByRole('checkbox', { name: /munger/i })
    expect(munger).not.toBeDisabled()
  })

  it('affiche le bouton Auto-fill', () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    expect(screen.getByTestId('autofill-button')).toBeInTheDocument()
  })

  it('pré-remplit les ratios Graham après Auto-fill réussi', async () => {
    vi.mocked(getExtract).mockResolvedValueOnce(MOCK_EXTRACT_RESPONSE)
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    await userEvent.type(screen.getByPlaceholderText('BNS'), 'BNS')
    await userEvent.click(screen.getByTestId('autofill-button'))
    await waitFor(() => {
      expect(screen.getByDisplayValue('11')).toBeInTheDocument()
    })
  })

  it("affiche le libellé honnête « Croissance EPS (totale) » (pas « 10a »)", () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    expect(screen.getByText('Croissance EPS (totale)')).toBeInTheDocument()
    expect(screen.queryByText('Croissance EPS 10a')).not.toBeInTheDocument()
  })

  it('affiche l’horizon réel « sur N ans » après Auto-fill', async () => {
    vi.mocked(getExtract).mockResolvedValueOnce(MOCK_EXTRACT_RESPONSE)
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    await userEvent.type(screen.getByPlaceholderText('BNS'), 'BNS')
    await userEvent.click(screen.getByTestId('autofill-button'))
    await waitFor(() => {
      expect(screen.getByTestId('eps-growth-horizon')).toHaveTextContent('sur 4 ans')
    })
  })

  it("affiche un message d'erreur si ticker introuvable (404)", async () => {
    vi.mocked(getExtract).mockRejectedValueOnce(new ApiError(404, 'Not Found'))
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    await userEvent.type(screen.getByPlaceholderText('BNS'), 'ZZZZZ')
    await userEvent.click(screen.getByTestId('autofill-button'))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Ticker introuvable')
    })
  })

  // ─── Tests Sprint 33 — Qualité bénéfices ────────────────────────────────────

  it('la checkbox Qualité bénéfices est désactivée sans Auto-fill', () => {
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    const checkbox = screen.getByTestId('earnings-checkbox')
    expect(checkbox).toBeDisabled()
  })

  it("Auto-fill avec earnings_quality active la checkbox Qualité bénéfices", async () => {
    vi.mocked(getExtract).mockResolvedValueOnce(MOCK_EXTRACT_WITH_EARNINGS)
    render(<AnalyzeForm onSubmit={vi.fn()} />)
    await userEvent.type(screen.getByPlaceholderText('BNS'), 'BNS')
    await userEvent.click(screen.getByTestId('autofill-button'))
    await waitFor(() => {
      expect(screen.getByTestId('earnings-checkbox')).not.toBeDisabled()
    })
    expect(screen.getByText(/chargé \(Yahoo Finance\)/i)).toBeInTheDocument()
  })

  it('earnings_ratios inclus dans le payload quand checkbox cochée', async () => {
    vi.mocked(getExtract).mockResolvedValueOnce(MOCK_EXTRACT_WITH_EARNINGS)
    const onSubmit = vi.fn()
    render(<AnalyzeForm onSubmit={onSubmit} />)

    await userEvent.type(screen.getByPlaceholderText('BNS'), 'BNS')
    await userEvent.click(screen.getByTestId('autofill-button'))

    await waitFor(() => expect(screen.getByTestId('earnings-checkbox')).not.toBeDisabled())

    await userEvent.click(screen.getByTestId('earnings-checkbox'))
    await userEvent.click(screen.getByText('Analyser'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce()
      const req = onSubmit.mock.calls[0][0]
      expect(req.earnings_ratios).toBeDefined()
      expect(req.earnings_ratios.sales_t).toBe(38_000_000_000)
    })
  })
})
