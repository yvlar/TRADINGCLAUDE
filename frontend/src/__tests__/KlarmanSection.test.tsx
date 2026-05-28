import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { KlarmanSection } from '../components/KlarmanSection'
import type { KlarmanOutput } from '../types'

const BASE_KLARMAN: KlarmanOutput = {
  ticker: 'BBD-B.TO',
  situation_type_qualifie: 'DISTRESSED',
  marge_securite_score: 7,
  preservation_capital_score: 5,
  discount_to_intrinsic: 0.35,
  verdict: 'OPPORTUNITE_FORTE',
  verdict_detail: 'Décote significative avec catalyseur de désendettement identifié.',
  recommandation_prochaine_etape: ['Analyser la structure de dette', 'Évaluer le calendrier du catalyseur'],
  citations: [],
  cost_usd: 0.013,
}

describe('KlarmanSection', () => {
  it('affiche le type de situation, le verdict et toggle fermé par défaut', () => {
    render(<KlarmanSection output={BASE_KLARMAN} />)
    expect(screen.getByTestId('klarman-situation')).toHaveTextContent('En détresse')
    expect(screen.getByTestId('klarman-verdict')).toHaveTextContent('OPPORTUNITE_FORTE')
    expect(screen.queryByTestId('klarman-marge-score')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche la décote vs valeur intrinsèque', async () => {
    const user = userEvent.setup()
    render(<KlarmanSection output={BASE_KLARMAN} />)

    await user.click(screen.getByTestId('klarman-toggle'))

    expect(screen.getByTestId('klarman-discount')).toHaveTextContent('35.0%')
  })

  it('masque la décote quand elle est null', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_KLARMAN, discount_to_intrinsic: null }
    render(<KlarmanSection output={output} />)

    await user.click(screen.getByTestId('klarman-toggle'))

    expect(screen.queryByTestId('klarman-discount')).not.toBeInTheDocument()
  })

  it('affiche les deux scores 0-10 une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<KlarmanSection output={BASE_KLARMAN} />)

    await user.click(screen.getByTestId('klarman-toggle'))

    expect(screen.getByTestId('klarman-marge-score')).toHaveTextContent('7/10')
    expect(screen.getByTestId('klarman-preservation-score')).toHaveTextContent('5/10')
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<KlarmanSection output={BASE_KLARMAN} />)

    await user.click(screen.getByTestId('klarman-toggle'))

    expect(screen.getByTestId('klarman-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/structure de dette/)).toBeInTheDocument()
  })

  it('affiche le libellé brut pour un type de situation inconnu', () => {
    const output = { ...BASE_KLARMAN, situation_type_qualifie: 'NET_NET' }
    render(<KlarmanSection output={output} />)
    expect(screen.getByTestId('klarman-situation')).toHaveTextContent('Net-net')
  })
})
