import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AnalysisResult } from '../components/AnalysisResult'
import { Disclaimer } from '../components/Disclaimer'
import { DISCLAIMER_HEADING, DISCLAIMER_TEXT } from '../constants/disclaimer'
import type { AnalyzeResponse } from '../types'

function buildResponse(): AnalyzeResponse {
  return {
    analysis_id: 'id-1',
    ticker: 'BNS',
    workflow: 'value_graham',
    skills_applied: ['graham_analysis'],
    graham: null,
    earnings_quality: null,
    dorsey: null,
    buffett: null,
    cost_usd: 0.001,
    created_at: '2026-05-30T00:00:00Z',
  } as AnalyzeResponse
}

describe('Disclaimer (Sprint 129)', () => {
  it('variante inline rend le titre et le texte d avertissement', () => {
    render(<Disclaimer variant="inline" />)
    const el = screen.getByTestId('disclaimer')
    expect(el).toHaveAttribute('data-variant', 'inline')
    expect(el).toHaveTextContent(DISCLAIMER_HEADING)
    expect(el).toHaveTextContent(DISCLAIMER_TEXT)
  })

  it('variante footer rend le texte sans le titre, discrète', () => {
    render(<Disclaimer variant="footer" />)
    const el = screen.getByTestId('disclaimer')
    expect(el).toHaveAttribute('data-variant', 'footer')
    expect(el).toHaveTextContent(DISCLAIMER_TEXT)
  })

  it('variante par défaut = inline', () => {
    render(<Disclaimer />)
    expect(screen.getByTestId('disclaimer')).toHaveAttribute('data-variant', 'inline')
  })

  it('est présent dans le bloc de résultats AnalysisResult', () => {
    render(<AnalysisResult result={buildResponse()} />)
    const el = screen.getByTestId('disclaimer')
    expect(el).toHaveTextContent(DISCLAIMER_TEXT)
  })
})
