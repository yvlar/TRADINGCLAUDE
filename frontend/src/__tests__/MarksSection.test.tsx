import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MarksSection } from '../components/MarksSection'
import type { MarksOutput } from '../types'

const BASE_MARKS: MarksOutput = {
  position_cycle: 'PESSIMISME_EXCESSIF',
  pendule_score: -4,
  second_level_insight: 'Le consensus surévalue le risque de récession ; les prix intègrent déjà le pire.',
  recommandation_timing: 'ACHETER_AGRESSIF',
  verdict_detail: 'Le pendule est proche de son extrême pessimiste — fenêtre contrariante.',
  recommandation_prochaine_etape: ['Déployer le cash progressivement', 'Surveiller les spreads de crédit'],
  citations: [],
  cost_usd: 0.009,
}

describe('MarksSection', () => {
  it('affiche la position dans le cycle, le timing et reste fermé par défaut', () => {
    render(<MarksSection output={BASE_MARKS} />)
    expect(screen.getByTestId('marks-position')).toHaveTextContent('Pessimisme excessif')
    expect(screen.getByTestId('marks-timing')).toHaveTextContent('ACHETER_AGRESSIF')
    expect(screen.queryByTestId('marks-pendule')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche le pendule avec le score', async () => {
    const user = userEvent.setup()
    render(<MarksSection output={BASE_MARKS} />)

    await user.click(screen.getByTestId('marks-toggle'))

    expect(screen.getByTestId('marks-pendule')).toHaveTextContent('-4')
  })

  it('préfixe d\'un + un score de pendule positif', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_MARKS, pendule_score: 3 }
    render(<MarksSection output={output} />)

    await user.click(screen.getByTestId('marks-toggle'))

    expect(screen.getByTestId('marks-pendule')).toHaveTextContent('+3')
  })

  it('affiche le second-level thinking une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<MarksSection output={BASE_MARKS} />)

    await user.click(screen.getByTestId('marks-toggle'))

    expect(screen.getByTestId('marks-insight')).toBeInTheDocument()
    expect(screen.getByText(/risque de récession/)).toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<MarksSection output={BASE_MARKS} />)

    await user.click(screen.getByTestId('marks-toggle'))

    expect(screen.getByTestId('marks-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/spreads de crédit/)).toBeInTheDocument()
  })

  it('affiche le libellé brut pour une position de cycle inconnue', () => {
    const output = { ...BASE_MARKS, position_cycle: 'INCONNU' }
    render(<MarksSection output={output} />)
    expect(screen.getByTestId('marks-position')).toHaveTextContent('INCONNU')
  })
})
