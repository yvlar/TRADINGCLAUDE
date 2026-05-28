import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PabraiSection } from '../components/PabraiSection'
import type { DhandhoPrincipe, PabraiOutput } from '../types'

const PRINCIPES: DhandhoPrincipe[] = Array.from({ length: 9 }, (_, i) => ({
  nom: `Principe Dhandho ${i + 1}`,
  satisfait: i % 2 === 0,
  commentaire: `Commentaire ${i + 1}`,
}))

const BASE_PABRAI: PabraiOutput = {
  ticker: 'FFH.TO',
  principes_dhandho: PRINCIPES,
  heads_i_win_score: 7,
  asymetrie: 3.5,
  kelly_fractionnel: 0.085,
  verdict: 'DHANDHO_FORT',
  verdict_detail: 'Pari asymétrique : faible downside, upside multiple.',
  recommandation_prochaine_etape: ['Vérifier le 13F de la source de cloning', 'Dimensionner via Kelly fractionnel'],
  citations: [],
  cost_usd: 0.011,
}

describe('PabraiSection', () => {
  it('affiche le verdict et reste fermé par défaut', () => {
    render(<PabraiSection output={BASE_PABRAI} />)
    expect(screen.getByTestId('pabrai-verdict')).toHaveTextContent('DHANDHO_FORT')
    expect(screen.queryByTestId('pabrai-metrics')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche l\'asymétrie et le Kelly fractionnel', async () => {
    const user = userEvent.setup()
    render(<PabraiSection output={BASE_PABRAI} />)

    await user.click(screen.getByTestId('pabrai-toggle'))

    expect(screen.getByTestId('pabrai-asymetrie')).toHaveTextContent('3.5×')
    expect(screen.getByTestId('pabrai-kelly')).toHaveTextContent('8.5%')
  })

  it('affiche N/A quand le Kelly fractionnel est null', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_PABRAI, kelly_fractionnel: null }
    render(<PabraiSection output={output} />)

    await user.click(screen.getByTestId('pabrai-toggle'))

    expect(screen.getByTestId('pabrai-kelly')).toHaveTextContent('N/A')
  })

  it('affiche le score heads-I-win /9 et les 9 principes', async () => {
    const user = userEvent.setup()
    render(<PabraiSection output={BASE_PABRAI} />)

    await user.click(screen.getByTestId('pabrai-toggle'))

    expect(screen.getByTestId('pabrai-score')).toHaveTextContent('7/9')
    expect(screen.getAllByTestId('pabrai-principe')).toHaveLength(9)
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<PabraiSection output={BASE_PABRAI} />)

    await user.click(screen.getByTestId('pabrai-toggle'))

    expect(screen.getByTestId('pabrai-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/13F/)).toBeInTheDocument()
  })

  it('reflète un verdict défavorable par un badge danger', () => {
    const output = { ...BASE_PABRAI, verdict: 'PAS_DHANDHO' }
    render(<PabraiSection output={output} />)
    expect(screen.getByTestId('pabrai-verdict')).toHaveTextContent('PAS_DHANDHO')
  })
})
