import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BuffettQualitySection } from '../components/BuffettQualitySection'
import type { BuffettQualityOutput } from '../types'

const BASE_BUFFETT: BuffettQualityOutput = {
  ticker: 'AAPL',
  filtres: [
    { filtre: 'Entreprise compréhensible', passe: true, score: 1, justification: 'Modèle d\'affaires clair' },
    { filtre: 'Économie favorable long terme', passe: true, score: 1, justification: 'ROIC > 30% durable' },
    { filtre: 'Direction compétente et honnête', passe: true, score: 1, justification: 'Allocation capital exemplaire' },
    { filtre: 'Prix très attractif', passe: false, score: 0, justification: 'P/E élevé vs croissance' },
  ],
  owner_earnings: 6.42,
  quality_score: 3,
  verdict: 'QUALITE_CORRECTE',
  verdict_detail: 'Compounder de qualité mais valorisation tendue actuellement.',
  drapeaux_rouges: ['Valorisation au-dessus de la moyenne historique'],
  recommandation_prochaine_etape: ['Attendre un recul de 15% du cours', 'Recalculer owner earnings au prochain 10-K'],
  citations: [],
  cost_usd: 0.018,
  confidence_score: 0.88,
}

describe('BuffettQualitySection', () => {
  it('affiche le verdict, le score qualité et le toggle fermé par défaut', () => {
    render(<BuffettQualitySection output={BASE_BUFFETT} />)
    expect(screen.getByTestId('buffett-verdict')).toHaveTextContent('QUALITE_CORRECTE')
    expect(screen.getByTestId('buffett-quality-score')).toHaveTextContent('3/4')
    expect(screen.queryByTestId('buffett-filtres')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche les 4 filtres', async () => {
    const user = userEvent.setup()
    render(<BuffettQualitySection output={BASE_BUFFETT} />)

    await user.click(screen.getByTestId('buffett-toggle'))

    const filtres = screen.getByTestId('buffett-filtres')
    expect(within(filtres).getByTestId('buffett-filtre-0')).toBeInTheDocument()
    expect(within(filtres).getByTestId('buffett-filtre-3')).toBeInTheDocument()
    expect(within(filtres).getByText(/Prix très attractif/)).toBeInTheDocument()
  })

  it('affiche les owner earnings une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<BuffettQualitySection output={BASE_BUFFETT} />)

    await user.click(screen.getByTestId('buffett-toggle'))

    const oe = screen.getByTestId('buffett-owner-earnings')
    expect(within(oe).getByText('6.42 $')).toBeInTheDocument()
  })

  it('affiche N/A pour owner earnings null', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_BUFFETT, owner_earnings: null }
    render(<BuffettQualitySection output={output} />)

    await user.click(screen.getByTestId('buffett-toggle'))

    const oe = screen.getByTestId('buffett-owner-earnings')
    expect(within(oe).getByText('N/A')).toBeInTheDocument()
  })

  it('affiche les drapeaux rouges et recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<BuffettQualitySection output={BASE_BUFFETT} />)

    await user.click(screen.getByTestId('buffett-toggle'))

    expect(screen.getByTestId('buffett-red-flags')).toBeInTheDocument()
    expect(screen.getByTestId('buffett-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/recul de 15%/)).toBeInTheDocument()
  })

  it('affiche le verdict REJETER avec variante danger', () => {
    const output = { ...BASE_BUFFETT, verdict: 'REJETER', quality_score: 1 }
    render(<BuffettQualitySection output={output} />)
    expect(screen.getByTestId('buffett-verdict')).toHaveTextContent('REJETER')
    expect(screen.getByTestId('buffett-quality-score')).toHaveTextContent('1/4')
  })
})
