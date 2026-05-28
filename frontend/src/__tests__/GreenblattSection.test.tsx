import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GreenblattSection } from '../components/GreenblattSection'
import type { GreenblattOutput } from '../types'

const BASE_GREENBLATT: GreenblattOutput = {
  ticker: 'ATD.TO',
  roc: 0.32,
  earnings_yield: 0.11,
  verdict: 'TOP_DECILE',
  situations_speciales: ['Spinoff récent', 'Rachat d\'actions agressif'],
  verdict_detail: 'ROC élevé combiné à un rendement des bénéfices attractif.',
  recommandation_prochaine_etape: ['Comparer au reste du décile', 'Vérifier la stabilité de l\'EBIT'],
  citations: [],
  cost_usd: 0.009,
}

describe('GreenblattSection', () => {
  it('affiche le verdict et toggle fermé par défaut', () => {
    render(<GreenblattSection output={BASE_GREENBLATT} />)
    expect(screen.getByTestId('greenblatt-verdict')).toHaveTextContent('TOP_DECILE')
    expect(screen.queryByTestId('greenblatt-metrics')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche le ROC en pourcentage', async () => {
    const user = userEvent.setup()
    render(<GreenblattSection output={BASE_GREENBLATT} />)

    await user.click(screen.getByTestId('greenblatt-toggle'))

    expect(screen.getByTestId('greenblatt-roc')).toHaveTextContent('32.0%')
  })

  it('affiche le rendement des bénéfices en pourcentage', async () => {
    const user = userEvent.setup()
    render(<GreenblattSection output={BASE_GREENBLATT} />)

    await user.click(screen.getByTestId('greenblatt-toggle'))

    expect(screen.getByTestId('greenblatt-earnings-yield')).toHaveTextContent('11.0%')
  })

  it('affiche les situations spéciales une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<GreenblattSection output={BASE_GREENBLATT} />)

    await user.click(screen.getByTestId('greenblatt-toggle'))

    expect(screen.getByTestId('greenblatt-situations')).toBeInTheDocument()
    expect(screen.getByText(/Spinoff récent/)).toBeInTheDocument()
  })

  it('masque les situations spéciales quand la liste est vide', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_GREENBLATT, situations_speciales: [] }
    render(<GreenblattSection output={output} />)

    await user.click(screen.getByTestId('greenblatt-toggle'))

    expect(screen.queryByTestId('greenblatt-situations')).not.toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<GreenblattSection output={BASE_GREENBLATT} />)

    await user.click(screen.getByTestId('greenblatt-toggle'))

    expect(screen.getByTestId('greenblatt-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/stabilité de l'EBIT/)).toBeInTheDocument()
  })
})
