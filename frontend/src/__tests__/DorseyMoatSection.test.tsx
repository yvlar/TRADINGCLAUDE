import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DorseyMoatSection } from '../components/DorseyMoatSection'
import type { DorseyMoatOutput } from '../types'

const BASE_DORSEY: DorseyMoatOutput = {
  ticker: 'CNR.TO',
  moat_type: 'WIDE',
  sources_identifiees: [
    { source: 'intangibles', present: false, intensite: 'FAIBLE', justification: 'Marque peu différenciante' },
    { source: 'switching_costs', present: true, intensite: 'MODÉRÉE', justification: 'Contrats long terme' },
    { source: 'network_effects', present: false, intensite: 'ABSENTE', justification: 'Pas d\'effet réseau' },
    { source: 'cost_advantages', present: true, intensite: 'FORTE', justification: 'Densité du réseau ferroviaire' },
    { source: 'efficient_scale', present: true, intensite: 'FORTE', justification: 'Duopole ferroviaire nord-américain' },
  ],
  roic_durability: 'FORTE',
  verdict_detail: 'Avantage concurrentiel large soutenu par l\'échelle efficiente.',
  drapeaux_rouges: ['Cyclicité du fret'],
  recommandation_prochaine_etape: ['Suivre les volumes intermodaux', 'Comparer ROIC avec CP'],
  citations: [],
  cost_usd: 0.015,
  confidence_score: 0.92,
}

describe('DorseyMoatSection', () => {
  it('affiche le type de moat et le toggle fermé par défaut', () => {
    render(<DorseyMoatSection output={BASE_DORSEY} />)
    expect(screen.getByTestId('dorsey-moat-type')).toHaveTextContent('WIDE')
    expect(screen.queryByTestId('dorsey-sources')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche les 5 sources d\'avantage', async () => {
    const user = userEvent.setup()
    render(<DorseyMoatSection output={BASE_DORSEY} />)

    await user.click(screen.getByTestId('dorsey-toggle'))

    const sources = screen.getByTestId('dorsey-sources')
    expect(within(sources).getByTestId('moat-source-efficient_scale')).toBeInTheDocument()
    expect(within(sources).getByTestId('moat-source-cost_advantages')).toBeInTheDocument()
    expect(within(sources).getAllByText(/✓|✗/).length).toBe(5)
  })

  it('affiche la durabilité du ROIC une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<DorseyMoatSection output={BASE_DORSEY} />)

    await user.click(screen.getByTestId('dorsey-toggle'))

    expect(screen.getByTestId('dorsey-durability')).toHaveTextContent('FORTE')
  })

  it('affiche les drapeaux rouges une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<DorseyMoatSection output={BASE_DORSEY} />)

    await user.click(screen.getByTestId('dorsey-toggle'))

    expect(screen.getByTestId('dorsey-red-flags')).toBeInTheDocument()
    expect(screen.getByText(/Cyclicité du fret/)).toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<DorseyMoatSection output={BASE_DORSEY} />)

    await user.click(screen.getByTestId('dorsey-toggle'))

    expect(screen.getByTestId('dorsey-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/volumes intermodaux/)).toBeInTheDocument()
  })

  it('masque les drapeaux rouges quand la liste est vide', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_DORSEY, drapeaux_rouges: [] }
    render(<DorseyMoatSection output={output} />)

    await user.click(screen.getByTestId('dorsey-toggle'))

    expect(screen.queryByTestId('dorsey-red-flags')).not.toBeInTheDocument()
  })
})
