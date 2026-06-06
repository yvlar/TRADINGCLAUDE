import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AnalysisResult } from '../components/AnalysisResult'
import { VerdictDisclaimer } from '../components/VerdictDisclaimer'
import { VERDICT_DISCLAIMER_TEXT } from '../constants/disclaimer'
import type { AnalyzeResponse, GrahamAnalysisOutput } from '../types'

function buildGraham(verdict: string): GrahamAnalysisOutput {
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
    verdict,
    verdict_detail: 'BNS passe 5/8 critères.',
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.001,
  }
}

function buildResponse(graham: GrahamAnalysisOutput | null): AnalyzeResponse {
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

describe('VerdictDisclaimer (E9-S1)', () => {
  it('rend un avertissement avec rôle note et le texte réglementaire', () => {
    render(<VerdictDisclaimer />)
    const note = screen.getByTestId('verdict-disclaimer')
    expect(note).toHaveAttribute('role', 'note')
    expect(note).toHaveTextContent(VERDICT_DISCLAIMER_TEXT)
  })

  it('est rendu adjacent au verdict Graham dans AnalysisResult', () => {
    render(<AnalysisResult result={buildResponse(buildGraham('CANDIDAT_SOLIDE'))} />)
    expect(screen.getByTestId('graham-verdict')).toBeInTheDocument()
    expect(screen.getByTestId('verdict-disclaimer')).toBeInTheDocument()
  })

  it("n'est pas rendu en l'absence de verdict et de score composite", () => {
    render(<AnalysisResult result={buildResponse(null)} />)
    expect(screen.queryByTestId('verdict-disclaimer')).not.toBeInTheDocument()
  })
})
