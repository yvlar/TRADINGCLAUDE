import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AnalysisResult } from '../components/AnalysisResult'
import type { AnalyzeResponse, GrahamAnalysisOutput } from '../types'

function buildGraham(): GrahamAnalysisOutput {
  return {
    ticker: 'BNS',
    profil_applique: 'DEFENSIF',
    defensive_score: 5,
    enterprising_score: 3,
    criteria_defensif: [],
    criteria_entreprenant: [],
    valeur_intrinseque_simple: 95.0,
    valeur_intrinseque_ajustee: 87.5,
    marge_securite: 0.09,
    graham_number: 88.2,
    drapeaux_rouges: [],
    verdict: 'CANDIDAT_SOLIDE',
    verdict_detail: 'BNS passe 5/8 critères.',
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.001,
  }
}

function buildResponse(overrides: Partial<AnalyzeResponse>): AnalyzeResponse {
  return {
    analysis_id: 'id-1',
    ticker: 'BNS',
    workflow: 'value_graham',
    skills_applied: ['graham_analysis'],
    graham: buildGraham(),
    earnings_quality: null,
    dorsey: null,
    buffett: null,
    cost_usd: 0.001,
    created_at: '2026-05-30T00:00:00Z',
    ...overrides,
  } as AnalyzeResponse
}

describe('AnalysisResult — traçabilité source+date (Sprint 139)', () => {
  it('affiche la source et la date quand présentes', () => {
    const result = buildResponse({
      ratios_fetched_at: '2026-05-20T09:00:00+00:00',
      ratios_source: 'Yahoo Finance',
    })
    render(<AnalysisResult result={result} />)
    const ligne = screen.getByTestId('result-ratios-source')
    expect(ligne).toHaveTextContent('Yahoo Finance')
    expect(ligne).toHaveTextContent('2026-05-20')
  })

  it("n'affiche rien quand la traçabilité est absente", () => {
    render(<AnalysisResult result={buildResponse({})} />)
    expect(screen.queryByTestId('result-ratios-source')).not.toBeInTheDocument()
  })
})
