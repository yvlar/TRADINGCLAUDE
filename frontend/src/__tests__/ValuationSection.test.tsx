import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ValuationSection } from '../components/ValuationSection'
import type { StockValuationOutput } from '../types'

const BASE_VALUATION: StockValuationOutput = {
  ticker: 'BNS.TO',
  methodes: [
    { methode: 'dcf', valeur: 72.5, hypotheses: 'WACC 9%, croissance terminale 2.5%' },
    { methode: 'comparables', valeur: 68.0, hypotheses: 'P/E forward 10x pairs bancaires' },
    { methode: 'sectoriel', valeur: 70.0, hypotheses: '1.2x valeur comptable tangible' },
  ],
  fourchette_basse: 68.0,
  fourchette_centrale: 70.5,
  fourchette_haute: 72.5,
  marge_securite_composite: 0.126,
  matrice_sensibilite: {
    wacc_range: [0.08, 0.09, 0.1],
    growth_range: [0.02, 0.025, 0.03],
    values: [
      [75.0, 78.0, 81.0],
      [70.0, 72.5, 75.0],
      [65.0, 67.0, 69.0],
    ],
  },
  verdict: 'SOUS_EVALUE',
  verdict_detail: 'Le titre se négocie sous sa juste valeur centrale estimée.',
  recommandation_prochaine_etape: ['Vérifier la qualité du portefeuille de prêts', 'Surveiller le ratio CET1'],
  citations: [],
  cost_usd: 0.022,
}

describe('ValuationSection', () => {
  it('affiche le verdict, la marge et le toggle fermé par défaut', () => {
    render(<ValuationSection output={BASE_VALUATION} />)
    expect(screen.getByTestId('valuation-verdict')).toHaveTextContent('SOUS_EVALUE')
    expect(screen.getByTestId('valuation-marge')).toHaveTextContent('+13%')
    expect(screen.queryByTestId('valuation-fourchette')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche la fourchette de valeur', async () => {
    const user = userEvent.setup()
    render(<ValuationSection output={BASE_VALUATION} />)

    await user.click(screen.getByTestId('valuation-toggle'))

    const fourchette = screen.getByTestId('valuation-fourchette')
    expect(within(fourchette).getByTestId('valuation-centrale')).toHaveTextContent('70.50 $')
  })

  it('affiche les 3 méthodes de triangulation', async () => {
    const user = userEvent.setup()
    render(<ValuationSection output={BASE_VALUATION} />)

    await user.click(screen.getByTestId('valuation-toggle'))

    const methodes = screen.getByTestId('valuation-methodes')
    expect(within(methodes).getByTestId('valuation-methode-dcf')).toBeInTheDocument()
    expect(within(methodes).getByTestId('valuation-methode-comparables')).toBeInTheDocument()
    expect(within(methodes).getByTestId('valuation-methode-sectoriel')).toBeInTheDocument()
  })

  it('affiche la matrice de sensibilité avec les pourcentages WACC', async () => {
    const user = userEvent.setup()
    render(<ValuationSection output={BASE_VALUATION} />)

    await user.click(screen.getByTestId('valuation-toggle'))

    const matrix = screen.getByTestId('valuation-sensitivity')
    expect(within(matrix).getByText('9.0%')).toBeInTheDocument()
    expect(within(matrix).getByText('72.50')).toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<ValuationSection output={BASE_VALUATION} />)

    await user.click(screen.getByTestId('valuation-toggle'))

    expect(screen.getByTestId('valuation-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/ratio CET1/)).toBeInTheDocument()
  })

  it('affiche une marge négative pour un titre surévalué', () => {
    const output = { ...BASE_VALUATION, verdict: 'SUREVALUE', marge_securite_composite: -0.15 }
    render(<ValuationSection output={output} />)
    expect(screen.getByTestId('valuation-verdict')).toHaveTextContent('SUREVALUE')
    expect(screen.getByTestId('valuation-marge')).toHaveTextContent('-15%')
  })
})
