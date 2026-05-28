import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MungerSection } from '../components/MungerSection'
import type { MungerOutput } from '../types'

const BASE_MUNGER: MungerOutput = {
  ticker: 'TSLA',
  biais_detectes: [
    { nom: 'Overconfidence', description: 'Hypothèses de croissance trop optimistes', impact_sur_these: 'MAJEUR' },
    { nom: 'Social Proof', description: 'Consensus haussier du marché', impact_sur_these: 'MODERE' },
  ],
  inversion_analysis: "La thèse échoue si la concurrence érode les marges plus vite que prévu.",
  lollapalooza_risk: true,
  verdict_comportemental: 'BIAIS_DETECTE',
  verdict_detail: 'Plusieurs biais amplificateurs présents — prudence requise.',
  recommandation_prochaine_etape: ['Stress-tester le scénario bear', 'Réduire la taille de position'],
  citations: [],
  cost_usd: 0.014,
}

describe('MungerSection', () => {
  it('affiche le verdict comportemental et toggle fermé par défaut', () => {
    render(<MungerSection output={BASE_MUNGER} />)
    expect(screen.getByTestId('munger-verdict')).toHaveTextContent('BIAIS_DETECTE')
    expect(screen.queryByTestId('munger-biais-list')).not.toBeInTheDocument()
  })

  it('affiche le badge lollapalooza quand le risque existe', () => {
    render(<MungerSection output={BASE_MUNGER} />)
    expect(screen.getByTestId('munger-lollapalooza')).toBeInTheDocument()
  })

  it('masque le badge lollapalooza quand le risque est absent', () => {
    const output = { ...BASE_MUNGER, lollapalooza_risk: false }
    render(<MungerSection output={output} />)
    expect(screen.queryByTestId('munger-lollapalooza')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche les biais détectés', async () => {
    const user = userEvent.setup()
    render(<MungerSection output={BASE_MUNGER} />)

    await user.click(screen.getByTestId('munger-toggle'))

    const list = screen.getByTestId('munger-biais-list')
    expect(within(list).getAllByTestId('munger-biais')).toHaveLength(2)
    expect(screen.getByText('Overconfidence')).toBeInTheDocument()
  })

  it('affiche un message quand aucun biais n\'est détecté', async () => {
    const user = userEvent.setup()
    const output = { ...BASE_MUNGER, biais_detectes: [] }
    render(<MungerSection output={output} />)

    await user.click(screen.getByTestId('munger-toggle'))

    expect(screen.getByTestId('munger-no-biais')).toBeInTheDocument()
    expect(screen.queryByTestId('munger-biais-list')).not.toBeInTheDocument()
  })

  it('affiche l\'analyse par inversion et les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<MungerSection output={BASE_MUNGER} />)

    await user.click(screen.getByTestId('munger-toggle'))

    expect(screen.getByTestId('munger-inversion')).toHaveTextContent(/érode les marges/)
    expect(screen.getByTestId('munger-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Stress-tester le scénario bear/)).toBeInTheDocument()
  })
})
