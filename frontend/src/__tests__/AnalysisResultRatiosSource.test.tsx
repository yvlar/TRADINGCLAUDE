import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AnalysisResult } from '../components/AnalysisResult'
import type {
  AnalyzeResponse,
  EarningsQualityOutput,
  GrahamAnalysisOutput,
  StockValuationOutput,
} from '../types'

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

function buildEarnings(): EarningsQualityOutput {
  return {
    ticker: 'BNS.TO',
    is_financial: false,
    m_score: {
      dsri: 1.05, gmi: 0.98, aqi: 1.01, sgi: 1.03, depi: 0.97,
      sgai: null, tata: -0.02, lvgi: 1.01, m_score: -2.45,
      interpretation: 'Faible risque (< -1.78)',
    },
    z_score: {
      variante: 'Altman classique', x1: 0.2, x2: 0.3, x3: 0.1, x4: 1.8, x5: 0.4,
      z_score: 3.15, interpretation: 'Zone sûre (> 2.99)',
    },
    f_score: { criteria: [], f_score: 7, interpretation: 'Qualité élevée' },
    c_score: { signaux: [], c_score: 1, interpretation: 'Faible risque' },
    sloan: { accrual_ratio: -0.03, interpretation: 'Accruals négatifs' },
    drapeaux_rouges: [],
    verdict: 'ATTENTION',
    verdict_detail: 'Un signal mineur.',
    confidence_score: 1.0,
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.012,
  } as EarningsQualityOutput
}

function buildValuation(): StockValuationOutput {
  return {
    ticker: 'BNS.TO',
    methodes: [],
    fourchette_basse: 68.0,
    fourchette_centrale: 70.5,
    fourchette_haute: 72.5,
    marge_securite_composite: 0.126,
    matrice_sensibilite: { wacc_range: [], growth_range: [], values: [] },
    verdict: 'SOUS_EVALUE',
    verdict_detail: 'Sous la juste valeur.',
    recommandation_prochaine_etape: [],
    citations: [],
    cost_usd: 0.022,
  } as StockValuationOutput
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

  it('conserve la source quand la date est absente (source seule, sans segment date)', () => {
    const result = buildResponse({ ratios_fetched_at: null, ratios_source: 'Yahoo Finance' })
    render(<AnalysisResult result={result} />)
    const ligne = screen.getByTestId('result-ratios-source')
    expect(ligne).toHaveTextContent('Yahoo Finance')
    expect(ligne).not.toHaveTextContent('récupéré le')
  })
})

describe('AnalysisResult — provenance par ratio sur l’analyse rendue (Sprint 150)', () => {
  it('affiche un badge de repli sur l’analyse rendue/rechargée quand la clé yfinance diffère', () => {
    const result = buildResponse({
      ratios_provenance: { pb: 'priceToBookRatio', debt_equity: 'debtToEquity' },
    })
    render(<AnalysisResult result={result} />)
    const prov = screen.getByTestId('result-ratios-provenance')
    // pb sur une clé de repli (≠ priceToBook) → badge ; debt_equity sur sa clé primaire → omis.
    expect(prov).toHaveTextContent('P/B')
    expect(prov).toHaveTextContent('priceToBookRatio')
    expect(prov).not.toHaveTextContent('Dette/Capitaux')
  })

  it('n’affiche aucun badge quand ratios_provenance est null', () => {
    render(<AnalysisResult result={buildResponse({ ratios_provenance: null })} />)
    expect(screen.queryByTestId('result-ratios-provenance')).not.toBeInTheDocument()
  })

  it('n’affiche aucun badge quand toutes les clés sont primaires (aucun repli)', () => {
    const result = buildResponse({
      ratios_provenance: { pb: 'priceToBook', debt_equity: 'debtToEquity', book_value: 'bookValue' },
    })
    render(<AnalysisResult result={result} />)
    expect(screen.queryByTestId('result-ratios-provenance')).not.toBeInTheDocument()
  })
})

describe('AnalysisResult — traçabilité earnings/valuation (Sprint 146)', () => {
  function buildPresent(): AnalyzeResponse {
    return buildResponse({
      earnings_quality: buildEarnings(),
      valuation: buildValuation(),
      earnings_ratios_fetched_at: '2026-05-21T09:00:00+00:00',
      earnings_ratios_source: 'Yahoo Finance',
      valuation_ratios_fetched_at: '2026-05-22T09:00:00+00:00',
      valuation_ratios_source: 'Yahoo Finance',
    })
  }

  it('affiche la source+date earnings et valuation, dans la carte une fois ouverte', async () => {
    const user = userEvent.setup()
    render(<AnalysisResult result={buildPresent()} />)

    await user.click(screen.getByTestId('eq-toggle'))
    const ligneEarnings = screen.getByTestId('earnings-ratios-source')
    expect(ligneEarnings).toHaveTextContent('Yahoo Finance')
    expect(ligneEarnings).toHaveTextContent('2026-05-21')

    await user.click(screen.getByTestId('valuation-toggle'))
    const ligneValuation = screen.getByTestId('valuation-ratios-source')
    expect(ligneValuation).toHaveTextContent('Yahoo Finance')
    expect(ligneValuation).toHaveTextContent('2026-05-22')
  })

  it('rend la note DANS la carte (parité Graham) — absente tant que la carte est repliée', () => {
    // Les cartes earnings/valuation sont repliées par défaut : la note vit dans leur
    // CardContent, donc elle n'est rendue qu'une fois la carte ouverte (pas orpheline dessous).
    render(<AnalysisResult result={buildPresent()} />)
    expect(screen.queryByTestId('earnings-ratios-source')).not.toBeInTheDocument()
    expect(screen.queryByTestId('valuation-ratios-source')).not.toBeInTheDocument()
  })

  it("n'affiche rien quand la traçabilité earnings/valuation est absente, carte ouverte", async () => {
    const user = userEvent.setup()
    const result = buildResponse({
      earnings_quality: buildEarnings(),
      valuation: buildValuation(),
    })
    render(<AnalysisResult result={result} />)

    await user.click(screen.getByTestId('eq-toggle'))
    await user.click(screen.getByTestId('valuation-toggle'))
    expect(screen.queryByTestId('earnings-ratios-source')).not.toBeInTheDocument()
    expect(screen.queryByTestId('valuation-ratios-source')).not.toBeInTheDocument()
  })
})
