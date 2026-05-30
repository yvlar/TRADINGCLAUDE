import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AnalysisResult } from '../components/AnalysisResult'
import type { AnalyzeResponse, GrahamAnalysisOutput } from '../types'

function buildGraham(grahamNumber: number | null): GrahamAnalysisOutput {
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
    graham_number: grahamNumber,
    drapeaux_rouges: [],
    verdict: 'CANDIDAT_SOLIDE',
    verdict_detail: 'BNS passe 5/8 critères.',
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.001,
  }
}

function buildResponse(graham: GrahamAnalysisOutput): AnalyzeResponse {
  return {
    analysis_id: 'id-1',
    ticker: 'BNS',
    workflow: 'value_graham',
    skills_applied: ['graham_analysis'],
    graham,
    earnings_quality: null,
    dorsey: null,
    buffett: null,
    cost_usd: 0.001,
    created_at: '2026-05-30T00:00:00Z',
  } as AnalyzeResponse
}

describe('AnalysisResult — Nombre de Graham (Sprint 128)', () => {
  it('affiche le nombre de Graham calculé', () => {
    render(<AnalysisResult result={buildResponse(buildGraham(88.2))} />)
    const ligne = screen.getByTestId('graham-number')
    expect(ligne).toHaveTextContent('$88.20')
  })

  it('masque la ligne quand le nombre de Graham est null', () => {
    render(<AnalysisResult result={buildResponse(buildGraham(null))} />)
    expect(screen.queryByTestId('graham-number')).not.toBeInTheDocument()
  })
})
