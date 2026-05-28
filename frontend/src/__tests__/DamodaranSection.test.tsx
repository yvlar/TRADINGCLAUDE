import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DamodaranSection } from '../components/DamodaranSection'
import type { DamodaranOutput } from '../types'

const BASE_DAMODARAN: DamodaranOutput = {
  ticker: 'SHOP.TO',
  test_coherence: 'PLAUSIBLE',
  erp_implied: 0.058,
  narrative_strength: 7,
  divergences_detectees: ['Marge cible vs marge historique', 'TAM optimiste'],
  verdict: 'NARRATIVE_ACCEPTABLE',
  verdict_detail: 'La narrative tient si la croissance reste au-dessus de 25 % cinq ans.',
  recommandation_prochaine_etape: ['Stress-tester le taux de croissance', 'Comparer aux comparables SaaS'],
  citations: [],
  cost_usd: 0.012,
}

describe('DamodaranSection', () => {
  it('affiche le test de cohérence, le verdict et reste fermé par défaut', () => {
    render(<DamodaranSection output={BASE_DAMODARAN} />)
    expect(screen.getByTestId('damodaran-coherence')).toHaveTextContent('Plausible')
    expect(screen.getByTestId('damodaran-verdict')).toHaveTextContent('NARRATIVE_ACCEPTABLE')
    expect(screen.queryByTestId('damodaran-ladder')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche l\'échelle possible/plausible/probable', async () => {
    const user = userEvent.setup()
    render(<DamodaranSection output={BASE_DAMODARAN} />)

    await user.click(screen.getByTestId('damodaran-toggle'))

    const ladder = screen.getByTestId('damodaran-ladder')
    expect(ladder).toHaveTextContent('Possible')
    expect(ladder).toHaveTextContent('Plausible')
    expect(ladder).toHaveTextContent('Probable')
  })

  it('affiche la solidité de la narrative /10 et l\'ERP implicite', async () => {
    const user = userEvent.setup()
    render(<DamodaranSection output={BASE_DAMODARAN} />)

    await user.click(screen.getByTestId('damodaran-toggle'))

    expect(screen.getByTestId('damodaran-strength')).toHaveTextContent('7/10')
    expect(screen.getByTestId('damodaran-erp')).toHaveTextContent('5.8%')
  })

  it('masque l\'ERP quand il est null', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_DAMODARAN, erp_implied: null }
    render(<DamodaranSection output={output} />)

    await user.click(screen.getByTestId('damodaran-toggle'))

    expect(screen.queryByTestId('damodaran-erp')).not.toBeInTheDocument()
  })

  it('affiche les divergences détectées une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<DamodaranSection output={BASE_DAMODARAN} />)

    await user.click(screen.getByTestId('damodaran-toggle'))

    expect(screen.getByTestId('damodaran-divergences')).toBeInTheDocument()
    expect(screen.getByText(/TAM optimiste/)).toBeInTheDocument()
  })

  it('affiche l\'état incohérent quand le test échoue', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_DAMODARAN, test_coherence: 'INCOHERENT' }
    render(<DamodaranSection output={output} />)

    expect(screen.getByTestId('damodaran-coherence')).toHaveTextContent('Incohérent')
    await user.click(screen.getByTestId('damodaran-toggle'))
    expect(screen.getByTestId('damodaran-ladder')).toHaveTextContent('Incohérent')
  })
})
