import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LynchCategoriesSection } from '../components/LynchCategoriesSection'
import type { LynchCategoriesOutput } from '../types'

const BASE_LYNCH: LynchCategoriesOutput = {
  ticker: 'SHOP.TO',
  categorie: 'FAST_GROWER',
  peg_ratio: 0.85,
  tenbagger_potential: true,
  score_croissance: 4,
  verdict: 'EXCELLENT',
  verdict_detail: 'Croissance rapide à valorisation raisonnable vs croissance.',
  recommandation_prochaine_etape: ['Vérifier la durabilité de la croissance', 'Surveiller la marge nette'],
  citations: [],
  cost_usd: 0.012,
}

describe('LynchCategoriesSection', () => {
  it('affiche la catégorie et le verdict, toggle fermé par défaut', () => {
    render(<LynchCategoriesSection output={BASE_LYNCH} />)
    expect(screen.getByTestId('lynch-categorie')).toHaveTextContent('Croissance rapide')
    expect(screen.getByTestId('lynch-verdict')).toHaveTextContent('EXCELLENT')
    expect(screen.queryByTestId('lynch-peg')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche le ratio PEG', async () => {
    const user = userEvent.setup()
    render(<LynchCategoriesSection output={BASE_LYNCH} />)

    await user.click(screen.getByTestId('lynch-toggle'))

    expect(screen.getByTestId('lynch-peg')).toHaveTextContent('0.85')
  })

  it('affiche N/A quand le PEG est null', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_LYNCH, peg_ratio: null }
    render(<LynchCategoriesSection output={output} />)

    await user.click(screen.getByTestId('lynch-toggle'))

    expect(screen.getByTestId('lynch-peg')).toHaveTextContent('N/A')
  })

  it('affiche le badge tenbagger quand le potentiel existe', async () => {
    const user = userEvent.setup()
    render(<LynchCategoriesSection output={BASE_LYNCH} />)

    await user.click(screen.getByTestId('lynch-toggle'))

    expect(screen.getByTestId('lynch-tenbagger')).toBeInTheDocument()
  })

  it('masque le badge tenbagger quand le potentiel est absent', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_LYNCH, tenbagger_potential: false }
    render(<LynchCategoriesSection output={output} />)

    await user.click(screen.getByTestId('lynch-toggle'))

    expect(screen.queryByTestId('lynch-tenbagger')).not.toBeInTheDocument()
  })

  it('affiche le score de croissance et les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<LynchCategoriesSection output={BASE_LYNCH} />)

    await user.click(screen.getByTestId('lynch-toggle'))

    expect(screen.getByTestId('lynch-score')).toHaveTextContent('4/5')
    expect(screen.getByTestId('lynch-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/durabilité de la croissance/)).toBeInTheDocument()
  })
})
