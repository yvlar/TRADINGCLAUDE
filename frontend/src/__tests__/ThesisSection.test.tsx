import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThesisSection } from '../components/ThesisSection'
import type { ThesisBuilderOutput } from '../types'

const BASE_THESIS: ThesisBuilderOutput = {
  ticker: 'BNS.TO',
  scenario_bull: {
    probabilite: 0.25,
    rendement_cible: 0.35,
    hypotheses: ['Reprise du cycle de taux', 'Expansion marges bancaires'],
  },
  scenario_base: {
    probabilite: 0.50,
    rendement_cible: 0.12,
    hypotheses: ['Croissance stable des prêts', 'Dividende maintenu'],
  },
  scenario_bear: {
    probabilite: 0.25,
    rendement_cible: -0.20,
    hypotheses: ['Hausse des provisions', 'Récession Amérique latine'],
  },
  kill_criteria: [
    'Ratio CET1 < 11% pendant 2 trimestres consécutifs',
    'Réduction du dividende',
  ],
  devils_advocate: 'L\'exposition à l\'Amérique latine reste un risque sous-estimé par le marché.',
  position_size_pct: 4.5,
  verdict_final: 'ACCUMULER',
  synthese_narrative:
    'BNS présente un profil rendement/risque attrayant au cours actuel.\n\nLa valorisation à 1.1× P/B offre une marge de sécurité raisonnable.',
  citations: [],
  cost_usd: 0.021,
}

describe('ThesisSection', () => {
  it('affiche le verdict et la taille de position, section fermée par défaut', () => {
    render(<ThesisSection output={BASE_THESIS} />)
    expect(screen.getByTestId('thesis-verdict')).toHaveTextContent('ACCUMULER')
    expect(screen.getByText(/4\.5%/)).toBeInTheDocument()
    expect(screen.queryByTestId('thesis-scenarios')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche les 3 scénarios', async () => {
    const user = userEvent.setup()
    render(<ThesisSection output={BASE_THESIS} />)

    await user.click(screen.getByTestId('thesis-toggle'))

    expect(screen.getByTestId('thesis-scenarios')).toBeInTheDocument()
    expect(screen.getByTestId('scenario-bull')).toBeInTheDocument()
    expect(screen.getByTestId('scenario-base')).toBeInTheDocument()
    expect(screen.getByTestId('scenario-bear')).toBeInTheDocument()
  })

  it('affiche les rendements cibles correctement formatés', async () => {
    const user = userEvent.setup()
    render(<ThesisSection output={BASE_THESIS} />)

    await user.click(screen.getByTestId('thesis-toggle'))

    expect(screen.getByText('+35%')).toBeInTheDocument()
    expect(screen.getByText('+12%')).toBeInTheDocument()
    expect(screen.getByText('-20%')).toBeInTheDocument()
  })

  it('affiche les kill criteria une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<ThesisSection output={BASE_THESIS} />)

    await user.click(screen.getByTestId('thesis-toggle'))

    expect(screen.getByTestId('thesis-kill-criteria')).toBeInTheDocument()
    expect(screen.getByText(/Réduction du dividende/)).toBeInTheDocument()
  })

  it("affiche le devil's advocate une fois ouvert", async () => {
    const user = userEvent.setup()
    render(<ThesisSection output={BASE_THESIS} />)

    await user.click(screen.getByTestId('thesis-toggle'))

    const da = screen.getByTestId('thesis-devils-advocate')
    expect(da).toBeInTheDocument()
    expect(within(da).getByText(/Amérique latine/)).toBeInTheDocument()
  })

  it('affiche la narrative découpée en paragraphes', async () => {
    const user = userEvent.setup()
    render(<ThesisSection output={BASE_THESIS} />)

    await user.click(screen.getByTestId('thesis-toggle'))

    expect(screen.getByTestId('thesis-narrative')).toBeInTheDocument()
    expect(screen.getByText(/profil rendement\/risque/)).toBeInTheDocument()
    expect(screen.getByText(/marge de sécurité raisonnable/)).toBeInTheDocument()
  })
})
